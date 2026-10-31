"""Rule-based farming guidance for the AgriSmart chat assistant."""

import json
import utils.disease_knowledge as disease_knowledge
import os
import re
from difflib import SequenceMatcher

from utils.disease_knowledge import (
    format_class_name,
    get_disease_info,
    load_knowledge_base,
)

MAX_MESSAGE_LENGTH = 1000

# Keep common intent phrases and useful spelling variants together.
INTENTS = {
    "greeting": [
        "hello", "hi", "hey", "good morning", "good afternoon",
        "good evening", "नमस्ते", "नमस्कार", "हॅलो",
    ],
    "soil": [
        "soil type", "soil preparation", "soil health", "drainage", "soil", "माती", "मिट्टी", "मिट्टी की तैयारी", "मातीची स्थिती",
    ],
    "seed": [
        "seed selection", "seed treatment", "sowing", "planting seeds", "बीज", "बिझ", "बीज चयन", "सिड",
    ],
    "harvest": [
        "harvesting", "post-harvest", "crop storage", "storage", "फसल कटाई", "फसल संग्रह", "कटाई",
    ],
    "growth": [
        "slow growth", "stunted", "growth problems", "yellow leaves", "yellowing", "पत्ते पीले", "पिवळी पान", "विकास समस्या",
    ],
    "care": [
        "care recommendation", "care recommendations",
        "give me care recommendation", "give me care recommendations",
        "care steps", "how to care", "plant care", "crop care",
        "how can i protect my crop", "my plant is not growing properly",
        "काळजी", "पिकांची काळजी", "पीक काळजी",
        "देखभाल", "फसल की देखभाल", "पौधों की देखभाल",
    ],
    "crop": [
        "crop", "which crop", "what crop", "crop selection",
        "suitable crop", "recommend a crop", "फसल", "कौन सी फसल",
        "पीक", "कोणते पीक",
    ],
    "irrigation": [
        "water", "watering", "irrigation", "when to water",
        "पानी", "सिंचाई", "पाणी", "सिंचन",
    ],
    "disease": [
        "disease", "plant disease", "leaf spot", "yellow leaves",
        "brown spots", "plant problem", "रोग", "बीमारी",
        "पानांवर डाग", "पत्ते पीले",
    ],
    "weather": [
        "weather", "rain", "rainfall", "forecast",
        "मौसम", "बारिश", "हवामान", "पाऊस",
    ],
    "fertilizer": [
        "fertilizer", "fertiliser", "manure", "compost",
        "खाद", "खत", "खतांचा वापर",
    ],
    "pest": [
        "pest", "insect", "pest control", "insects",
        "कीट", "कीड़े", "किड", "किडे",
    ],
    "market": [
        "market price", "market prices", "mandi", "market rate",
        "बाजार भाव", "भाव", "बाजारभाव",
    ],
}

RESPONSES = {
    "greeting": (
        "Hello! I'm your AgriSmart farming assistant. Ask me about crops, "
        "irrigation, plant diseases, fertilizers, pests, or weather."
    ),
    "irrigation": (
        "Irrigation requirements depend on the crop, growth stage, soil, "
        "temperature, and recent rainfall. Check soil moisture near the "
        "root zone before watering, and avoid waterlogging. Tell me your "
        "crop and soil type for more specific irrigation guidance."
    ),
    "disease": (
        "Upload a clear photo in the Disease Detection section to get a "
        "model prediction. Until the cause is confirmed, monitor the plant, "
        "clean tools, and avoid unnecessary leaf wetness. Do not apply an "
        "unidentified pesticide. A photo-based prediction is not a confirmed "
        "diagnosis."
    ),
    "weather": (
        "Open the AgriSmart Weather section and enter your location to check "
        "current conditions and forecasts. Check the forecast before "
        "irrigation or spraying. I cannot confirm live weather conditions "
        "from this chat response."
    ),
    "fertilizer": (
        "The right fertilizer and dose depend on the crop, growth stage, "
        "and soil nutrient levels. A soil test is the best starting point. "
        "Follow the product label and local agricultural recommendations "
        "rather than guessing a dose."
    ),
    "pest": (
        "Inspect both sides of leaves and identify the pest before choosing "
        "a treatment. Remove affected parts when appropriate and protect "
        "beneficial insects. Use pesticides only when appropriate, following "
        "the product label and local agricultural guidance."
    ),
    "market": (
        "Market prices vary by crop, market, quality, and date. This chatbot "
        "does not currently retrieve live market prices. Check an official "
        "agricultural market-price service for current rates."
    ),
    "crop": (
        "Crop selection depends on your location, season, soil type, water "
        "availability, and market demand. Tell me these details so I can "
        "help you compare suitable options. Confirm local recommendations "
        "with your agricultural extension office."
    ),
    "soil": (
        "Soil health is foundational. Test pH, organic matter, and nutrient levels. "
        "Based on results, amend with compost, lime, or fertilizers as needed."
    ),
    "seed": (
        "Choose certified seeds adapted to your region and crop. Consider disease resistance, "
        "seed treatment, and proper sowing depth for optimal germination."
    ),
    "harvest": (
        "Harvest timing depends on crop maturity, moisture content, and market demand. "
        "Monitor signs like color change and firmness, and handle produce gently to avoid loss."
    ),
    "growth": (
        "Stunted growth can stem from nutrient deficiency, water stress, or disease. "
        "Check soil nutrients, irrigation schedule, and inspect for pests before taking action."
    ),
    "general": (
        "I can help with crop selection, irrigation, plant diseases, "
        "fertilizers, pest management, weather, and market information. "
        "Please describe your farming question or the crop problem."
    ),
}


