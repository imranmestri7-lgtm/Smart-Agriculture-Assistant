import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(BASE_DIR, "data", "disease_knowledge_base.json")
LABELS_PATH = os.path.join(BASE_DIR, "models", "class_labels.json")

# Map of standard crop keywords to identify supported crops
SUPPORTED_CROP_KEYWORDS = {
    "apple": "Apple",
    "blueberry": "Blueberry",
    "cherry": "Cherry",
    "corn": "Corn (Maize)",
    "maize": "Corn (Maize)",
    "grape": "Grape",
    "orange": "Orange (Citrus)",
    "citrus": "Orange (Citrus)",
    "peach": "Peach",
    "pepper": "Bell Pepper",
    "bell pepper": "Bell Pepper",
    "potato": "Potato",
    "raspberry": "Raspberry",
    "soybean": "Soybean",
    "squash": "Squash",
    "strawberry": "Strawberry",
    "tomato": "Tomato"
}

_kb_cache = None


def load_knowledge_base():
    """Load the disease knowledge base from JSON."""
    global _kb_cache
    if _kb_cache is not None:
        return _kb_cache

    if not os.path.isfile(KB_PATH):
        print(f"Warning: Disease knowledge base file not found at {KB_PATH}")
        return {}

    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            _kb_cache = json.load(f)
        return _kb_cache
    except Exception as e:
        print(f"Error loading disease knowledge base: {e}")
        return {}


def format_class_name(class_name):
    """Format raw model class name into a clean readable string."""
    if not class_name:
        return "Unknown"
    return str(class_name).replace("___", " — ").replace("_", " ")


def check_crop_compatibility(user_crop, predicted_crop):
    """
    Check if the crop selected by the user is compatible with the predicted crop.
    Returns (is_compatible, message).
    """
    if not user_crop:
        return True, ""

    user_clean = str(user_crop).strip().lower()
    if user_clean in ("", "not sure", "other", "other plant or fruit", "select crop"):
        return True, ""

    pred_clean = str(predicted_crop).strip().lower()

    # Find which supported crop category matches user_crop
    matched_user_category = None
    for kw, cat in SUPPORTED_CROP_KEYWORDS.items():
        if kw in user_clean:
            matched_user_category = cat.lower()
            break

    # If the user selected an unsupported crop like Rice, Wheat, Cotton
    if not matched_user_category:
        return False, (
            f"The selected crop '{user_crop}' is not supported by this plant disease model. "
            f"The model was trained on 14 specific crops and its prediction of '{predicted_crop}' "
            f"cannot be applied to '{user_crop}'."
        )

    # Check if the matched user category matches the predicted crop
    if matched_user_category not in pred_clean and pred_clean not in matched_user_category:
        return False, (
            f"The selected crop '{user_crop}' does not match the predicted plant '{predicted_crop}'. "
            "Please verify that the uploaded image corresponds to the selected crop."
        )

    return True, ""


def get_disease_info(class_name, confidence=None, user_crop=None, language=None):
    """
    Retrieve structured knowledge base entry for a given class name.
    Handles healthy foliage, low confidence, and crop mismatch safely.
    Supports optional language translation for Marathi ('mr') and Hindi ('hi').
    """
    kb = load_knowledge_base()
    raw_class = str(class_name or "").strip()

    entry = kb.get(raw_class)

    # Fallback for unknown or missing class
    if not entry:
        is_healthy = "healthy" in raw_class.lower()
        crop_name = raw_class.split("___")[0].replace("_", " ") if "___" in raw_class else "Plant"
        display_name = format_class_name(raw_class)

        entry = {
            "class_name": raw_class,
            "display_name": display_name,
            "crop": crop_name,
            "is_healthy": is_healthy,
            "category": "healthy" if is_healthy else "unknown",
            "description": (
                f"Foliage evaluated as {display_name}. "
                "Specific detailed profile is currently unavailable for this class."
            ),
            "symptoms": [
                "Visual appearance corresponds to the predicted class profile"
            ],
            "possible_causes": [
                "Environmental conditions or pathogen specific to the crop"
            ],
            "prevention": [
                "Ensure proper plant spacing and good air circulation",
                "Water at the base of the plant to keep foliage dry",
                "Sanitize tools and remove decaying crop residues"
            ],
            "care_recommendations": [
                "Monitor foliage daily for changes or spreading lesions",
                "Consult a local agricultural extension officer if symptoms worsen"
            ],
            "safe_treatment": [
                "Do not apply unverified chemical treatments without confirming the disease cause",
                "Consult local agricultural extension authorities for approved regional practices"
            ]
        }
    else:
        # Create a shallow copy so we can add runtime evaluation fields
        entry = dict(entry)

    # Determine uncertainty status
    conf_value = 0.0
    if confidence is not None:
        try:
            conf_value = float(confidence)
        except (ValueError, TypeError):
            conf_value = 0.0

    is_low_confidence = conf_value < 60.0 if confidence is not None else False
    entry["confidence"] = round(conf_value, 2)
    entry["is_uncertain"] = is_low_confidence

    # Check user crop compatibility
    is_compatible, compatibility_message = check_crop_compatibility(user_crop, entry.get("crop"))
    entry["is_crop_compatible"] = is_compatible
    entry["crop_compatibility_message"] = compatibility_message

    # Safety disclaimer
    entry["disclaimer"] = (
        "This evaluation is a model‑assisted prediction, not a certified laboratory diagnosis. "
        "Symptoms should be verified in the field before choosing any management or treatment practices. "
        "No chemical pesticide is prescribed without local regulatory guidance."
    )

    # ---------------------------------------------------------------------
    # Language translation handling
    # ---------------------------------------------------------------------
    if language in ("mr", "hi"):
        # Load translations lazily (cached globally)
        translations = _load_translation_file()
        lang_dict = translations.get(language, {})
        trans_entry = lang_dict.get(raw_class)
        if isinstance(trans_entry, dict):
            # Merge translated fields, falling back to English when missing
            for key in ["display_name", "description", "symptoms", "possible_causes", "prevention", "care_recommendations", "safe_treatment", "disclaimer"]:
                if key in trans_entry and trans_entry[key]:
                    entry[key] = trans_entry[key]
    return entry

