"""Utility for analyzing plant leaf images in Farmer Assistant chat.

Provides:
- Image validation (extension, max 5 MB, PIL header verify)
- TensorFlow model inference using plant_disease_model.keras
- Strict isolation and secure filename handling
- Multilingual (English, Marathi, Hindi) 6-part structured response
- Honest handling of low-confidence (<30%) or non-leaf photos
"""

import io
import os
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB limit
CONFIDENCE_THRESHOLD = 30.0  # Percentage below which image is marked unidentifiable

DEFAULT_PROMPTS = {
    "en": "Please analyze this plant image and tell me if it has any disease or needs care.",
    "mr": "कृपया या वनस्पतीचे फोटो तपासा आणि यावर कोणताही रोग आहे का किंवा काय काळजी घ्यावी ते सांगा.",
    "hi": "कृपया इस पौधे की तस्वीर का विश्लेषण करें और बताएं कि क्या इसमें कोई बीमारी है या क्या देखभाल आवश्यक है。"
}

CROP_TRANSLATIONS = {
    "apple": {"mr": "सफरचंद (Apple)", "hi": "सेब (Apple)"},
    "blueberry": {"mr": "ब्लूबेरी (Blueberry)", "hi": "ब्लूबेरी (Blueberry)"},
    "cherry": {"mr": "चेरी (Cherry)", "hi": "चेरी (Cherry)"},
    "corn": {"mr": "मका (Corn)", "hi": "मक्का (Corn)"},
    "grape": {"mr": "द्राक्षे (Grape)", "hi": "अंगूर (Grape)"},
    "orange": {"mr": "संत्री (Orange)", "hi": "संतरा (Orange)"},
    "peach": {"mr": "पीच (Peach)", "hi": "आड़ू (Peach)"},
    "pepper": {"mr": "शिमला मिरची (Bell Pepper)", "hi": "शिमला मिर्च (Bell Pepper)"},
    "potato": {"mr": "बटाटा (Potato)", "hi": "आलू (Potato)"},
    "raspberry": {"mr": "रास्पबेरी (Raspberry)", "hi": "रसभरी (Raspberry)"},
    "soybean": {"mr": "सोयाबीन (Soybean)", "hi": "सोयाबीन (Soybean)"},
    "squash": {"mr": "भोपळा (Squash)", "hi": "कद्दू (Squash)"},
    "strawberry": {"mr": "स्ट्रॉबेरी (Strawberry)", "hi": "स्ट्रॉबेरी (Strawberry)"},
    "tomato": {"mr": "टोमॅटो (Tomato)", "hi": "टमाटर (Tomato)"},
}


def get_default_prompt(lang="en"):
    """Return default farmer question for image analysis."""
    return DEFAULT_PROMPTS.get(lang, DEFAULT_PROMPTS["en"])


def localize_crop(crop_name, lang="en"):
    """Translate crop name into Marathi or Hindi if applicable."""
    if not crop_name or lang not in ("mr", "hi"):
        return crop_name
    c_lower = str(crop_name).lower()
    for key, trans in CROP_TRANSLATIONS.items():
        if key in c_lower:
            return trans.get(lang, crop_name)
    return crop_name


def validate_image_file(uploaded_file):
    """Validate uploaded file for presence, format, size, and image integrity.

    Returns:
        (image_bytes, error_message, status_code)
    """
    if not uploaded_file or not uploaded_file.filename:
        return None, "Please select or capture a valid plant image.", 400

    _, ext = os.path.splitext(uploaded_file.filename)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return (
            None,
            "Invalid image format. Supported formats: JPG, JPEG, PNG, WEBP.",
            400,
        )

    # Read bytes with 5 MB + 1 check
    image_bytes = uploaded_file.read(MAX_IMAGE_SIZE + 1)
    if not image_bytes:
        return None, "The uploaded image file is empty.", 400

    if len(image_bytes) > MAX_IMAGE_SIZE:
        return None, "Image file size must not exceed 5 MB.", 413

    # Verify image integrity via PIL
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
            if img.format not in ("JPEG", "PNG", "WEBP"):
                return None, "The uploaded file is not a supported image type.", 400
    except (UnidentifiedImageError, OSError, ValueError):
        return None, "Corrupted or invalid image file. Please upload a real photo.", 400

    return image_bytes, None, 200


