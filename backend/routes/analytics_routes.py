from datetime import date, datetime
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

GROWTH_STAGES_ORDER = [
    "Newly Planted",
    "Growing",
    "Flowering",
    "Fruiting",
    "Ready for Harvest",
    "Harvested"
]


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

    return user_id, None


def _parse_disease_label(predicted_class):
    """Parse crop prefix and disease name from standard model class format."""
    if not predicted_class:
        return "Unknown Crop", "Unknown Condition", False

    clean_cls = str(predicted_class).strip()
    if "___" in clean_cls:
        crop_part, disease_part = clean_cls.split("___", 1)
        crop_name = crop_part.replace("_", " ").title()
        disease_name = disease_part.replace("_", " ").title()
        is_healthy = "healthy" in disease_part.lower()
        return crop_name, disease_name, is_healthy

    is_healthy = "healthy" in clean_cls.lower()
    return "Plant", clean_cls.replace("_", " ").title(), is_healthy


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


@analytics_bp.route("/filter-options", methods=["GET"])
def get_filter_options():
    """Return list of farms and crops available for filter dropdowns."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Farmer's farms
        cursor.execute("SELECT id, farm_name FROM farms WHERE user_id = %s ORDER BY farm_name ASC", (user_id,))
        farms = cursor.fetchall() or []

        # 2. Distinct crop names from farmer's registered crops, irrigation, and diagnoses
        cursor.execute("SELECT DISTINCT crop_name FROM crops WHERE user_id = %s AND crop_name IS NOT NULL", (user_id,))
        crop_rows = cursor.fetchall() or []
        crop_names = {r["crop_name"].strip() for r in crop_rows if r.get("crop_name")}

        cursor.execute("SELECT DISTINCT crop FROM irrigation_history WHERE user_id = %s AND crop IS NOT NULL", (user_id,))
        irrig_rows = cursor.fetchall() or []
        for r in irrig_rows:
            if r.get("crop"):
                crop_names.add(r["crop"].strip())

        return jsonify({
            "status": "success",
            "farms": [{"id": f["id"], "farm_name": f["farm_name"]} for f in farms],
            "crops": sorted(list(crop_names))
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Could not load filter options: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@analytics_bp.route("/overview", methods=["GET"])
def get_analytics_overview():
    """Compute and return complete smart analytics for authenticated farmer."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    # Query parameters
    farm_id_param = request.args.get("farm_id", "").strip()
    crop_name_param = request.args.get("crop_name", "").strip()
    start_date_param = request.args.get("start_date", "").strip()
    end_date_param = request.args.get("end_date", "").strip()

    farm_id = None
    if farm_id_param:
        try:
            farm_id = int(farm_id_param)
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid farm_id parameter."}), 400

    # Validate dates if provided
    start_date = None
    if start_date_param:
        try:
            start_date = datetime.strptime(start_date_param[:10], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid start_date format (YYYY-MM-DD expected)."}), 400

    end_date = None
    if end_date_param:
        try:
            end_date = datetime.strptime(end_date_param[:10], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid end_date format (YYYY-MM-DD expected)."}), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # =====================================================================
        # 1. SUMMARY STATS (Overall or Filtered)
        # =====================================================================
        cursor.execute("SELECT COUNT(*) AS cnt FROM farms WHERE user_id = %s", (user_id,))
        total_farms = int(cursor.fetchone()["cnt"] or 0)

        cursor.execute("SELECT COUNT(*) AS cnt FROM crops WHERE user_id = %s", (user_id,))
        total_crops = int(cursor.fetchone()["cnt"] or 0)

        cursor.execute("SELECT COUNT(*) AS cnt FROM diagnosis_history WHERE user_id = %s", (user_id,))
        total_diagnoses = int(cursor.fetchone()["cnt"] or 0)

        cursor.execute("SELECT COUNT(*) AS cnt FROM irrigation_history WHERE user_id = %s", (user_id,))
        total_irrigations = int(cursor.fetchone()["cnt"] or 0)

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM crops
            WHERE user_id = %s AND growth_status IN ('Growing', 'Flowering', 'Fruiting')
        """, (user_id,))
        crops_growing = int(cursor.fetchone()["cnt"] or 0)

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM crops
            WHERE user_id = %s AND growth_status = 'Ready for Harvest'
        """, (user_id,))
        crops_ready = int(cursor.fetchone()["cnt"] or 0)

        # =====================================================================
        # 2. CROP ANALYTICS
        # =====================================================================
        crop_where = ["c.user_id = %s"]
        crop_params = [user_id]

        if farm_id is not None:
            crop_where.append("c.farm_id = %s")
            crop_params.append(farm_id)
        if crop_name_param:
            crop_where.append("c.crop_name = %s")
            crop_params.append(crop_name_param)
        if start_date:
            crop_where.append("c.planting_date >= %s")
            crop_params.append(start_date)
        if end_date:
            crop_where.append("c.planting_date <= %s")
            crop_params.append(end_date)

        crop_where_sql = " AND ".join(crop_where)

        # 2a. Crop distribution by crop name
        cursor.execute(f"""
            SELECT c.crop_name, COUNT(*) AS count,
                   COALESCE(SUM(c.cultivated_area), 0) AS total_area,
                   MAX(c.area_unit) AS area_unit
            FROM crops c
            WHERE {crop_where_sql}
            GROUP BY c.crop_name
            ORDER BY count DESC
        """, tuple(crop_params))
        crop_dist_rows = cursor.fetchall() or []
        crops_by_name = []
        for r in crop_dist_rows:
            crops_by_name.append({
                "crop_name": r["crop_name"],
                "count": int(r["count"]),
                "total_area": float(r["total_area"]),
                "area_unit": r["area_unit"] or "acre"
            })

        # 2b. Crop growth-stage distribution
        cursor.execute(f"""
            SELECT c.growth_status, COUNT(*) AS count
            FROM crops c
            WHERE {crop_where_sql}
            GROUP BY c.growth_status
        """, tuple(crop_params))
        stage_rows = cursor.fetchall() or []
        stage_counts = {s: 0 for s in GROWTH_STAGES_ORDER}
        for r in stage_rows:
            st = r["growth_status"]
            if st in stage_counts:
                stage_counts[st] = int(r["count"])
            else:
                stage_counts[st] = int(r["count"])
        growth_stages = [{"stage": st, "count": stage_counts.get(st, 0)} for st in GROWTH_STAGES_ORDER]

        # 2c. Number of crops registered per farm
        cursor.execute(f"""
            SELECT COALESCE(f.farm_name, 'Unassigned') AS farm_name,
                   c.farm_id,
                   COUNT(c.id) AS count
            FROM crops c
            LEFT JOIN farms f ON f.id = c.farm_id
            WHERE {crop_where_sql}
            GROUP BY c.farm_id, f.farm_name
            ORDER BY count DESC
        """, tuple(crop_params))
        crops_per_farm_rows = cursor.fetchall() or []
        crops_per_farm = []
        for r in crops_per_farm_rows:
            crops_per_farm.append({
                "farm_name": r["farm_name"],
                "farm_id": r["farm_id"],
                "count": int(r["count"])
            })

        # 2d. Crop planting and harvest timeline
        cursor.execute(f"""
            SELECT c.id, c.crop_name, c.variety,
                   COALESCE(f.farm_name, 'Unassigned') AS farm_name,
                   c.planting_date, c.expected_harvest_date,
                   c.growth_status, c.cultivated_area, c.area_unit
            FROM crops c
            LEFT JOIN farms f ON f.id = c.farm_id
            WHERE {crop_where_sql}
            ORDER BY c.planting_date DESC
            LIMIT 20
        """, tuple(crop_params))
        timeline_rows = cursor.fetchall() or []
        crop_timeline = []
        for r in timeline_rows:
            p_date = r["planting_date"]
            h_date = r["expected_harvest_date"]
            crop_timeline.append({
                "id": r["id"],
                "crop_name": r["crop_name"],
                "variety": r["variety"] or "",
                "farm_name": r["farm_name"],
                "planting_date": p_date.strftime("%Y-%m-%d") if p_date else None,
                "days_since_planting": _calculate_days_since_planting(p_date),
                "expected_harvest_date": h_date.strftime("%Y-%m-%d") if h_date else None,
                "growth_status": r["growth_status"] or "Newly Planted",
                "cultivated_area": float(r["cultivated_area"]) if r["cultivated_area"] else None,
                "area_unit": r["area_unit"] or "acre"
            })

        # =====================================================================
        # 3. DISEASE ANALYTICS
        # =====================================================================
        diag_where = ["dh.user_id = %s"]
        diag_params = [user_id]

        if crop_name_param:
            diag_where.append("LOWER(dh.predicted_class) LIKE %s")
            diag_params.append(f"%{crop_name_param.lower()}%")
        if start_date:
            diag_where.append("DATE(dh.diagnosis_date) >= %s")
            diag_params.append(start_date)
        if end_date:
            diag_where.append("DATE(dh.diagnosis_date) <= %s")
            diag_params.append(end_date)

        diag_where_sql = " AND ".join(diag_where)

        cursor.execute(f"""
            SELECT dh.predicted_class, dh.confidence, dh.diagnosis_date
            FROM diagnosis_history dh
            WHERE {diag_where_sql}
            ORDER BY dh.diagnosis_date DESC
        """, tuple(diag_params))
        diag_records = cursor.fetchall() or []

        disease_counts = {}
        crop_type_counts = {}
        daily_diag_counts = {}
        healthy_count = 0
        diseased_count = 0

        for row in diag_records:
            pred_cls = row["predicted_class"]
            crop_type, disease_name, is_healthy = _parse_disease_label(pred_cls)

            if is_healthy:
                healthy_count += 1
            else:
                diseased_count += 1

            # Disease frequencies
            if disease_name not in disease_counts:
                disease_counts[disease_name] = {"count": 0, "confidences": []}
            disease_counts[disease_name]["count"] += 1
            if row.get("confidence") is not None:
                disease_counts[disease_name]["confidences"].append(float(row["confidence"]))

            # Crop distribution
            crop_type_counts[crop_type] = crop_type_counts.get(crop_type, 0) + 1

            # Trends over time (YYYY-MM-DD)
            d_date = row.get("diagnosis_date")
            if d_date:
                d_str = d_date.strftime("%Y-%m-%d") if isinstance(d_date, (datetime, date)) else str(d_date)[:10]
                daily_diag_counts[d_str] = daily_diag_counts.get(d_str, 0) + 1

        top_diseases = []
        for name, info in sorted(disease_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:10]:
            confs = info["confidences"]
            avg_conf = round(sum(confs) / len(confs), 1) if confs else None
            top_diseases.append({
                "disease_name": name,
                "count": info["count"],
                "avg_confidence": avg_conf
            })

        crop_disease_distribution = [
            {"crop_type": k, "count": v}
            for k, v in sorted(crop_type_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        disease_trends = [
            {"date": k, "count": v}
            for k, v in sorted(daily_diag_counts.items())
        ]

        disease_analytics = {
            "total_diagnoses": len(diag_records),
            "healthy_count": healthy_count,
            "diseased_count": diseased_count,
            "top_diseases": top_diseases,
            "crop_distribution": crop_disease_distribution,
            "trends_over_time": disease_trends
        }

        # =====================================================================
        # 4. IRRIGATION ANALYTICS
        # =====================================================================
        irrig_where = ["ih.user_id = %s"]
        irrig_params = [user_id]

        if crop_name_param:
            irrig_where.append("LOWER(ih.crop) = %s")
            irrig_params.append(crop_name_param.lower())
        if start_date:
            irrig_where.append("DATE(ih.created_at) >= %s")
            irrig_params.append(start_date)
        if end_date:
            irrig_where.append("DATE(ih.created_at) <= %s")
            irrig_params.append(end_date)

        irrig_where_sql = " AND ".join(irrig_where)

        cursor.execute(f"""
            SELECT ih.crop, ih.soil_moisture, ih.is_irrigation_needed,
                   ih.water_quantity_mm, ih.recommendation_status, ih.created_at
            FROM irrigation_history ih
            WHERE {irrig_where_sql}
            ORDER BY ih.created_at ASC
        """, tuple(irrig_params))
        irrig_records = cursor.fetchall() or []

        total_irrig_recs = len(irrig_records)
        irrig_needed_count = sum(1 for r in irrig_records if r.get("is_irrigation_needed"))
        irrig_not_needed_count = total_irrig_recs - irrig_needed_count

        total_water_mm = sum(
            float(r["water_quantity_mm"]) for r in irrig_records
            if r.get("water_quantity_mm") is not None
        )
        avg_water_mm = round(total_water_mm / total_irrig_recs, 2) if total_irrig_recs > 0 else 0.0

        # Crop-wise irrigation summaries
        irrig_by_crop = {}
        daily_irrig_activity = {}

        for r in irrig_records:
            c_name = r.get("crop") or "Unknown Crop"
            if c_name not in irrig_by_crop:
                irrig_by_crop[c_name] = {
                    "count": 0,
                    "moistures": [],
                    "water_quantities": []
                }
            irrig_by_crop[c_name]["count"] += 1
            if r.get("soil_moisture") is not None:
                irrig_by_crop[c_name]["moistures"].append(float(r["soil_moisture"]))
            if r.get("water_quantity_mm") is not None:
                irrig_by_crop[c_name]["water_quantities"].append(float(r["water_quantity_mm"]))

            c_date = r.get("created_at")
            if c_date:
                d_str = c_date.strftime("%Y-%m-%d") if isinstance(c_date, (datetime, date)) else str(c_date)[:10]
                if d_str not in daily_irrig_activity:
                    daily_irrig_activity[d_str] = {"count": 0, "moistures": []}
                daily_irrig_activity[d_str]["count"] += 1
                if r.get("soil_moisture") is not None:
                    daily_irrig_activity[d_str]["moistures"].append(float(r["soil_moisture"]))

        crop_irrigation_summaries = []
        for c_name, stats in irrig_by_crop.items():
            cnt = stats["count"]
            avg_m = round(sum(stats["moistures"]) / len(stats["moistures"]), 1) if stats["moistures"] else 0.0
            tot_w = round(sum(stats["water_quantities"]), 1)
            crop_irrigation_summaries.append({
                "crop": c_name,
                "count": cnt,
                "avg_soil_moisture": avg_m,
                "total_water_mm": tot_w
            })
        crop_irrigation_summaries.sort(key=lambda x: x["count"], reverse=True)

        irrigation_activity = []
        for d_str, stats in sorted(daily_irrig_activity.items()):
            avg_m = round(sum(stats["moistures"]) / len(stats["moistures"]), 1) if stats["moistures"] else 0.0
            irrigation_activity.append({
                "date": d_str,
                "count": stats["count"],
                "avg_soil_moisture": avg_m
            })

        irrigation_analytics = {
            "total_recommendations": total_irrig_recs,
            "irrigation_needed_count": irrig_needed_count,
            "irrigation_not_needed_count": irrig_not_needed_count,
            "total_estimated_water_mm": round(total_water_mm, 2),
            "avg_water_mm": avg_water_mm,
            "crop_summaries": crop_irrigation_summaries,
            "activity_over_time": irrigation_activity
        }

        # Response payload
        return jsonify({
            "status": "success",
            "summary": {
                "total_farms": total_farms,
                "total_crops": total_crops,
                "total_diagnoses": total_diagnoses,
                "total_irrigations": total_irrigations,
                "crops_growing": crops_growing,
                "crops_ready_for_harvest": crops_ready
            },
            "crop_analytics": {
                "crops_by_name": crops_by_name,
                "growth_stages": growth_stages,
                "crops_per_farm": crops_per_farm,
                "timeline": crop_timeline
            },
            "disease_analytics": disease_analytics,
            "irrigation_analytics": irrigation_analytics,
            "filters_applied": {
                "farm_id": farm_id,
                "crop_name": crop_name_param or None,
                "start_date": start_date_param or None,
                "end_date": end_date_param or None
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error in analytics: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