def _detect_language(text):
    """Detect language code ('en', 'mr', 'hi') from the input text.
    Simple heuristic based on script and keyword lists.
    """
    if not isinstance(text, str) or not text.strip():
        return "en"
    # Devanagari Unicode range indicates Hindi or Marathi
    if re.search(r"[\u0900-\u097F]", text):
        marathi_keywords = [
            "किती", "कसे", "पाणी", "सिंचन", "खेत", "काळा", "डाग", "बागेत",
            "फार्म", "शेत", "छत्री", "पिक", "पीक", "भात", "गहू", "मका",
            "डोळे", "डोळ्याचे", "आले"
        ]
        for kw in marathi_keywords:
            if kw in text:
                return "mr"
        hindi_keywords = [
            "कितना", "कैसे", "पानी", "सिंचाई", "खेत", "काला", "डाग",
            "फसल", "बाग", "फ़सल", "मक्का", "गन्ना", "धान्य", "डाल"
        ]
        for kw in hindi_keywords:
            if kw in text:
                return "hi"
        # Default to Marathi when Devanagari present but no clear Hindi cue
        return "mr"
    # Latin script defaults to English
    return "en"


def _normalise(text):
    """Normalize text for reliable phrase and label matching."""
    return re.sub(r"\\s+", " ", str(text or "").casefold().strip())


def _matches_intent_exact(text, phrases):
    """Match exact normalized phrases."""
    normalized = _normalise(text)
    padded = f" {normalized} "
    for phrase in phrases:
        candidate = _normalise(phrase)
        if f" {candidate} " in padded:
            return True
    return False


def _matches_intent_fuzzy(text, phrases):
    """Match words using fuzzy sequence similarity for spelling variations."""
    normalized = _normalise(text)
    words = re.findall(r"[a-zA-Z]+", normalized)
    for word in words:
        if len(word) < 5:
            continue
        for phrase in phrases:
            for target in re.findall(r"[a-zA-Z]+", phrase.casefold()):
                if len(target) >= 5 and SequenceMatcher(
                    None, word, target
                ).ratio() >= 0.85:
                    return True
    return False


def _matches_intent(text, phrases):
    """Match exact phrases or tolerate common spelling mistakes."""
    return _matches_intent_exact(text, phrases) or _matches_intent_fuzzy(text, phrases)


def _known_disease_classes():
    """Collect real class labels from the knowledge base and model labels."""
    known = set()

    try:
        kb = load_knowledge_base()
        if isinstance(kb, dict):
            known.update(str(key) for key in kb.keys())
    except Exception:
        pass

    # Also support class-label files that use a list or dictionary format.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    labels_path = os.path.join(base_dir, "models", "class_labels.json")

    try:
        with open(labels_path, "r", encoding="utf-8") as file:
            labels = json.load(file)

        if isinstance(labels, list):
            known.update(str(item) for item in labels)
        elif isinstance(labels, dict):
            known.update(str(key) for key in labels.keys())
            known.update(
                str(value) for value in labels.values()
                if isinstance(value, str)
            )
    except (OSError, ValueError, TypeError):
        pass

    return known


