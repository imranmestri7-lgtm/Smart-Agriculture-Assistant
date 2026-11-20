"""
AgriSmart - Seasonal & Soil-Aware Crop Recommendation Engine
Feature Upgrade 9, Phase 2 (Part 2)

Provides agronomic crop recommendations for Maharashtra and Indian agro-climatic zones based on:
1. Seasonal appropriateness (Kharif, Rabi, Zaid) with sowing and harvest windows.
2. Soil compatibility (Black cotton / Regur, Loamy, Sandy Loam, Clay, Red / Laterite, Silt).
3. Previous crop history & crop rotation risk assessment (integrating Part 1 botanical rules).
4. Strict multi-tenant farmer data isolation (JWT user_id enforcement).
5. Transparent agronomic reasoning distinguishing location-specific advice from general guidance.
"""

from datetime import date, datetime
import re

from config import get_db_connection
from utils.crop_rotation_engine import classify_crop, _normalize_name


# =============================================================================
# SOIL NORMALIZATION & PROFILES
# =============================================================================

SOIL_ALIASES = {
    # Black Cotton / Regur
    "black": "black",
    "black cotton": "black",
    "black cotton soil": "black",
    "regur": "black",
    "काळी जमीन": "black",
    "काळी कापशी जमीन": "black",
    "काली मिट्टी": "black",
    "regur soil": "black",
    "heavy clay loam": "black",
    # Loamy
    "loamy": "loamy",
    "loam": "loamy",
    "alluvial": "loamy",
    "गाळाची जमीन": "loamy",
    "सुपीक जमीन": "loamy",
    "दोमट मिट्टी": "loamy",
    "alluvial soil": "loamy",
    "medium loam": "loamy",
    # Sandy / Sandy Loam
    "sandy": "sandy",
    "sandy loam": "sandy",
    "sand": "sandy",
    "वाळूयुक्त जमीन": "sandy",
    "रेतीली मिट्टी": "sandy",
    "light soil": "sandy",
    # Red / Laterite
    "red": "red",
    "laterite": "red",
    "red soil": "red",
    "laterite soil": "red",
    "तांबडी जमीन": "red",
    "लाल मिट्टी": "red",
    "red sandy loam": "red",
    # Clay
    "clay": "clay",
    "heavy clay": "clay",
    "चिकणमाती": "clay",
    "चिकणी मिट्टी": "clay",
    # Silt
    "silt": "silt",
    "silty": "silt",
    "silt loam": "silt",
    "गाळ जमीन": "silt",
    "सिल्ट मिट्टी": "silt",
}

SOIL_DISPLAY_INFO = {
    "black": {
        "key": "black",
        "display_name": "Black Cotton Soil (Regur)",
        "name_mr": "काळी कापशी जमीन (रेगूर)",
        "name_hi": "काली मिट्टी (रेगुर)",
        "characteristics": "High clay content (montmorillonite), deep profile, superior moisture retention, rich in calcium, potassium, and magnesium."
    },
    "loamy": {
        "key": "loamy",
        "display_name": "Loamy / Alluvial Soil",
        "name_mr": "गाळाची / सुपीक जमीन",
        "name_hi": "दोमट मिट्टी",
        "characteristics": "Balanced blend of sand, silt, and clay; optimal drainage and aeration; rich organic crumb structure."
    },
    "sandy": {
        "key": "sandy",
        "display_name": "Sandy Loam / Sandy Soil",
        "name_mr": "वाळूयुक्त जमीन",
        "name_hi": "रेतीली मिट्टी",
        "characteristics": "Rapid water infiltration, porous, warms up quickly; low water and nutrient holding capacity."
    },
    "red": {
        "key": "red",
        "display_name": "Red / Laterite Soil",
        "name_mr": "तांबडी जमीन",
        "name_hi": "लाल / लॅटेराइट मिट्टी",
        "characteristics": "Rich in iron oxides, mildly acidic to neutral; free-draining; requires organic matter and phosphorus supplementation."
    },
    "clay": {
        "key": "clay",
        "display_name": "Clay Soil",
        "name_mr": "चिकणमाती जमीन",
        "name_hi": "चिकनी मिट्टी",
        "characteristics": "Very high water retention, slow drainage, prone to waterlogging; sticky when wet, compacts easily."
    },
    "silt": {
        "key": "silt",
        "display_name": "Silt Soil",
        "name_mr": "गाळ जमीन",
        "name_hi": "सिल्ट मिट्टी",
        "characteristics": "Fine texture, smooth, good moisture holding; prone to surface crusting after drying."
    }
}


def normalize_soil_type(soil_str):
    """Normalize user input or database value into standard soil key."""
    if not soil_str:
        return None
    cleaned = str(soil_str).strip().lower()
    return SOIL_ALIASES.get(cleaned, None)


# =============================================================================
# SEASONAL LOGIC FOR MAHARASHTRA & CENTRAL INDIA
# =============================================================================

def get_current_indian_season(ref_date=None):
    """
    Determine current agricultural season in Maharashtra.
    - Kharif: June 1 – October 15
    - Rabi: October 16 – February 15
    - Zaid: February 16 – May 31
    """
    d = ref_date or date.today()
    month = d.month
    day = d.day

    if (month == 6 and day >= 1) or (7 <= month <= 9) or (month == 10 and day <= 15):
        return "Kharif"
    elif (month == 10 and day >= 16) or (month in (11, 12, 1)) or (month == 2 and day <= 15):
        return "Rabi"
    else:
        return "Zaid"


# =============================================================================
# AGRONOMIC CROP KNOWLEDGE BASE (ICAR / MPKV RAHURI / PDKV AKOLA REFERENCES)
# =============================================================================

