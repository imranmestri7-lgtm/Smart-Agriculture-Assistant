"""
AgriSmart - Smart Crop Reminder Engine
Feature Upgrade 9, Phase 3 (Part 2)

Generates and manages crop milestone and growth-stage reminders:
- Sowing milestone reminders (configurable lead days, e.g. -7, -1, 0)
- Harvest milestone reminders (configurable lead days, e.g. -14, -7, 0)
- Crop growth-stage care reminders (Vegetative, Flowering, Grain/Fruit development)
- Clear labeling for estimated dates and general agronomic guidance
- Farmer-level multi-tenant isolation and strict duplicate prevention
- Direct integration with farm_activities and notifications
"""

from datetime import date, datetime, timedelta
import re

from config import get_db_connection


# =============================================================================
# DEFAULT REMINDER CONFIGURATION & GUIDANCE TEMPLATES
# =============================================================================

DEFAULT_SOWING_LEAD_DAYS = [7, 1, 0]
DEFAULT_HARVEST_LEAD_DAYS = [14, 7, 0]

# Standard agronomic stage milestones based on crop duration fractions
GROWTH_STAGE_PROFILES = [
    {
        "milestone_type": "vegetative",
        "fraction": 0.22,
        "min_days_after_sowing": 14,
        "title_template": "Vegetative Care: {crop_name}",
        "description_template": "Estimated vegetative & tillering stage for {crop_name} ({variety}) at {farm_name}.",
        "guidance": (
            "General Agronomic Advice: Check seedling emergence, uniform plant stand, and root establishment. "
            "Maintain moderate soil moisture without waterlogging. Carry out light weeding or shallow inter-cultivation "
            "to prevent weed competition before canopy closure. If recommended by soil test, apply the first split dose of nitrogen."
        )
    },
    {
        "milestone_type": "flowering",
        "fraction": 0.50,
        "min_days_after_sowing": 30,
        "title_template": "Flowering Phase Care: {crop_name}",
        "description_template": "Estimated critical flowering / bloom stage for {crop_name} ({variety}) at {farm_name}.",
        "guidance": (
            "General Agronomic Advice: Flowering is a moisture-critical stage. Ensure consistent and timely irrigation "
            "to prevent flower or bud drop. Scout foliage and flowers early in the morning for sucking pests or pod borers. "
            "Avoid high-pressure chemical sprays during peak pollination hours to safeguard beneficial pollinators."
        )
    },
    {
        "milestone_type": "fruit_development",
        "fraction": 0.72,
        "min_days_after_sowing": 45,
        "title_template": "Grain / Fruit Development: {crop_name}",
        "description_template": "Estimated pod/grain filling or fruit sizing phase for {crop_name} ({variety}) at {farm_name}.",
        "guidance": (
            "General Agronomic Advice: Maintain optimal soil moisture to support maximum grain filling or fruit expansion. "
            "Avoid moisture stress which can cause premature shriveling. Monitor lower canopy for fungal spots or fruit borers. "
            "Begin tapering off irrigation as the crop approaches physiological maturity."
        )
    }
]


# =============================================================================
# SETTINGS & PREFERENCES
# =============================================================================

