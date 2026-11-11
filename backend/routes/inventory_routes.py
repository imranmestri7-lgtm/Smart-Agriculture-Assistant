from datetime import date, datetime, timedelta
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")

VALID_INVENTORY_CATEGORIES = [
    "Seeds",
    "Fertilizers",
    "Pesticides",
    "Herbicides",
    "Farming equipment",
    "Irrigation supplies",
    "Tools and machinery",
    "Other agricultural supplies"
]

CATEGORY_LOOKUP = {
    "seeds": "Seeds",
    "seed": "Seeds",
    "fertilizers": "Fertilizers",
    "fertilizer": "Fertilizers",
    "manure": "Fertilizers",
    "pesticides": "Pesticides",
    "pesticide": "Pesticides",
    "insecticide": "Pesticides",
    "fungicide": "Pesticides",
    "herbicides": "Herbicides",
    "herbicide": "Herbicides",
    "weedicide": "Herbicides",
    "farming equipment": "Farming equipment",
    "equipment": "Farming equipment",
    "irrigation supplies": "Irrigation supplies",
    "irrigation": "Irrigation supplies",
    "drip": "Irrigation supplies",
    "pipes": "Irrigation supplies",
    "tools and machinery": "Tools and machinery",
    "tools": "Tools and machinery",
    "machinery": "Tools and machinery",
    "other agricultural supplies": "Other agricultural supplies",
    "other": "Other agricultural supplies",
    "supplies": "Other agricultural supplies"
}

VALID_MOVEMENT_TYPES = [
    "Purchase / Addition",
    "Usage / Consumption",
    "Adjustment",
    "Damaged or Expired",
    "Transfer"
]

MOVEMENT_LOOKUP = {
    "purchase / addition": "Purchase / Addition",
    "purchase": "Purchase / Addition",
    "addition": "Purchase / Addition",
    "add": "Purchase / Addition",
    "usage / consumption": "Usage / Consumption",
    "usage": "Usage / Consumption",
    "consumption": "Usage / Consumption",
    "use": "Usage / Consumption",
    "consume": "Usage / Consumption",
    "adjustment": "Adjustment",
    "adjust": "Adjustment",
    "audit": "Adjustment",
    "damaged or expired": "Damaged or Expired",
    "damaged": "Damaged or Expired",
    "expired": "Damaged or Expired",
    "damage": "Damaged or Expired",
    "transfer": "Transfer"
}


