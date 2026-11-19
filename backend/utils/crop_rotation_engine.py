"""
AgriSmart - Crop Rotation Analysis Engine (Feature Upgrade 9, Phase 2 Part 1)
Agronomic botanical classification, pattern recognition, and rotation advice.
Provides multi-tenant farmer data isolation, crop family mapping, and scientifically backed legume suggestions.
"""

from datetime import date, datetime
import re

# =============================================================================
# BOTANICAL FAMILIES & AGRONOMIC ATTRIBUTES
# =============================================================================

BOTANICAL_FAMILIES = {
    "Fabaceae": {
        "family_name": "Fabaceae",
        "common_name": "Legumes / Pulses (Nitrogen Fixers)",
        "crops": [
            "chickpea", "gram", "chana", "bengal gram", "kabuli chana",
            "pigeon pea", "tur", "arhar", "red gram", "toor",
            "soybean", "soya", "soyabean",
            "green gram", "moong", "mung", "mung bean",
            "black gram", "urad", "mash",
            "cowpea", "chavli", "lobia",
            "peas", "mattar", "green peas", "field pea",
            "lentil", "lentils", "masoor",
            "groundnut", "peanut", "moongphali", "shengdana",
            "fenugreek", "methi",
            "cluster bean", "guar", "gawar",
            "sunn hemp", "dhaincha", "horse gram", "kulthi"
        ],
        "category": "legume",
        "nutrient_impact": "restorative",
        "nitrogen_fixer": True,
        "root_depth": "medium taproot",
        "default_legumes": ["Chickpea (Chana)", "Soybean", "Green Gram (Moong)", "Pigeon Pea (Tur)", "Black Gram (Urad)"]
    },
    "Poaceae": {
        "family_name": "Poaceae",
        "common_name": "Gramineae / Grass & Cereal Family",
        "crops": [
            "wheat", "gehun",
            "rice", "paddy", "dhan", "chawal",
            "maize", "corn", "makka",
            "sorghum", "jowar", "great millet",
            "pearl millet", "bajra",
            "finger millet", "ragi", "nachni",
            "sugarcane", "ganna", "oos",
            "barley", "jau",
            "oats", "jai"
        ],
        "category": "cereal",
        "nutrient_impact": "heavy_feeder",
        "nitrogen_fixer": False,
        "root_depth": "shallow fibrous",
        "vulnerabilities": ["Soil nitrogen depletion", "Potassium mining", "Phalaris minor weed buildup", "Stem borer accumulation"]
    },
    "Solanaceae": {
        "family_name": "Solanaceae",
        "common_name": "Nightshade Family",
        "crops": [
            "tomato", "tamatar",
            "potato", "aloo", "batata",
            "eggplant", "brinjal", "baingan", "vangi", "aubergine",
            "chilli", "chili", "mirchi", "green chilli", "pepper", "capsicum", "bell pepper", "shimla mirch",
            "tobacco", "tambaku"
        ],
        "category": "solanaceous",
        "nutrient_impact": "heavy_feeder",
        "nitrogen_fixer": False,
        "root_depth": "medium taproot",
        "vulnerabilities": ["Bacterial wilt (Ralstonia)", "Early and late blight", "Root-knot nematodes (Meloidogyne)", "Fusarium wilt"]
    },
    "Malvaceae": {
        "family_name": "Malvaceae",
        "common_name": "Mallow Family",
        "crops": [
            "cotton", "kapas", "kapaas",
            "okra", "bhindi", "bhendi", "ladyfinger", "lady finger"
        ],
        "category": "fiber_vegetable",
        "nutrient_impact": "heavy_feeder",
        "nitrogen_fixer": False,
        "root_depth": "deep taproot",
        "vulnerabilities": ["Pink bollworm persistence", "Whitefly and yellow vein mosaic virus", "Verticillium wilt"]
    },
    "Cucurbitaceae": {
        "family_name": "Cucurbitaceae",
        "common_name": "Gourd & Melon Family",
        "crops": [
            "watermelon", "tarbooj", "kalingad",
            "muskmelon", "kharbooja", "cantaloupe",
            "cucumber", "khira", "kakdi",
            "bottle gourd", "lauki", "dudhi", "doodhi",
            "bitter gourd", "karela",
            "pumpkin", "kaddu", "bhopla",
            "ridge gourd", "turai", "sponge gourd", "gilki", "ash gourd", "petha",
            "pointed gourd", "parwal", "snake gourd"
        ],
        "category": "gourd",
        "nutrient_impact": "medium_feeder",
        "nitrogen_fixer": False,
        "root_depth": "shallow-medium vines",
        "vulnerabilities": ["Downy and powdery mildew", "Fruit fly infestation", "Fusarium soil rot", "Damping-off"]
    },
    "Brassicaceae": {
        "family_name": "Brassicaceae",
        "common_name": "Cruciferous / Mustard Family",
        "crops": [
            "mustard", "sarson", "rai", "mohari",
            "cabbage", "patta gobhi", "kobi",
            "cauliflower", "phool gobhi",
            "radish", "mooli",
            "turnip", "shalgam",
            "broccoli"
        ],
        "category": "crucifer",
        "nutrient_impact": "medium_feeder",
        "nitrogen_fixer": False,
        "root_depth": "medium taproot",
        "vulnerabilities": ["Clubroot disease", "White rust", "Aphids accumulation"]
    },
    "Alliaceae": {
        "family_name": "Alliaceae",
        "common_name": "Allium / Onion & Garlic Family",
        "crops": [
            "onion", "pyaaz", "kanda",
            "garlic", "lahsun", "lasun"
        ],
        "category": "allium",
        "nutrient_impact": "light_medium_feeder",
        "nitrogen_fixer": False,
        "root_depth": "shallow bulbs",
        "vulnerabilities": ["Purple blotch", "Thrips infestation", "Basal rot"]
    },
    "Zingiberaceae": {
        "family_name": "Zingiberaceae",
        "common_name": "Ginger & Turmeric Family",
        "crops": [
            "ginger", "adrak", "ale",
            "turmeric", "haldi", "halad"
        ],
        "category": "rhizome",
        "nutrient_impact": "heavy_feeder",
        "nitrogen_fixer": False,
        "root_depth": "shallow rhizomatous",
        "vulnerabilities": ["Rhizome rot (Pythium)", "Bacterial soft rot"]
    },
    "Asteraceae": {
        "family_name": "Asteraceae",
        "common_name": "Sunflower / Oilseed Family",
        "crops": [
            "sunflower", "surajmukhi",
            "safflower", "kardi"
        ],
        "category": "oilseed",
        "nutrient_impact": "medium_feeder",
        "nitrogen_fixer": False,
        "root_depth": "deep taproot",
        "vulnerabilities": ["Alternaria leaf spot", "Rust", "Subsoil moisture extraction"]
    }
}