def get_or_create_reminder_settings(user_id, conn=None):
    """
    Retrieve or initialize the farmer's reminder configuration.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT user_id, sowing_lead_days, harvest_lead_days, enable_growth_stages
            FROM crop_plan_reminder_settings
            WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()

        if not row:
            sowing_str = ",".join(str(d) for d in DEFAULT_SOWING_LEAD_DAYS)
            harvest_str = ",".join(str(d) for d in DEFAULT_HARVEST_LEAD_DAYS)
            cur.execute("""
                INSERT INTO crop_plan_reminder_settings (user_id, sowing_lead_days, harvest_lead_days, enable_growth_stages)
                VALUES (%s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE user_id = user_id
            """, (user_id, sowing_str, harvest_str))
            conn.commit()
            row = {
                "user_id": user_id,
                "sowing_lead_days": sowing_str,
                "harvest_lead_days": harvest_str,
                "enable_growth_stages": 1
            }

        cur.close()

        # Parse comma-separated strings to integer lists
        sowing_days = _parse_days_list(row.get("sowing_lead_days"), DEFAULT_SOWING_LEAD_DAYS)
        harvest_days = _parse_days_list(row.get("harvest_lead_days"), DEFAULT_HARVEST_LEAD_DAYS)

        return {
            "user_id": user_id,
            "sowing_lead_days": sowing_days,
            "harvest_lead_days": harvest_days,
            "enable_growth_stages": bool(row.get("enable_growth_stages", 1))
        }
    finally:
        if close_conn and conn:
            conn.close()


def update_reminder_settings(user_id, settings_dict, conn=None):
    """
    Update farmer's reminder configuration with validation.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        sowing_days = settings_dict.get("sowing_lead_days", DEFAULT_SOWING_LEAD_DAYS)
        harvest_days = settings_dict.get("harvest_lead_days", DEFAULT_HARVEST_LEAD_DAYS)
        enable_growth = 1 if settings_dict.get("enable_growth_stages", True) else 0

        # Validate and normalize
        sowing_list = _validate_days_input(sowing_days, DEFAULT_SOWING_LEAD_DAYS)
        harvest_list = _validate_days_input(harvest_days, DEFAULT_HARVEST_LEAD_DAYS)

        sowing_str = ",".join(str(d) for d in sowing_list)
        harvest_str = ",".join(str(d) for d in harvest_list)

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO crop_plan_reminder_settings (user_id, sowing_lead_days, harvest_lead_days, enable_growth_stages)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                sowing_lead_days = VALUES(sowing_lead_days),
                harvest_lead_days = VALUES(harvest_lead_days),
                enable_growth_stages = VALUES(enable_growth_stages)
        """, (user_id, sowing_str, harvest_str, enable_growth))
        conn.commit()
        cur.close()

        return {
            "user_id": user_id,
            "sowing_lead_days": sowing_list,
            "harvest_lead_days": harvest_list,
            "enable_growth_stages": bool(enable_growth)
        }
    finally:
        if close_conn and conn:
            conn.close()


def _parse_days_list(days_str, default_val):
    if not days_str:
        return default_val
    try:
        return sorted([int(x.strip()) for x in str(days_str).split(",") if x.strip().lstrip("-").isdigit()], reverse=True)
    except Exception:
        return default_val


def _validate_days_input(days_input, default_val):
    if isinstance(days_input, str):
        days_input = [x.strip() for x in days_input.split(",") if x.strip()]
    if not isinstance(days_input, (list, tuple, set)):
        return default_val
    cleaned = []
    for d in days_input:
        try:
            val = int(d)
            if 0 <= val <= 60:  # Valid range: 0 to 60 days lead time
                cleaned.append(val)
        except (ValueError, TypeError):
            continue
    return sorted(list(set(cleaned)), reverse=True) if cleaned else default_val


# =============================================================================
# REMINDER GENERATION ENGINE
# =============================================================================

def generate_reminders_for_plan(user_id, plan_id, conn=None, custom_settings=None):
    """
    Generate milestone and growth-stage reminders for a specific crop plan.
    Prevents duplicates using unique keys, preserves user-completed/dismissed status,
    and isolates records to the authenticated user.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cur = conn.cursor(dictionary=True)

        # 1. Fetch crop plan ensuring strict farmer isolation
        cur.execute("""
            SELECT p.id, p.user_id, p.farm_id, p.crop_name, p.variety, p.season,
                   p.planned_sowing_date, p.expected_harvest_date, p.status, p.notes,
                   f.farm_name
            FROM crop_plans p
            LEFT JOIN farms f ON f.id = p.farm_id
            WHERE p.id = %s AND p.user_id = %s
        """, (plan_id, user_id))
        plan = cur.fetchone()

        if not plan:
            cur.close()
            return {"generated": 0, "skipped": 0, "reminders": []}

        # Do not generate reminders for Cancelled plans
        if plan.get("status") == "Cancelled":
            cur.close()
            return {"generated": 0, "skipped": 0, "reminders": []}

        # 2. Get settings
        settings = custom_settings or get_or_create_reminder_settings(user_id, conn)
        sowing_lead_days = settings.get("sowing_lead_days", DEFAULT_SOWING_LEAD_DAYS)
        harvest_lead_days = settings.get("harvest_lead_days", DEFAULT_HARVEST_LEAD_DAYS)
        enable_growth_stages = settings.get("enable_growth_stages", True)

        sowing_date = plan.get("planned_sowing_date")
        harvest_date = plan.get("expected_harvest_date")

        # Parse dates safely
        sow_dt = None
        if sowing_date:
            sow_dt = sowing_date if isinstance(sowing_date, date) else datetime.strptime(str(sowing_date)[:10], "%Y-%m-%d").date()

        har_dt = None
        if harvest_date:
            har_dt = harvest_date if isinstance(harvest_date, date) else datetime.strptime(str(harvest_date)[:10], "%Y-%m-%d").date()

        crop_name = plan.get("crop_name") or "Crop"
        variety = plan.get("variety") or "Standard"
        farm_name = plan.get("farm_name") or "Main Field"
        farm_id = plan.get("farm_id")

        reminders_to_insert = []

        # =========================================================================
        # A. SOWING MILESTONE REMINDERS
        # =========================================================================
        if sow_dt:
            for lead in sowing_lead_days:
                due_dt = sow_dt - timedelta(days=lead)
                unique_key = f"plan_{plan_id}_milestone_sowing_{lead}"

                if lead > 1:
                    title = f"Sowing Preparation: {crop_name} ({lead} days before)"
                    desc = f"Planned sowing of {crop_name} ({variety}) at {farm_name} is in {lead} days."
                    guidance = (
                        "Procure certified seeds from verified sources. Conduct seed germination test if using stored seed. "
                        "Carry out recommended bio-fertilizer / fungicide seed treatment (e.g. Trichoderma / Rhizobium). "
                        "Prepare fine tilth field beds with adequate basal manure."
                    )
                elif lead == 1:
                    title = f"Sowing Readiness: {crop_name} (Tomorrow)"
                    desc = f"Planned sowing of {crop_name} is scheduled for tomorrow at {farm_name}."
                    guidance = (
                        "Check field soil moisture (optimal vapsa condition). Calibrate seed drill / planting furrow spacing. "
                        "Ensure labour or machinery is ready for morning planting."
                    )
                else:  # lead == 0
                    title = f"Planned Sowing Date: {crop_name} (Today)"
                    desc = f"Today is the planned sowing date for {crop_name} at {farm_name}."
                    guidance = (
                        "Complete seed sowing at recommended depth and spacing. If soil moisture is low, apply initial light irrigation."
                    )

                reminders_to_insert.append({
                    "user_id": user_id,
                    "crop_plan_id": plan_id,
                    "farm_id": farm_id,
                    "reminder_type": "milestone",
                    "milestone_type": "sowing",
                    "title": title,
                    "description": desc,
                    "guidance": guidance,
                    "due_date": due_dt.strftime("%Y-%m-%d"),
                    "days_offset": -lead,
                    "is_estimated": 0,
                    "unique_key": unique_key
                })

        # =========================================================================
        # B. HARVEST MILESTONE REMINDERS
        # =========================================================================
        if har_dt:
            for lead in harvest_lead_days:
                due_dt = har_dt - timedelta(days=lead)
                unique_key = f"plan_{plan_id}_milestone_harvest_{lead}"

                if lead > 7:
                    title = f"Pre-Harvest Check: {crop_name} ({lead} days before)"
                    desc = f"Expected harvest of {crop_name} ({variety}) at {farm_name} is scheduled in {lead} days."
                    guidance = (
                        "Cease chemical fungicide/pesticide sprays to honor pre-harvest withholding periods. "
                        "Inspect crops for physiological maturity (leaf yellowing, pod firmness, grain moisture level)."
                    )
                elif lead > 0:
                    title = f"Harvest Preparation: {crop_name} ({lead} days before)"
                    desc = f"Expected harvest of {crop_name} is in {lead} days at {farm_name}."
                    guidance = (
                        "Clean and prepare threshing ground or drying yard. Arrange harvesting labour or combine harvester. "
                        "Inspect grain storage sacks, crates, and storage moisture safety."
                    )
                else:  # lead == 0
                    title = f"Expected Harvest Date: {crop_name} (Today)"
                    desc = f"Today is the projected harvest date for {crop_name} at {farm_name}."
                    guidance = (
                        "Harvest during dry, clear weather. Avoid morning dew or damp conditions to reduce post-harvest fungal rot. "
                        "Record actual harvest quantity and move produce to well-ventilated dry storage."
                    )

                reminders_to_insert.append({
                    "user_id": user_id,
                    "crop_plan_id": plan_id,
                    "farm_id": farm_id,
                    "reminder_type": "milestone",
                    "milestone_type": "harvest",
                    "title": title,
                    "description": desc,
                    "guidance": guidance,
                    "due_date": due_dt.strftime("%Y-%m-%d"),
                    "days_offset": -lead,
                    "is_estimated": 0,
                    "unique_key": unique_key
                })

        # =========================================================================
        # C. GROWTH STAGE CARE REMINDERS (Estimated Agronomic Guidance)
        # =========================================================================
        if enable_growth_stages and sow_dt and har_dt and (har_dt > sow_dt):
            duration_days = (har_dt - sow_dt).days

            # Only generate growth stages for crop cycles of 30 days or longer
            if duration_days >= 30:
                for stage in GROWTH_STAGE_PROFILES:
                    calc_offset = max(stage["min_days_after_sowing"], round(duration_days * stage["fraction"]))
                    # Don't place growth stages within 5 days of harvest
                    if calc_offset >= (duration_days - 5):
                        continue

                    due_dt = sow_dt + timedelta(days=calc_offset)
                    unique_key = f"plan_{plan_id}_growth_{stage['milestone_type']}_{calc_offset}"

                    title = stage["title_template"].format(crop_name=crop_name)
                    desc = stage["description_template"].format(
                        crop_name=crop_name,
                        variety=variety,
                        farm_name=farm_name
                    )

                    reminders_to_insert.append({
                        "user_id": user_id,
                        "crop_plan_id": plan_id,
                        "farm_id": farm_id,
                        "reminder_type": "growth_stage",
                        "milestone_type": stage["milestone_type"],
                        "title": title,
                        "description": desc,
                        "guidance": stage["guidance"],
                        "due_date": due_dt.strftime("%Y-%m-%d"),
                        "days_offset": calc_offset,
                        "is_estimated": 1,
                        "unique_key": unique_key
                    })

        # 3. Persist reminders idempotently
        # Note: We update title, description, guidance, due_date and farm_id if plan dates shifted,
        # but WE NEVER OVERWRITE an already 'completed' or 'dismissed' status back to 'pending'!
        inserted_count = 0
        for rem in reminders_to_insert:
            cur.execute("""
                INSERT INTO crop_plan_reminders (
                    user_id, crop_plan_id, farm_id, reminder_type, milestone_type,
                    title, description, guidance, due_date, days_offset,
                    status, is_estimated, unique_key
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    'pending', %s, %s
                )
                ON DUPLICATE KEY UPDATE
                    title = VALUES(title),
                    description = VALUES(description),
                    guidance = VALUES(guidance),
                    due_date = VALUES(due_date),
                    days_offset = VALUES(days_offset),
                    farm_id = VALUES(farm_id),
                    is_estimated = VALUES(is_estimated)
            """, (
                rem["user_id"], rem["crop_plan_id"], rem["farm_id"], rem["reminder_type"], rem["milestone_type"],
                rem["title"], rem["description"], rem["guidance"], rem["due_date"], rem["days_offset"],
                rem["is_estimated"], rem["unique_key"]
            ))
            inserted_count += 1

        conn.commit()
        cur.close()

        return {
            "plan_id": plan_id,
            "generated": inserted_count,
            "reminders_count": len(reminders_to_insert)
        }
    finally:
        if close_conn and conn:
            conn.close()


def generate_reminders_for_all_plans(user_id, conn=None):
    """
    Generate and synchronize reminders for all active crop plans of the farmer.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id FROM crop_plans
            WHERE user_id = %s AND status != 'Cancelled'
        """, (user_id,))
        plans = cur.fetchall() or []
        cur.close()

        settings = get_or_create_reminder_settings(user_id, conn)
        total_generated = 0

        for p in plans:
            res = generate_reminders_for_plan(user_id, p["id"], conn, custom_settings=settings)
            total_generated += res.get("generated", 0)

        return {
            "total_plans": len(plans),
            "total_generated": total_generated
        }
    finally:
        if close_conn and conn:
            conn.close()