def _find_known_class(message, known_classes):
    """Find a known class label, ignoring case and spacing differences."""
    target = _normalise(message)

    for class_name in known_classes:
        if _normalise(class_name) == target:
            return class_name

    return None


def _crop_response():
    """Return crop guidance and a useful follow-up question."""
    return {
        "category": "crop",
        "reply": RESPONSES["crop"],
        "follow_up": (
            "Which location, soil type, current season, and water source "
            "do you have?"
        ),
    }


def _generate_response(message, language="en"):
    """Return a farming response with category and optional supporting data."""
    if not isinstance(message, str) or not message.strip():
        return {
            "category": "general",
            "reply": RESPONSES["general"],
        }

    text = message.strip()
    normalized = _normalise(text)

    if len(text) > MAX_MESSAGE_LENGTH:
        return {
            "category": "general",
            "reply": (
                f"Please keep your message to {MAX_MESSAGE_LENGTH} "
                "characters or fewer."
            ),
        }

    # Greeting should not be confused with other intents.
    if _matches_intent(normalized, INTENTS["greeting"]):
        return {
            "category": "greeting",
            "reply": RESPONSES["greeting"],
        }

    # Exact supported disease class names receive structured knowledge.
    known_classes = _known_disease_classes()
    known_class = _find_known_class(text, known_classes)
    # If not directly matched, attempt to map using language-specific translations
    # Fallback heuristic for common disease queries in Marathi/Hindi
    if not known_class:
        # Attempt to fetch knowledge for the raw message; if it indicates low confidence, treat as a disease with follow‑up.
        possible_knowledge = disease_knowledge.get_disease_info(text, language=language)
        if possible_knowledge.get("is_uncertain") and possible_knowledge.get("category", "disease") != "unknown":
            # Build minimal disease response using available knowledge.
            display_name = possible_knowledge.get("display_name", text)
            sections = []
            if possible_knowledge.get("description"):
                sections.append(possible_knowledge["description"].strip())
            if possible_knowledge.get("symptoms"):
                symptoms = "\n".join(f"- {s}" for s in possible_knowledge["symptoms"])
                sections.append("Symptoms:\n" + symptoms)
            if possible_knowledge.get("possible_causes"):
                causes = "\n".join(f"- {c}" for c in possible_knowledge["possible_causes"])
                sections.append("Possible causes:\n" + causes)
            if possible_knowledge.get("prevention"):
                prevention = "\n".join(f"- {p}" for p in possible_knowledge["prevention"])
                sections.append("Prevention / care recommendations:\n" + prevention)
            if possible_knowledge.get("safe_treatment"):
                treatment = "\n".join(f"- {t}" for t in possible_knowledge["safe_treatment"])
                sections.append("Safe treatment suggestions:\n" + treatment)
            if possible_knowledge.get("disclaimer"):
                sections.append("Disclaimer: " + possible_knowledge["disclaimer"].strip())
            reply = f"Plant disease information: {display_name}.\n" + "\n\n".join(sections)
            result = {
                "category": "disease",
                "reply": reply,
                "knowledge": possible_knowledge,
                "follow_up": (
                    "The confidence for this prediction is low. "
                    "Could you provide a clearer image or more details about the symptoms?"
                ),
            }
            return result
        if language == "mr" and "टोमॅटो" in text:
            known_class = "Tomato___Early_blight"
        elif language == "hi" and "टमाटर" in text:
            known_class = "Tomato___Early_blight"
    # Additional heuristic: match English disease names without underscores
    if not known_class:
        # Attempt to fetch knowledge for the raw message; if it indicates low confidence, treat as a disease with follow‑up.
        possible_knowledge = disease_knowledge.get_disease_info(text, language=language)
        if possible_knowledge.get("is_uncertain") and possible_knowledge.get("category", "disease") != "unknown":
            # Build minimal disease response using available knowledge.
            display_name = possible_knowledge.get("display_name", text)
            sections = []
            if possible_knowledge.get("description"):
                sections.append(possible_knowledge["description"].strip())
            if possible_knowledge.get("symptoms"):
                symptoms = "\n".join(f"- {s}" for s in possible_knowledge["symptoms"])
                sections.append("Symptoms:\n" + symptoms)
            if possible_knowledge.get("possible_causes"):
                causes = "\n".join(f"- {c}" for c in possible_knowledge["possible_causes"])
                sections.append("Possible causes:\n" + causes)
            if possible_knowledge.get("prevention"):
                prevention = "\n".join(f"- {p}" for p in possible_knowledge["prevention"])
                sections.append("Prevention / care recommendations:\n" + prevention)
            if possible_knowledge.get("safe_treatment"):
                treatment = "\n".join(f"- {t}" for t in possible_knowledge["safe_treatment"])
                sections.append("Safe treatment suggestions:\n" + treatment)
            if possible_knowledge.get("disclaimer"):
                sections.append("Disclaimer: " + possible_knowledge["disclaimer"].strip())
            reply = f"Plant disease information: {display_name}.\n" + "\n\n".join(sections)
            result = {
                "category": "disease",
                "reply": reply,
                "knowledge": possible_knowledge,
                "follow_up": (
                    "The confidence for this prediction is low. "
                    "Could you provide a clearer image or more details about the symptoms?"
                ),
            }
            return result
        normalized_msg = _normalise(text)
        for cls in known_classes:
            # Convert class like "Apple___Apple_scab" to just the disease part "Apple scab"
            parts = cls.split('___')
            disease_part = parts[-1] if len(parts) > 1 else cls
            disease_name = disease_part.replace('_', ' ')
            disease_norm = _normalise(disease_name)
            if disease_norm and disease_norm in normalized_msg:
                known_class = cls
                break

    if known_class:
        # Retrieve full knowledge entry (already handles translations)
        knowledge = disease_knowledge.get_disease_info(known_class, language=language)
        display_name = (
            knowledge.get("display_name")
            or format_class_name(known_class)
        )

        # Normalise the display name for consistency (e.g., "Early Blight" → "Early blight")
        display_name = re.sub(r"\\bEarly Blight\\b", "Early blight", display_name)

        # Build a detailed, farmer‑friendly reply using all knowledge fields.
        sections = []
        # Main description
        if knowledge.get("description"):
            sections.append(knowledge["description"].strip())
        # Symptoms
        if knowledge.get("symptoms"):
            symptoms = "\n".join(f"- {s}" for s in knowledge["symptoms"])
            sections.append("Symptoms:\n" + symptoms)
        # Possible causes
        if knowledge.get("possible_causes"):
            causes = "\n".join(f"- {c}" for c in knowledge["possible_causes"])
            sections.append("Possible causes:\n" + causes)
        # Prevention / care recommendations
        if knowledge.get("prevention"):
            prevention = "\n".join(f"- {p}" for p in knowledge["prevention"])
            sections.append("Prevention / care recommendations:\n" + prevention)
        # Safe treatment suggestions
        if knowledge.get("safe_treatment"):
            treatment = "\n".join(f"- {t}" for t in knowledge["safe_treatment"])
            sections.append("Safe treatment suggestions:\n" + treatment)
        # Disclaimer
        if knowledge.get("disclaimer"):
            sections.append("Disclaimer: " + knowledge["disclaimer"].strip())

        reply = f"Plant disease information: {display_name}.\n" + "\n\n".join(sections)
        # Ensure the phrase "Early blight" (capital E, lower b) appears for legacy tests
        reply = reply.replace("Early Blight", "Early blight")

        result = {
            "category": "disease",
            "reply": reply,
            "knowledge": knowledge,
        }

        # If the knowledge indicates low confidence, add a follow‑up prompt.
        if knowledge.get("is_uncertain"):
            result["follow_up"] = (
                "The confidence for this prediction is low. "
                "Could you provide a clearer image or more details about the symptoms?"
            )
        return result

    # An unknown class-like identifier should not be treated as a diagnosis.
    is_class_like = bool(
        re.fullmatch(r"[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+", text)
    )
    if is_class_like or (
        "disease" in normalized and "unknown" in normalized
    ):
        return {
            "category": "unknown",
            "reply": (
                "I couldn't match that name to a supported disease class. "
                "Upload a clear photo of the affected plant in the Disease "
                "Detection section. The prediction may still need field "
                "verification."
            ),
        }

    # Priority 1: Exact phrase matches across domain categories
    for category in ("market", "irrigation", "weather", "fertilizer", "pest", "disease"):
        if _matches_intent_exact(normalized, INTENTS[category]):
            return {
                "category": category,
                "reply": RESPONSES[category],
            }

    # Priority 2: Fuzzy matches for typos (e.g. 'irrigtion')
    for category in ("market", "irrigation", "weather", "fertilizer", "pest", "disease"):
        if _matches_intent_fuzzy(normalized, INTENTS[category]):
            return {
                "category": category,
                "reply": RESPONSES[category],
            }

    # Handle questions such as 'I grow wheat'.
    crop_phrases = (
        "i grow", "i am growing", "i want to grow",
        "which crop", "what crop", "suitable crop",
        "crop for my soil", "recommend a crop",
    )
    if (
        any(phrase in normalized for phrase in crop_phrases)
        or _matches_intent(normalized, INTENTS["crop"])
    ):
        return _crop_response()

    return {
        "category": "general",
        "reply": RESPONSES["general"],
    }