MAHARASHTRA_CROP_CATALOG = [
    # -------------------------------------------------------------------------
    # KHARIF CROPS (Monsoon)
    # -------------------------------------------------------------------------
    {
        "crop_name": "Soybean",
        "scientific_name": "Glycine max",
        "family": "Fabaceae",
        "season": "Kharif",
        "sowing_window": "June 15 – July 15",
        "duration_days_min": 90,
        "duration_days_max": 105,
        "expected_harvest_window": "September – October",
        "is_legume": True,
        "nitrogen_fixer": True,
        "optimal_soils": ["black", "loamy"],
        "compatible_soils": ["clay", "silt"],
        "unsuitable_soils": ["sandy"],
        "soil_reasons": {
            "black": "Deep black soils retain the consistent root moisture essential for pod filling and nitrogen fixation without rapid drying.",
            "loamy": "Loamy soil offers ideal root aeration and balanced nutrient availability for rapid vegetative canopy development.",
            "clay": "Clay soils sustain adequate moisture, though surface drainage must be maintained during heavy monsoon spells.",
            "sandy": "Sandy soils dry out too rapidly between rainfall events, causing moisture stress during critical flowering and pod development stages."
        },
        "regional_suitability": "Prime crop for Vidarbha, Marathwada, and Western Maharashtra (Nashik, Kolhapur, Sangli).",
        "local_names": {"en": "Soybean", "mr": "सोयाबीन", "hi": "सोयाबीन"},
        "agronomic_highlights": [
            "Symbiotic Rhizobium nodules biologically fix 40–80 kg N/ha into the soil.",
            "Excellent Kharif break crop prior to Rabi Wheat or Chickpea.",
            "Matures within 90–105 days, leaving ample residual soil moisture for winter crops."
        ],
        "alternatives": ["Green Gram (Moong)", "Pigeon Pea (Tur)", "Black Gram (Urad)"]
    },
    {
        "crop_name": "Cotton",
        "scientific_name": "Gossypium hirsutum",
        "family": "Malvaceae",
        "season": "Kharif",
        "sowing_window": "June 15 – July 10",
        "duration_days_min": 150,
        "duration_days_max": 180,
        "expected_harvest_window": "November – January",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["black"],
        "compatible_soils": ["loamy", "clay"],
        "unsuitable_soils": ["sandy", "red"],
        "soil_reasons": {
            "black": "Deep black cotton soils (>90 cm depth) provide the continuous subsoil moisture and calcium needed for long-season boll development.",
            "loamy": "Fertile loams support healthy vegetative growth, though supplementary irrigation is required during post-monsoon boll opening.",
            "sandy": "Sandy soils cannot store sufficient moisture for a 160-day deep-rooted crop, resulting in premature boll shedding.",
            "red": "Shallow red laterite soils typically lack the moisture-retention depth and exchangeable bases needed for high-yield cotton."
        },
        "regional_suitability": "Leading commercial cash crop of Vidarbha, Marathwada, and Khandesh regions.",
        "local_names": {"en": "Cotton (Kapas)", "mr": "कापूस", "hi": "कपास"},
        "agronomic_highlights": [
            "Deep taproot utilizes sub-surface moisture late into the winter season.",
            "High revenue commercial crop under timely pest and nutrient management.",
            "Must be rotated with legumes every 1–2 cycles to prevent pink bollworm persistence."
        ],
        "alternatives": ["Soybean", "Pigeon Pea (Tur)", "Sorghum (Jowar)"]
    },
    {
        "crop_name": "Pigeon Pea",
        "scientific_name": "Cajanus cajan",
        "family": "Fabaceae",
        "season": "Kharif",
        "sowing_window": "June 15 – July 10",
        "duration_days_min": 150,
        "duration_days_max": 180,
        "expected_harvest_window": "December – January",
        "is_legume": True,
        "nitrogen_fixer": True,
        "optimal_soils": ["black", "loamy", "red"],
        "compatible_soils": ["clay", "silt"],
        "unsuitable_soils": ["sandy"],
        "soil_reasons": {
            "black": "Tolerates medium to deep black soils, sending deep taproots (up to 2 meters) to break subsoil hardpans.",
            "loamy": "Excellent root development and high nodulation in friable, well-aerated loams.",
            "red": "Deep red loamy soils provide good drainage that prevents Phytophthora stem blight.",
            "sandy": "Shallow sandy soils restrict deep root establishment and cause drought stress during winter pod filling."
        },
        "regional_suitability": "Widely grown across Marathwada, Vidarbha, and Solapur, often intercropped with Soybean or Cotton.",
        "local_names": {"en": "Pigeon Pea (Tur / Arhar)", "mr": "तूर", "hi": "अरहर / तूर"},
        "agronomic_highlights": [
            "Fixes 40–100 kg atmospheric nitrogen per hectare and sheds organic leaf litter.",
            "Extensive deep taproot system aerates compacted soil strata.",
            "Drought-resilient pulse crop providing vital food security and high market value."
        ],
        "alternatives": ["Soybean", "Chickpea", "Black Gram (Urad)"]
    },
    {
        "crop_name": "Rice",
        "scientific_name": "Oryza sativa",
        "family": "Poaceae",
        "season": "Kharif",
        "sowing_window": "Nursery: June; Transplanting: July",
        "duration_days_min": 110,
        "duration_days_max": 135,
        "expected_harvest_window": "October – November",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["clay", "red"],
        "compatible_soils": ["black", "silt", "loamy"],
        "unsuitable_soils": ["sandy"],
        "soil_reasons": {
            "clay": "Heavy clay holds standing water with minimal percolation loss, ideal for lowland paddy puddling.",
            "red": "Red lateritic soils in high-rainfall Konkan and Western Ghats support outstanding wet-season rice cultivation.",
            "black": "Black soils support paddy under controlled irrigation, though heavy stickiness complicates mechanical puddling.",
            "sandy": "Sandy soils allow rapid water percolation, making standing water maintenance impossible without immense water loss."
        },
        "regional_suitability": "Staple crop across Konkan coastal strip, Western Ghat valleys, and Eastern Vidarbha (Bhandara, Gondia).",
        "local_names": {"en": "Paddy / Rice", "mr": "भात / धान", "hi": "धान / चावल"},
        "agronomic_highlights": [
            "Thrives in heavy monsoon rainfall and lowland waterlogged conditions where other crops perish.",
            "Excellent staple food crop with robust local mandi markets.",
            "Must be followed by a restorative pulse or oilseed in Rabi to rebuild soil structure."
        ],
        "alternatives": ["Finger Millet (Ragi)", "Maize", "Soybean"]
    },
    {
        "crop_name": "Maize",
        "scientific_name": "Zea mays",
        "family": "Poaceae",
        "season": "Kharif",
        "sowing_window": "June 15 – July 15",
        "duration_days_min": 95,
        "duration_days_max": 115,
        "expected_harvest_window": "September – October",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["loamy", "black"],
        "compatible_soils": ["silt", "red"],
        "unsuitable_soils": ["clay", "sandy"],
        "soil_reasons": {
            "loamy": "Deep, well-drained loams rich in organic matter provide the balanced moisture and aeration maize roots require.",
            "black": "Medium black soils support vigorous vegetative growth if ridge-and-furrow planting avoids waterlogging.",
            "clay": "Poorly drained heavy clay leads to water stagnation, causing yellowing and root asphyxiation.",
            "sandy": "Rapid nutrient leaching in sandy soils deprives fast-growing maize of critical nitrogen and zinc."
        },
        "regional_suitability": "Popular in Nashik, Dhule, Jalgaon, Aurangabad, and Kolhapur for grain and poultry feed.",
        "local_names": {"en": "Maize / Corn", "mr": "मका", "hi": "मक्का"},
        "agronomic_highlights": [
            "High biomass and grain yield potential under balanced NPK fertilization.",
            "Dual-purpose: nutritious green fodder for livestock and commercial grain.",
            "Follow with leguminous Chickpea or Onion in Rabi."
        ],
        "alternatives": ["Sorghum (Jowar)", "Pearl Millet (Bajra)", "Soybean"]
    },
    {
        "crop_name": "Pearl Millet",
        "scientific_name": "Pennisetum glaucum",
        "family": "Poaceae",
        "season": "Kharif",
        "sowing_window": "June 20 – July 20",
        "duration_days_min": 75,
        "duration_days_max": 90,
        "expected_harvest_window": "September – October",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["sandy", "red", "loamy"],
        "compatible_soils": ["black", "silt"],
        "unsuitable_soils": ["clay"],
        "soil_reasons": {
            "sandy": "Remarkably drought-hardy; fibrous root system efficiently extracts water from light, sandy topsoils.",
            "red": "Tolerates shallow, well-drained red soils in rainfed rain-shadow tracts.",
            "loamy": "Produces exceptional grain yields in light to medium loamy soils.",
            "clay": "Susceptible to waterlogging and seedling rot in heavy, poorly drained clay soils."
        },
        "regional_suitability": "Thrives in rain-shadow drought-prone belts of Western Maharashtra and Marathwada (Ahmednagar, Beed, Jalna, Solapur).",
        "local_names": {"en": "Pearl Millet (Bajra)", "mr": "बाजरी", "hi": "बाजरा"},
        "agronomic_highlights": [
            "High climate resilience; tolerates dry spells and temperatures above 40°C.",
            "Nutrient-dense millet rich in iron, zinc, and dietary fiber.",
            "Requires 30–40% less water than maize or rice."
        ],
        "alternatives": ["Sorghum (Jowar)", "Green Gram (Moong)", "Cowpea (Chavli)"]
    },
    {
        "crop_name": "Green Gram",
        "scientific_name": "Vigna radiata",
        "family": "Fabaceae",
        "season": "Kharif",
        "sowing_window": "June 15 – July 10",
        "duration_days_min": 60,
        "duration_days_max": 70,
        "expected_harvest_window": "August – September",
        "is_legume": True,
        "nitrogen_fixer": True,
        "optimal_soils": ["loamy", "black"],
        "compatible_soils": ["red", "silt"],
        "unsuitable_soils": ["clay", "sandy"],
        "soil_reasons": {
            "loamy": "Well-aerated loams facilitate rapid root nodulation and early synchronous pod maturation.",
            "black": "Medium black soils conserve ideal moisture for this ultra-short duration pulse.",
            "clay": "Heavy waterlogged clay induces seedling damping-off and root rot.",
            "sandy": "Very coarse sand causes quick moisture depletion during flowering."
        },
        "regional_suitability": "Popular short Kharif crop across Marathwada, Vidarbha, and Khandesh.",
        "local_names": {"en": "Green Gram (Moong)", "mr": "मूग", "hi": "मूंग"},
        "agronomic_highlights": [
            "Fastest-maturing pulse (60–70 days); vacates fields early for timely Rabi sowing.",
            "Enriches soil with 30–40 kg N/ha through biological fixation.",
            "Excellent catch crop providing quick cash flow."
        ],
        "alternatives": ["Black Gram (Urad)", "Cowpea (Chavli)", "Soybean"]
    },
    {
        "crop_name": "Groundnut",
        "scientific_name": "Arachis hypogaea",
        "family": "Fabaceae",
        "season": "Kharif",
        "sowing_window": "June 20 – July 15",
        "duration_days_min": 105,
        "duration_days_max": 120,
        "expected_harvest_window": "October – November",
        "is_legume": True,
        "nitrogen_fixer": True,
        "optimal_soils": ["sandy", "red", "loamy"],
        "compatible_soils": ["silt"],
        "unsuitable_soils": ["black", "clay"],
        "soil_reasons": {
            "sandy": "Loose, friable sandy loam allows flower pegs (gynophores) to effortlessly penetrate into soil and expand pods.",
            "red": "Light red soils provide easy pod development and smooth, damage-free harvesting.",
            "black": "Heavy sticky black soils severely impede peg penetration; upon drying, hard clods cause severe pod breakage during digging.",
            "clay": "Dense clay compaction leads to deformed pods, poor aeration, and high pod loss at harvest."
        },
        "regional_suitability": "Grown in Dhule, Jalgaon, Kolhapur, Satara, and coastal Konkan tracts with light soils.",
        "local_names": {"en": "Groundnut (Peanut)", "mr": "भुईमूग", "hi": "मूंगफली"},
        "agronomic_highlights": [
            "Valuable dual-purpose oilseed and high-protein fodder crop.",
            "Biological nitrogen fixer enriching soil organic nitrogen.",
            "Strictly requires loose, non-sticky topsoil for optimal pod yield."
        ],
        "alternatives": ["Soybean", "Sesame (Til)", "Cowpea (Chavli)"]
    },

    # -------------------------------------------------------------------------
    # RABI CROPS (Winter)
    # -------------------------------------------------------------------------
    {
        "crop_name": "Wheat",
        "scientific_name": "Triticum aestivum",
        "family": "Poaceae",
        "season": "Rabi",
        "sowing_window": "October 25 – November 20",
        "duration_days_min": 110,
        "duration_days_max": 125,
        "expected_harvest_window": "March – April",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["black", "loamy", "clay"],
        "compatible_soils": ["silt"],
        "unsuitable_soils": ["sandy", "red"],
        "soil_reasons": {
            "black": "Deep black soils hold residual winter moisture and maintain the cool root zone required for wheat tillering and grain filling.",
            "loamy": "Fertile loamy soils offer an ideal physical environment for crown root initiation and uniform nutrient absorption.",
            "clay": "Clay soils sustain steady moisture through the winter reproductive stages, though light irrigations are advised.",
            "sandy": "Sandy soils dry too quickly under winter winds, requiring excessively frequent irrigations that leach nutrients."
        },
        "regional_suitability": "Premier Rabi grain across Western Maharashtra (Nashik, Pune, Ahmednagar) and Vidarbha (Nagpur, Amravati).",
        "local_names": {"en": "Wheat", "mr": "गहू", "hi": "गेहूं"},
        "agronomic_highlights": [
            "Staple winter cereal with reliable market demand and high yield potential.",
            "Performs exceptionally well following Kharif legumes (Soybean, Moong) that leave residual nitrogen.",
            "Requires 4–5 timely irrigations at critical stages (CRI, tillering, flowering, grain filling)."
        ],
        "alternatives": ["Chickpea (Chana)", "Rabi Sorghum (Jowar)", "Mustard"]
    },
    {
        "crop_name": "Chickpea",
        "scientific_name": "Cicer arietinum",
        "family": "Fabaceae",
        "season": "Rabi",
        "sowing_window": "October 10 – November 15",
        "duration_days_min": 90,
        "duration_days_max": 110,
        "expected_harvest_window": "January – February",
        "is_legume": True,
        "nitrogen_fixer": True,
        "optimal_soils": ["black", "loamy"],
        "compatible_soils": ["clay", "silt"],
        "unsuitable_soils": ["sandy"],
        "soil_reasons": {
            "black": "Medium to deep black soils conserve residual monsoon moisture, perfectly sustaining rainfed and semi-irrigated chickpea roots.",
            "loamy": "Loams promote deep taproot growth and high root nodulation with minimal risk of wilt.",
            "clay": "Clay soils perform well if well-drained; over-irrigation must be avoided to prevent collar rot and wilt.",
            "sandy": "Sandy soils dry out rapidly in winter, causing moisture stress before pod setting."
        },
        "regional_suitability": "Major pulse across Marathwada, Vidarbha, Khandesh, and Western Maharashtra.",
        "local_names": {"en": "Chickpea (Chana / Gram)", "mr": "हरभरा", "hi": "चना"},
        "agronomic_highlights": [
            "Fixes 30–50 kg N/ha biologically and breaks cereal pest and grassy weed cycles.",
            "Low water requirement; excels on residual soil moisture with only 1–2 protective waterings.",
            "Ideal rotation crop following Kharif Cotton, Maize, or Pearl Millet."
        ],
        "alternatives": ["Wheat", "Rabi Sorghum", "Lentil (Masoor)"]
    },
    {
        "crop_name": "Rabi Sorghum",
        "scientific_name": "Sorghum bicolor",
        "family": "Poaceae",
        "season": "Rabi",
        "sowing_window": "September 15 – October 15",
        "duration_days_min": 115,
        "duration_days_max": 130,
        "expected_harvest_window": "January – February",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["black"],
        "compatible_soils": ["loamy", "clay"],
        "unsuitable_soils": ["sandy", "red"],
        "soil_reasons": {
            "black": "Deep black soils (>60 cm depth) store conserved monsoon moisture critical for post-rainy sorghum development.",
            "loamy": "Medium loams support good growth under 1–2 supplementary irrigations at boot leaf stage.",
            "sandy": "Shallow sandy soils lose stored moisture rapidly, causing severe terminal drought before grain formation."
        },
        "regional_suitability": "Famous 'Maldhandi' jowar grown across Solapur, Ahmednagar, Pune, Satara, and Marathwada.",
        "local_names": {"en": "Rabi Sorghum (Jowar)", "mr": "रब्बी ज्वारी (मालदांडी)", "hi": "रबी ज्वार"},
        "agronomic_highlights": [
            "Produces premium pearly grain with sweet, nutritious stover (kadbi) vital for livestock.",
            "Thrives on receding soil moisture in deep black soils with zero or minimal irrigation.",
            "Deep fibrous root system binds soil and prevents winter erosion."
        ],
        "alternatives": ["Chickpea (Chana)", "Wheat", "Safflower (Kardi)"]
    },
    {
        "crop_name": "Onion",
        "scientific_name": "Allium cepa",
        "family": "Alliaceae",
        "season": "Rabi",
        "sowing_window": "Nursery: Oct; Transplanting: Nov – Dec",
        "duration_days_min": 120,
        "duration_days_max": 135,
        "expected_harvest_window": "March – May",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["loamy", "sandy"],
        "compatible_soils": ["black", "silt"],
        "unsuitable_soils": ["clay"],
        "soil_reasons": {
            "loamy": "Friable, organic-rich loamy soil enables symmetrical bulb enlargement, excellent skin color, and easy uprooting.",
            "sandy": "Well-manured sandy loam prevents bulb distortion and minimizes fungal root rots.",
            "black": "Medium black soils produce good bulbs if raised beds prevent water accumulation around necks.",
            "clay": "Heavy compact clay resists bulb expansion, causing split, misshapen bulbs and post-harvest storage decay."
        },
        "regional_suitability": "Maharashtra's premier cash vegetable (Nashik, Ahmednagar, Pune, Solapur leading national production).",
        "local_names": {"en": "Onion", "mr": "कांदा", "hi": "प्याज"},
        "agronomic_highlights": [
            "High commercial value with long post-harvest storage potential in chawls.",
            "Shallow feeding root system benefits from drip fertigation and raised-bed planting.",
            "Must be rotated with non-allium crops to prevent purple blotch and basal rot spore buildup."
        ],
        "alternatives": ["Garlic", "Chickpea", "Wheat"]
    },
    {
        "crop_name": "Mustard",
        "scientific_name": "Brassica juncea",
        "family": "Brassicaceae",
        "season": "Rabi",
        "sowing_window": "October 1 – October 25",
        "duration_days_min": 100,
        "duration_days_max": 115,
        "expected_harvest_window": "January – February",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["loamy", "sandy"],
        "compatible_soils": ["black", "silt"],
        "unsuitable_soils": ["clay"],
        "soil_reasons": {
            "loamy": "Fertile loams provide ideal moisture and nutrient drainage for deep root penetration and siliqua (pod) development.",
            "sandy": "Sandy loams warm up quickly and prevent white rust, allowing efficient short-season growth.",
            "clay": "Heavy clay waterlogging causes collar rot and restricts root aeration."
        },
        "regional_suitability": "Grown in Khandesh, Vidarbha, and North Maharashtra as pure crop or intercrop.",
        "local_names": {"en": "Mustard (Rai / Sarson)", "mr": "मोहरी / राई", "hi": "सरसों / राई"},
        "agronomic_highlights": [
            "Low water requirement (only 2–3 irrigations required).",
            "High seed oil content (38–42%) with strong local demand.",
            "Glucosinolate root exudates act as natural biofumigants suppressing soil nematodes."
        ],
        "alternatives": ["Chickpea", "Wheat", "Safflower"]
    },

    # -------------------------------------------------------------------------
    # ZAID CROPS (Summer)
    # -------------------------------------------------------------------------
    {
        "crop_name": "Summer Green Gram",
        "scientific_name": "Vigna radiata",
        "family": "Fabaceae",
        "season": "Zaid",
        "sowing_window": "February 15 – March 10",
        "duration_days_min": 60,
        "duration_days_max": 65,
        "expected_harvest_window": "April – May",
        "is_legume": True,
        "nitrogen_fixer": True,
        "optimal_soils": ["loamy", "black"],
        "compatible_soils": ["silt", "red"],
        "unsuitable_soils": ["sandy", "clay"],
        "soil_reasons": {
            "loamy": "Optimal capillary water movement and root aeration under hot summer sun with controlled irrigation.",
            "black": "Deep black soils retain moisture between 4–5 day summer irrigation intervals, preventing flower drop.",
            "sandy": "Extreme summer evaporation in sandy soils causes moisture stress and flower abscission.",
            "clay": "Heavy clay develops deep baking cracks under summer heat that tear delicate root hairs."
        },
        "regional_suitability": "Ideal summer catch crop where assured tube-well or canal irrigation exists.",
        "local_names": {"en": "Summer Moong", "mr": "उन्हाळी मूग", "hi": "ग्रीष्मकालीन मूंग"},
        "agronomic_highlights": [
            "Quick 60-day turnover fitting snugly between Rabi harvest and Kharif sowing.",
            "Leaves 35–45 kg N/ha in soil, greatly reducing Kharif fertilizer costs.",
            "High summer market prices and low incidence of foliar diseases under dry air."
        ],
        "alternatives": ["Summer Groundnut", "Cowpea (Chavli)", "Fodder Sorghum"]
    },
    {
        "crop_name": "Summer Groundnut",
        "scientific_name": "Arachis hypogaea",
        "family": "Fabaceae",
        "season": "Zaid",
        "sowing_window": "January 15 – February 15",
        "duration_days_min": 115,
        "duration_days_max": 125,
        "expected_harvest_window": "May – June",
        "is_legume": True,
        "nitrogen_fixer": True,
        "optimal_soils": ["sandy", "loamy", "red"],
        "compatible_soils": ["silt"],
        "unsuitable_soils": ["black", "clay"],
        "soil_reasons": {
            "sandy": "Warm, friable sandy loam accelerates pegging and yields bright, unblemished pods with zero harvesting loss.",
            "loamy": "Balanced loams produce dense pod clusters with high kernel shelling percentage under regular watering.",
            "black": "Heavy clay baking in summer heat makes pod retrieval virtually impossible without destroying vines.",
            "clay": "Severe soil compaction restricts subterranean pod development."
        },
        "regional_suitability": "Thrives in Western Maharashtra and Marathwada wherever summer irrigation is assured.",
        "local_names": {"en": "Summer Groundnut", "mr": "उन्हाळी भुईमूग", "hi": "ग्रीष्मकालीन मूंगफली"},
        "agronomic_highlights": [
            "Significantly higher pod yield and oil content than rainfed Kharif crop due to abundant sunlight.",
            "Low pest pressure compared to monsoon conditions.",
            "Fixes nitrogen and improves friability for subsequent Kharif cereals."
        ],
        "alternatives": ["Summer Green Gram (Moong)", "Sesame (Til)", "Watermelon"]
    },
    {
        "crop_name": "Watermelon",
        "scientific_name": "Citrullus lanatus",
        "family": "Cucurbitaceae",
        "season": "Zaid",
        "sowing_window": "January 15 – February 28",
        "duration_days_min": 80,
        "duration_days_max": 95,
        "expected_harvest_window": "April – May",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["sandy", "loamy"],
        "compatible_soils": ["red", "silt"],
        "unsuitable_soils": ["clay", "black"],
        "soil_reasons": {
            "sandy": "Porous sandy soil warms up rapidly in late winter, promoting vigorous vine run and rapid root respiration.",
            "loamy": "Fertile loams provide continuous nutrient delivery under drip fertigation, yielding large sweet fruit.",
            "clay": "Excess moisture retention in heavy clay induces root rot and damping-off during early vine growth.",
            "black": "Wet black soil causes soil-fruit contact fungal decay and uneven sugar development."
        },
        "regional_suitability": "Major summer cash crop across Ahmednagar, Solapur, Pune, Jalgaon, and river basin soils.",
        "local_names": {"en": "Watermelon", "mr": "कलिंगड / टरबूज", "hi": "तरबूज"},
        "agronomic_highlights": [
            "Rapid 80–90 day cycle yielding 25–40 tonnes/ha under drip and plastic mulch.",
            "High summer cash return coinciding with peak heatwave demand.",
            "Rotate with legumes or cereals; avoid repeating cucurbit family crops to prevent Fusarium wilt."
        ],
        "alternatives": ["Muskmelon", "Cucumber", "Summer Moong"]
    },
    {
        "crop_name": "Cucumber",
        "scientific_name": "Cucumis sativus",
        "family": "Cucurbitaceae",
        "season": "Zaid",
        "sowing_window": "February 1 – March 15",
        "duration_days_min": 65,
        "duration_days_max": 80,
        "expected_harvest_window": "April – June",
        "is_legume": False,
        "nitrogen_fixer": False,
        "optimal_soils": ["loamy", "sandy"],
        "compatible_soils": ["silt", "red"],
        "unsuitable_soils": ["clay"],
        "soil_reasons": {
            "loamy": "Deep, well-drained loams provide consistent moisture required for straight, non-bitter, crisp fruit.",
            "sandy": "Sandy loam enables early harvesting and rapid root growth under frequent drip irrigation.",
            "clay": "Heavy drainage stagnation causes collar rot and downy mildew proliferation."
        },
        "regional_suitability": "Widespread around peri-urban consumption belts (Pune, Nashik, Thane, Nagpur).",
        "local_names": {"en": "Cucumber", "mr": "काकडी", "hi": "खीरा"},
        "agronomic_highlights": [
            "Short duration with multiple pickings over 4–6 weeks.",
            "High market liquidity in fresh vegetable wholesale mandis.",
            "Respond exceptionally well to trellising and organic mulching."
        ],
        "alternatives": ["Bottle Gourd (Dudhi)", "Bitter Gourd (Karela)", "Summer Moong"]
    }
]