def save_chat_image(image_bytes, user_id, original_filename=None):
    """Save the validated image to backend/uploads with user isolation prefix.

    Returns:
        safe_filename (e.g. 'chat_leaf_42_a1b2c3d4e5f6.jpg')
    """
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    ext = ".jpg"
    if original_filename:
        _, orig_ext = os.path.splitext(secure_filename(original_filename))
        if orig_ext.lower() in ALLOWED_EXTENSIONS:
            ext = orig_ext.lower()

    unique_token = uuid.uuid4().hex[:12]
    safe_filename = f"chat_leaf_{user_id}_{unique_token}{ext}"
    target_path = os.path.join(UPLOADS_DIR, safe_filename)

    with open(target_path, "wb") as f:
        f.write(image_bytes)

    return safe_filename


def analyze_leaf_image(image_bytes, language="en"):
    """Run TensorFlow plant disease inference and return structured diagnosis.

    Returns:
        dict with keys:
            - is_confident: bool (True if confidence >= 30%)
            - predicted_class: str
            - confidence: float
            - top_predictions: list of dicts
            - knowledge: dict from disease_knowledge
            - reply: str (structured 6-part response in selected language)
    """
    lang = language.lower() if language in ("en", "mr", "hi") else "en"

    # Import model and preprocessor from disease_routes to reuse memory
    try:
        from routes.disease_routes import model, class_labels, preprocess_image
    except Exception as e:
        model = None
        class_labels = None
        print(f"Error importing disease model: {e}")

    if model is None or class_labels is None:
        # Fallback if model could not be loaded
        return {
            "is_confident": False,
            "predicted_class": "Model_Unavailable",
            "confidence": 0.0,
            "top_predictions": [],
            "knowledge": {},
            "reply": _get_model_unavailable_reply(lang),
        }

    try:
        processed = preprocess_image(image_bytes)
        predictions = model.predict(processed, verbose=0)
        probabilities = predictions[0]

        predicted_idx = int(probabilities.argmax())
        predicted_class = class_labels[predicted_idx]
        confidence = float(probabilities[predicted_idx]) * 100.0

        top_indices = probabilities.argsort()[-3:][::-1]
        top_predictions = [
            {
                "class_name": class_labels[int(idx)],
                "confidence": round(float(probabilities[idx]) * 100.0, 2),
            }
            for idx in top_indices
        ]
    except Exception as err:
        print(f"Image analysis inference error: {err}")
        return {
            "is_confident": False,
            "predicted_class": "Inference_Error",
            "confidence": 0.0,
            "top_predictions": [],
            "knowledge": {},
            "reply": _get_inference_error_reply(lang),
        }

    from utils import disease_knowledge

    knowledge = disease_knowledge.get_disease_info(
        predicted_class, confidence=confidence, language=lang
    )

    is_confident = confidence >= CONFIDENCE_THRESHOLD

    if not is_confident:
        reply = _format_low_confidence_reply(confidence, lang)
    else:
        reply = _format_structured_vision_reply(predicted_class, confidence, knowledge, lang)

    return {
        "is_confident": is_confident,
        "predicted_class": predicted_class,
        "confidence": round(confidence, 2),
        "top_predictions": top_predictions,
        "knowledge": knowledge,
        "reply": reply,
    }


def _get_model_unavailable_reply(lang):
    if lang == "mr":
        return (
            "⚠️ वनस्पती रोग तपासणी मॉडेल सध्या उपलब्ध नाही. कृपया काही वेळाने पुन्हा प्रयत्न करा "
            "किंवा नजीकच्या कृषी सहाय्यकांशी संपर्क साधा."
        )
    if lang == "hi":
        return (
            "⚠️ पौध रोग पहचान मॉडल वर्तमान में अनुपलब्ध है। कृपया कुछ समय बाद पुनः प्रयास करें "
            "या स्थानीय कृषि सहायक से संपर्क करें।"
        )
    return (
        "⚠️ The plant disease detection model is currently unavailable. Please try again in a few "
        "moments or consult a local agricultural extension officer."
    )