# =============================================================================
# REMINDER QUERY & STATUS CONTROLLER
# =============================================================================

def get_farmer_reminders(user_id, conn=None, filters=None):
    """
    Retrieve reminders with rich categorization:
    - is_upcoming: due in future (status == 'pending')
    - is_today: due today (status == 'pending')
    - is_overdue: due before today (status == 'pending')
    - completed / dismissed
    Supports filtering by status ('pending', 'completed', 'dismissed', 'upcoming', 'overdue', 'today', 'all'),
    type ('milestone', 'growth_stage', 'all'), plan_id, and farm_id.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    filters = filters or {}
    today = date.today()

    try:
        cur = conn.cursor(dictionary=True)

        query = """
            SELECT r.id, r.user_id, r.crop_plan_id, r.farm_id, r.reminder_type, r.milestone_type,
                   r.title, r.description, r.guidance, r.due_date, r.days_offset,
                   r.status, r.is_estimated, r.completed_at, r.dismissed_at, r.unique_key,
                   r.created_at, r.updated_at,
                   p.crop_name, p.variety, p.season, p.planning_year,
                   p.planned_sowing_date, p.expected_harvest_date, p.status AS plan_status,
                   f.farm_name
            FROM crop_plan_reminders r
            JOIN crop_plans p ON p.id = r.crop_plan_id
            LEFT JOIN farms f ON f.id = r.farm_id
            WHERE r.user_id = %s
        """
        params = [user_id]

        # Filter by plan_id
        plan_id = filters.get("plan_id")
        if plan_id:
            try:
                query += " AND r.crop_plan_id = %s"
                params.append(int(plan_id))
            except (ValueError, TypeError):
                pass

        # Filter by farm_id
        farm_id = filters.get("farm_id")
        if farm_id and str(farm_id).lower() != "all":
            try:
                query += " AND r.farm_id = %s"
                params.append(int(farm_id))
            except (ValueError, TypeError):
                pass

        # Filter by reminder_type
        rem_type = filters.get("type", "all").strip().lower()
        if rem_type in ("milestone", "growth_stage"):
            query += " AND r.reminder_type = %s"
            params.append(rem_type)

        # Filter by date window if provided
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        if start_date and end_date:
            query += " AND r.due_date BETWEEN %s AND %s"
            params.extend([start_date, end_date])

        # Order by due date ascending
        query += " ORDER BY r.due_date ASC, r.id ASC"

        cur.execute(query, tuple(params))
        raw_rows = cur.fetchall() or []
        cur.close()

        # Categorize rows and apply status filtering
        status_filter = filters.get("status", "all").strip().lower()

        categorized_reminders = []
        counts = {
            "total": len(raw_rows),
            "upcoming": 0,
            "today": 0,
            "overdue": 0,
            "completed": 0,
            "dismissed": 0
        }

        for r in raw_rows:
            due_dt = r["due_date"]
            if not isinstance(due_dt, date):
                due_dt = datetime.strptime(str(due_dt)[:10], "%Y-%m-%d").date()

            st = r["status"]
            diff_days = (due_dt - today).days

            is_today = (st == "pending" and diff_days == 0)
            is_overdue = (st == "pending" and diff_days < 0)
            is_upcoming = (st == "pending" and diff_days > 0)

            if is_today:
                counts["today"] += 1
            elif is_overdue:
                counts["overdue"] += 1
            elif is_upcoming:
                counts["upcoming"] += 1

            if st == "completed":
                counts["completed"] += 1
            elif st == "dismissed":
                counts["dismissed"] += 1

            # Format relative date string
            if is_today:
                rel_label = "Due Today"
            elif is_overdue:
                days_ago = abs(diff_days)
                rel_label = f"Overdue by {days_ago} day{'s' if days_ago != 1 else ''}"
            elif is_upcoming:
                rel_label = f"In {diff_days} day{'s' if diff_days != 1 else ''}"
            elif st == "completed":
                rel_label = "Completed"
            else:
                rel_label = "Dismissed"

            item = {
                "id": r["id"],
                "crop_plan_id": r["crop_plan_id"],
                "farm_id": r["farm_id"],
                "farm_name": r["farm_name"] or "Main Field",
                "crop_name": r["crop_name"],
                "variety": r["variety"] or "Standard",
                "season": r["season"],
                "planning_year": r["planning_year"],
                "plan_status": r["plan_status"],
                "reminder_type": r["reminder_type"],
                "milestone_type": r["milestone_type"],
                "title": r["title"],
                "description": r["description"],
                "guidance": r["guidance"],
                "due_date": due_dt.strftime("%Y-%m-%d"),
                "days_offset": r["days_offset"],
                "days_from_today": diff_days,
                "relative_label": rel_label,
                "status": st,
                "is_today": is_today,
                "is_overdue": is_overdue,
                "is_upcoming": is_upcoming,
                "is_estimated": bool(r["is_estimated"]),
                "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                "dismissed_at": r["dismissed_at"].isoformat() if r["dismissed_at"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            }

            # Filter evaluation
            include = True
            if status_filter == "pending":
                include = (st == "pending")
            elif status_filter == "completed":
                include = (st == "completed")
            elif status_filter == "dismissed":
                include = (st == "dismissed")
            elif status_filter == "upcoming":
                include = is_upcoming
            elif status_filter == "today":
                include = is_today
            elif status_filter == "overdue":
                include = is_overdue
            elif status_filter == "active":  # upcoming, today, or overdue
                include = (st == "pending")

            if include:
                categorized_reminders.append(item)

        # Apply limit if requested
        limit = filters.get("limit")
        if limit:
            try:
                categorized_reminders = categorized_reminders[:int(limit)]
            except (ValueError, TypeError):
                pass

        return {
            "reminders": categorized_reminders,
            "counts": counts,
            "total_returned": len(categorized_reminders)
        }
    finally:
        if close_conn and conn:
            conn.close()


def update_reminder_status(user_id, reminder_id, new_status, conn=None):
    """
    Update reminder status with validation ('completed', 'dismissed', 'pending').
    Enforces user ownership.
    """
    valid_statuses = ("pending", "completed", "dismissed")
    new_status = (new_status or "").strip().lower()
    if new_status not in valid_statuses:
        return {"status": "error", "message": f"Invalid status '{new_status}'. Expected one of {valid_statuses}."}

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT id, user_id, status FROM crop_plan_reminders
            WHERE id = %s AND user_id = %s
        """, (reminder_id, user_id))
        reminder = cur.fetchone()

        if not reminder:
            cur.close()
            return {"status": "error", "message": "Reminder not found or access denied.", "code": 404}

        now_dt = datetime.now()
        completed_at = now_dt if new_status == "completed" else None
        dismissed_at = now_dt if new_status == "dismissed" else None

        cur.execute("""
            UPDATE crop_plan_reminders
            SET status = %s,
                completed_at = %s,
                dismissed_at = %s
            WHERE id = %s AND user_id = %s
        """, (new_status, completed_at, dismissed_at, reminder_id, user_id))
        conn.commit()
        cur.close()

        return {
            "status": "success",
            "message": f"Reminder status updated to '{new_status}'.",
            "reminder_id": reminder_id,
            "new_status": new_status
        }
    finally:
        if close_conn and conn:
            conn.close()