# Helper to load the translation JSON (cached)
_TRANSLATION_CACHE = None
def _load_translation_file():
    path = os.path.join(BASE_DIR, "data", "disease_knowledge_translations.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load disease translations: {e}")
        return {}
    global _TRANSLATION_CACHE
    if _TRANSLATION_CACHE is not None:
        return _TRANSLATION_CACHE
    path = os.path.join(BASE_DIR, "data", "disease_knowledge_translations.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _TRANSLATION_CACHE = json.load(f)
    except Exception as e:
        print(f"Failed to load disease translations: {e}")
        _TRANSLATION_CACHE = {}
    return _TRANSLATION_CACHE

    """
    Retrieve structured knowledge base entry for a given class name.
    Handles healthy foliage, low confidence, and crop mismatch safely.
    """
    kb = load_knowledge_base()
    raw_class = str(class_name or "").strip()

    entry = kb.get(raw_class)

    # Fallback for unknown or missing class
    if not entry:
        is_healthy = "healthy" in raw_class.lower()
        crop_name = raw_class.split("___")[0].replace("_", " ") if "___" in raw_class else "Plant"
        display_name = format_class_name(raw_class)

        entry = {
            "class_name": raw_class,
            "display_name": display_name,
            "crop": crop_name,
            "is_healthy": is_healthy,
            "category": "healthy" if is_healthy else "unknown",
            "description": (
                f"Foliage evaluated as {display_name}. "
                "Specific detailed profile is currently unavailable for this class."
            ),
            "symptoms": [
                "Visual appearance corresponds to the predicted class profile"
            ],
            "possible_causes": [
                "Environmental conditions or pathogen specific to the crop"
            ],
            "prevention": [
                "Ensure proper plant spacing and good air circulation",
                "Water at the base of the plant to keep foliage dry",
                "Sanitize tools and remove decaying crop residues"
            ],
            "care_recommendations": [
                "Monitor foliage daily for changes or spreading lesions",
                "Consult a local agricultural extension officer if symptoms worsen"
            ],
            "safe_treatment": [
                "Do not apply unverified chemical treatments without confirming the disease cause",
                "Consult local agricultural extension authorities for approved regional practices"
            ]
        }
    else:
        # Create a shallow copy so we can add runtime evaluation fields
        entry = dict(entry)

    # Determine uncertainty status
    conf_value = 0.0
    if confidence is not None:
        try:
            conf_value = float(confidence)
        except (ValueError, TypeError):
            conf_value = 0.0

    is_low_confidence = conf_value < 60.0 if confidence is not None else False
    entry["confidence"] = round(conf_value, 2)
    entry["is_uncertain"] = is_low_confidence

    # Check user crop compatibility
    is_compatible, compatibility_message = check_crop_compatibility(user_crop, entry.get("crop"))
    entry["is_crop_compatible"] = is_compatible
    entry["crop_compatibility_message"] = compatibility_message

    # Safety disclaimer
    entry["disclaimer"] = (
        "This evaluation is a model‑assisted prediction, not a certified laboratory diagnosis. "
        "Symptoms should be verified in the field before choosing any management or treatment practices. "
        "No chemical pesticide is prescribed without local regulatory guidance."
    )

    return entry