# =============================================================================
# EVALUATION ENGINES (SOIL & ROTATION COMPATIBILITY)
# =============================================================================

def evaluate_soil_compatibility(crop_def, soil_key):
    """
    Evaluate crop suitability against a normalized soil key.
    Returns (compatibility_label, suitability_score, agronomic_reason)
    """
    if not soil_key:
        return (
            "General Guidance (Soil Unknown)",
            70,
            "Soil type is not registered for this farm. Suitability is evaluated on regional Maharashtra agro-climatic averages. Register your farm soil type for field-specific matching."
        )

    soil_key = soil_key.lower().strip()

    if soil_key in crop_def.get("optimal_soils", []):
        reason = crop_def.get("soil_reasons", {}).get(soil_key) or (
            f"{SOIL_DISPLAY_INFO.get(soil_key, {}).get('display_name', soil_key)} offers optimal physical structure, "
            f"aeration, and nutrient retention for {crop_def['crop_name']}."
        )
        return ("Optimal", 95, reason)

    elif soil_key in crop_def.get("compatible_soils", []):
        reason = crop_def.get("soil_reasons", {}).get(soil_key) or (
            f"{SOIL_DISPLAY_INFO.get(soil_key, {}).get('display_name', soil_key)} is compatible with {crop_def['crop_name']} "
            "under standard soil and moisture management practices."
        )
        return ("Compatible", 75, reason)

    elif soil_key in crop_def.get("unsuitable_soils", []):
        reason = crop_def.get("soil_reasons", {}).get(soil_key) or (
            f"{SOIL_DISPLAY_INFO.get(soil_key, {}).get('display_name', soil_key)} presents physical or drainage constraints "
            f"that restrict healthy growth or harvesting of {crop_def['crop_name']}."
        )
        return ("Unsuitable", 25, reason)

    else:
        return (
            "Moderate",
            55,
            f"{SOIL_DISPLAY_INFO.get(soil_key, {}).get('display_name', soil_key)} has intermediate suitability for {crop_def['crop_name']}; monitor drainage and organic matter."
        )