def _get_inference_error_reply(lang):
    if lang == "mr":
        return (
            "⚠️ प्रतिमेचे विश्लेषण करताना त्रुटी आली. कृपया स्पष्ट आणि योग्य आकाराचा फोटो पुन्हा अपलोड करा."
        )
    if lang == "hi":
        return (
            "⚠️ छवि का विश्लेषण करते समय त्रुटि हुई। कृपया स्पष्ट और उपयुक्त आकार का फोटो दोबारा अपलोड करें।"
        )
    return (
        "⚠️ An error occurred while analyzing the image. Please upload a clear photo with good lighting."
    )


def _format_low_confidence_reply(confidence, lang):
    """Honest notification when confidence is < 30% or non-leaf image."""
    conf_str = f"{confidence:.1f}%"
    if lang == "mr":
        return (
            f"🔍 **प्रतिमा ओळख सूचना (अचूकता: {conf_str})**\n\n"
            "आम्ही या छायाचित्रात समर्थित वनस्पतीचे स्पष्ट पान ओळखू शकलो नाही (विश्वासार्हता ३०% पेक्षा कमी आहे).\n\n"
            "आमचा सहाय्यक खालील १४ पिकांवरील पानांच्या रोगांची अचूक तपासणी करतो:\n"
            "• सफरचंद, ब्लूबेरी, चेरी, मका, द्राक्षे, संत्रा, पीच, शिमला मिरची, बटाटा, रास्पबेरी, सोयाबीन, भोपळा, स्ट्रॉबेरी आणि टोमॅटो.\n\n"
            "📸 **चांगला फोटो काढण्यासाठी उपयुक्त सूचना:**\n"
            "१. कॅमेरा पानापासून १५–२० सेंमी अंतरावर धरून फोकस करा.\n"
            "२. चांगल्या नैसर्गिक सूर्यप्रकाशात फोटो घ्या; थेट सावली किंवा प्रखर फ्लॅश टाळा.\n"
            "३. संपूर्ण झाडाऐवजी रोगट पानावर थेट लक्ष केंद्रित करा.\n"
            "४. कॅमेरा हलणार नाही याची काळजी घ्या जेणेकरून फोटो स्पष्ट येईल.\n\n"
            "कृपया स्पष्ट फोटो काढून पुन्हा पाठवा!"
        )
    if lang == "hi":
        return (
            f"🔍 **छवि पहचान सूचना (विश्वास स्तर: {conf_str})**\n\n"
            "हम इस तस्वीर में किसी समर्थित पौधे की स्पष्ट पत्ती की पहचान नहीं कर सके (विश्वास स्तर ३०% से कम है)।\n\n"
            "हमारा सहायक निम्नलिखित १४ फसलों की पत्तियों के रोगों की पहचान करता है:\n"
            "• सेब, ब्लूबेरी, चेरी, मक्का, अंगूर, संतरा, आड़ू, शिमला मिर्च, आलू, रसभरी, सोयाबीन, कद्दू, स्ट्रॉबेरी और टमाटर।\n\n"
            "📸 **स्पष्ट तस्वीर लेने के सुझाव:**\n"
            "१. कैमरे को पत्ती से १५-२० सेमी की दूरी पर रखकर फोकस करें।\n"
            "२. प्राकृतिक और अच्छी रोशनी में फोटो लें; तेज परछाई या फ्लैश की चमक से बचें।\n"
            "३. पूरे पेड़ के बजाय प्रभावित पत्ती के धब्बों पर सीधा ध्यान केंद्रित करें।\n"
            "४. कैमरा स्थिर रखें ताकि तस्वीर धुंधली न आए।\n\n"
            "कृपया एक स्पष्ट तस्वीर लेकर दोबारा प्रयास करें!"
        )
    return (
        f"🔍 **Image Recognition Notice (Confidence: {conf_str})**\n\n"
        "We could not clearly identify a recognized plant leaf in this photo (confidence is below 30%).\n\n"
        "Our assistant is trained to recognize leaf conditions across 14 supported crops:\n"
        "• Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Bell Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, and Tomato.\n\n"
        "📸 **Tips for Capturing a Clearer Photo:**\n"
        "1. Hold the camera 15–20 cm away and focus directly on an individual leaf.\n"
        "2. Ensure good, natural daylight; avoid deep shadows or direct flash glare.\n"
        "3. Focus on visible spots, lesions, or discoloration rather than the whole plant.\n"
        "4. Keep your device steady to prevent motion blur.\n\n"
        "Please take a clearer photo and send it again!"
    )