def _authenticate():
    """Extract and validate user ID from Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({
            "status": "error",
            "message": "Authentication required. Please log in."
        }), 401)

    token = auth_header.split(" ", 1)[1].strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
        return None, (jsonify({
            "status": "error",
            "message": "Invalid or expired session. Please log in again."
        }), 401)

    return user_id, None


def _format_date(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]


def _format_time(val):
    if val is None:
        return None
    if isinstance(val, timedelta):
        total_seconds = int(val.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    if isinstance(val, datetime):
        return val.strftime("%H:%M")
    return str(val)[:5]


def _insert_notification_if_new(connection, cursor, user_id, category, title, message, severity="info", link=None, unique_key=None, related_id=None):
    """Insert notification only if unique_key does not already exist for this user."""
    if unique_key:
        cursor.execute("""
            SELECT id FROM notifications
            WHERE user_id = %s AND unique_key = %s
        """, (user_id, unique_key))
        if cursor.fetchone():
            return False

    cursor.execute("""
        INSERT INTO notifications (user_id, category, title, message, severity, link, unique_key, related_id, is_read, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, NOW())
    """, (user_id, category, title, message, severity, link, unique_key, related_id))
    return True


def sync_inventory_alerts_for_user(user_id, cursor, connection):
    """
    Sync low-stock, out-of-stock, and expiring/expired inventory alerts into the notifications table.
    Respects user notification preferences.
    """
    try:
        cursor.execute("""
            SELECT inventory_alerts FROM notification_preferences
            WHERE user_id = %s
        """, (user_id,))
        pref = cursor.fetchone()
        if pref and not pref.get("inventory_alerts", 1):
            return 0

        today = date.today()
        today_str = today.strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT id, item_name, category, quantity, unit, min_threshold, expiry_date
            FROM farm_inventory
            WHERE user_id = %s
        """, (user_id,))
        items = cursor.fetchall()

        inserted_count = 0
        for item in items:
            item_id = item["id"]
            name = item["item_name"]
            qty = float(item["quantity"])
            unit = item["unit"]
            threshold = float(item["min_threshold"])
            exp_date = item.get("expiry_date")

            # 1. Out of Stock
            if qty <= 0:
                u_key = f"inv_out_{item_id}_{today_str}"
                title = f"Out of Stock: {name}"
                msg = f"'{name}' is completely out of stock (0 {unit}). Restock immediately to avoid field delays."
                if _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "urgent", "#inventorySection", u_key, item_id):
                    inserted_count += 1

            # 2. Low Stock Warning
            elif qty <= threshold:
                u_key = f"inv_low_{item_id}_{today_str}"
                title = f"Low Stock Warning: {name}"
                msg = f"'{name}' is running low with only {qty:.2f} {unit} left (threshold: {threshold:.2f} {unit})."
                if _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "warning", "#inventorySection", u_key, item_id):
                    inserted_count += 1

            # 3. Expiry Checks
            if exp_date:
                if isinstance(exp_date, datetime):
                    exp_date = exp_date.date()
                diff_days = (exp_date - today).days
                exp_date_str = exp_date.strftime("%Y-%m-%d")

                if diff_days < 0:
                    u_key = f"inv_expired_{item_id}_{today_str}"
                    title = f"Expired Inventory: {name}"
                    msg = f"'{name}' expired on {exp_date_str} ({abs(diff_days)} days ago). Do not use expired agricultural chemicals or seeds."
                    if _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "urgent", "#inventorySection", u_key, item_id):
                        inserted_count += 1
                elif 0 <= diff_days <= 14:
                    u_key = f"inv_expiring_{item_id}_{exp_date_str}"
                    title = f"Stock Expiring Soon: {name}"
                    msg = f"'{name}' will expire in {diff_days} days on {exp_date_str}. Plan usage before expiration."
                    if _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "warning", "#inventorySection", u_key, item_id):
                        inserted_count += 1

        return inserted_count
    except Exception as e:
        print(f"Error syncing inventory alerts: {e}")
        return 0


# =========================================================
# ENDPOINTS
# =========================================================