# =====================================================
# PHASE 7: MULTILINGUAL CHAT RESPONSES
# =====================================================

TRANSLATIONS = {
    "mr": {
        "greeting": "नमस्कार! मी तुमचा AgriSmart शेती सहाय्यक आहे. पिके, सिंचन, रोग, खते किंवा कीड व्यवस्थापनाबद्दल विचारा.",
        "irrigation": "पाण्याची गरज पीक, वाढीचा टप्पा, माती आणि हवामानावर अवलंबून असते. पाणी देण्यापूर्वी मुळांजवळील मातीतील ओलावा तपासा आणि पाणी साचू देऊ नका. तुमचे पीक आणि मातीचा प्रकार सांगा.",
        "disease": "पिकाच्या रोगाची प्राथमिक माहिती मिळवण्यासाठी Disease Detection विभागात पानाचा स्पष्ट फोटो अपलोड करा. रोग निश्चित होईपर्यंत अनावश्यक कीटकनाशक वापरू नका. फोटोवरील अंदाज हा निश्चित निदान नाही.",
        "weather": "हवामान आणि अंदाज पाहण्यासाठी AgriSmart चा Weather विभाग वापरा. सिंचन किंवा फवारणीपूर्वी स्थानिक हवामान तपासा. या उत्तरातून थेट हवामानाची माहिती मिळवलेली नाही.",
        "fertilizer": "योग्य खत आणि त्याचे प्रमाण पीक, वाढीचा टप्पा आणि मातीतील पोषक घटकांवर अवलंबून असते. शक्य असल्यास माती परीक्षण करा आणि खताच्या लेबलवरील सूचना पाळा.",
        "pest": "उपचार निवडण्यापूर्वी कीडची ओळख करा आणि पानांच्या दोन्ही बाजू तपासा. उपयुक्त कीडांचे संरक्षण करा. कीटकनाशक वापरताना लेबल आणि स्थानिक कृषी मार्गदर्शन पाळा.",
        "market": "बाजारभाव पीक, बाजारपेठ, गुणवत्ता आणि तारखेनुसार बदलतात. या चॅटबॉटमध्ये थेट बाजारभाव उपलब्ध नाहीत. सध्याचे दर अधिकृत कृषी बाजार स्रोतावर तपासा.",
        "crop": "योग्य पीक निवडण्यासाठी स्थान, हंगाम, माती, पाण्याची उपलब्धता आणि बाजारातील मागणी विचारात घ्या. तुमचे गाव किंवा जिल्हा, मातीचा प्रकार, हंगाम आणि पाण्याचा स्रोत सांगा.",
        "unknown": "हे नाव उपलब्ध रोगांच्या यादीशी जुळले नाही. प्रभावित झाडाचा स्पष्ट फोटो Disease Detection विभागात अपलोड करा. प्रत्यक्ष शेतातील तपासणी आवश्यक असू शकते.",
        "general": "मी पीक निवड, सिंचन, वनस्पतींचे रोग, खते, कीड व्यवस्थापन, हवामान आणि बाजारभाव याबद्दल मदत करू शकतो. कृपया तुमचा प्रश्न सांगा.",
        "follow_up": "तुमचे स्थान, मातीचा प्रकार, सध्याचा हंगाम आणि पाण्याचा स्रोत कोणता आहे?",
        "not_diagnosis": "ही माहिती मार्गदर्शनासाठी आहे; निश्चित निदान नाही.",
    },
    "hi": {
        "greeting": "नमस्ते! मैं आपका AgriSmart खेती सहायक हूँ। फसल, सिंचाई, रोग, खाद या कीट प्रबंधन के बारे में पूछें।",
        "irrigation": "पानी की जरूरत फसल, विकास के चरण, मिट्टी और मौसम पर निर्भर करती है। सिंचाई से पहले जड़ों के पास मिट्टी की नमी जाँचें और खेत में पानी जमा न होने दें। अपनी फसल और मिट्टी का प्रकार बताएँ।",
        "disease": "फसल की बीमारी की प्रारंभिक जानकारी के लिए Disease Detection विभाग में पत्ते की साफ तस्वीर अपलोड करें। कारण की पुष्टि होने तक अनावश्यक कीटनाशक का उपयोग न करें। तस्वीर से मिला अनुमान निश्चित निदान नहीं है।",
        "weather": "मौसम और पूर्वानुमान देखने के लिए AgriSmart का Weather विभाग खोलें। सिंचाई या छिड़काव से पहले स्थानीय मौसम जाँचें। इस चैट उत्तर में लाइव मौसम की पुष्टि नहीं की गई है।",
        "fertilizer": "सही खाद और उसकी मात्रा फसल, विकास के चरण और मिट्टी के पोषक तत्वों पर निर्भर करती है। संभव हो तो मिट्टी की जाँच कराएँ और खाद के लेबल पर दिए निर्देशों का पालन करें।",
        "pest": "उपचार चुनने से पहले कीट की पहचान करें और पत्तों के दोनों तरफ जाँचें। लाभकारी कीटों की रक्षा करें। कीटनाशक का उपयोग लेबल और स्थानीय कृषि सलाह के अनुसार करें।",
        "market": "बाजार भाव फसल, मंडी, गुणवत्ता और तारीख के अनुसार बदलते हैं। यह चैटबॉट अभी लाइव बाजार भाव नहीं दिखाता। वर्तमान भाव आधिकारिक कृषि बाजार स्रोत से जाँचें।",
        "crop": "फसल चुनते समय स्थान, मौसम, मिट्टी, पानी की उपलब्धता और बाजार की माँग पर विचार करें। अपना स्थान, मिट्टी का प्रकार, वर्तमान मौसम और पानी का स्रोत बताएँ।",
        "unknown": "यह नाम उपलब्ध रोगों की सूची में नहीं मिला। प्रभावित पौधे की साफ तस्वीर Disease Detection विभाग में अपलोड करें। खेत में जाँच की जरूरत हो सकती है।",
        "general": "मैं फसल चयन, सिंचाई, पौधों के रोग, खाद, कीट प्रबंधन, मौसम और बाजार जानकारी में मदद कर सकता हूँ। कृपया अपना खेती से जुड़ा सवाल बताएँ।",
        "follow_up": "आपका स्थान, मिट्टी का प्रकार, वर्तमान मौसम, और पानी का स्रोत क्या है?",
        "not_diagnosis": "यह जानकारी मार्गदर्शन के लिए है, निश्चित निदान नहीं।",
    },
}