def add_reminder_to_farm_activities(user_id, reminder_id, conn=None):
    """
    Convert a crop plan reminder into a farm_activities entry,
    reusing the existing farm activity and calendar systems.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT r.*, p.crop_name, p.variety, f.farm_name
            FROM crop_plan_reminders r
            JOIN crop_plans p ON p.id = r.crop_plan_id
            LEFT JOIN farms f ON f.id = r.farm_id
            WHERE r.id = %s AND r.user_id = %s
        """, (reminder_id, user_id))
        rem = cur.fetchone()

        if not rem:
            cur.close()
            return {"status": "error", "message": "Reminder not found or access denied.", "code": 404}

        # Map reminder milestone to valid farm_activities categories
        milestone = rem["milestone_type"]
        if milestone == "sowing":
            category = "Sowing and planting"
            priority = "High"
        elif milestone == "harvest":
            category = "Harvesting"
            priority = "High"
        elif milestone in ("vegetative", "flowering", "fruit_development"):
            category = "Crop inspection"
            priority = "Medium"
        else:
            category = "Other activities"
            priority = "Medium"

        due_date = rem["due_date"]
        due_str = due_date.strftime("%Y-%m-%d") if isinstance(due_date, date) else str(due_date)[:10]

        title = f"[Plan] {rem['title']}"
        desc_parts = [rem["description"] or ""]
        if rem.get("guidance"):
            desc_parts.append(f"Guidance:\n{rem['guidance']}")
        description = "\n\n".join(desc_parts)

        # Check if activity already created for this reminder to avoid duplicates
        cur.execute("""
            SELECT id FROM farm_activities
            WHERE user_id = %s AND title = %s AND scheduled_date = %s
        """, (user_id, title, due_str))
        existing_act = cur.fetchone()

        if existing_act:
            cur.close()
            return {
                "status": "success",
                "message": "Activity already exists in Farm Activities.",
                "activity_id": existing_act["id"],
                "already_existed": True
            }

        # Insert new activity
        cur.execute("""
            INSERT INTO farm_activities (
                user_id, farm_id, title, description, category,
                priority, status, scheduled_date, reminder_enabled, notes
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, 'Pending', %s, 1, %s
            )
        """, (
            user_id, rem["farm_id"], title, description, category,
            priority, due_str, f"Generated from Crop Plan #{rem['crop_plan_id']} Reminder #{rem['id']}"
        ))
        conn.commit()
        activity_id = cur.lastrowid
        cur.close()

        return {
            "status": "success",
            "message": "Reminder successfully added to Farm Activities.",
            "activity_id": activity_id,
            "already_existed": False
        }
    finally:
        if close_conn and conn:
            conn.close()
