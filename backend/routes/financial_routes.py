import re
from datetime import date, datetime
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

financial_bp = Blueprint("finance", __name__, url_prefix="/api/finance")

VALID_EXPENSE_CATEGORIES = [
    "Seeds",
    "Fertilizers",
    "Pesticides",
    "Labour",
    "Irrigation and electricity",
    "Machinery and equipment",
    "Transportation",
    "Other expenses"
]

CATEGORY_LOOKUP = {
    "seeds": "Seeds",
    "fertilizer": "Fertilizers",
    "fertilizers": "Fertilizers",
    "pesticide": "Pesticides",
    "pesticides": "Pesticides",
    "labour": "Labour",
    "labor": "Labour",
    "irrigation": "Irrigation and electricity",
    "irrigation and electricity": "Irrigation and electricity",
    "irrigation & electricity": "Irrigation and electricity",
    "electricity": "Irrigation and electricity",
    "machinery": "Machinery and equipment",
    "machinery and equipment": "Machinery and equipment",
    "machinery & equipment": "Machinery and equipment",
    "equipment": "Machinery and equipment",
    "transport": "Transportation",
    "transportation": "Transportation",
    "other": "Other expenses",
    "other expenses": "Other expenses",
    "miscellaneous": "Other expenses"
}


def _authenticate():
    """Extract and validate user ID from Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({
            "status": "error",
            "message": "Authentication required. Please log in."
        }), 401)

    token = auth_header[len("Bearer "):].strip()
    user_id = get_user_id_from_token(token)
    if user_id is None:
        return None, (jsonify({
            "status": "error",
            "message": "Invalid or expired login token. Please log in again."
        }), 401)

    return int(user_id), None


def _normalize_category(cat_str):
    if not cat_str or not isinstance(cat_str, str):
        return None
    cleaned = cat_str.strip().lower()
    return CATEGORY_LOOKUP.get(cleaned, cat_str.strip())


def _parse_date(val):
    if not val:
        return None
    if isinstance(val, (date, datetime)):
        return val.strftime("%Y-%m-%d") if isinstance(val, date) else val.date().strftime("%Y-%m-%d")
    s = str(val).strip()
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _get_season_for_date(date_val):
    """Determine Indian crop season (Kharif, Rabi, Zaid) for a given date."""
    if not date_val:
        return "Unknown"
    if isinstance(date_val, str):
        try:
            date_val = datetime.strptime(date_val, "%Y-%m-%d").date()
        except ValueError:
            return "Unknown"
    month = date_val.month
    year = date_val.year
    if 6 <= month <= 10:
        return f"Kharif {year}"
    elif month in (11, 12):
        return f"Rabi {year}-{year+1}"
    elif month in (1, 2, 3):
        return f"Rabi {year-1}-{year}"
    else:  # 4, 5
        return f"Zaid {year}"


# =============================================================================
# CONTEXT: CROPS & FARMS FOR DROPDOWNS
# =============================================================================

@financial_bp.route("/context-crops", methods=["GET"])
def get_context_crops():
    """Retrieve registered crops and farms for the authenticated farmer."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT id, crop_name, variety, farm_id, field_location, planting_date
            FROM crops
            WHERE user_id = %s
            ORDER BY planting_date DESC, id DESC
        """, (user_id,))
        crops = cur.fetchall() or []

        cur.execute("""
            SELECT id, farm_name, location
            FROM farms
            WHERE user_id = %s
            ORDER BY id ASC
        """, (user_id,))
        farms = cur.fetchall() or []

        return jsonify({
            "status": "success",
            "crops": [
                {
                    "id": c["id"],
                    "crop_name": c["crop_name"],
                    "variety": c.get("variety") or "",
                    "farm_id": c.get("farm_id"),
                    "field_location": c.get("field_location") or "",
                    "planting_date": str(c["planting_date"]) if c.get("planting_date") else None
                } for c in crops
            ],
            "farms": [
                {
                    "id": f["id"],
                    "farm_name": f["farm_name"],
                    "location": f.get("location") or ""
                } for f in farms
            ],
            "categories": VALID_EXPENSE_CATEGORIES
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =============================================================================
# EXPENSE MANAGEMENT CRUD
# =============================================================================

@financial_bp.route("/expenses", methods=["GET"])
def list_expenses():
    """List farm expenses for the authenticated farmer with optional filtering."""
    user_id, err = _authenticate()
    if err:
        return err

    crop_id = request.args.get("crop_id")
    category = request.args.get("category")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    offset = max(int(request.args.get("offset", 0)), 0)

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        query = """
            SELECT e.id, e.user_id, e.farm_id, e.crop_id, e.crop_name, e.category,
                   e.amount, e.expense_date, e.quantity, e.unit, e.description, e.notes,
                   e.created_at, e.updated_at,
                   f.farm_name, c.variety
            FROM farm_expenses e
            LEFT JOIN farms f ON f.id = e.farm_id
            LEFT JOIN crops c ON c.id = e.crop_id
            WHERE e.user_id = %s
        """
        params = [user_id]

        if crop_id:
            query += " AND e.crop_id = %s"
            params.append(crop_id)

        if category and category.lower() != "all":
            norm_cat = _normalize_category(category)
            query += " AND e.category = %s"
            params.append(norm_cat)

        if start_date:
            parsed_start = _parse_date(start_date)
            if parsed_start:
                query += " AND e.expense_date >= %s"
                params.append(parsed_start)

        if end_date:
            parsed_end = _parse_date(end_date)
            if parsed_end:
                query += " AND e.expense_date <= %s"
                params.append(parsed_end)

        query += " ORDER BY e.expense_date DESC, e.id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, tuple(params))
        rows = cur.fetchall() or []

        # Count total records & total amount for these filters
        count_q = """
            SELECT COUNT(*) AS total_count, COALESCE(SUM(amount), 0) AS total_amount
            FROM farm_expenses e
            WHERE e.user_id = %s
        """
        count_params = [user_id]
        if crop_id:
            count_q += " AND e.crop_id = %s"
            count_params.append(crop_id)
        if category and category.lower() != "all":
            count_q += " AND e.category = %s"
            count_params.append(_normalize_category(category))
        if start_date and _parse_date(start_date):
            count_q += " AND e.expense_date >= %s"
            count_params.append(_parse_date(start_date))
        if end_date and _parse_date(end_date):
            count_q += " AND e.expense_date <= %s"
            count_params.append(_parse_date(end_date))

        cur.execute(count_q, tuple(count_params))
        totals = cur.fetchone() or {"total_count": 0, "total_amount": 0.0}

        expenses = []
        for r in rows:
            expenses.append({
                "id": r["id"],
                "farm_id": r.get("farm_id"),
                "farm_name": r.get("farm_name") or "",
                "crop_id": r.get("crop_id"),
                "crop_name": r.get("crop_name") or "",
                "variety": r.get("variety") or "",
                "category": r["category"],
                "amount": float(r["amount"]),
                "expense_date": str(r["expense_date"]),
                "quantity": float(r["quantity"]) if r.get("quantity") is not None else None,
                "unit": r.get("unit") or "",
                "description": r.get("description") or "",
                "notes": r.get("notes") or "",
                "season": _get_season_for_date(r["expense_date"]),
                "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else None
            })

        return jsonify({
            "status": "success",
            "expenses": expenses,
            "total_count": int(totals["total_count"]),
            "total_amount": float(totals["total_amount"])
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@financial_bp.route("/expenses", methods=["POST"])
def create_expense():
    """Record a new farm expense."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    raw_amount = data.get("amount")
    try:
        amount = float(raw_amount)
        if amount <= 0:
            return jsonify({"status": "error", "message": "Expense amount must be greater than 0."}), 400
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Valid positive expense amount in INR (₹) is required."}), 400

    raw_cat = data.get("category", "")
    category = _normalize_category(raw_cat)
    if not category:
        return jsonify({
            "status": "error",
            "message": f"Expense category is required. Valid categories: {', '.join(VALID_EXPENSE_CATEGORIES)}"
        }), 400

    raw_date = data.get("expense_date")
    expense_date = _parse_date(raw_date)
    if not expense_date:
        return jsonify({"status": "error", "message": "Valid expense date (YYYY-MM-DD) is required."}), 400

    crop_id = data.get("crop_id")
    crop_name = str(data.get("crop_name", "")).strip() or None
    farm_id = data.get("farm_id")

    quantity = None
    if data.get("quantity") not in (None, ""):
        try:
            quantity = float(data.get("quantity"))
            if quantity < 0:
                return jsonify({"status": "error", "message": "Quantity cannot be negative."}), 400
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "Invalid numeric quantity provided."}), 400

    unit = str(data.get("unit", "")).strip() or None
    description = str(data.get("description", "")).strip() or None
    notes = str(data.get("notes", "")).strip() or None

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Validate crop belongs to user if crop_id provided
        if crop_id:
            cur.execute("SELECT id, crop_name, farm_id FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
            crop_row = cur.fetchone()
            if not crop_row:
                return jsonify({"status": "error", "message": "Selected crop does not belong to your account."}), 403
            crop_name = crop_row["crop_name"]
            if not farm_id and crop_row.get("farm_id"):
                farm_id = crop_row["farm_id"]

        # Validate farm belongs to user if farm_id provided
        if farm_id:
            cur.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
            if not cur.fetchone():
                return jsonify({"status": "error", "message": "Selected farm does not belong to your account."}), 403

        cur.execute("""
            INSERT INTO farm_expenses (user_id, farm_id, crop_id, crop_name, category, amount, expense_date, quantity, unit, description, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, farm_id, crop_id, crop_name, category, amount, expense_date, quantity, unit, description, notes))
        conn.commit()

        new_id = cur.lastrowid

        return jsonify({
            "status": "success",
            "message": "Expense recorded successfully.",
            "expense": {
                "id": new_id,
                "user_id": user_id,
                "farm_id": farm_id,
                "crop_id": crop_id,
                "crop_name": crop_name,
                "category": category,
                "amount": amount,
                "expense_date": expense_date,
                "quantity": quantity,
                "unit": unit,
                "description": description,
                "notes": notes,
                "season": _get_season_for_date(expense_date)
            }
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@financial_bp.route("/expenses/<int:expense_id>", methods=["GET"])
def get_expense(expense_id):
    """Retrieve single farm expense."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT e.*, f.farm_name, c.variety
            FROM farm_expenses e
            LEFT JOIN farms f ON f.id = e.farm_id
            LEFT JOIN crops c ON c.id = e.crop_id
            WHERE e.id = %s AND e.user_id = %s
        """, (expense_id, user_id))
        row = cur.fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Expense not found."}), 404

        return jsonify({
            "status": "success",
            "expense": {
                "id": row["id"],
                "farm_id": row.get("farm_id"),
                "farm_name": row.get("farm_name") or "",
                "crop_id": row.get("crop_id"),
                "crop_name": row.get("crop_name") or "",
                "variety": row.get("variety") or "",
                "category": row["category"],
                "amount": float(row["amount"]),
                "expense_date": str(row["expense_date"]),
                "quantity": float(row["quantity"]) if row.get("quantity") is not None else None,
                "unit": row.get("unit") or "",
                "description": row.get("description") or "",
                "notes": row.get("notes") or "",
                "season": _get_season_for_date(row["expense_date"])
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@financial_bp.route("/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    """Update an existing farm expense."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id FROM farm_expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
        if not cur.fetchone():
            return jsonify({"status": "error", "message": "Expense not found."}), 404

        raw_amount = data.get("amount")
        try:
            amount = float(raw_amount)
            if amount <= 0:
                return jsonify({"status": "error", "message": "Expense amount must be greater than 0."}), 400
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "Valid positive expense amount in INR (₹) is required."}), 400

        category = _normalize_category(data.get("category", ""))
        if not category:
            return jsonify({"status": "error", "message": "Valid expense category is required."}), 400

        expense_date = _parse_date(data.get("expense_date"))
        if not expense_date:
            return jsonify({"status": "error", "message": "Valid expense date (YYYY-MM-DD) is required."}), 400

        crop_id = data.get("crop_id")
        crop_name = str(data.get("crop_name", "")).strip() or None
        farm_id = data.get("farm_id")

        quantity = None
        if data.get("quantity") not in (None, ""):
            try:
                quantity = float(data.get("quantity"))
                if quantity < 0:
                    return jsonify({"status": "error", "message": "Quantity cannot be negative."}), 400
            except (TypeError, ValueError):
                return jsonify({"status": "error", "message": "Invalid numeric quantity provided."}), 400

        unit = str(data.get("unit", "")).strip() or None
        description = str(data.get("description", "")).strip() or None
        notes = str(data.get("notes", "")).strip() or None

        if crop_id:
            cur.execute("SELECT id, crop_name, farm_id FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
            crop_row = cur.fetchone()
            if not crop_row:
                return jsonify({"status": "error", "message": "Selected crop does not belong to your account."}), 403
            crop_name = crop_row["crop_name"]
            if not farm_id and crop_row.get("farm_id"):
                farm_id = crop_row["farm_id"]

        if farm_id:
            cur.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
            if not cur.fetchone():
                return jsonify({"status": "error", "message": "Selected farm does not belong to your account."}), 403

        cur.execute("""
            UPDATE farm_expenses
            SET farm_id = %s, crop_id = %s, crop_name = %s, category = %s,
                amount = %s, expense_date = %s, quantity = %s, unit = %s,
                description = %s, notes = %s
            WHERE id = %s AND user_id = %s
        """, (farm_id, crop_id, crop_name, category, amount, expense_date, quantity, unit, description, notes, expense_id, user_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Expense updated successfully.",
            "expense": {
                "id": expense_id,
                "farm_id": farm_id,
                "crop_id": crop_id,
                "crop_name": crop_name,
                "category": category,
                "amount": amount,
                "expense_date": expense_date,
                "quantity": quantity,
                "unit": unit,
                "description": description,
                "notes": notes,
                "season": _get_season_for_date(expense_date)
            }
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@financial_bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    """Delete single farm expense."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id FROM farm_expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
        if not cur.fetchone():
            return jsonify({"status": "error", "message": "Expense not found."}), 404

        cur.execute("DELETE FROM farm_expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Expense deleted successfully."
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =============================================================================
# HARVEST & REVENUE MANAGEMENT CRUD
# =============================================================================

@financial_bp.route("/harvests", methods=["GET"])
def list_harvests():
    """List farm harvest and sales records for the authenticated farmer."""
    user_id, err = _authenticate()
    if err:
        return err

    crop_id = request.args.get("crop_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    offset = max(int(request.args.get("offset", 0)), 0)

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        query = """
            SELECT h.id, h.user_id, h.farm_id, h.crop_id, h.crop_name, h.harvest_date,
                   h.quantity, h.unit, h.price_per_unit, h.total_revenue, h.buyer_name, h.notes,
                   h.created_at, h.updated_at,
                   f.farm_name, c.variety
            FROM farm_harvests h
            LEFT JOIN farms f ON f.id = h.farm_id
            LEFT JOIN crops c ON c.id = h.crop_id
            WHERE h.user_id = %s
        """
        params = [user_id]

        if crop_id:
            query += " AND h.crop_id = %s"
            params.append(crop_id)

        if start_date:
            parsed_start = _parse_date(start_date)
            if parsed_start:
                query += " AND h.harvest_date >= %s"
                params.append(parsed_start)

        if end_date:
            parsed_end = _parse_date(end_date)
            if parsed_end:
                query += " AND h.harvest_date <= %s"
                params.append(parsed_end)

        query += " ORDER BY h.harvest_date DESC, h.id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, tuple(params))
        rows = cur.fetchall() or []

        # Totals
        count_q = """
            SELECT COUNT(*) AS total_count,
                   COALESCE(SUM(total_revenue), 0) AS total_revenue,
                   COALESCE(SUM(quantity), 0) AS total_quantity
            FROM farm_harvests h
            WHERE h.user_id = %s
        """
        count_params = [user_id]
        if crop_id:
            count_q += " AND h.crop_id = %s"
            count_params.append(crop_id)
        if start_date and _parse_date(start_date):
            count_q += " AND h.harvest_date >= %s"
            count_params.append(_parse_date(start_date))
        if end_date and _parse_date(end_date):
            count_q += " AND h.harvest_date <= %s"
            count_params.append(_parse_date(end_date))

        cur.execute(count_q, tuple(count_params))
        totals = cur.fetchone() or {"total_count": 0, "total_revenue": 0.0, "total_quantity": 0.0}

        harvests = []
        for r in rows:
            harvests.append({
                "id": r["id"],
                "farm_id": r.get("farm_id"),
                "farm_name": r.get("farm_name") or "",
                "crop_id": r.get("crop_id"),
                "crop_name": r["crop_name"],
                "variety": r.get("variety") or "",
                "harvest_date": str(r["harvest_date"]),
                "quantity": float(r["quantity"]),
                "unit": r["unit"],
                "price_per_unit": float(r["price_per_unit"]),
                "total_revenue": float(r["total_revenue"]),
                "buyer_name": r.get("buyer_name") or "",
                "notes": r.get("notes") or "",
                "season": _get_season_for_date(r["harvest_date"]),
                "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else None
            })

        return jsonify({
            "status": "success",
            "harvests": harvests,
            "total_count": int(totals["total_count"]),
            "total_revenue": float(totals["total_revenue"]),
            "total_quantity": float(totals["total_quantity"])
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@financial_bp.route("/harvests", methods=["POST"])
def create_harvest():
    """Record an actual crop harvest and sales income."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    crop_name = str(data.get("crop_name", "")).strip()
    crop_id = data.get("crop_id")
    farm_id = data.get("farm_id")

    harvest_date = _parse_date(data.get("harvest_date"))
    if not harvest_date:
        return jsonify({"status": "error", "message": "Valid harvest date (YYYY-MM-DD) is required."}), 400

    try:
        quantity = float(data.get("quantity"))
        if quantity <= 0:
            return jsonify({"status": "error", "message": "Harvest quantity must be greater than 0."}), 400
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Valid positive harvest quantity is required."}), 400

    unit = str(data.get("unit", "")).strip()
    if not unit:
        return jsonify({"status": "error", "message": "Harvest unit (e.g. kg, quintals, tons) is required."}), 400

    try:
        price_per_unit = float(data.get("price_per_unit"))
        if price_per_unit < 0:
            return jsonify({"status": "error", "message": "Selling price per unit cannot be negative."}), 400
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Valid price per unit in INR (₹) is required."}), 400

    # Calculate revenue = quantity * price_per_unit
    raw_rev = data.get("total_revenue")
    if raw_rev is not None and str(raw_rev).strip() != "":
        try:
            total_revenue = round(float(raw_rev), 2)
            if total_revenue < 0:
                return jsonify({"status": "error", "message": "Total revenue cannot be negative."}), 400
        except (TypeError, ValueError):
            total_revenue = round(quantity * price_per_unit, 2)
    else:
        total_revenue = round(quantity * price_per_unit, 2)

    buyer_name = str(data.get("buyer_name", "")).strip() or None
    notes = str(data.get("notes", "")).strip() or None

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        if crop_id:
            cur.execute("SELECT id, crop_name, farm_id FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
            crop_row = cur.fetchone()
            if not crop_row:
                return jsonify({"status": "error", "message": "Selected crop does not belong to your account."}), 403
            crop_name = crop_row["crop_name"]
            if not farm_id and crop_row.get("farm_id"):
                farm_id = crop_row["farm_id"]

        if not crop_name:
            return jsonify({"status": "error", "message": "Crop name is required."}), 400

        if farm_id:
            cur.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
            if not cur.fetchone():
                return jsonify({"status": "error", "message": "Selected farm does not belong to your account."}), 403

        cur.execute("""
            INSERT INTO farm_harvests (user_id, farm_id, crop_id, crop_name, harvest_date, quantity, unit, price_per_unit, total_revenue, buyer_name, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, farm_id, crop_id, crop_name, harvest_date, quantity, unit, price_per_unit, total_revenue, buyer_name, notes))
        conn.commit()

        new_id = cur.lastrowid

        return jsonify({
            "status": "success",
            "message": "Harvest and sales recorded successfully.",
            "harvest": {
                "id": new_id,
                "user_id": user_id,
                "farm_id": farm_id,
                "crop_id": crop_id,
                "crop_name": crop_name,
                "harvest_date": harvest_date,
                "quantity": quantity,
                "unit": unit,
                "price_per_unit": price_per_unit,
                "total_revenue": total_revenue,
                "buyer_name": buyer_name,
                "notes": notes,
                "season": _get_season_for_date(harvest_date)
            }
        }), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@financial_bp.route("/harvests/<int:harvest_id>", methods=["GET"])
def get_harvest(harvest_id):
    """Retrieve single harvest record."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT h.*, f.farm_name, c.variety
            FROM farm_harvests h
            LEFT JOIN farms f ON f.id = h.farm_id
            LEFT JOIN crops c ON c.id = h.crop_id
            WHERE h.id = %s AND h.user_id = %s
        """, (harvest_id, user_id))
        row = cur.fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Harvest record not found."}), 404

        return jsonify({
            "status": "success",
            "harvest": {
                "id": row["id"],
                "farm_id": row.get("farm_id"),
                "farm_name": row.get("farm_name") or "",
                "crop_id": row.get("crop_id"),
                "crop_name": row["crop_name"],
                "variety": row.get("variety") or "",
                "harvest_date": str(row["harvest_date"]),
                "quantity": float(row["quantity"]),
                "unit": row["unit"],
                "price_per_unit": float(row["price_per_unit"]),
                "total_revenue": float(row["total_revenue"]),
                "buyer_name": row.get("buyer_name") or "",
                "notes": row.get("notes") or "",
                "season": _get_season_for_date(row["harvest_date"])
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@financial_bp.route("/harvests/<int:harvest_id>", methods=["PUT"])
def update_harvest(harvest_id):
    """Update harvest and sales record."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id FROM farm_harvests WHERE id = %s AND user_id = %s", (harvest_id, user_id))
        if not cur.fetchone():
            return jsonify({"status": "error", "message": "Harvest record not found."}), 404

        crop_name = str(data.get("crop_name", "")).strip()
        crop_id = data.get("crop_id")
        farm_id = data.get("farm_id")

        harvest_date = _parse_date(data.get("harvest_date"))
        if not harvest_date:
            return jsonify({"status": "error", "message": "Valid harvest date (YYYY-MM-DD) is required."}), 400

        try:
            quantity = float(data.get("quantity"))
            if quantity <= 0:
                return jsonify({"status": "error", "message": "Harvest quantity must be greater than 0."}), 400
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "Valid positive harvest quantity is required."}), 400

        unit = str(data.get("unit", "")).strip()
        if not unit:
            return jsonify({"status": "error", "message": "Harvest unit is required."}), 400

        try:
            price_per_unit = float(data.get("price_per_unit"))
            if price_per_unit < 0:
                return jsonify({"status": "error", "message": "Price per unit cannot be negative."}), 400
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "Valid price per unit is required."}), 400

        raw_rev = data.get("total_revenue")
        if raw_rev is not None and str(raw_rev).strip() != "":
            try:
                total_revenue = round(float(raw_rev), 2)
                if total_revenue < 0:
                    return jsonify({"status": "error", "message": "Total revenue cannot be negative."}), 400
            except (TypeError, ValueError):
                total_revenue = round(quantity * price_per_unit, 2)
        else:
            total_revenue = round(quantity * price_per_unit, 2)

        buyer_name = str(data.get("buyer_name", "")).strip() or None
        notes = str(data.get("notes", "")).strip() or None

        if crop_id:
            cur.execute("SELECT id, crop_name, farm_id FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
            crop_row = cur.fetchone()
            if not crop_row:
                return jsonify({"status": "error", "message": "Selected crop does not belong to your account."}), 403
            crop_name = crop_row["crop_name"]
            if not farm_id and crop_row.get("farm_id"):
                farm_id = crop_row["farm_id"]

        if not crop_name:
            return jsonify({"status": "error", "message": "Crop name is required."}), 400

        if farm_id:
            cur.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
            if not cur.fetchone():
                return jsonify({"status": "error", "message": "Selected farm does not belong to your account."}), 403

        cur.execute("""
            UPDATE farm_harvests
            SET farm_id = %s, crop_id = %s, crop_name = %s, harvest_date = %s,
                quantity = %s, unit = %s, price_per_unit = %s, total_revenue = %s,
                buyer_name = %s, notes = %s
            WHERE id = %s AND user_id = %s
        """, (farm_id, crop_id, crop_name, harvest_date, quantity, unit, price_per_unit, total_revenue, buyer_name, notes, harvest_id, user_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Harvest record updated successfully.",
            "harvest": {
                "id": harvest_id,
                "farm_id": farm_id,
                "crop_id": crop_id,
                "crop_name": crop_name,
                "harvest_date": harvest_date,
                "quantity": quantity,
                "unit": unit,
                "price_per_unit": price_per_unit,
                "total_revenue": total_revenue,
                "buyer_name": buyer_name,
                "notes": notes,
                "season": _get_season_for_date(harvest_date)
            }
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@financial_bp.route("/harvests/<int:harvest_id>", methods=["DELETE"])
def delete_harvest(harvest_id):
    """Delete harvest record."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT id FROM farm_harvests WHERE id = %s AND user_id = %s", (harvest_id, user_id))
        if not cur.fetchone():
            return jsonify({"status": "error", "message": "Harvest record not found."}), 404

        cur.execute("DELETE FROM farm_harvests WHERE id = %s AND user_id = %s", (harvest_id, user_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Harvest record deleted successfully."
        }), 200
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =============================================================================
# SMART FINANCIAL CALCULATIONS & OVERVIEW
# =============================================================================

@financial_bp.route("/summary", methods=["GET"])
def get_financial_summary():
    """
    Computes real-time farm financial summary:
    - Total expenses (sum of actual recorded expenses)
    - Total revenue (sum of actual recorded harvest sales)
    - Net profit/loss = Total revenue - Total expenses
    - Profit margin % = (Net profit / Total revenue) * 100
    - Category cost breakdown
    - Crop-wise profitability
    - Monthly financial trends
    - Season-wise financial summary
    """
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # 1. Total expenses
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total_expenses, COUNT(*) AS count_expenses
            FROM farm_expenses
            WHERE user_id = %s
        """, (user_id,))
        exp_row = cur.fetchone() or {"total_expenses": 0.0, "count_expenses": 0}
        total_expenses = float(exp_row["total_expenses"] or 0.0)
        count_expenses = int(exp_row["count_expenses"] or 0)

        # 2. Total revenue
        cur.execute("""
            SELECT COALESCE(SUM(total_revenue), 0) AS total_revenue,
                   COALESCE(SUM(quantity), 0) AS total_harvested,
                   COUNT(*) AS count_harvests
            FROM farm_harvests
            WHERE user_id = %s
        """, (user_id,))
        harv_row = cur.fetchone() or {"total_revenue": 0.0, "total_harvested": 0.0, "count_harvests": 0}
        total_revenue = float(harv_row["total_revenue"] or 0.0)
        count_harvests = int(harv_row["count_harvests"] or 0)
        total_harvested_qty = float(harv_row["total_harvested"] or 0.0)

        # 3. Net profit & Profit margin
        net_profit = round(total_revenue - total_expenses, 2)
        profit_margin = round((net_profit / total_revenue) * 100, 2) if total_revenue > 0 else 0.0
        is_profitable = net_profit >= 0

        # 4. Category breakdown
        cur.execute("""
            SELECT category, COALESCE(SUM(amount), 0) AS category_total, COUNT(*) AS items_count
            FROM farm_expenses
            WHERE user_id = %s
            GROUP BY category
            ORDER BY category_total DESC
        """, (user_id,))
        cat_rows = cur.fetchall() or []
        category_breakdown = []
        for r in cat_rows:
            c_amt = float(r["category_total"])
            pct = round((c_amt / total_expenses) * 100, 1) if total_expenses > 0 else 0.0
            category_breakdown.append({
                "category": r["category"],
                "total_amount": c_amt,
                "percentage": pct,
                "items_count": int(r["items_count"])
            })

        # 5. Crop-wise profitability
        # Fetch expenses by crop
        cur.execute("""
            SELECT COALESCE(crop_name, 'General Farm Overhead') AS crop_name,
                   COALESCE(SUM(amount), 0) AS crop_expenses
            FROM farm_expenses
            WHERE user_id = %s
            GROUP BY COALESCE(crop_name, 'General Farm Overhead')
        """, (user_id,))
        crop_exp_map = {r["crop_name"]: float(r["crop_expenses"]) for r in (cur.fetchall() or [])}

        # Fetch revenue by crop
        cur.execute("""
            SELECT crop_name, COALESCE(SUM(total_revenue), 0) AS crop_revenue,
                   COALESCE(SUM(quantity), 0) AS crop_qty
            FROM farm_harvests
            WHERE user_id = %s
            GROUP BY crop_name
        """, (user_id,))
        crop_rev_rows = cur.fetchall() or []
        crop_rev_map = {r["crop_name"]: {"revenue": float(r["crop_revenue"]), "qty": float(r["crop_qty"])} for r in crop_rev_rows}

        all_crop_names = sorted(list(set(crop_exp_map.keys()) | set(crop_rev_map.keys())))
        crop_profitability = []
        for cname in all_crop_names:
            c_exp = crop_exp_map.get(cname, 0.0)
            c_rev_data = crop_rev_map.get(cname, {"revenue": 0.0, "qty": 0.0})
            c_rev = c_rev_data["revenue"]
            c_profit = round(c_rev - c_exp, 2)
            c_margin = round((c_profit / c_rev) * 100, 2) if c_rev > 0 else 0.0
            crop_profitability.append({
                "crop_name": cname,
                "total_expenses": c_exp,
                "total_revenue": c_rev,
                "net_profit": c_profit,
                "profit_margin": c_margin,
                "harvest_quantity": c_rev_data["qty"],
                "is_profitable": c_profit >= 0
            })
        crop_profitability.sort(key=lambda x: x["net_profit"], reverse=True)

        # 6. Monthly trends (expenses vs revenue over the last 12 months)
        cur.execute("""
            SELECT DATE_FORMAT(expense_date, '%Y-%m') AS ym,
                   COALESCE(SUM(amount), 0) AS month_expenses
            FROM farm_expenses
            WHERE user_id = %s
            GROUP BY DATE_FORMAT(expense_date, '%Y-%m')
            ORDER BY ym ASC
        """, (user_id,))
        month_exp_map = {r["ym"]: float(r["month_expenses"]) for r in (cur.fetchall() or [])}

        cur.execute("""
            SELECT DATE_FORMAT(harvest_date, '%Y-%m') AS ym,
                   COALESCE(SUM(total_revenue), 0) AS month_revenue
            FROM farm_harvests
            WHERE user_id = %s
            GROUP BY DATE_FORMAT(harvest_date, '%Y-%m')
            ORDER BY ym ASC
        """, (user_id,))
        month_rev_map = {r["ym"]: float(r["month_revenue"]) for r in (cur.fetchall() or [])}

        all_months = sorted(list(set(month_exp_map.keys()) | set(month_rev_map.keys())))
        monthly_trends = []
        for ym in all_months:
            m_exp = month_exp_map.get(ym, 0.0)
            m_rev = month_rev_map.get(ym, 0.0)
            m_profit = round(m_rev - m_exp, 2)
            monthly_trends.append({
                "month": ym,
                "expenses": m_exp,
                "revenue": m_rev,
                "net_profit": m_profit
            })

        # 7. Season-wise summary
        # Gather all expense records with dates
        cur.execute("SELECT expense_date, amount FROM farm_expenses WHERE user_id = %s", (user_id,))
        exp_all = cur.fetchall() or []
        cur.execute("SELECT harvest_date, total_revenue FROM farm_harvests WHERE user_id = %s", (user_id,))
        harv_all = cur.fetchall() or []

        seasons_data = {}
        for r in exp_all:
            s_name = _get_season_for_date(r["expense_date"])
            if s_name not in seasons_data:
                seasons_data[s_name] = {"season": s_name, "expenses": 0.0, "revenue": 0.0}
            seasons_data[s_name]["expenses"] += float(r["amount"])

        for r in harv_all:
            s_name = _get_season_for_date(r["harvest_date"])
            if s_name not in seasons_data:
                seasons_data[s_name] = {"season": s_name, "expenses": 0.0, "revenue": 0.0}
            seasons_data[s_name]["revenue"] += float(r["total_revenue"])

        seasonal_summary = []
        for s_name, s_val in seasons_data.items():
            s_exp = round(s_val["expenses"], 2)
            s_rev = round(s_val["revenue"], 2)
            s_profit = round(s_rev - s_exp, 2)
            s_margin = round((s_profit / s_rev) * 100, 2) if s_rev > 0 else 0.0
            seasonal_summary.append({
                "season": s_name,
                "expenses": s_exp,
                "revenue": s_rev,
                "net_profit": s_profit,
                "profit_margin": s_margin,
                "is_profitable": s_profit >= 0
            })
        seasonal_summary.sort(key=lambda x: x["season"], reverse=True)

        # 8. Recent 5 expenses
        cur.execute("""
            SELECT e.id, e.crop_name, e.category, e.amount, e.expense_date, e.quantity, e.unit, e.description, f.farm_name
            FROM farm_expenses e
            LEFT JOIN farms f ON f.id = e.farm_id
            WHERE e.user_id = %s
            ORDER BY e.expense_date DESC, e.id DESC
            LIMIT 5
        """, (user_id,))
        recent_exp = [
            {
                "id": r["id"],
                "crop_name": r.get("crop_name") or "",
                "farm_name": r.get("farm_name") or "",
                "category": r["category"],
                "amount": float(r["amount"]),
                "expense_date": str(r["expense_date"]),
                "description": r.get("description") or "",
                "quantity": float(r["quantity"]) if r.get("quantity") is not None else None,
                "unit": r.get("unit") or ""
            } for r in (cur.fetchall() or [])
        ]

        # 9. Recent 5 harvests
        cur.execute("""
            SELECT h.id, h.crop_name, h.harvest_date, h.quantity, h.unit, h.price_per_unit, h.total_revenue, h.buyer_name, f.farm_name
            FROM farm_harvests h
            LEFT JOIN farms f ON f.id = h.farm_id
            WHERE h.user_id = %s
            ORDER BY h.harvest_date DESC, h.id DESC
            LIMIT 5
        """, (user_id,))
        recent_harv = [
            {
                "id": r["id"],
                "crop_name": r.get("crop_name") or "",
                "farm_name": r.get("farm_name") or "",
                "harvest_date": str(r["harvest_date"]),
                "quantity": float(r.get("quantity") or 0.0),
                "unit": r.get("unit") or "",
                "price_per_unit": float(r.get("price_per_unit") or 0.0),
                "total_revenue": float(r.get("total_revenue") or 0.0),
                "buyer_name": r.get("buyer_name") or ""
            } for r in (cur.fetchall() or [])
        ]

        empty_state = (count_expenses == 0 and count_harvests == 0)

        return jsonify({
            "status": "success",
            "summary": {
                "total_expenses": total_expenses,
                "total_revenue": total_revenue,
                "net_profit": net_profit,
                "profit_margin": profit_margin,
                "is_profitable": is_profitable,
                "count_expenses": count_expenses,
                "count_harvests": count_harvests,
                "total_harvested_quantity": total_harvested_qty,
                "empty_state": empty_state
            },
            "category_breakdown": category_breakdown,
            "crop_profitability": crop_profitability,
            "monthly_trends": monthly_trends,
            "seasonal_summary": seasonal_summary,
            "recent_expenses": recent_exp,
            "recent_harvests": recent_harv
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