# Seasonal Legume Matrix for Suggestions
SEASON_LEGUMES = {
    "Kharif": ["Soybean", "Green Gram (Moong)", "Black Gram (Urad)", "Pigeon Pea (Tur)", "Cowpea (Chavli)"],
    "Rabi": ["Chickpea (Chana)", "Field Pea (Mattar)", "Lentils (Masoor)"],
    "Zaid": ["Green Gram (Moong)", "Cowpea (Chavli)", "Cluster Bean (Guar)"],
    "Year-round": ["Chickpea (Chana)", "Soybean", "Green Gram (Moong)", "Pigeon Pea (Tur)"]
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _normalize_name(name):
    """Normalize crop name to lowercase alphanumeric words."""
    if not name:
        return ""
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", str(name).lower())
    return " ".join(clean.split())


def classify_crop(crop_name):
    """
    Classify a crop name into its botanical family, nutrient role, and agronomic characteristics.
    """
    norm = _normalize_name(crop_name)
    if not norm:
        return {
            "family": "Unknown",
            "common_name": "Unclassified Crop",
            "category": "other",
            "is_legume": False,
            "nitrogen_fixer": False,
            "nutrient_impact": "medium_feeder",
            "root_depth": "medium",
            "normalized_name": ""
        }

    tokens = norm.split()

    # Priority match against known botanical families
    for fam_key, fam_data in BOTANICAL_FAMILIES.items():
        for known_crop in fam_data["crops"]:
            # Direct exact match or token containment
            if known_crop in norm or any(t == known_crop for t in tokens):
                is_legume = fam_data.get("nitrogen_fixer", False) or fam_data.get("category") == "legume"
                return {
                    "family": fam_key,
                    "common_name": fam_data["common_name"],
                    "category": fam_data["category"],
                    "is_legume": is_legume,
                    "nitrogen_fixer": is_legume,
                    "nutrient_impact": fam_data.get("nutrient_impact", "medium_feeder"),
                    "root_depth": fam_data.get("root_depth", "medium"),
                    "normalized_name": norm,
                    "matched_crop": known_crop
                }

    return {
        "family": "Other",
        "common_name": "General Agricultural Crop",
        "category": "other",
        "is_legume": False,
        "nitrogen_fixer": False,
        "nutrient_impact": "medium_feeder",
        "root_depth": "medium",
        "normalized_name": norm
    }


def _date_to_str(d):
    """Format date or string safely."""
    if not d:
        return None
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    s = str(d).strip()
    return s[:10] if len(s) >= 10 else s


# =============================================================================
# ROTATION ANALYSIS ENGINE
# =============================================================================

def analyze_crop_rotation_for_farm(farm_info, history_crops, planned_crops):
    """
    Analyze sequential crop patterns for a single farm.
    
    Args:
        farm_info: dict with farm id, farm_name, total_area, area_unit, location
        history_crops: list of dicts from `crops` table
        planned_crops: list of dicts from `crop_plans` table
        
    Returns:
        Structured analysis dict with timeline, detected issues, positive patterns,
        legume recommendations, and health score.
    """
    farm_id = farm_info.get("id")
    farm_name = farm_info.get("farm_name") or "Unassigned Farm"

    # 1. Build unified chronological timeline
    timeline = []

    for c in history_crops:
        d_val = c.get("planting_date") or c.get("created_at")
        d_str = _date_to_str(d_val)
        classification = classify_crop(c.get("crop_name", ""))
        timeline.append({
            "record_id": c.get("id"),
            "crop_name": c.get("crop_name", "").strip(),
            "variety": c.get("variety") or "",
            "date": d_str,
            "season": None,
            "source": "history",
            "status": c.get("growth_status") or "Harvested",
            "area": float(c.get("cultivated_area") or 0.0) if c.get("cultivated_area") else None,
            "area_unit": c.get("area_unit") or farm_info.get("area_unit") or "Acres",
            "field_location": c.get("field_location") or "",
            "family": classification["family"],
            "family_common": classification["common_name"],
            "is_legume": classification["is_legume"],
            "nutrient_impact": classification["nutrient_impact"]
        })

    for p in planned_crops:
        d_val = p.get("planned_sowing_date") or p.get("created_at")
        d_str = _date_to_str(d_val)
        classification = classify_crop(p.get("crop_name", ""))
        timeline.append({
            "record_id": p.get("id"),
            "crop_name": p.get("crop_name", "").strip(),
            "variety": p.get("variety") or "",
            "date": d_str,
            "season": p.get("season"),
            "planning_year": p.get("planning_year"),
            "source": "plan",
            "status": p.get("status") or "Planned",
            "area": float(p.get("land_area") or 0.0) if p.get("land_area") else None,
            "area_unit": p.get("area_unit") or "Acres",
            "field_location": p.get("field_location") or "",
            "family": classification["family"],
            "family_common": classification["common_name"],
            "is_legume": classification["is_legume"],
            "nutrient_impact": classification["nutrient_impact"]
        })

    # Sort timeline chronologically
    timeline.sort(key=lambda x: (x["date"] or "9999-99-99", x["record_id"] or 0))

    total_records = len(timeline)

    # 2. Insufficient Data Check
    if total_records < 2:
        return {
            "farm_id": farm_id,
            "farm_name": farm_name,
            "total_records": total_records,
            "crop_count": total_records,
            "has_sufficient_history": False,
            "insufficient_reason": (
                f"Insufficient crop records for '{farm_name}'. At least 2 sequential crop cycles "
                "(past harvests or seasonal crop plans) are required to evaluate rotation health and soil impacts."
            ),
            "timeline": timeline,
            "issues": [],
            "suggestions": [
                {
                    "context": "Initial Crop Planning Advice",
                    "target_family": "Fabaceae (Legumes / Pulses)",
                    "suitable_crops": ["Chickpea (Chana)", "Soybean", "Green Gram (Moong)", "Pigeon Pea (Tur)"],
                    "agronomic_reason": (
                        "For healthy crop rotation, always include a leguminous pulse crop every 2-3 seasons "
                        "to naturally fix atmospheric nitrogen and prevent continuous pest cycles."
                    ),
                    "benefits": [
                        "Cultivates symbiotic Rhizobium root nodules",
                        "Restores 30 to 80 kg nitrogen per hectare naturally",
                        "Breaks soil-borne pathogen cycles"
                    ]
                }
            ],
            "positive_patterns": [],
            "rotation_score": None,
            "rotation_rating": "Insufficient Data"
        }

    # 3. Pattern Detection Across Consecutive Entries
    issues = []
    positive_patterns = []
    suggestions = []
    score_deduction = 0
    score_bonus = 0

    for i in range(len(timeline) - 1):
        prev = timeline[i]
        curr = timeline[i + 1]

        prev_crop = prev["crop_name"]
        curr_crop = curr["crop_name"]
        prev_fam = prev["family"]
        curr_fam = curr["family"]

        prev_norm = _normalize_name(prev_crop)
        curr_norm = _normalize_name(curr_crop)

        # Check A: Repeated Identical Crop (Monoculture)
        if prev_norm and curr_norm and (prev_norm == curr_norm or prev_norm in curr_norm or curr_norm in prev_norm):
            severity = "HIGH"
            if curr_fam in ("Solanaceae", "Malvaceae"):
                severity = "CRITICAL"
                deduction = 35
            elif curr_fam == "Poaceae":
                deduction = 25
            else:
                deduction = 20

            score_deduction += deduction

            issue_item = {
                "type": "REPEATED_CROP",
                "severity": severity,
                "crop_1": prev_crop,
                "crop_2": curr_crop,
                "date_1": prev["date"],
                "date_2": curr["date"],
                "family": curr_fam,
                "title": f"Repeated Monoculture: {curr_crop} after {prev_crop}",
                "description": (
                    f"Planting '{curr_crop}' consecutively on the same farm exhausts the exact same soil nutrient strata, "
                    f"proliferates specialized root pests, and increases synthetic fertilizer requirements."
                ),
                "risks": [
                    f"Severe soil nutrient exhaustion in the {prev.get('root_depth', 'root')} layer",
                    f"Accumulation of host-specific fungi, nematodes, and soil-borne blights",
                    "Aggressive weed adaptation to the same seasonal crop lifecycle"
                ]
            }
            issues.append(issue_item)

            # Legume Suggestion for Repeated Crop
            suggestions.append({
                "context": f"Break Monoculture of '{curr_crop}'",
                "target_family": "Fabaceae (Legumes / Pulses)",
                "suitable_crops": SEASON_LEGUMES.get(curr.get("season") or "Year-round", SEASON_LEGUMES["Year-round"]),
                "agronomic_reason": (
                    f"Immediately rotate after '{prev_crop}' with a pulse or legume crop. Legumes host Rhizobium nodules "
                    "that fix atmospheric nitrogen, build soil humus, and deprive host-specific pests of their food source."
                ),
                "benefits": [
                    "Fixes biological atmospheric nitrogen, cutting chemical urea expenses",
                    "Starves root pathogens specific to this monoculture",
                    "Improves soil crumb structure and aeration"
                ]
            })

        # Check B: Repeated Botanical Family (Even if different crop names)
        elif prev_fam == curr_fam and curr_fam not in ("Other", "Unknown"):
            if curr_fam == "Solanaceae":
                severity = "HIGH"
                deduction = 30
                specific_risks = [
                    "High accumulation of Bacterial Wilt (Ralstonia solanacearum)",
                    "Early and Late Blight (Alternaria / Phytophthora) spore persistence in soil",
                    "Root-knot nematode (Meloidogyne spp.) infestation multiplication"
                ]
                reason = (
                    f"Both '{prev_crop}' and '{curr_crop}' belong to the Solanaceae (Nightshade) family. "
                    "Successive Solanaceous crops drastically escalate bacterial wilt, root-knot nematodes, and Fusarium wilt."
                )
                alt_family = "Fabaceae (Legumes)"
                alt_crops = ["Chickpea (Chana)", "Soybean", "Green Gram (Moong)"]
            elif curr_fam == "Malvaceae":
                severity = "HIGH"
                deduction = 25
                specific_risks = [
                    "Pink bollworm pest carryover between cotton and okra",
                    "Whitefly proliferation transmitting Yellow Vein Mosaic Virus",
                    "Verticillium wilt accumulation in deep soil strata"
                ]
                reason = (
                    f"Both '{prev_crop}' and '{curr_crop}' belong to the Malvaceae family. "
                    "Okra and Cotton share identical insect pests (especially pink bollworm and whitefly vectors)."
                )
                alt_family = "Fabaceae (Legumes) or Poaceae (Cereals)"
                alt_crops = ["Pigeon Pea (Tur)", "Chickpea (Chana)", "Sorghum (Jowar)"]
            elif curr_fam == "Cucurbitaceae":
                severity = "MEDIUM"
                deduction = 20
                specific_risks = [
                    "Downy and Powdery Mildew spores surviving in crop debris",
                    "Fruit fly pupae persistence in topsoil",
                    "Fusarium wilt seedling damping-off"
                ]
                reason = (
                    f"Both '{prev_crop}' and '{curr_crop}' are Cucurbits (Gourds/Melons). "
                    "Successive vine crops harbor severe fruit fly larvae and fungal mildews."
                )
                alt_family = "Fabaceae (Legumes) or Alliaceae (Onion/Garlic)"
                alt_crops = ["Cowpea (Chavli)", "Green Gram (Moong)", "Onion"]
            elif curr_fam == "Poaceae":
                severity = "MEDIUM"
                deduction = 15
                specific_risks = [
                    "Continuous nitrogen, phosphorus, and zinc depletion",
                    "Shallow root-pan compaction without taproot aeration",
                    "Grassy weed (e.g. Phalaris minor) seed multiplication"
                ]
                reason = (
                    f"Consecutive cereal crops ('{prev_crop}' followed by '{curr_crop}') heavily deplete soil nitrogen "
                    "and micronutrients without any restorative organic matter replenishment."
                )
                alt_family = "Fabaceae (Legumes / Pulses)"
                alt_crops = ["Chickpea (Chana)", "Soybean", "Green Gram (Moong)", "Black Gram (Urad)"]
            else:
                severity = "MEDIUM"
                deduction = 15
                specific_risks = [
                    "Soil nutrient imbalance within the same feeding layer",
                    "Shared family pest susceptibility"
                ]
                reason = f"Consecutive crops from the {curr_fam} family share similar nutrient demands and root architecture."
                alt_family = "Fabaceae (Legumes)"
                alt_crops = ["Chickpea (Chana)", "Green Gram (Moong)"]

            score_deduction += deduction

            issues.append({
                "type": "REPEATED_FAMILY",
                "severity": severity,
                "crop_1": prev_crop,
                "crop_2": curr_crop,
                "date_1": prev["date"],
                "date_2": curr["date"],
                "family": curr_fam,
                "title": f"Consecutive {curr_fam} Family: {curr_crop} after {prev_crop}",
                "description": reason,
                "risks": specific_risks
            })

            suggestions.append({
                "context": f"Break {curr_fam} Family Repetition ('{prev_crop}' → '{curr_crop}')",
                "target_family": alt_family,
                "suitable_crops": alt_crops,
                "agronomic_reason": (
                    f"Substitute or follow with {alt_family}. Legume rotation provides biological nitrogen fixation, "
                    "restores root-zone biological equilibrium, and completely interrupts host-specific disease vectors."
                ),
                "benefits": [
                    "Eliminates host plants for family-specific fungi and insect vectors",
                    "Restores balanced nitrogen and micronutrient profiles",
                    "Improves subsequent crop yield potential"
                ]
            })

        # Check C: Heavy Feeder to Heavy Feeder Exhaustion (Solanaceae -> Poaceae or Malvaceae -> Poaceae without Legume)
        elif prev["nutrient_impact"] == "heavy_feeder" and curr["nutrient_impact"] == "heavy_feeder":
            # If neither is a legume and both are heavy nutrient drainers
            if not prev["is_legume"] and not curr["is_legume"]:
                score_deduction += 10
                issues.append({
                    "type": "NUTRIENT_EXHAUSTION",
                    "severity": "LOW",
                    "crop_1": prev_crop,
                    "crop_2": curr_crop,
                    "date_1": prev["date"],
                    "date_2": curr["date"],
                    "family": f"{prev_fam} → {curr_fam}",
                    "title": f"Consecutive Heavy Feeders: {curr_crop} after {prev_crop}",
                    "description": (
                        f"Both '{prev_crop}' ({prev_fam}) and '{curr_crop}' ({curr_fam}) are heavy nutrient-demanding crops. "
                        "Without an intermediate legume or green manure crop, soil organic matter and fertility decline rapidly."
                    ),
                    "risks": [
                        "Substantial decline in organic carbon and available nitrogen",
                        "Elevated synthetic fertilizer dependency to maintain baseline yields"
                    ]
                })

                suggestions.append({
                    "context": f"Soil Fertility Recharge after '{prev_crop}'",
                    "target_family": "Fabaceae (Legumes / Green Manure)",
                    "suitable_crops": ["Green Gram (Moong)", "Cowpea (Chavli)", "Sunn Hemp", "Dhaincha"],
                    "agronomic_reason": (
                        "Introduce a short-duration pulse or green manure crop between heavy feeder seasons to replenish nitrogen "
                        "and restore soil biological vitality."
                    ),
                    "benefits": [
                        "Adds 40-70 kg nitrogen per hectare biologically",
                        "Increases soil water retention and beneficial microbial activity"
                    ]
                })

        # Check D: Beneficial Legume Rotation Recognition
        if not prev["is_legume"] and curr["is_legume"]:
            score_bonus += 12
            positive_patterns.append({
                "type": "BENEFICIAL_LEGUME_ROTATION",
                "crop_1": prev_crop,
                "crop_2": curr_crop,
                "date_1": prev["date"],
                "date_2": curr["date"],
                "title": f"Beneficial Legume Rotation: {curr_crop} after {prev_crop}",
                "description": (
                    f"Excellent agronomic practice! Planting '{curr_crop}' (Legume) after '{prev_crop}' ({prev_fam}) "
                    "biologically fixes atmospheric nitrogen, enriches soil organic matter, and breaks the pest cycle."
                ),
                "benefits": [
                    "Rhizobium root nodules fix biological atmospheric nitrogen",
                    "Breaks soil-borne pathogen cycles of the preceding crop",
                    "Enhances soil structure and reduces subsequent fertilizer cost"
                ]
            })

    # Calculate final rotation score (clamp between 10 and 100)
    raw_score = 100 - score_deduction + score_bonus
    final_score = max(10, min(100, raw_score))

    if final_score >= 80:
        rotation_rating = "Healthy Rotation"
        status_color = "green"
    elif final_score >= 50:
        rotation_rating = "Needs Attention"
        status_color = "amber"
    else:
        rotation_rating = "High Risk"
        status_color = "red"

    # Deduplicate suggestions by context
    unique_suggestions = []
    seen_contexts = set()
    for s in suggestions:
        if s["context"] not in seen_contexts:
            seen_contexts.add(s["context"])
            unique_suggestions.append(s)

    return {
        "farm_id": farm_id,
        "farm_name": farm_name,
        "total_records": total_records,
        "crop_count": total_records,
        "has_sufficient_history": True,
        "insufficient_reason": None,
        "timeline": timeline,
        "issues": issues,
        "issues_count": len(issues),
        "suggestions": unique_suggestions,
        "positive_patterns": positive_patterns,
        "rotation_score": final_score,
        "rotation_rating": rotation_rating,
        "status_color": status_color
    }


def analyze_all_farmer_farms(user_id, farm_id=None, db_conn=None):
    """
    Perform crop rotation analysis for one or all farms belonging to a farmer.
    Guarantees strict farmer data isolation.
    """
    from config import get_db_connection

    conn = db_conn or get_db_connection()
    should_close = db_conn is None

    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch farmer's farms
        farm_query = "SELECT id, farm_name, location, total_area, area_unit FROM farms WHERE user_id = %s"
        farm_params = [user_id]
        if farm_id and str(farm_id).isdigit() and int(farm_id) > 0:
            farm_query += " AND id = %s"
            farm_params.append(int(farm_id))
        farm_query += " ORDER BY farm_name ASC, id ASC"

        cursor.execute(farm_query, tuple(farm_params))
        farms = cursor.fetchall() or []

        # If user has no registered farms, create a virtual unassigned farm entry
        if not farms:
            farms = [{
                "id": None,
                "farm_name": "General Farm / Unassigned Plots",
                "location": "",
                "total_area": 0.0,
                "area_unit": "Acres"
            }]

        results = []

        for f in farms:
            f_id = f["id"]

            # Query historical crops from `crops`
            if f_id:
                cursor.execute("""
                    SELECT id, crop_name, variety, planting_date, cultivated_area, area_unit, growth_status, field_location, created_at
                    FROM crops
                    WHERE user_id = %s AND farm_id = %s
                    ORDER BY COALESCE(planting_date, created_at) ASC, id ASC
                """, (user_id, f_id))
            else:
                cursor.execute("""
                    SELECT id, crop_name, variety, planting_date, cultivated_area, area_unit, growth_status, field_location, created_at
                    FROM crops
                    WHERE user_id = %s AND (farm_id IS NULL OR farm_id = 0)
                    ORDER BY COALESCE(planting_date, created_at) ASC, id ASC
                """, (user_id,))
            hist_crops = cursor.fetchall() or []

            # Query planned crops from `crop_plans`
            if f_id:
                cursor.execute("""
                    SELECT id, crop_name, variety, season, planning_year, planned_sowing_date, expected_harvest_date, land_area, area_unit, status, field_location, created_at
                    FROM crop_plans
                    WHERE user_id = %s AND farm_id = %s
                    ORDER BY COALESCE(planned_sowing_date, created_at) ASC, id ASC
                """, (user_id, f_id))
            else:
                cursor.execute("""
                    SELECT id, crop_name, variety, season, planning_year, planned_sowing_date, expected_harvest_date, land_area, area_unit, status, field_location, created_at
                    FROM crop_plans
                    WHERE user_id = %s AND (farm_id IS NULL OR farm_id = 0)
                    ORDER BY COALESCE(planned_sowing_date, created_at) ASC, id ASC
                """, (user_id,))
            plan_crops = cursor.fetchall() or []

            analysis = analyze_crop_rotation_for_farm(f, hist_crops, plan_crops)
            results.append(analysis)

        return results

    finally:
        if should_close and conn:
            conn.close()
