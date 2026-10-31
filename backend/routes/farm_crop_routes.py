from datetime import date, datetime
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

farm_bp = Blueprint("farm", __name__, url_prefix="/api/farms")
crop_mgmt_bp = Blueprint("crop_mgmt", __name__, url_prefix="/api/crops")

ALLOWED_AREA_UNITS = {"acre", "hectare"}
ALLOWED_GROWTH_STATUSES = [
    "Newly Planted",
    "Growing",
    "Flowering",
    "Fruiting",
    "Ready for Harvest",
    "Harvested"
]
GROWING_STATUSES = {"Growing", "Flowering", "Fruiting"}


def _authenticate():
    """Extract and validate the authenticated user ID from Bearer token."""
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

    return user_id, None


def _calculate_days_since_planting(planting_date):
    """Calculate integer days elapsed since planting date."""
    if not planting_date:
        return 0
    if isinstance(planting_date, str):
        try:
            planting_date = datetime.strptime(planting_date[:10], "%Y-%m-%d").date()
        except ValueError:
            return 0
    elif isinstance(planting_date, datetime):
        planting_date = planting_date.date()
    today = date.today()
    delta = (today - planting_date).days
    return max(0, delta)


# =============================================================================
# FARMS API
# =============================================================================

@farm_bp.route("", methods=["GET"])
def list_farms():
    """List all farms belonging to the authenticated farmer."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                f.id,
                f.farm_name,
                f.location,
                CAST(f.total_area AS CHAR) AS total_area,
                f.area_unit,
                f.created_at,
                f.updated_at,
                COUNT(c.id) AS crop_count
            FROM farms f
            LEFT JOIN crops c ON c.farm_id = f.id
            WHERE f.user_id = %s
            GROUP BY f.id
            ORDER BY f.created_at DESC
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()

        farms = []
        for r in rows:
            farms.append({
                "id": r["id"],
                "farm_name": r["farm_name"],
                "location": r["location"],
                "total_area": float(r["total_area"]) if r["total_area"] else 0.0,
                "area_unit": r["area_unit"],
                "crop_count": int(r["crop_count"] or 0),
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
                "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
            })

        return jsonify({
            "status": "success",
            "count": len(farms),
            "farms": farms
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Could not retrieve farms: {str(e)}"
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@farm_bp.route("", methods=["POST"])
def add_farm():
    """Add a new farm for the authenticated farmer."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    data = request.get_json(silent=True) or {}
    farm_name = str(data.get("farm_name", "")).strip()
    location = str(data.get("location", "")).strip()
    area_raw = data.get("total_area")
    area_unit = str(data.get("area_unit", "acre")).strip().lower()

    if not farm_name:
        return jsonify({"status": "error", "message": "Farm name is required."}), 400
    if len(farm_name) > 150:
        return jsonify({"status": "error", "message": "Farm name must be 150 characters or less."}), 400

    if not location:
        return jsonify({"status": "error", "message": "Farm location is required."}), 400
    if len(location) > 200:
        return jsonify({"status": "error", "message": "Location must be 200 characters or less."}), 400

    try:
        total_area = float(area_raw)
        if total_area <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Total area must be a positive number."}), 400

    if area_unit not in ALLOWED_AREA_UNITS:
        return jsonify({
            "status": "error",
            "message": f"Area unit must be one of: {', '.join(sorted(ALLOWED_AREA_UNITS))}."
        }), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        insert_query = """
            INSERT INTO farms (user_id, farm_name, location, total_area, area_unit)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (user_id, farm_name, location, total_area, area_unit))
        farm_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Farm registered successfully.",
            "farm": {
                "id": farm_id,
                "farm_name": farm_name,
                "location": location,
                "total_area": total_area,
                "area_unit": area_unit,
                "crop_count": 0
            }
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Failed to save farm: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@farm_bp.route("/<int:farm_id>", methods=["GET"])
def get_farm(farm_id):
    """Retrieve details for a single farm owned by authenticated farmer."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT f.id, f.farm_name, f.location, CAST(f.total_area AS CHAR) AS total_area,
                   f.area_unit, f.created_at, f.updated_at,
                   COUNT(c.id) AS crop_count
            FROM farms f
            LEFT JOIN crops c ON c.farm_id = f.id
            WHERE f.id = %s AND f.user_id = %s
            GROUP BY f.id
        """, (farm_id, user_id))
        farm = cursor.fetchone()

        if not farm:
            return jsonify({"status": "error", "message": "Farm not found or access denied."}), 404

        return jsonify({
            "status": "success",
            "farm": {
                "id": farm["id"],
                "farm_name": farm["farm_name"],
                "location": farm["location"],
                "total_area": float(farm["total_area"]) if farm["total_area"] else 0.0,
                "area_unit": farm["area_unit"],
                "crop_count": int(farm["crop_count"] or 0),
                "created_at": farm["created_at"].isoformat() if farm.get("created_at") else None,
                "updated_at": farm["updated_at"].isoformat() if farm.get("updated_at") else None,
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@farm_bp.route("/<int:farm_id>", methods=["PUT"])
def update_farm(farm_id):
    """Update details of an existing farm."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    data = request.get_json(silent=True) or {}
    farm_name = str(data.get("farm_name", "")).strip()
    location = str(data.get("location", "")).strip()
    area_raw = data.get("total_area")
    area_unit = str(data.get("area_unit", "acre")).strip().lower()

    if not farm_name:
        return jsonify({"status": "error", "message": "Farm name is required."}), 400
    if len(farm_name) > 150:
        return jsonify({"status": "error", "message": "Farm name must be 150 characters or less."}), 400

    if not location:
        return jsonify({"status": "error", "message": "Farm location is required."}), 400
    if len(location) > 200:
        return jsonify({"status": "error", "message": "Location must be 200 characters or less."}), 400

    try:
        total_area = float(area_raw)
        if total_area <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Total area must be a positive number."}), 400

    if area_unit not in ALLOWED_AREA_UNITS:
        return jsonify({
            "status": "error",
            "message": f"Area unit must be one of: {', '.join(sorted(ALLOWED_AREA_UNITS))}."
        }), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Farm not found or access denied."}), 404

        update_query = """
            UPDATE farms
            SET farm_name = %s, location = %s, total_area = %s, area_unit = %s
            WHERE id = %s AND user_id = %s
        """
        cursor.execute(update_query, (farm_name, location, total_area, area_unit, farm_id, user_id))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Farm updated successfully.",
            "farm": {
                "id": farm_id,
                "farm_name": farm_name,
                "location": location,
                "total_area": total_area,
                "area_unit": area_unit
            }
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Failed to update farm: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@farm_bp.route("/<int:farm_id>", methods=["DELETE"])
def delete_farm(farm_id):
    """Delete a farm and its associated crops."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, farm_name FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
        farm = cursor.fetchone()
        if not farm:
            return jsonify({"status": "error", "message": "Farm not found or access denied."}), 404

        cursor.execute("DELETE FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": f"Farm '{farm['farm_name']}' deleted successfully."
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Failed to delete farm: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =============================================================================
# CROPS & GROWTH TRACKING API
# =============================================================================

@crop_mgmt_bp.route("", methods=["GET"])
def list_crops():
    """List crops for authenticated farmer, with optional farm_id filter."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    farm_id_param = request.args.get("farm_id")

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        base_query = """
            SELECT
                c.id,
                c.user_id,
                c.farm_id,
                f.farm_name,
                c.crop_name,
                c.variety,
                c.planting_date,
                CAST(c.cultivated_area AS CHAR) AS cultivated_area,
                c.area_unit,
                c.growth_status,
                c.expected_harvest_date,
                c.notes,
                c.created_at,
                c.updated_at
            FROM crops c
            LEFT JOIN farms f ON f.id = c.farm_id
            WHERE c.user_id = %s
        """
        params = [user_id]

        if farm_id_param:
            try:
                params.append(int(farm_id_param))
                base_query += " AND c.farm_id = %s"
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid farm_id parameter."}), 400

        base_query += " ORDER BY c.planting_date DESC, c.id DESC"
        cursor.execute(base_query, tuple(params))
        rows = cursor.fetchall()

        crops = []
        for r in rows:
            p_date = r["planting_date"]
            p_date_str = p_date.strftime("%Y-%m-%d") if p_date else None
            h_date = r["expected_harvest_date"]
            h_date_str = h_date.strftime("%Y-%m-%d") if h_date else None

            crops.append({
                "id": r["id"],
                "farm_id": r["farm_id"],
                "farm_name": r["farm_name"] or "Unassigned Farm",
                "crop_name": r["crop_name"],
                "variety": r["variety"] or "",
                "planting_date": p_date_str,
                "days_since_planting": _calculate_days_since_planting(p_date),
                "cultivated_area": float(r["cultivated_area"]) if r["cultivated_area"] else None,
                "area_unit": r["area_unit"] or "acre",
                "growth_status": r["growth_status"] or "Newly Planted",
                "expected_harvest_date": h_date_str,
                "notes": r["notes"] or "",
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
                "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
            })

        return jsonify({
            "status": "success",
            "count": len(crops),
            "crops": crops
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Could not retrieve crops: {str(e)}"
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@crop_mgmt_bp.route("", methods=["POST"])
def add_crop():
    """Register a new crop associated with one of the farmer's farms."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    data = request.get_json(silent=True) or {}
    farm_id = data.get("farm_id")
    crop_name = str(data.get("crop_name", "")).strip()
    variety = str(data.get("variety", "")).strip()
    planting_date_str = str(data.get("planting_date", "")).strip()
    cultivated_area_raw = data.get("cultivated_area")
    area_unit = str(data.get("area_unit", "acre")).strip().lower()
    expected_harvest_str = str(data.get("expected_harvest_date", "")).strip()
    growth_status = str(data.get("growth_status", "Newly Planted")).strip()
    notes = str(data.get("notes", "")).strip()

    if not farm_id:
        return jsonify({"status": "error", "message": "Please select a registered farm."}), 400

    try:
        farm_id = int(farm_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid farm ID."}), 400

    if not crop_name:
        return jsonify({"status": "error", "message": "Crop name is required."}), 400
    if len(crop_name) > 100:
        return jsonify({"status": "error", "message": "Crop name must be 100 characters or less."}), 400

    if len(variety) > 100:
        return jsonify({"status": "error", "message": "Crop variety must be 100 characters or less."}), 400

    if not planting_date_str:
        return jsonify({"status": "error", "message": "Planting date is required."}), 400

    try:
        planting_date = datetime.strptime(planting_date_str[:10], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"status": "error", "message": "Planting date must be in YYYY-MM-DD format."}), 400

    try:
        cultivated_area = float(cultivated_area_raw)
        if cultivated_area <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Cultivated area must be a positive number."}), 400

    if area_unit not in ALLOWED_AREA_UNITS:
        return jsonify({
            "status": "error",
            "message": f"Area unit must be one of: {', '.join(sorted(ALLOWED_AREA_UNITS))}."
        }), 400

    expected_harvest_date = None
    if expected_harvest_str:
        try:
            expected_harvest_date = datetime.strptime(expected_harvest_str[:10], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": "error", "message": "Expected harvest date must be in YYYY-MM-DD format."}), 400

    if growth_status not in ALLOWED_GROWTH_STATUSES:
        return jsonify({
            "status": "error",
            "message": f"Invalid growth status. Allowed statuses: {', '.join(ALLOWED_GROWTH_STATUSES)}."
        }), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Validate that the farm belongs to the authenticated farmer
        cursor.execute("SELECT id, farm_name FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
        farm_row = cursor.fetchone()
        if not farm_row:
            return jsonify({
                "status": "error",
                "message": "Selected farm not found or does not belong to you."
            }), 400

        insert_query = """
            INSERT INTO crops (
                user_id, farm_id, crop_name, variety,
                planting_date, cultivated_area, area_unit,
                expected_harvest_date, growth_status, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            user_id, farm_id, crop_name, variety if variety else None,
            planting_date, cultivated_area, area_unit,
            expected_harvest_date, growth_status, notes if notes else None
        ))
        crop_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Crop registered successfully.",
            "crop": {
                "id": crop_id,
                "farm_id": farm_id,
                "farm_name": farm_row["farm_name"],
                "crop_name": crop_name,
                "variety": variety,
                "planting_date": planting_date.strftime("%Y-%m-%d"),
                "days_since_planting": _calculate_days_since_planting(planting_date),
                "cultivated_area": cultivated_area,
                "area_unit": area_unit,
                "expected_harvest_date": expected_harvest_date.strftime("%Y-%m-%d") if expected_harvest_date else None,
                "growth_status": growth_status,
                "notes": notes
            }
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Failed to save crop: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@crop_mgmt_bp.route("/<int:crop_id>", methods=["GET"])
def get_crop(crop_id):
    """Get single crop details."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT c.*, f.farm_name, CAST(c.cultivated_area AS CHAR) AS cultivated_area_str
            FROM crops c
            LEFT JOIN farms f ON f.id = c.farm_id
            WHERE c.id = %s AND c.user_id = %s
        """, (crop_id, user_id))
        r = cursor.fetchone()

        if not r:
            return jsonify({"status": "error", "message": "Crop not found or access denied."}), 404

        p_date = r["planting_date"]
        p_date_str = p_date.strftime("%Y-%m-%d") if p_date else None
        h_date = r["expected_harvest_date"]
        h_date_str = h_date.strftime("%Y-%m-%d") if h_date else None

        return jsonify({
            "status": "success",
            "crop": {
                "id": r["id"],
                "farm_id": r["farm_id"],
                "farm_name": r["farm_name"] or "Unassigned Farm",
                "crop_name": r["crop_name"],
                "variety": r["variety"] or "",
                "planting_date": p_date_str,
                "days_since_planting": _calculate_days_since_planting(p_date),
                "cultivated_area": float(r["cultivated_area_str"]) if r["cultivated_area_str"] else None,
                "area_unit": r["area_unit"] or "acre",
                "growth_status": r["growth_status"] or "Newly Planted",
                "expected_harvest_date": h_date_str,
                "notes": r["notes"] or "",
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
                "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@crop_mgmt_bp.route("/<int:crop_id>", methods=["PUT"])
def update_crop(crop_id):
    """Update details of an existing crop."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    data = request.get_json(silent=True) or {}
    farm_id = data.get("farm_id")
    crop_name = str(data.get("crop_name", "")).strip()
    variety = str(data.get("variety", "")).strip()
    planting_date_str = str(data.get("planting_date", "")).strip()
    cultivated_area_raw = data.get("cultivated_area")
    area_unit = str(data.get("area_unit", "acre")).strip().lower()
    expected_harvest_str = str(data.get("expected_harvest_date", "")).strip()
    growth_status = str(data.get("growth_status", "Newly Planted")).strip()
    notes = str(data.get("notes", "")).strip()

    if not farm_id:
        return jsonify({"status": "error", "message": "Please select a registered farm."}), 400

    try:
        farm_id = int(farm_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid farm ID."}), 400

    if not crop_name:
        return jsonify({"status": "error", "message": "Crop name is required."}), 400
    if len(crop_name) > 100:
        return jsonify({"status": "error", "message": "Crop name must be 100 characters or less."}), 400

    if len(variety) > 100:
        return jsonify({"status": "error", "message": "Crop variety must be 100 characters or less."}), 400

    if not planting_date_str:
        return jsonify({"status": "error", "message": "Planting date is required."}), 400

    try:
        planting_date = datetime.strptime(planting_date_str[:10], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"status": "error", "message": "Planting date must be in YYYY-MM-DD format."}), 400

    try:
        cultivated_area = float(cultivated_area_raw)
        if cultivated_area <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Cultivated area must be a positive number."}), 400

    if area_unit not in ALLOWED_AREA_UNITS:
        return jsonify({
            "status": "error",
            "message": f"Area unit must be one of: {', '.join(sorted(ALLOWED_AREA_UNITS))}."
        }), 400

    expected_harvest_date = None
    if expected_harvest_str:
        try:
            expected_harvest_date = datetime.strptime(expected_harvest_str[:10], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": "error", "message": "Expected harvest date must be in YYYY-MM-DD format."}), 400

    if growth_status not in ALLOWED_GROWTH_STATUSES:
        return jsonify({
            "status": "error",
            "message": f"Invalid growth status. Allowed statuses: {', '.join(ALLOWED_GROWTH_STATUSES)}."
        }), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Crop not found or access denied."}), 404

        cursor.execute("SELECT id, farm_name FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
        farm_row = cursor.fetchone()
        if not farm_row:
            return jsonify({"status": "error", "message": "Selected farm does not belong to you."}), 400

        update_query = """
            UPDATE crops
            SET farm_id = %s, crop_name = %s, variety = %s,
                planting_date = %s, cultivated_area = %s, area_unit = %s,
                expected_harvest_date = %s, growth_status = %s, notes = %s
            WHERE id = %s AND user_id = %s
        """
        cursor.execute(update_query, (
            farm_id, crop_name, variety if variety else None,
            planting_date, cultivated_area, area_unit,
            expected_harvest_date, growth_status, notes if notes else None,
            crop_id, user_id
        ))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Crop updated successfully.",
            "crop": {
                "id": crop_id,
                "farm_id": farm_id,
                "farm_name": farm_row["farm_name"],
                "crop_name": crop_name,
                "variety": variety,
                "planting_date": planting_date.strftime("%Y-%m-%d"),
                "days_since_planting": _calculate_days_since_planting(planting_date),
                "cultivated_area": cultivated_area,
                "area_unit": area_unit,
                "expected_harvest_date": expected_harvest_date.strftime("%Y-%m-%d") if expected_harvest_date else None,
                "growth_status": growth_status,
                "notes": notes
            }
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Failed to update crop: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@crop_mgmt_bp.route("/<int:crop_id>/status", methods=["PATCH", "PUT"])
def update_crop_status(crop_id):
    """Manually update the growth status of a crop."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    data = request.get_json(silent=True) or {}
    new_status = str(data.get("growth_status", "")).strip()

    if new_status not in ALLOWED_GROWTH_STATUSES:
        return jsonify({
            "status": "error",
            "message": f"Invalid growth status. Allowed: {', '.join(ALLOWED_GROWTH_STATUSES)}."
        }), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, crop_name FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
        crop = cursor.fetchone()
        if not crop:
            return jsonify({"status": "error", "message": "Crop not found or access denied."}), 404

        cursor.execute("UPDATE crops SET growth_status = %s WHERE id = %s AND user_id = %s", (new_status, crop_id, user_id))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": f"Growth status for '{crop['crop_name']}' updated to '{new_status}'.",
            "crop_id": crop_id,
            "growth_status": new_status
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Failed to update status: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@crop_mgmt_bp.route("/<int:crop_id>", methods=["DELETE"])
def delete_crop(crop_id):
    """Delete a crop with ownership validation."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, crop_name FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
        crop = cursor.fetchone()
        if not crop:
            return jsonify({"status": "error", "message": "Crop not found or access denied."}), 404

        cursor.execute("DELETE FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": f"Crop '{crop['crop_name']}' deleted successfully."
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Failed to delete crop: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@crop_mgmt_bp.route("/dashboard-summary", methods=["GET"])
def dashboard_summary():
    """Retrieve summarized farm and crop counts for the farmer dashboard."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Total farms
        cursor.execute("SELECT COUNT(*) AS total FROM farms WHERE user_id = %s", (user_id,))
        total_farms = int(cursor.fetchone()["total"] or 0)

        # 2. Total crops
        cursor.execute("SELECT COUNT(*) AS total FROM crops WHERE user_id = %s", (user_id,))
        total_crops = int(cursor.fetchone()["total"] or 0)

        # 3. Crops currently growing (Growing, Flowering, Fruiting)
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM crops
            WHERE user_id = %s AND growth_status IN ('Growing', 'Flowering', 'Fruiting')
        """, (user_id,))
        crops_growing = int(cursor.fetchone()["total"] or 0)

        # 4. Crops ready for harvest
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM crops
            WHERE user_id = %s AND growth_status = 'Ready for Harvest'
        """, (user_id,))
        crops_ready = int(cursor.fetchone()["total"] or 0)

        # Status breakdown
        cursor.execute("""
            SELECT growth_status, COUNT(*) AS count
            FROM crops
            WHERE user_id = %s
            GROUP BY growth_status
        """, (user_id,))
        breakdown_rows = cursor.fetchall()
        status_counts = {s: 0 for s in ALLOWED_GROWTH_STATUSES}
        for b in breakdown_rows:
            if b["growth_status"] in status_counts:
                status_counts[b["growth_status"]] = int(b["count"])

        return jsonify({
            "status": "success",
            "summary": {
                "total_farms": total_farms,
                "total_crops": total_crops,
                "crops_growing": crops_growing,
                "crops_ready_for_harvest": crops_ready,
                "status_breakdown": status_counts
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