def evaluate_rotation_impact(candidate_crop_def, previous_crop_info):
    """
    Assess crop rotation impact between previous crop and candidate crop.
    Returns dict with rotation_status, risk_level, notes, and suggested alternatives.
    """
    if not previous_crop_info or not previous_crop_info.get("crop_name"):
        return {
            "rotation_status": "Neutral",
            "rotation_risk_level": "NONE",
            "is_rotation_hazard": False,
            "is_rotation_benefit": False,
            "rotation_notes": "No preceding crop recorded on this farm plot; rotational sequence is open.",
            "alternatives": []
        }

    prev_name = previous_crop_info.get("crop_name", "").strip()
    prev_class = classify_crop(prev_name)
    prev_family = prev_class.get("family", "Unknown")
    prev_is_legume = prev_class.get("is_legume", False)

    cand_name = candidate_crop_def["crop_name"]
    cand_family = candidate_crop_def["family"]
    cand_is_legume = candidate_crop_def.get("is_legume", False)

    prev_norm = _normalize_name(prev_name)
    cand_norm = _normalize_name(cand_name)

    # 1. Monoculture: Identical Crop
    if prev_norm and cand_norm and (prev_norm == cand_norm or prev_norm in cand_norm or cand_norm in prev_norm):
        return {
            "rotation_status": "Rotation Hazard",
            "rotation_risk_level": "HIGH",
            "is_rotation_hazard": True,
            "is_rotation_benefit": False,
            "rotation_notes": (
                f"Repeated Monoculture Warning: Planting '{cand_name}' immediately after '{prev_name}' "
                "exhausts identical root-zone nutrient reserves and dramatically multiplies crop-specific soil fungi and pests."
            ),
            "alternatives": candidate_crop_def.get("alternatives", ["Chickpea", "Soybean", "Green Gram"])
        }

    # 2. Family Repetition (Solanaceae, Malvaceae, Cucurbitaceae, Poaceae)
    if prev_family == cand_family and cand_family not in ("Other", "Unknown"):
        risk_desc = ""
        if cand_family == "Solanaceae":
            risk_desc = "Severe risk of Bacterial Wilt (Ralstonia) and Early/Late Blight fungal carryover."
        elif cand_family == "Malvaceae":
            risk_desc = "Pink bollworm pupae persistence and Whitefly/Yellow Vein Mosaic carryover."
        elif cand_family == "Cucurbitaceae":
            risk_desc = "Fruit fly pupae persistence and Downy/Powdery Mildew survival in crop residue."
        elif cand_family == "Poaceae":
            risk_desc = "Continuous topsoil nitrogen depletion, zinc exhaustion, and grassy weed buildup."
        else:
            risk_desc = f"Shared family pests and similar root architecture within the {cand_family} family."

        return {
            "rotation_status": "Rotation Hazard",
            "rotation_risk_level": "HIGH" if cand_family in ("Solanaceae", "Malvaceae") else "MEDIUM",
            "is_rotation_hazard": True,
            "is_rotation_benefit": False,
            "rotation_notes": (
                f"Consecutive {cand_family} Family Warning: Both '{prev_name}' and '{cand_name}' belong to {cand_family}. {risk_desc}"
            ),
            "alternatives": candidate_crop_def.get("alternatives", ["Chickpea", "Soybean", "Green Gram"])
        }

    # 3. Beneficial Legume Rotation
    if not prev_is_legume and cand_is_legume:
        return {
            "rotation_status": "Recommended Rotation",
            "rotation_risk_level": "NONE",
            "is_rotation_hazard": False,
            "is_rotation_benefit": True,
            "rotation_notes": (
                f"Highly Beneficial Rotation: Planting leguminous '{cand_name}' after '{prev_name}' ({prev_family}) "
                "biologically fixes atmospheric nitrogen, enhances soil humus, and disrupts the previous crop's pest cycle."
            ),
            "alternatives": []
        }

    # 4. Compatible Rotation
    return {
        "rotation_status": "Compatible Rotation",
        "rotation_risk_level": "NONE",
        "is_rotation_hazard": False,
        "is_rotation_benefit": False,
        "rotation_notes": f"Safe rotational sequence with different root depths and nutrient profiles after '{prev_name}'.",
        "alternatives": []
    }