@inventory_bp.route("/summary", methods=["GET"])
def get_inventory_summary():
    """
    Get inventory KPIs: total items, total valuation in INR, low stock count,
    out of stock count, expiring soon (<= 30d), expired count, category breakdown,
    critical items list, and recent movements.
    """
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        expiring_threshold_str = (today + timedelta(days=30)).strftime("%Y-%m-%d")

        # Sync notifications
        sync_inventory_alerts_for_user(user_id, cursor, conn)
        conn.commit()

        # 1. Total counts & Valuation
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_items,
                COALESCE(SUM(quantity * purchase_price), 0.00) AS total_valuation,
                SUM(CASE WHEN quantity > 0 AND quantity <= min_threshold THEN 1 ELSE 0 END) AS low_stock_count,
                SUM(CASE WHEN quantity <= 0 THEN 1 ELSE 0 END) AS out_of_stock_count,
                SUM(CASE WHEN expiry_date IS NOT NULL AND expiry_date >= %s AND expiry_date <= %s THEN 1 ELSE 0 END) AS expiring_count,
                SUM(CASE WHEN expiry_date IS NOT NULL AND expiry_date < %s THEN 1 ELSE 0 END) AS expired_count
            FROM farm_inventory
            WHERE user_id = %s
        """, (today_str, expiring_threshold_str, today_str, user_id))
        metrics = cursor.fetchone() or {}

        # 2. Category Breakdown
        cursor.execute("""
            SELECT category, COUNT(*) AS count, COALESCE(SUM(quantity * purchase_price), 0.00) AS total_val
            FROM farm_inventory
            WHERE user_id = %s
            GROUP BY category
            ORDER BY total_val DESC
        """, (user_id,))
        by_category = {r["category"]: {"count": r["count"], "value": float(r["total_val"])} for r in cursor.fetchall()}

        # 3. Critical Items needing immediate attention (out of stock, low stock, expired, expiring)
        cursor.execute("""
            SELECT i.*, f.farm_name
            FROM farm_inventory i
            LEFT JOIN farms f ON i.farm_id = f.id
            WHERE i.user_id = %s AND (
                i.quantity <= i.min_threshold OR 
                (i.expiry_date IS NOT NULL AND i.expiry_date <= %s)
            )
            ORDER BY (i.quantity <= 0) DESC, (i.expiry_date IS NOT NULL AND i.expiry_date < %s) DESC, i.quantity ASC
            LIMIT 6
        """, (user_id, expiring_threshold_str, today_str))
        critical_items = []
        for r in cursor.fetchall():
            qty = float(r["quantity"])
            thresh = float(r["min_threshold"])
            exp = r.get("expiry_date")
            if exp and isinstance(exp, datetime):
                exp = exp.date()

            status = "In Stock"
            if qty <= 0:
                status = "Out of Stock"
            elif exp and exp < today:
                status = "Expired"
            elif qty <= thresh:
                status = "Low Stock"
            elif exp and 0 <= (exp - today).days <= 30:
                status = "Expiring Soon"

            critical_items.append({
                "id": r["id"],
                "item_name": r["item_name"],
                "category": r["category"],
                "quantity": qty,
                "unit": r["unit"],
                "min_threshold": thresh,
                "purchase_price": float(r["purchase_price"]),
                "expiry_date": _format_date(r.get("expiry_date")),
                "farm_name": r.get("farm_name"),
                "status": status
            })

        # 4. Recent Movements
        cursor.execute("""
            SELECT m.*, i.item_name, c.crop_name, f.farm_name
            FROM farm_inventory_movements m
            JOIN farm_inventory i ON m.inventory_id = i.id
            LEFT JOIN crops c ON m.crop_id = c.id
            LEFT JOIN farms f ON m.farm_id = f.id
            WHERE m.user_id = %s
            ORDER BY m.movement_date DESC, m.id DESC
            LIMIT 5
        """, (user_id,))
        recent_movements = []
        for m in cursor.fetchall():
            recent_movements.append({
                "id": m["id"],
                "inventory_id": m["inventory_id"],
                "item_name": m["item_name"],
                "movement_type": m["movement_type"],
                "quantity": float(m["quantity"]),
                "unit": m["unit"],
                "movement_date": _format_date(m["movement_date"]),
                "movement_time": _format_time(m.get("movement_time")),
                "crop_name": m.get("crop_name"),
                "farm_name": m.get("farm_name"),
                "reason": m.get("reason") or ""
            })

        summary_payload = {
            "total_items": int(metrics.get("total_items") or 0),
            "total_valuation": float(metrics.get("total_valuation") or 0.0),
            "low_stock_count": int(metrics.get("low_stock_count") or 0),
            "out_of_stock_count": int(metrics.get("out_of_stock_count") or 0),
            "expiring_count": int(metrics.get("expiring_count") or 0),
            "expiring_soon_count": int(metrics.get("expiring_count") or 0),
            "expired_count": int(metrics.get("expired_count") or 0),
            "by_category": by_category,
            "critical_items": critical_items,
            "recent_movements": recent_movements
        }
        return jsonify({
            "status": "success",
            "summary": summary_payload,
            "data": summary_payload
        }), 200

    except Exception as e:
        print(f"Error fetching inventory summary: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch inventory summary."}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route("", methods=["GET"])
def list_inventory():
    """
    List inventory items with optional filtering by category, status, farm_id, and search query.
    """
    user_id, err = _authenticate()
    if err:
        return err

    category_filter = request.args.get("category", "all").strip()
    status_filter = request.args.get("status", "all").strip().lower()
    farm_filter = request.args.get("farm_id", "all").strip()
    search = request.args.get("search", "").strip()
    limit = min(int(request.args.get("limit", 150)), 300)
    offset = max(int(request.args.get("offset", 0)), 0)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT i.*, f.farm_name, f.location AS farm_location
            FROM farm_inventory i
            LEFT JOIN farms f ON i.farm_id = f.id
            WHERE i.user_id = %s
        """
        params = [user_id]

        if category_filter and category_filter.lower() != "all":
            norm_cat = CATEGORY_LOOKUP.get(category_filter.lower(), category_filter)
            query += " AND i.category = %s"
            params.append(norm_cat)

        if farm_filter and farm_filter.lower() != "all" and farm_filter.isdigit():
            query += " AND i.farm_id = %s"
            params.append(int(farm_filter))

        if search:
            query += " AND (i.item_name LIKE %s OR i.supplier_name LIKE %s OR i.notes LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        query += " ORDER BY i.item_name ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        today = date.today()
        expiring_threshold = today + timedelta(days=30)

        items = []
        for r in rows:
            qty = float(r["quantity"])
            threshold = float(r["min_threshold"])
            price = float(r["purchase_price"])
            exp = r.get("expiry_date")
            if exp and isinstance(exp, datetime):
                exp = exp.date()

            # Determine status badge
            status = "In Stock"
            if qty <= 0:
                status = "Out of Stock"
            elif exp and exp < today:
                status = "Expired"
            elif qty <= threshold:
                status = "Low Stock"
            elif exp and 0 <= (exp - today).days <= 30:
                status = "Expiring Soon"

            # Apply in-memory status filter if requested
            if status_filter != "all":
                if status_filter in ("low_stock", "low stock", "low") and status != "Low Stock":
                    continue
                if status_filter in ("out_of_stock", "out of stock", "out") and status != "Out of Stock":
                    continue
                if status_filter in ("expiring", "expiring_soon", "expiring soon") and status != "Expiring Soon":
                    continue
                if status_filter == "expired" and status != "Expired":
                    continue
                if status_filter in ("in_stock", "in stock") and status != "In Stock":
                    continue

            items.append({
                "id": r["id"],
                "user_id": r["user_id"],
                "farm_id": r["farm_id"],
                "farm_name": r.get("farm_name"),
                "farm_location": r.get("farm_location"),
                "item_name": r["item_name"],
                "category": r["category"],
                "quantity": qty,
                "unit": r["unit"],
                "purchase_price": price,
                "total_value": round(qty * price, 2),
                "purchase_date": _format_date(r["purchase_date"]),
                "supplier_name": r.get("supplier_name") or "",
                "min_threshold": threshold,
                "expiry_date": _format_date(r.get("expiry_date")),
                "storage_location": r.get("storage_location") or "",
                "notes": r.get("notes") or "",
                "status": status
            })

        return jsonify({
            "status": "success",
            "items": items,
            "data": items,
            "count": len(items),
            "total": len(items)
        }), 200

    except Exception as e:
        print(f"Error listing inventory: {e}")
        return jsonify({"status": "error", "message": "Failed to list inventory."}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route("/<int:item_id>", methods=["GET"])
def get_inventory_detail(item_id):
    """Retrieve full details of an inventory item with movement history."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT i.*, f.farm_name, f.location AS farm_location
            FROM farm_inventory i
            LEFT JOIN farms f ON i.farm_id = f.id
            WHERE i.id = %s AND i.user_id = %s
        """, (item_id, user_id))
        r = cursor.fetchone()

        if not r:
            return jsonify({"status": "error", "message": "Inventory item not found."}), 404

        qty = float(r["quantity"])
        threshold = float(r["min_threshold"])
        price = float(r["purchase_price"])
        exp = r.get("expiry_date")
        if exp and isinstance(exp, datetime):
            exp = exp.date()

        today = date.today()
        status = "In Stock"
        if qty <= 0:
            status = "Out of Stock"
        elif exp and exp < today:
            status = "Expired"
        elif qty <= threshold:
            status = "Low Stock"
        elif exp and 0 <= (exp - today).days <= 30:
            status = "Expiring Soon"

        # Fetch movements history
        cursor.execute("""
            SELECT m.*, c.crop_name, f.farm_name
            FROM farm_inventory_movements m
            LEFT JOIN crops c ON m.crop_id = c.id
            LEFT JOIN farms f ON m.farm_id = f.id
            WHERE m.inventory_id = %s AND m.user_id = %s
            ORDER BY m.movement_date DESC, m.id DESC
            LIMIT 20
        """, (item_id, user_id))
        movements = []
        for m in cursor.fetchall():
            movements.append({
                "id": m["id"],
                "movement_type": m["movement_type"],
                "quantity": float(m["quantity"]),
                "unit": m["unit"],
                "movement_date": _format_date(m["movement_date"]),
                "movement_time": _format_time(m.get("movement_time")),
                "crop_name": m.get("crop_name"),
                "farm_name": m.get("farm_name"),
                "reason": m.get("reason") or "",
                "notes": m.get("notes") or ""
            })

        item = {
            "id": r["id"],
            "user_id": r["user_id"],
            "farm_id": r["farm_id"],
            "farm_name": r.get("farm_name"),
            "farm_location": r.get("farm_location"),
            "item_name": r["item_name"],
            "category": r["category"],
            "quantity": qty,
            "unit": r["unit"],
            "purchase_price": price,
            "total_value": round(qty * price, 2),
            "purchase_date": _format_date(r["purchase_date"]),
            "supplier_name": r.get("supplier_name") or "",
            "min_threshold": threshold,
            "expiry_date": _format_date(r.get("expiry_date")),
            "storage_location": r.get("storage_location") or "",
            "notes": r.get("notes") or "",
            "status": status,
            "movements": movements
        }

        return jsonify({
            "status": "success",
            "item": item,
            "data": item
        }), 200

    except Exception as e:
        print(f"Error fetching inventory detail: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch item details."}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route("", methods=["POST"])