def _format_structured_vision_reply(predicted_class, confidence, knowledge, lang):
    """Build the required 6-part farmer-friendly response."""
    display_name = knowledge.get("display_name") or predicted_class.replace("___", " — ").replace("_", " ")
    crop = knowledge.get("crop") or predicted_class.split("___")[0].replace("_", " ")
    crop_localized = localize_crop(crop, lang)
    is_healthy = knowledge.get("is_healthy", False) or "healthy" in predicted_class.lower()

    symptoms = knowledge.get("symptoms") or []
    if isinstance(symptoms, list):
        symptoms_text = "\n• ".join([str(s) for s in symptoms if s])
    else:
        symptoms_text = str(symptoms)

    causes = knowledge.get("possible_causes") or []
    if isinstance(causes, list):
        causes_text = "\n• ".join([str(c) for c in causes if c])
    else:
        causes_text = str(causes)

    prevention = knowledge.get("prevention") or []
    if isinstance(prevention, list):
        prevention_text = "\n• ".join([str(p) for p in prevention if p])
    else:
        prevention_text = str(prevention)

    treatments = knowledge.get("safe_treatment") or knowledge.get("care_recommendations") or []
    if isinstance(treatments, list):
        treatments_text = "\n• ".join([str(t) for t in treatments if t])
    else:
        treatments_text = str(treatments)

    conf_str = f"{confidence:.1f}%"

    if lang == "mr":
        healthy_obs = "पानांचा रंग आणि रचना निरोगी दिसत असून रोगाचे कोणतेही स्पष्ट लक्षण आढळत नाही."
        healthy_diag = f"{crop_localized} पिकाचे पान निरोगी दिसत आहे."
        healthy_causes = "योग्य पोषण, पुरेसा सूर्यप्रकाश आणि संतुलित सिंचनामुळे वनस्पती निरोगी आहे."
        healthy_treat = "नियमित सेंद्रिय खतांचा वापर आणि प्रतिबंधात्मक निंबोळी अर्क फवारणी सुरू ठेवा."

        return (
            f"📸 **वनस्पती प्रतिमा विश्लेषण**\n\n"
            f"१. **प्रतिमेतील निरीक्षण (Observation):**\n"
            f"• पीक: {crop_localized}\n"
            f"• दिसणारी लक्षणे: {symptoms_text if not is_healthy else healthy_obs}\n"
            f"• AI मॉडेल अचूकता (Confidence): {conf_str}\n\n"
            f"२. **संभाव्य वनस्पती समस्या (Possible Condition):**\n"
            f"• आढळलेली स्थिती: {display_name if not is_healthy else healthy_diag}\n"
            f"• *महत्त्वाची सूचना*: हे प्रतिमेवर आधारित स्वयंचलित AI दृश्य मूल्यांकन आहे, प्रयोगशाळेतील प्रमाणित रोगनिदान नाही.\n\n"
            f"३. **संभाव्य कारणे (Possible Causes):**\n"
            f"• {causes_text if not is_healthy else healthy_causes}\n\n"
            f"४. **शिफारस केलेली खबरदारी (Recommended Precautions):**\n"
            f"• {prevention_text}\n\n"
            f"५. **प्रत्यक्ष काळजी व सुरक्षित उपचार (Safe Care & Treatment):**\n"
            f"• {treatments_text if not is_healthy else healthy_treat}\n"
            f"• *टीप*: कोणतीही तीव्र रासायनिक औषधे वापरण्यापूर्वी तज्ज्ञांचा सल्ला घ्या; सुरुवातीला सेंद्रिय उपायांना प्राधान्य द्या.\n\n"
            f"६. **कृषी तज्ज्ञांशी कधी संपर्क साधावा (Expert Consultation):**\n"
            f"• जर पानांवरील डाग किंवा पिवळेपणा ३ ते ५ दिवसांत २०% पेक्षा जास्त झाडांवर पसरला तर.\n"
            f"• मुख्य खोड किंवा फांद्या सुकू लागल्यास अथवा फळांवर डाग दिसल्यास.\n"
            f"• स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी अधिकाऱ्यांकडून प्रत्यक्ष पाहणी करून घ्या."
        )

    if lang == "hi":
        healthy_obs = "पत्तियों का रंग और बनावट स्वस्थ दिखाई दे रही है और किसी रोग के लक्षण नहीं हैं।"
        healthy_diag = f"{crop_localized} की पत्ती स्वस्थ प्रतीत हो रही है।"
        healthy_causes = "संतुलित पोषण, पर्याप्त धूप और उचित सिंचाई के कारण पौधा स्वस्थ है।"
        healthy_treat = "नियमित जैविक खाद और निवारक नीम तेल का छिड़काव जारी रखें।"

        return (
            f"📸 **पौधे की तस्वीर का विश्लेषण**\n\n"
            f"१. **तस्वीर में क्या देखा गया (Observation):**\n"
            f"• फसल: {crop_localized}\n"
            f"• देखे गए लक्षण: {symptoms_text if not is_healthy else healthy_obs}\n"
            f"• AI मॉडल विश्वास स्तर (Confidence): {conf_str}\n\n"
            f"२. **संभाव्य पौधे की समस्या (Possible Condition):**\n"
            f"• पहचानी गई स्थिति: {display_name if not is_healthy else healthy_diag}\n"
            f"• *महत्वपूर्ण सूचना*: यह छवि मॉडल पर आधारित स्वचालित दृश्य मूल्यांकन है, प्रमाणित प्रयोगशाला परीक्षण नहीं।\n\n"
            f"३. **संभाव्य कारण (Possible Causes):**\n"
            f"• {causes_text if not is_healthy else healthy_causes}\n\n"
            f"४. **सुझाई गई सावधानियां (Recommended Precautions):**\n"
            f"• {prevention_text}\n\n"
            f"५. **व्यावहारिक देखभाल और सुरक्षित उपचार (Safe Care & Treatment):**\n"
            f"• {treatments_text if not is_healthy else healthy_treat}\n"
            f"• *नोट*: बिना विशेषज्ञ सलाह के अत्यधिक रासायनिक कीटनाशकों का उपयोग न करें; पहले जैविक तरीकों को अपनाएं।\n\n"
            f"६. **कृषि विशेषज्ञ से कब संपर्क करें (Expert Consultation):**\n"
            f"• यदि पत्तियों पर धब्बे ३ से ५ दिनों में २०% से अधिक क्षेत्र में फैल जाएं।\n"
            f"• यदि शाखाएं या मुख्य तना सूखने लगे अथवा फलों पर लक्षण दिखें।\n"
            f"• प्रमाणित उपचार के लिए नजदीकी कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।"
        )

    # Default English
    healthy_obs = "Foliage shows vibrant color and structure with no abnormal spots or wilting."
    healthy_diag = f"{crop} leaf appears healthy and vigorous."
    healthy_causes = "Balanced soil nutrients, proper watering, and favorable weather maintain healthy growth."
    healthy_treat = "Maintain regular crop monitoring and apply organic preventive measures like neem oil."

    return (
        f"📸 **Plant Image Analysis**\n\n"
        f"1. **What is Observed**:\n"
        f"• Crop: {crop}\n"
        f"• Visual Symptoms: {symptoms_text if not is_healthy else healthy_obs}\n"
        f"• Model Confidence: {conf_str}\n\n"
        f"2. **Possible Plant Problem**:\n"
        f"• Condition Detected: {display_name if not is_healthy else healthy_diag}\n"
        f"• *Notice*: This is an automated visual evaluation based on an image model, not a certified laboratory diagnosis.\n\n"
        f"3. **Possible Causes**:\n"
        f"• {causes_text if not is_healthy else healthy_causes}\n\n"
        f"4. **Recommended Precautions**:\n"
        f"• {prevention_text}\n\n"
        f"5. **Practical Care & Treatment Steps**:\n"
        f"• {treatments_text if not is_healthy else healthy_treat}\n"
        f"• *Guideline*: Prioritize cultural and organic practices first; avoid unverified high-potency chemical mixes without certified agronomic consultation.\n\n"
        f"6. **When to Contact an Agricultural Expert**:\n"
        f"• If lesions or wilting spread across more than 20% of your crop canopy within 3 to 5 days.\n"
        f"• If lesions spread from foliage to fruits or main vascular stems.\n"
        f"• Consult your local Krishi Vigyan Kendra (KVK) or extension officer before applying scheduled prescription chemicals."
    )