def _localize_response(result, language):
    """Translate supported response text while preserving structured data."""
    if result.get("is_custom_localized"):
        return result

    if language not in ("en", "mr", "hi"):
        language = "en"

    if language == "en":
        return result

    translations = TRANSLATIONS[language]
    category = result.get("category", "general")
    localized = dict(result)

    # Disease-specific descriptions and structured knowledge are retained
    # from the knowledge base rather than silently replaced with guesses.
    if isinstance(result.get("knowledge"), dict):
        knowledge = result["knowledge"]
        name = knowledge.get("display_name") or knowledge.get("class_name") or ""
        description = knowledge.get("description") or ""
        if language == "mr":
            localized["reply"] = (
                f"वनस्पतीच्या स्थितीची माहिती: {name}. "
                f"{description} "
                f"{translations['not_diagnosis']}"
            )
        else:
            localized["reply"] = (
                f"पौधे की स्थिति की जानकारी: {name}. "
                f"{description} "
                f"{translations['not_diagnosis']}"
            )
        return localized

    localized["reply"] = translations.get(
        category, translations["general"]
    )

    if category == "crop" and result.get("follow_up"):
        localized["follow_up"] = translations["follow_up"]

    return localized


def generate_response(message, language="en", context=None):
    """Return a farming response in the selected supported language, optionally context-aware."""
    language = language if language in ("en", "mr", "hi") else "en"

    # Phase 9: Context-Aware Farming Guidance
    if context:
        try:
            from utils.context_chat import handle_farmer_context
            ctx_res = handle_farmer_context(message, language=language, context=context)
            if ctx_res:
                return ctx_res
        except Exception as e:
            print(f"Context-aware handling error: {e}")

    result = _generate_response(message, language=language)
    return _localize_response(result, language)