# =============================================================================
# MAIN RECOMMENDATION ORCHESTRATION ENGINE
# =============================================================================

def generate_seasonal_crop_recommendations(
    user_id,
    farm_id=None,
    season=None,
    soil_override=None,
    limit=15,
    db_conn=None
):
    """
    Generate seasonal and soil-aware crop recommendations for an authenticated farmer.
    Enforces strict multi-tenant isolation (user_id parameterization).
    """
    conn = db_conn or get_db_connection()
    should_close = db_conn is None

    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch Farmer's Farm Details
        farm_info = None
        if farm_id and str(farm_id).isdigit() and int(farm_id) > 0:
            cursor.execute(
                "SELECT id, farm_name, location, total_area, area_unit, soil_type FROM farms WHERE id = %s AND user_id = %s",
                (int(farm_id), user_id)
            )
            farm_info = cursor.fetchone()
            if not farm_info:
                return {
                    "status": "error",
                    "message": "Farm not found or unauthorized.",
                    "code": 404
                }
        else:
            # Pick first farm if available
            cursor.execute(
                "SELECT id, farm_name, location, total_area, area_unit, soil_type FROM farms WHERE user_id = %s ORDER BY id ASC LIMIT 1",
                (user_id,)
            )
            farm_info = cursor.fetchone()

        # 2. Determine Registered / Detected Soil Type
        resolved_soil = None
        soil_source = "missing"

        if soil_override and normalize_soil_type(soil_override):
            resolved_soil = normalize_soil_type(soil_override)
            soil_source = "user_override"
        elif farm_info and farm_info.get("soil_type") and normalize_soil_type(farm_info["soil_type"]):
            resolved_soil = normalize_soil_type(farm_info["soil_type"])
            soil_source = "farm_profile"
        else:
            # Check recent irrigation record for this farmer
            cursor.execute(
                "SELECT soil_type FROM irrigation_history WHERE user_id = %s AND soil_type IS NOT NULL ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            irrig_row = cursor.fetchone()
            if irrig_row and irrig_row.get("soil_type") and normalize_soil_type(irrig_row["soil_type"]):
                resolved_soil = normalize_soil_type(irrig_row["soil_type"])
                soil_source = "irrigation_history"

        soil_known = resolved_soil is not None
        soil_meta = SOIL_DISPLAY_INFO.get(resolved_soil, {}) if soil_known else {}

        # 3. Retrieve Preceding Crop on Farm for Crop Rotation Context
        previous_crop = None
        if farm_info and farm_info.get("id"):
            fid = farm_info["id"]
            # Look first at recently planned or harvested crops
            cursor.execute("""
                SELECT 'history' AS source, crop_name, variety, planting_date AS event_date, created_at
                FROM crops
                WHERE user_id = %s AND farm_id = %s
                ORDER BY COALESCE(planting_date, created_at) DESC, id DESC
                LIMIT 1
            """, (user_id, fid))
            prev_row = cursor.fetchone()

            # Also check crop_plans
            cursor.execute("""
                SELECT 'plan' AS source, crop_name, variety, planned_sowing_date AS event_date, created_at
                FROM crop_plans
                WHERE user_id = %s AND farm_id = %s
                ORDER BY COALESCE(planned_sowing_date, created_at) DESC, id DESC
                LIMIT 1
            """, (user_id, fid))
            plan_row = cursor.fetchone()

            # Choose the most chronologically relevant preceding crop
            candidate_prev = None
            if prev_row and plan_row:
                d1 = str(prev_row.get("event_date") or prev_row.get("created_at") or "")
                d2 = str(plan_row.get("event_date") or plan_row.get("created_at") or "")
                candidate_prev = plan_row if d2 >= d1 else prev_row
            else:
                candidate_prev = prev_row or plan_row

            if candidate_prev:
                c_class = classify_crop(candidate_prev["crop_name"])
                previous_crop = {
                    "crop_name": candidate_prev["crop_name"],
                    "variety": candidate_prev.get("variety") or "",
                    "family": c_class.get("family", "Unknown"),
                    "is_legume": c_class.get("is_legume", False),
                    "event_date": str(candidate_prev.get("event_date") or "")[:10],
                    "source": candidate_prev.get("source", "history")
                }

        # 4. Seasonal Filtering
        current_active_season = get_current_indian_season()
        target_season = None
        if season and str(season).strip().lower() != "all":
            norm_s = str(season).strip().capitalize()
            if norm_s in ("Kharif", "Rabi", "Zaid"):
                target_season = norm_s
            else:
                target_season = current_active_season

        # 5. Filter and Evaluate Recommendations
        recommendations = []
        for crop in MAHARASHTRA_CROP_CATALOG:
            # Seasonal match check
            if target_season and crop["season"] != target_season:
                continue

            # Soil compatibility check
            compat_label, soil_score, soil_reason = evaluate_soil_compatibility(crop, resolved_soil)

            # Rotation impact check
            rotation_info = evaluate_rotation_impact(crop, previous_crop)

            # Advice scope (location-specific vs general guidance)
            advice_scope = "location_specific" if (soil_known and farm_info and farm_info.get("location")) else "general_guidance"

            # Composite ranking score:
            # Base = soil suitability score (0-100)
            # Bonus +15 for recommended legume rotation
            # Penalty -40 for rotation hazard
            # Small bonus if matching active current season (+5)
            comp_score = soil_score
            if rotation_info.get("is_rotation_benefit"):
                comp_score += 15
            elif rotation_info.get("is_rotation_hazard"):
                comp_score -= 40
            if crop["season"] == current_active_season:
                comp_score += 5

            reasons = [
                f"{compat_label} match for {soil_meta.get('display_name', 'Maharashtra soil zones')} during {crop['season']} season.",
                crop.get("regional_suitability", "High regional suitability for Maharashtra.")
            ]
            if crop.get("agronomic_highlights"):
                reasons.extend(crop["agronomic_highlights"][:2])

            rec_item = {
                "crop_name": crop["crop_name"],
                "scientific_name": crop["scientific_name"],
                "family": crop["family"],
                "season": crop["season"],
                "sowing_window": crop["sowing_window"],
                "duration_days_min": crop["duration_days_min"],
                "duration_days_max": crop["duration_days_max"],
                "crop_duration": f"{crop['duration_days_min']}–{crop['duration_days_max']} days",
                "expected_harvest_window": crop["expected_harvest_window"],
                "soil_compatibility": compat_label,
                "soil_suitability_score": soil_score,
                "soil_compatibility_reason": soil_reason,
                "rotation_status": rotation_info["rotation_status"],
                "rotation_risk_level": rotation_info["rotation_risk_level"],
                "is_rotation_hazard": rotation_info["is_rotation_hazard"],
                "is_rotation_benefit": rotation_info["is_rotation_benefit"],
                "rotation_notes": rotation_info["rotation_notes"],
                "is_legume": crop["is_legume"],
                "nitrogen_fixer": crop["nitrogen_fixer"],
                "recommendation_reasons": reasons,
                "alternatives": rotation_info.get("alternatives") or crop.get("alternatives", []),
                "advice_scope": advice_scope,
                "local_names": crop.get("local_names", {}),
                "composite_score": comp_score
            }
            recommendations.append(rec_item)

        # Sort recommendations: highest composite score first, but keep unsuitables at the end
        recommendations.sort(key=lambda r: r["composite_score"], reverse=True)

        if limit and isinstance(limit, int) and limit > 0:
            recommendations = recommendations[:limit]

        # Construct Farm Context
        farm_context = {
            "farm_id": farm_info["id"] if farm_info else None,
            "farm_name": farm_info["farm_name"] if farm_info else "General Farm / Unassigned",
            "location": farm_info.get("location") if farm_info else "",
            "soil_type": resolved_soil,
            "soil_display_name": soil_meta.get("display_name", "Unspecified / Missing Soil"),
            "soil_known": soil_known,
            "soil_source": soil_source,
            "soil_limitation_notice": (
                None if soil_known else
                "Soil type is not registered for this farm. General seasonal recommendations are provided based on Maharashtra regional averages. Register your farm soil type (e.g. Black Cotton, Loam, Sandy Loam) for field-specific matching."
            ),
            "previous_crop": previous_crop
        }

        return {
            "status": "success",
            "current_season": current_active_season,
            "selected_season": target_season or "all",
            "farm_context": farm_context,
            "recommendations_count": len(recommendations),
            "recommendations": recommendations,
            "disclaimer": (
                "Agronomic recommendations are referenced from ICAR, MPKV Rahuri, and PDKV Akola packages of practices. "
                "Always verify local rainfall, irrigation availability, and seed suitability before sowing."
            )
        }

    finally:
        if should_close and conn:
            conn.close()