def create_inventory_item():
    """Create a new inventory item and log initial addition movement."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    item_name = str(data.get("item_name", "")).strip()
    category_raw = str(data.get("category", "")).strip()
    quantity_raw = data.get("quantity", 0)
    unit = str(data.get("unit", "kg")).strip() or "kg"
    purchase_price_raw = data.get("purchase_price", 0.0)
    purchase_date_raw = str(data.get("purchase_date", "")).strip()
    supplier_name = str(data.get("supplier_name", "")).strip() if data.get("supplier_name") else None
    min_threshold_raw = data.get("min_threshold", 5.0)
    expiry_date_raw = str(data.get("expiry_date", "")).strip() if data.get("expiry_date") else None
    storage_location = str(data.get("storage_location", "")).strip() if data.get("storage_location") else None
    farm_id = data.get("farm_id")
    notes = str(data.get("notes", "")).strip() if data.get("notes") else None

    # Validation
    if not item_name:
        return jsonify({"status": "error", "message": "Item name is required."}), 400
    if len(item_name) > 150:
        return jsonify({"status": "error", "message": "Item name must not exceed 150 characters."}), 400

    if not category_raw:
        normalized_cat = "Other agricultural supplies"
    else:
        normalized_cat = CATEGORY_LOOKUP.get(category_raw.lower())
        if not normalized_cat:
            normalized_cat = next((c for c in VALID_INVENTORY_CATEGORIES if c.lower() == category_raw.lower()), None)
        if not normalized_cat:
            return jsonify({
                "status": "error",
                "message": f"Invalid category. Must be one of: {', '.join(VALID_INVENTORY_CATEGORIES)}"
            }), 400

    try:
        quantity = float(quantity_raw)
        if quantity < 0:
            return jsonify({"status": "error", "message": "Initial quantity must be a non-negative number."}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Quantity must be a valid number."}), 400

    try:
        purchase_price = float(purchase_price_raw)
        if purchase_price < 0:
            return jsonify({"status": "error", "message": "Purchase price cannot be negative."}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Purchase price must be a valid number."}), 400

    try:
        min_threshold = float(min_threshold_raw)
        if min_threshold < 0:
            return jsonify({"status": "error", "message": "Minimum threshold cannot be negative."}), 400
    except (ValueError, TypeError):
        min_threshold = 5.0

    if not purchase_date_raw:
        purchase_date_raw = date.today().strftime("%Y-%m-%d")
    try:
        purchase_date = datetime.strptime(purchase_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid purchase date format (YYYY-MM-DD)."}), 400

    expiry_date = None
    if expiry_date_raw:
        try:
            expiry_date = datetime.strptime(expiry_date_raw, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid expiry date format (YYYY-MM-DD)."}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Validate farm if provided
        validated_farm_id = None
        if farm_id is not None and str(farm_id).strip() != "":
            try:
                fid = int(farm_id)
                cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (fid, user_id))
                if cursor.fetchone():
                    validated_farm_id = fid
                else:
                    return jsonify({"status": "error", "message": "Selected farm was not found."}), 400
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid farm ID."}), 400

        # Insert inventory item
        cursor.execute("""
            INSERT INTO farm_inventory (
                user_id, farm_id, item_name, category, quantity, unit,
                purchase_price, purchase_date, supplier_name, min_threshold,
                expiry_date, storage_location, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, validated_farm_id, item_name, normalized_cat, quantity, unit,
            purchase_price, purchase_date, supplier_name, min_threshold,
            expiry_date, storage_location, notes
        ))
        item_id = cursor.lastrowid

        # Insert initial stock movement audit row if quantity > 0
        if quantity > 0:
            cursor.execute("""
                INSERT INTO farm_inventory_movements (
                    inventory_id, user_id, farm_id, movement_type, quantity,
                    unit, movement_date, movement_time, reason, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
            """, (
                item_id, user_id, validated_farm_id, "Purchase / Addition", quantity,
                unit, purchase_date, "Initial inventory entry", f"Supplier: {supplier_name or 'N/A'}"
            ))

        conn.commit()

        # Sync alerts
        sync_inventory_alerts_for_user(user_id, cursor, conn)
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Inventory item created successfully.",
            "item_id": item_id
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error creating inventory item: {e}")
        return jsonify({"status": "error", "message": "Failed to create inventory item."}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route("/<int:item_id>", methods=["PUT"])
def update_inventory_item(item_id):
    """Update inventory item properties."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM farm_inventory WHERE id = %s AND user_id = %s", (item_id, user_id))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"status": "error", "message": "Inventory item not found."}), 404

        item_name = str(data.get("item_name", existing["item_name"])).strip()
        if not item_name:
            return jsonify({"status": "error", "message": "Item name is required."}), 400

        category_raw = str(data.get("category", existing["category"])).strip()
        normalized_cat = CATEGORY_LOOKUP.get(category_raw.lower())
        if not normalized_cat:
            normalized_cat = next((c for c in VALID_INVENTORY_CATEGORIES if c.lower() == category_raw.lower()), None)
        if not normalized_cat:
            return jsonify({"status": "error", "message": "Invalid category."}), 400

        unit = str(data.get("unit", existing["unit"])).strip() or existing["unit"]
        
        try:
            purchase_price = float(data.get("purchase_price", existing["purchase_price"]))
            if purchase_price < 0:
                return jsonify({"status": "error", "message": "Purchase price cannot be negative."}), 400
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Purchase price must be a valid number."}), 400

        try:
            min_threshold = float(data.get("min_threshold", existing["min_threshold"]))
            if min_threshold < 0:
                return jsonify({"status": "error", "message": "Minimum threshold cannot be negative."}), 400
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Minimum threshold must be a valid number."}), 400

        purchase_date_val = data.get("purchase_date")
        if purchase_date_val is not None and str(purchase_date_val).strip() != "":
            try:
                purchase_date = datetime.strptime(str(purchase_date_val)[:10], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid purchase date format."}), 400
        else:
            purchase_date = existing["purchase_date"]

        expiry_date = None
        if "expiry_date" in data:
            exp_val = data.get("expiry_date")
            if exp_val and str(exp_val).strip():
                try:
                    expiry_date = datetime.strptime(str(exp_val)[:10], "%Y-%m-%d").date()
                except ValueError:
                    return jsonify({"status": "error", "message": "Invalid expiry date format."}), 400
        else:
            expiry_date = existing.get("expiry_date")

        supplier_name = str(data.get("supplier_name", "")).strip() if "supplier_name" in data else existing.get("supplier_name")
        storage_location = str(data.get("storage_location", "")).strip() if "storage_location" in data else existing.get("storage_location")
        notes = str(data.get("notes", "")).strip() if "notes" in data else existing.get("notes")

        # Validate farm
        farm_id = data.get("farm_id") if "farm_id" in data else existing.get("farm_id")
        validated_farm_id = None
        if farm_id is not None and str(farm_id).strip() != "":
            try:
                fid = int(farm_id)
                cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (fid, user_id))
                if cursor.fetchone():
                    validated_farm_id = fid
                else:
                    return jsonify({"status": "error", "message": "Selected farm not found."}), 400
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid farm ID."}), 400

        cursor.execute("""
            UPDATE farm_inventory SET
                farm_id = %s,
                item_name = %s,
                category = %s,
                unit = %s,
                purchase_price = %s,
                purchase_date = %s,
                supplier_name = %s,
                min_threshold = %s,
                expiry_date = %s,
                storage_location = %s,
                notes = %s
            WHERE id = %s AND user_id = %s
        """, (
            validated_farm_id, item_name, normalized_cat, unit, purchase_price,
            purchase_date, supplier_name or None, min_threshold, expiry_date,
            storage_location or None, notes or None, item_id, user_id
        ))
        conn.commit()

        sync_inventory_alerts_for_user(user_id, cursor, conn)
        conn.commit()

        return jsonify({"status": "success", "message": "Inventory item updated successfully."}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating inventory item: {e}")
        return jsonify({"status": "error", "message": "Failed to update item."}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route("/<int:item_id>", methods=["DELETE"])
def delete_inventory_item(item_id):
    """Delete an inventory item and all associated movement records."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM farm_inventory WHERE id = %s AND user_id = %s", (item_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Inventory item not found."}), 404

        cursor.execute("DELETE FROM farm_inventory WHERE id = %s AND user_id = %s", (item_id, user_id))
        conn.commit()

        return jsonify({"status": "success", "message": "Inventory item deleted successfully."}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error deleting inventory item: {e}")
        return jsonify({"status": "error", "message": "Failed to delete item."}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route("/<int:item_id>/movement", methods=["POST"])
def record_stock_movement(item_id):
    """
    Record a stock movement (Purchase, Usage, Adjustment, Damaged/Expired, Transfer)
    with transactional stock update and negative stock prevention.
    """
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    movement_type_raw = str(data.get("movement_type", "")).strip()
    quantity_raw = data.get("quantity")
    movement_date_raw = str(data.get("movement_date", "")).strip()
    crop_id = data.get("crop_id")
    farm_id = data.get("farm_id")
    reason = str(data.get("reason", "")).strip() if data.get("reason") else None
    notes = str(data.get("notes", "")).strip() if data.get("notes") else None

    # Normalization & Validation
    norm_mov_type = MOVEMENT_LOOKUP.get(movement_type_raw.lower())
    if not norm_mov_type:
        norm_mov_type = next((m for m in VALID_MOVEMENT_TYPES if m.lower() == movement_type_raw.lower()), None)
    if not norm_mov_type:
        return jsonify({
            "status": "error",
            "message": f"Invalid movement type. Must be one of: {', '.join(VALID_MOVEMENT_TYPES)}"
        }), 400

    try:
        quantity = float(quantity_raw)
        if quantity <= 0:
            return jsonify({"status": "error", "message": "Movement quantity must be greater than 0."}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Quantity must be a valid positive number."}), 400

    if not movement_date_raw:
        movement_date_raw = date.today().strftime("%Y-%m-%d")
    try:
        movement_date = datetime.strptime(movement_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid movement date (YYYY-MM-DD)."}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Lock inventory row for update
        cursor.execute("SELECT id, quantity, unit, farm_id FROM farm_inventory WHERE id = %s AND user_id = %s FOR UPDATE", (item_id, user_id))
        item = cursor.fetchone()
        if not item:
            return jsonify({"status": "error", "message": "Inventory item not found."}), 404

        current_qty = float(item["quantity"])
        unit = item["unit"]

        # Calculate new stock level based on movement type
        if norm_mov_type == "Purchase / Addition":
            new_qty = current_qty + quantity

        elif norm_mov_type in ("Usage / Consumption", "Damaged or Expired"):
            # Prevent negative stock
            if current_qty < quantity:
                return jsonify({
                    "status": "error",
                    "message": f"Insufficient stock. Available: {current_qty:.2f} {unit}, attempted: {quantity:.2f} {unit}."
                }), 400
            new_qty = current_qty - quantity

        elif norm_mov_type == "Adjustment":
            # Direct adjustment mode
            adjust_mode = str(data.get("adjust_mode", "relative")).lower()
            if adjust_mode == "absolute":
                new_qty = quantity
            else:
                # Relative delta (can be positive or negative)
                is_reduction = bool(data.get("is_reduction", False))
                new_qty = current_qty - quantity if is_reduction else current_qty + quantity
                if new_qty < 0:
                    return jsonify({"status": "error", "message": "Adjustment would result in negative stock."}), 400

        elif norm_mov_type == "Transfer":
            if current_qty < quantity:
                return jsonify({
                    "status": "error",
                    "message": f"Insufficient stock for transfer. Available: {current_qty:.2f} {unit}."
                }), 400
            new_qty = current_qty - quantity

        # Update inventory quantity
        cursor.execute("""
            UPDATE farm_inventory
            SET quantity = %s
            WHERE id = %s AND user_id = %s
        """, (new_qty, item_id, user_id))

        # Insert movement audit row
        cursor.execute("""
            INSERT INTO farm_inventory_movements (
                inventory_id, user_id, crop_id, farm_id, movement_type,
                quantity, unit, movement_date, movement_time, reason, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        """, (
            item_id, user_id, crop_id or None, farm_id or item.get("farm_id"),
            norm_mov_type, quantity, unit, movement_date, reason, notes
        ))
        conn.commit()

        # Sync alerts
        sync_inventory_alerts_for_user(user_id, cursor, conn)
        conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Stock movement '{norm_mov_type}' recorded successfully.",
            "previous_quantity": current_qty,
            "new_quantity": new_qty,
            "unit": unit
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error recording stock movement: {e}")
        return jsonify({"status": "error", "message": "Failed to record stock movement."}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route("/<int:item_id>/movements", methods=["GET"])
def get_item_movements(item_id):
    """Retrieve complete stock movement history for a specific inventory item."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT m.*, i.item_name, c.crop_name, f.farm_name
            FROM farm_inventory_movements m
            JOIN farm_inventory i ON m.inventory_id = i.id
            LEFT JOIN crops c ON m.crop_id = c.id
            LEFT JOIN farms f ON m.farm_id = f.id
            WHERE m.inventory_id = %s AND m.user_id = %s
            ORDER BY m.movement_date DESC, m.id DESC
        """, (item_id, user_id))
        rows = cursor.fetchall()

        movements = []
        for m in rows:
            movements.append({
                "id": m["id"],
                "inventory_id": m["inventory_id"],
                "item_name": m["item_name"],
                "movement_type": m["movement_type"],
                "quantity": float(m["quantity"]),
                "unit": m["unit"],
                "movement_date": _format_date(m["movement_date"]),
                "movement_time": _format_time(m.get("movement_time")),
                "crop_name": m.get("crop_name"),
                "farm_name": m.get("farm_name"),
                "reason": m.get("reason") or "",
                "notes": m.get("notes") or ""
            })

        return jsonify({
            "status": "success",
            "movements": movements,
            "count": len(movements)
        }), 200

    except Exception as e:
        print(f"Error fetching item movements: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch movement history."}), 500
    finally:
        if conn:
            conn.close()


@inventory_bp.route("/low-stock", methods=["GET"])
def get_low_stock_items():
    """Retrieve items needing urgent restocking or nearing expiration."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        today = date.today()
        cursor.execute("""
            SELECT i.*, f.farm_name
            FROM farm_inventory i
            LEFT JOIN farms f ON i.farm_id = f.id
            WHERE i.user_id = %s AND (
                i.quantity <= i.min_threshold OR 
                (i.expiry_date IS NOT NULL AND i.expiry_date <= DATE_ADD(NOW(), INTERVAL 14 DAY))
            )
            ORDER BY (i.quantity <= 0) DESC, i.quantity ASC
        """, (user_id,))
        rows = cursor.fetchall()

        items = []
        for r in rows:
            qty = float(r["quantity"])
            thresh = float(r["min_threshold"])
            exp = r.get("expiry_date")
            if exp and isinstance(exp, datetime):
                exp = exp.date()

            status = "Low Stock"
            if qty <= 0:
                status = "Out of Stock"
            elif exp and exp < today:
                status = "Expired"
            elif exp and 0 <= (exp - today).days <= 14:
                status = "Expiring Soon"

            items.append({
                "id": r["id"],
                "item_name": r["item_name"],
                "category": r["category"],
                "quantity": qty,
                "unit": r["unit"],
                "min_threshold": thresh,
                "purchase_price": float(r["purchase_price"]),
                "expiry_date": _format_date(r.get("expiry_date")),
                "farm_name": r.get("farm_name"),
                "status": status
            })

        return jsonify({
            "status": "success",
            "items": items,
            "data": items,
            "count": len(items),
            "total": len(items)
        }), 200

    except Exception as e:
        print(f"Error fetching low stock items: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch low stock items."}), 500
    finally:
        if conn:
            conn.close()
