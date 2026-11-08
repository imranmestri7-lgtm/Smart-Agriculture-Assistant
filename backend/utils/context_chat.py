"""Context-aware farming assistant engine for AgriSmart Phase 9.

Analyzes authenticated farmer records (farms, crops, diagnoses, irrigation, weather)
and provides personalized, accurate, multilingual guidance with conversation continuity.
"""

from datetime import date, datetime
import os
import re
import requests

WEATHER_API_BASE_URL = "https://api.weatherapi.com/v1"


def _format_date(d):
    """Format date string or date object cleanly."""
    if not d:
        return ""
    if isinstance(d, (datetime, date)):
        return d.strftime("%Y-%m-%d")
    return str(d)[:10]


def _calculate_days_since(p_date):
    """Calculate days elapsed since planting date."""
    if not p_date:
        return None
    try:
        if isinstance(p_date, str):
            p_date = datetime.strptime(p_date[:10], "%Y-%m-%d").date()
        elif isinstance(p_date, datetime):
            p_date = p_date.date()
        return max(0, (date.today() - p_date).days)
    except Exception:
        return None


def _calculate_days_until(h_date):
    """Calculate integer days until harvest date."""
    if not h_date:
        return None
    try:
        if isinstance(h_date, str):
            h_date = datetime.strptime(h_date[:10], "%Y-%m-%d").date()
        elif isinstance(h_date, datetime):
            h_date = h_date.date()
        return (h_date - date.today()).days
    except Exception:
        return None


def _find_matching_crop(text, crops):
    """Find a crop mentioned in the text among the farmer's registered crops."""
    text_lower = text.lower()
    for c in crops:
        c_name = (c.get("crop_name") or "").lower()
        if c_name and c_name in text_lower:
            return c
    return None


def _infer_crop_from_recent_chat(recent_chat, crops):
    """Infer active crop from recent conversation messages for follow-up continuity."""
    if not recent_chat or not crops:
        return None

    # Scan from latest message backwards
    for chat_turn in reversed(recent_chat):
        combined = f"{chat_turn.get('message', '')} {chat_turn.get('response', '')}".lower()
        for c in crops:
            c_name = (c.get("crop_name") or "").lower()
            if c_name and (f" {c_name} " in f" {combined} " or combined.startswith(c_name) or combined.endswith(c_name)):
                return c
    return None


def _get_growth_stage_advice(crop_name, growth_status, language):
    """Return verified agronomic care advice for a crop's current growth stage."""
    status = (growth_status or "Newly Planted").strip()

    advice_en = {
        "Newly Planted": f"For newly planted {crop_name}, maintain light surface moisture for seed germination and seedling establishment. Avoid water stagnation.",
        "Growing": f"For {crop_name} in the active vegetative stage, ensure adequate nitrogen and balanced nutrients. Regularly weed and check leaf undersides for early pests.",
        "Flowering": f"Critical flowering stage for {crop_name}: Maintain consistent soil moisture without waterlogging. Avoid harsh chemical sprays during active pollination to protect bees.",
        "Fruiting": f"For fruiting {crop_name}: Ensure steady watering to prevent fruit splitting or blossom-end rot. Monitor calcium and potassium levels.",
        "Ready for Harvest": f"{crop_name} is ready for harvest! Cease irrigation a few days prior to harvesting to improve shelf life and reduce post-harvest moisture rots. Harvest during cool morning hours.",
        "Harvested": f"{crop_name} has been harvested. Clear field residues to prevent pest carryover and consider soil testing before the next planting cycle."
    }

    advice_mr = {
        "Newly Planted": f"नुकत्याच लावलेल्या {crop_name} पिकासाठी बियाणे उगवणीसाठी मातीत हलका ओलावा ठेवा. पाणी साचू देऊ नका.",
        "Growing": f"सध्या वाढीच्या टप्प्यातील {crop_name} पिकासाठी योग्य खतांचे व्यवस्थापन आणि नियमित खुरपणी करा. पानांच्या खाली कीड आहे का ते तपासा.",
        "Flowering": f"{crop_name} पिकासाठी फुलोऱ्याचा टप्पा अत्यंत महत्त्वाचा आहे: मातीमध्ये नियमित ओलावा ठेवा. परागीभवनादरम्यान मधमाश्यांचे रक्षण करण्यासाठी कडक कीटकनाशक फवारणी टाळा.",
        "Fruiting": f"फळधारणेच्या टप्प्यातील {crop_name} पिकासाठी: फळांना तडे जाऊ नयेत म्हणून पाण्याचे योग्य प्रमाण ठेवा. कॅल्शियम व पोटॅशियमची कमतरता भासू देऊ नका.",
        "Ready for Harvest": f"{crop_name} पीक काढणीसाठी तयार आहे! साठवणूक क्षमता वाढवण्यासाठी काढणीच्या काही दिवस आधी पाणी देणे थांबवा. सकाळी थंड वेळेत काढणी करा.",
        "Harvested": f"{crop_name} पिकाची काढणी पूर्ण झाली आहे. पुढील हंगामापूर्वी जमिनीची मशागत आणि माती परीक्षण करून घ्या."
    }

    advice_hi = {
        "Newly Planted": f"नई बोई गई {crop_name} फसल के लिए अंकुरण हेतु मिट्टी में हल्की नमी बनाए रखें। खेत में पानी जमा न होने दें।",
        "Growing": f"विकास चरण में {crop_name} फसल के लिए संतुलित नाइट्रोजन और पोषक तत्वों की आपूर्ति सुनिश्चित करें। समय पर निराई-गुड़ाई करें।",
        "Flowering": f"{crop_name} फसल के लिए फूल आने का चरण महत्वपूर्ण है: मिट्टी में नियमित नमी रखें। परागण के समय मधुमक्खियों की सुरक्षा हेतु तेज कीटनाशक न छिड़कें।",
        "Fruiting": f"फल बनने के चरण में {crop_name} फसल के लिए: फलों को फटने से बचाने हेतु नियमित सिंचाई करें। कैल्शियम और पोटेशियम की निगरानी करें।",
        "Ready for Harvest": f"{crop_name} फसल कटाई के लिए तैयार है! भंडारण क्षमता बेहतर रखने के लिए कटाई से कुछ दिन पहले पानी देना बंद करें। सुबह के समय कटाई करें।",
        "Harvested": f"{crop_name} फसल की कटाई हो चुकी है। अगले मौसम की तैयारी के लिए खेत की जुताई और मिट्टी की जांच कराएं।"
    }

    if language == "mr":
        return advice_mr.get(status, advice_mr["Growing"])
    elif language == "hi":
        return advice_hi.get(status, advice_hi["Growing"])
    return advice_en.get(status, advice_en["Growing"])


def _extract_recent_disease_info(recent_chat, diagnoses=None):
    """Extract most recently diagnosed plant disease and crop from conversation or diagnosis history.

    Returns dict with keys: class_name, display_name, crop, is_healthy or None
    """
    if recent_chat:
        for turn in reversed(recent_chat):
            msg = turn.get("message") or ""
            resp = turn.get("response") or ""

            # 1. Tag in message: [class:Tomato___Early_blight]
            class_match = re.search(r"\[class:([A-Za-z0-9_]+)\]", msg)
            if class_match:
                cls_name = class_match.group(1)
                is_healthy = "healthy" in cls_name.lower()
                crop = cls_name.split("___")[0].replace("_", " ") if "___" in cls_name else "Plant"
                return {
                    "class_name": cls_name,
                    "display_name": cls_name.replace("___", " — ").replace("_", " "),
                    "crop": crop,
                    "is_healthy": is_healthy
                }

            # 2. Structured vision markers in response
            if any(k in resp for k in ("Plant Image Analysis", "वनस्पती प्रतिमा विश्लेषण", "पौधे की तस्वीर का विश्लेषण", "Condition Detected:", "आढळलेली स्थिती:", "पहचानी गई स्थिति:")):
                cond_match = re.search(r"(?:Condition Detected|आढळलेली स्थिती|पहचानी गई स्थिति):\s*([^\n\r*]+)", resp)
                if cond_match:
                    display = cond_match.group(1).strip()
                    is_healthy = any(h in display.lower() for h in ("healthy", "निरोगी", "स्वस्थ"))
                    crop_match = re.search(r"(?:Crop|पीक|फसल):\s*([^\n\r*]+)", resp)
                    crop_name = crop_match.group(1).strip() if crop_match else "Plant"
                    crop_name = crop_name.split("(")[0].strip()
                    return {
                        "class_name": display,
                        "display_name": display,
                        "crop": crop_name,
                        "is_healthy": is_healthy
                    }

    # 3. Fallback to recent diagnosis from database
    if diagnoses and len(diagnoses) > 0:
        pred_cls = diagnoses[0].get("predicted_class")
        if pred_cls and pred_cls != "Unknown":
            is_healthy = "healthy" in pred_cls.lower()
            crop = pred_cls.split("___")[0].replace("_", " ") if "___" in pred_cls else "Plant"
            return {
                "class_name": pred_cls,
                "display_name": pred_cls.replace("___", " — ").replace("_", " "),
                "crop": crop,
                "is_healthy": is_healthy
            }

    return None


def is_context_relevant_query(message: str) -> bool:
    """Return True if message requests personalized farmer context, history, or follow-up."""
    if not message or not isinstance(message, str):
        return False

    raw = message.strip()
    text = raw.lower()

    # Never treat model disease class names (e.g. Tomato___Early_blight) as personal context
    if "___" in raw:
        return False

    # 1. Quick suggestion chips and explicit context queries
    context_patterns = [
        # Crop status
        "crop status", "crops status", "show my crop", "show my crops", "what crops do i have",
        "which crops am i growing", "what crops am i growing", "crops am i growing", "crops do i have",
        "my registered crops", "list my crops", "list of crops", "tell me about my",
        "माझी पिके", "पिकांची स्थिती", "पिकांची सद्यस्थिती", "पिकांची माहिती",
        "मेरी फसलें", "फसल स्थिति", "फसल की स्थिति", "फसलों की स्थिति",

        # Harvest reminders
        "harvest reminder", "harvest reminders", "when is my crop expected to be harvested",
        "which crops are ready for harvest", "ready for harvest", "when will my crop be harvested",
        "harvest date", "expected harvest", "when will it be harvested", "when will it be",
        "when should i harvest it", "when to harvest it", "when to harvest",
        "काढणी स्मरणपत्रे", "काढणी माहिती", "काढणी तारीख", "कापणी", "काढणी कधी", "कटाई रिमाइंडर", "फसल कटाई", "कटाई कब",

        # Irrigation history / guidance from records
        "what irrigation recommendation did i receive", "irrigation recommendation did i receive",
        "what irrigation recommendation", "recent irrigation", "irrigation guidance",
        "how much water did", "my irrigation status", "does my crop need water",
        "how much water does it need", "when to water it", "how much water", "when should i water it",
        "सिंचन मार्गदर्शन", "सिंचन शिफारस", "सिंचाई मार्गदर्शन", "सिंचाई सिफारिश",
        "याला किती पाणी द्यावे", "पाणी कधी द्यावे", "इसे कितना पानी चाहिए", "पानी कब दें",

        # Disease diagnosis history & prevention
        "recent disease diagnosis", "recent diagnosis", "show my diagnosis", "my disease diagnosis",
        "what diseases were found", "previous disease", "disease history", "disease prevention",
        "रोगनिदान", "माझे रोगनिदान", "मागील रोग", "बीमारी जांच", "रोग निदान", "रोग प्रतिबंध", "रोग रोकथाम",

        # Farm summary
        "my farm summary", "give me my farm", "farm summary", "my farms",
        "शेताचा सारांश", "माझे शेत", "खेत का सारांश", "मेरा खेत",

        # Weather info
        "weather information", "weather info", "weather forecast for my", "हवामान माहिती", "मौसम जानकारी",

        # Crop care / precautions on registered/unregistered crops
        "what should i do for my", "what should i do for", "how should i care for my",
        "precautions for my", "precaution for my", "care recommendation for my",
        "protect my crop", "protect my growing",
        "काय काळजी घ्यावी", "काय करावे माझ्या", "क्या करना चाहिए मेरी", "मेरी फसल की देखभाल",

        # Follow-up continuity cues
        "when will it be", "how to care for it", "what care does it need", "what care does it",
        "how do i care for this", "how to care for this", "care for this", "care for this condition", "care for this plant",
        "what fertilizer should i give", "what fertilizer does it need", "कोणते खत द्यावे", "कौन सी खाद दें",

        # Disease follow-up continuity cues
        "how do i treat this", "how to treat this", "treatment for this", "how to cure this",
        "what should i spray", "which fungicide", "can i spray", "how to cure it", "how to treat it",
        "how to cure", "how to treat", "treat this disease", "cure this disease", "spray for this",
        "fungicide for this", "medicine for this", "what medicine", "what chemical", "what spray",
        "how to prevent this", "how can i prevent this", "how to prevent it", "prevention for this",
        "stop this disease", "stop it from spreading", "will it spread", "can it spread", "spread to other",
        "what causes this", "what caused it", "why did this happen", "cause of this", "what is the cause",
        "tell me more about this disease", "tell me more about this", "what should i do about this",
        "what to do for this disease", "what should i do for this", "what to do now", "what should i do",

        # Marathi disease follow-ups
        "हा रोग कसा बरा करावा", "यावर काय उपाय करावा", "उपाय काय", "यावर कोणती फवारणी करावी",
        "कोणते औषध फवारावे", "औषध काय", "फवारणी काय करावी", "हा रोग कशामुळे होतो",
        "हा कसा पसरतो", "हा रोग कसा रोखावा", "यावर काय करावे", "या रोगावर उपाय",
        "या रोगाची काळजी", "हा रोग बरा होईल का", "हा पसरू शकतो का",

        # Hindi disease follow-ups
        "इसका इलाज कैसे करें", "इस बीमारी का क्या उपाय है", "कौन सी दवा छिड़कें",
        "क्या छिड़काव करें", "यह किस कारण से होता है", "यह कैसे फैलता है",
        "इसको कैसे रोकें", "इस बीमारी से कैसे बचें", "मुझे क्या करना चाहिए",
        "इस पर क्या उपाय करें", "क्या यह फैल सकती है", "इस बीमारी की दवा",
    ]

    for pat in context_patterns:
        if pat in text:
            return True

    return False


def handle_farmer_context(message, language="en", context=None):
    """
    Examines message in the context of the logged-in farmer's data.
    Returns a dict with {"category": ..., "reply": ..., "is_custom_localized": True} or None.
    """
    if not context or not isinstance(context, dict):
        return None

    raw_text = (message or "").strip()
    text = raw_text.lower()
    crops = context.get("crops") or []
    farms = context.get("farms") or []
    diagnoses = context.get("recent_diagnoses") or []
    irrigations = context.get("recent_irrigations") or []
    recent_chat = context.get("recent_chat") or []

    # 1. Identify active crop (from current message or conversation continuity)
    matched_crop = _find_matching_crop(text, crops)
    is_follow_up = False

    if not matched_crop:
        # Check follow-up indicators
        follow_up_cues = (
            "it", "its", "this crop", "my crop", "harvest date", "when to harvest",
            "when is it", "how to care", "precautions", "what care", "what to do",
            "status", "water", "irrigation", "काढणी", "काळजी", "कटाई", "देखभाल"
        )
        if any(cue in text for cue in follow_up_cues):
            inferred = _infer_crop_from_recent_chat(recent_chat, crops)
            if inferred:
                matched_crop = inferred
                is_follow_up = True

    # =========================================================================
    # INTENT 0: RECENT DISEASE / LEAF DIAGNOSIS FOLLOW-UP
    # =========================================================================
    recent_disease = _extract_recent_disease_info(recent_chat, diagnoses)

    disease_followup_cues = (
        "this disease", "the disease", "this problem", "this condition",
        "treat this", "how to treat", "treatment", "cure", "fungicide",
        "spray for this", "which fungicide", "medicine for this", "how to cure",
        "prevent this", "prevention for this", "stop it from spreading", "will it spread", "can it spread",
        "cause of this", "what causes this", "what caused it", "why did this happen",
        "what should i do about this disease", "what to do for this disease",
        # Marathi
        "हा रोग", "हा आजार", "या रोगा", "या रोगावर", "यावर फवारणी", "औषध काय",
        "बरे करावे", "प्रतिबंध", "रोखावा", "पसरतो", "पसरू", "कशामुळे होतो", "यावर काय उपाय",
        # Hindi
        "यह बीमारी", "इस बीमारी", "इसका इलाज", "इस बीमारी का उपाय", "दवा छिड़कें",
        "रोकथाम", "रोकें", "फैलता", "फैलेगा", "इस बीमारी का कारण"
    )

    potential_crops = ("cotton", "wheat", "rice", "sugarcane", "potato", "maize", "soybean", "onion", "banana", "chilli")
    has_unregistered_crop_query = any(re.search(rf"\b{w}\b", text) for w in potential_crops) and "disease" not in text and "रोग" not in text and "बीमारी" not in text
    has_registered_crop_mention = any((c.get("crop_name") or "").lower() in text for c in crops if c.get("crop_name"))

    is_asking_disease = (
        recent_disease is not None and
        not has_registered_crop_mention and
        not has_unregistered_crop_query and
        any(cue in text for cue in disease_followup_cues)
    )

    if is_asking_disease:
        from utils import disease_knowledge
        from utils.image_chat import localize_crop
        cls_name = recent_disease.get("class_name") or "Plant condition"
        knowledge = disease_knowledge.get_disease_info(cls_name, language=language)
        display_name = knowledge.get("display_name") or recent_disease.get("display_name") or "Plant condition"
        raw_crop = knowledge.get("crop") or recent_disease.get("crop") or "Plant"
        crop_name = localize_crop(raw_crop, language)
        is_healthy = recent_disease.get("is_healthy", False) or knowledge.get("is_healthy", False)

        if is_healthy:
            if language == "mr":
                reply = (
                    f"आपल्या नुकत्याच तपासलेल्या छायाचित्रानुसार आपले **{crop_name}** पीक **निरोगी (Healthy)** आढळले आहे.\n\n"
                    f"पिकाची निरोगी वाढ टिकवण्यासाठी:\n"
                    f"• **सिंचन**: पानांवर पाणी न टाकता मुळांशी ठिबक सिंचनाने पाणी द्या.\n"
                    f"• **पोषण**: वाढीच्या टप्प्यानुसार संतुलित सेंद्रिय खत किंवा कंपोस्ट वापरा.\n"
                    f"• **तपासणी**: पानांच्या खाली कीड किंवा डाग आहेत का ते आठवड्यातून एकदा तपासा.\n"
                    f"• **हवा खेळती ठेवणे**: अतिरिक्त फांद्यांची छाटणी करून झाडात पुरेशी हवा खेळती राहील याची काळजी घ्या."
                )
            elif language == "hi":
                reply = (
                    f"आपकी हालिया तस्वीर के अनुसार आपकी **{crop_name}** फसल **स्वस्थ (Healthy)** पाई गई है।\n\n"
                    f"फसल को स्वस्थ बनाए रखने के लिए:\n"
                    f"• **सिंचाई**: पत्तियों को गीला किए बिना ड्रिप द्वारा केवल जड़ों में पानी दें।\n"
                    f"• **पोषण**: विकास चरण के अनुसार संतुलित जैविक खाद या कंपोस्ट का प्रयोग करें।\n"
                    f"• **निरीक्षण**: सप्ताह में एक बार पत्तियों के नीचे कीट या धब्बों की जांच करें।\n"
                    f"• **हवा और धूप**: खेत में खरपतवार नियंत्रण रखें ताकि पौधों को पर्याप्त धूप और हवा मिल सके।"
                )
            else:
                reply = (
                    f"Based on your recent leaf photo, your **{crop_name}** was evaluated as **Healthy**.\n\n"
                    f"To keep your {crop_name} thriving and productive:\n"
                    f"• **Irrigation**: Water at the base early in the morning using drip irrigation to keep leaves dry.\n"
                    f"• **Nutrition**: Apply balanced compost or organic fertilizer matching the current vegetative stage.\n"
                    f"• **Monitoring**: Regularly inspect lower foliage and stems for early signs of pests or discoloration.\n"
                    f"• **Airflow**: Prune dense shoots to ensure good ventilation and prevent microclimates favorable to fungi."
                )
            return {"category": "disease", "reply": reply, "knowledge": knowledge, "is_custom_localized": True}

        # Diseased condition: check sub-intents
        symptoms_list = knowledge.get("symptoms", [])
        causes_list = knowledge.get("possible_causes", [])
        treatments_list = knowledge.get("safe_treatment") or knowledge.get("care_recommendations") or []
        prevention_list = knowledge.get("prevention", [])

        # Sub-intent A: Treatment / Spray / Medicine / Cure
        is_treat_query = any(k in text for k in (
            "treat", "cure", "spray", "fungicide", "medicine", "remedy",
            "उपचार", "फवारणी", "औषध", "बरे", "बरा", "उपाय", "इलाज", "दवा", "छिड़काव"
        ))

        # Sub-intent B: Prevention / Stop Spread
        is_prev_query = any(k in text for k in (
            "prevent", "prevention", "stop", "spread", "avoid",
            "प्रतिबंध", "रोखावा", "पसरतो", "पसरू", "रोकथाम", "रोकें", "फैल"
        ))

        # Sub-intent C: Causes / Why
        is_cause_query = any(k in text for k in (
            "cause", "why", "origin", "reason",
            "कारण", "कशामुळे", "क्यों"
        ))

        if is_treat_query:
            if language == "mr":
                treat_str = "\n• ".join([str(t) for t in treatments_list[:3]]) if treatments_list else "शिफारस केलेल्या जैविक किंवा तांबे-युक्त उत्पादनांची फवारणी करा आणि कृषी तज्ज्ञांचा सल्ला घ्या."
                reply = (
                    f"आपल्या **{crop_name}** पिकावरील **{display_name}** रोगनिदानावर आधारित सुरक्षित उपचार उपाय:\n\n"
                    f"• **स्वच्छता**: रोगट पाने त्वरित कात्रीने कापून शेताबाहेर नेऊन नष्ट करा. रोगट अवशेष शेतात ठेवू नका.\n"
                    f"• **उपचार व फवारणी शिफारसी**:\n• {treat_str}\n"
                    f"• **फवारणीची वेळ**: सकाळी लवकर किंवा संध्याकाळी कोरड्या हवामानात फवारणी करा. औषधाच्या लेबलवरील सूचना तंतोतंत पाळा.\n\n"
                    f"*टीप: रासायनिक औषधांच्या वापरापूर्वी स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी अधिकाऱ्यांचा सल्ला घ्या.*"
                )
            elif language == "hi":
                treat_str = "\n• ".join([str(t) for t in treatments_list[:3]]) if treatments_list else "अनुशंसित जैविक या तांबा-युक्त कवकनाशी का प्रयोग करें और कृषि विशेषज्ञ से सलाह लें।"
                reply = (
                    f"आपकी **{crop_name}** फसल के **{display_name}** रोग निदान पर आधारित सुरक्षित उपचार उपाय:\n\n"
                    f"• **स्वच्छता**: संक्रमित पत्तियों को तुरंत काटकर खेत से दूर नष्ट कर दें।\n"
                    f"• **उपचार और छिड़काव सलाह**:\n• {treat_str}\n"
                    f"• **छिड़काव का समय**: सुबह जल्दी या शाम को शांत मौसम में छिड़काव करें। उत्पाद लेबल के निर्देशों का पालन करें।\n\n"
                    f"*नोट: गंभीर प्रकोप में नजदीकी कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।*"
                )
            else:
                treat_str = "\n• ".join([str(t) for t in treatments_list[:3]]) if treatments_list else "Apply recommended protective bio-fungicides and consult a local agricultural extension officer."
                reply = (
                    f"Based on your recent diagnosis for **{display_name}** on **{crop_name}**, here are the recommended safe treatment steps:\n\n"
                    f"• **Sanitation**: Immediately prune and safely dispose of infected leaves or stems. Do not leave diseased debris in the field.\n"
                    f"• **Safe Treatment Guidance**:\n• {treat_str}\n"
                    f"• **Application Advice**: Spray during calm, dry morning or late afternoon hours. Always observe product label instructions and pre-harvest intervals.\n\n"
                    f"*Note: For severe infections or chemical prescriptions, consult your local Krishi Vigyan Kendra (KVK) or extension officer.*"
                )
            return {"category": "disease", "reply": reply, "knowledge": knowledge, "is_custom_localized": True}

        if is_prev_query:
            if language == "mr":
                prev_str = "\n• ".join([str(p) for p in prevention_list[:4]]) if prevention_list else "पिकांची फेरपालट करा आणि पानांवर पाणी साचणे टाळा."
                reply = (
                    f"**{display_name}** हा रोग इतर झाडांवर पसरू नये म्हणून खबरदारीचे उपाय:\n\n"
                    f"• {prev_str}\n"
                    f"• **पाण्याचे व्यवस्थापन**: पाण्याचा निचरा योग्य ठेवा आणि मुळांशी ठिबक सिंचनाने पाणी द्या.\n"
                    f"• **साधने निर्जंतुक करणे**: छाटणीची कात्री किंवा अवजारे एका झाडाहून दुसऱ्या झाडावर वापरताना स्वच्छ करा."
                )
            elif language == "hi":
                prev_str = "\n• ".join([str(p) for p in prevention_list[:4]]) if prevention_list else "फसलों का चक्र अपनाएं और पत्तियों पर पानी जमा न होने दें।"
                reply = (
                    f"**{display_name}** को अन्य पौधों में फैलने से रोकने के लिए सावधानियां:\n\n"
                    f"• {prev_str}\n"
                    f"• **जल प्रबंधन**: केवल ड्रिप सिंचाई का प्रयोग करें ताकि पत्तियों पर पानी का छिड़काव न हो।\n"
                    f"• **औजारों की सफाई**: छंटाई के औजारों को समय-समय पर साफ करें ताकि संक्रमण न फैले।"
                )
            else:
                prev_str = "\n• ".join([str(p) for p in prevention_list[:4]]) if prevention_list else "Practice crop rotation and avoid overhead watering."
                reply = (
                    f"To prevent **{display_name}** and stop it from spreading to other plants:\n\n"
                    f"• {prev_str}\n"
                    f"• **Water Management**: Switch to drip irrigation at the root zone. Avoid overhead watering to prevent splashing fungal spores onto leaves.\n"
                    f"• **Tool Disinfection**: Clean and sanitize pruning tools with 70% alcohol or bleach between plants.\n\n"
                    f"*Healthy cultural practices protect both current yield and future planting cycles.*"
                )
            return {"category": "disease", "reply": reply, "knowledge": knowledge, "is_custom_localized": True}

        if is_cause_query:
            if language == "mr":
                cause_str = "\n• ".join([str(c) for c in causes_list[:3]]) if causes_list else "ओलसर हवामानात बुरशीचे बीजाणू पिकांवर पसरल्यामुळे हा रोग होतो."
                reply = (
                    f"**{crop_name}** वरील **{display_name}** रोगाची मुख्य कारणे:\n\n"
                    f"• {cause_str}\n\n"
                    f"उबदार आणि ओलसर हवामान, पाऊस किंवा पानांवर पाणी साचल्यामुळे बुरशीची वाढ वेगाने होते."
                )
            elif language == "hi":
                cause_str = "\n• ".join([str(c) for c in causes_list[:3]]) if causes_list else "नम मौसम में कवक के बीजाणु फैलने से यह रोग होता है।"
                reply = (
                    f"**{crop_name}** पर **{display_name}** रोग के मुख्य कारण:\n\n"
                    f"• {cause_str}\n\n"
                    f"गर्म और अत्यधिक नम मौसम तथा पत्तियों पर पानी जमा रहने से रोगजनक कवक तेजी से पनपते हैं।"
                )
            else:
                cause_str = "\n• ".join([str(c) for c in causes_list[:3]]) if causes_list else "Fungal spores or bacteria surviving in crop residues under warm, humid conditions."
                reply = (
                    f"The primary causes and vectors for **{display_name}** on **{crop_name}** are:\n\n"
                    f"• {cause_str}\n\n"
                    f"Warm, humid conditions and extended leaf wetness (rain splash, overhead irrigation, or dense shade) create the ideal environment for infection."
                )
            return {"category": "disease", "reply": reply, "knowledge": knowledge, "is_custom_localized": True}

        # Default general follow-up
        if language == "mr":
            treat_str = "\n• ".join([str(t) for t in treatments_list[:2]]) if treatments_list else "सुरक्षित जैविक उपाय वापरा."
            prev_str = "\n• ".join([str(p) for p in prevention_list[:2]]) if prevention_list else "पिकांची स्वच्छता ठेवा."
            reply = (
                f"आपल्या **{crop_name}** पिकावरील **{display_name}** साठी आवश्यक मार्गदर्शन:\n\n"
                f"• **उपचार**:\n• {treat_str}\n\n"
                f"• **प्रतिबंधक उपाय**:\n• {prev_str}\n\n"
                f"अधिक माहितीसाठी आपण फवारणी, प्रतिबंध किंवा कारणांविषयी स्वतंत्रपणे विचारू शकता."
            )
        elif language == "hi":
            treat_str = "\n• ".join([str(t) for t in treatments_list[:2]]) if treatments_list else "सुरक्षित जैविक उपाय अपनाएं।"
            prev_str = "\n• ".join([str(p) for p in prevention_list[:2]]) if prevention_list else "खेत की स्वच्छता बनाए रखें।"
            reply = (
                f"आपकी **{crop_name}** फसल के **{display_name}** के लिए आवश्यक मार्गदर्शन:\n\n"
                f"• **उपचार**:\n• {treat_str}\n\n"
                f"• **रोकथाम उपाय**:\n• {prev_str}\n\n"
                f"अधिक जानकारी के लिए आप छिड़काव, रोकथाम या कारणों के बारे में अलग से पूछ सकते हैं।"
            )
        else:
            treat_str = "\n• ".join([str(t) for t in treatments_list[:2]]) if treatments_list else "Apply safe bio-controls."
            prev_str = "\n• ".join([str(p) for p in prevention_list[:2]]) if prevention_list else "Maintain field sanitation."
            reply = (
                f"Summary action guide for **{display_name}** on **{crop_name}**:\n\n"
                f"• **Immediate Treatment Steps**:\n• {treat_str}\n\n"
                f"• **Prevention & Care**:\n• {prev_str}\n\n"
                f"Feel free to ask for specific spraying guidance, causes, or organic prevention tips!"
            )
        return {"category": "disease", "reply": reply, "knowledge": knowledge, "is_custom_localized": True}

    # =========================================================================
    # INTENT 1: MY CROP STATUS / ALL CROPS INQUIRY
    # =========================================================================
    is_crop_status_query = any(k in text for k in (
        "my crop status", "crop status", "show my crop", "show my crops", "what crops do i have",
        "which crops am i growing", "what crops am i growing", "crops am i growing", "crops do i have",
        "my registered crops", "list my crops", "list of crops",
        "माझी पिके", "पिकांची स्थिती", "पिकांची सद्यस्थिती", "पिकांची माहिती",
        "मेरी फसलें", "फसल स्थिति", "फसल की स्थिति", "फसलों की स्थिति"
    ))

    if is_crop_status_query and not matched_crop:
        if not crops:
            if language == "mr":
                return {
                    "category": "crop",
                    "reply": "आपल्या AgriSmart खात्यात अद्याप कोणतीही पिके नोंदवलेली नाहीत. पिकांची प्रगती ट्रॅक करण्यासाठी आपण वरील 'Farm & Crop Management' विभागात पीक जोडू शकता. आपल्याला पीक निवडीबद्दल सामान्य माहिती हवी आहे का?",
                    "is_custom_localized": True
                }
            elif language == "hi":
                return {
                    "category": "crop",
                    "reply": "आपके AgriSmart खाते में अभी कोई फसल पंजीकृत नहीं है। फसलों की प्रगति ट्रैक करने के लिए आप ऊपर 'Farm & Crop Management' अनुभाग में फसल दर्ज कर सकते हैं। क्या आपको फसल चयन पर सामान्य जानकारी चाहिए?",
                    "is_custom_localized": True
                }
            return {
                "category": "crop",
                "reply": "You currently do not have any registered crops in your AgriSmart account. You can register your crops and fields in the 'Farm & Crop Management' section above. Would you like general advice on crop selection?",
                "is_custom_localized": True
            }

        # Build list of registered crops
        if language == "mr":
            lines = ["आपल्या नोंदणीकृत पिकांची सद्यस्थिती खालीलप्रमाणे आहे:"]
            for c in crops:
                variety_str = f" (वाण: {c['variety']})" if c.get("variety") else ""
                farm_str = f" - शेत: {c['farm_name']}" if c.get("farm_name") else ""
                days = _calculate_days_since(c.get("planting_date"))
                days_str = f", लागवड: {days} दिवसांपूर्वी" if days is not None else ""
                lines.append(f"• **{c['crop_name']}**{variety_str}{farm_str} — वाढीची स्थिती: **{c.get('growth_status', 'Newly Planted')}**{days_str} ({c.get('cultivated_area', '')} {c.get('area_unit', 'acre')}).")
            lines.append("\nयापैकी कोणत्याही पिकाच्या काळजी किंवा काढणीविषयी आपण सविस्तर विचारू शकता.")
            return {"category": "crop", "reply": "\n".join(lines), "is_custom_localized": True}

        elif language == "hi":
            lines = ["आपकी पंजीकृत फसलों की वर्तमान स्थिति निम्नलिखित है:"]
            for c in crops:
                variety_str = f" (किस्म: {c['variety']})" if c.get("variety") else ""
                farm_str = f" - खेत: {c['farm_name']}" if c.get("farm_name") else ""
                days = _calculate_days_since(c.get("planting_date"))
                days_str = f", बुवाई: {days} दिन पहले" if days is not None else ""
                lines.append(f"• **{c['crop_name']}**{variety_str}{farm_str} — विकास चरण: **{c.get('growth_status', 'Newly Planted')}**{days_str} ({c.get('cultivated_area', '')} {c.get('area_unit', 'acre')}).")
            lines.append("\nइनमें से किसी भी फसल की देखभाल या कटाई के संबंध में आप विस्तार से पूछ सकते हैं।")
            return {"category": "crop", "reply": "\n".join(lines), "is_custom_localized": True}

        else:
            lines = ["Here is the current status of your registered crops:"]
            for c in crops:
                variety_str = f" (Variety: {c['variety']})" if c.get("variety") else ""
                farm_str = f" at {c['farm_name']}" if c.get("farm_name") else ""
                days = _calculate_days_since(c.get("planting_date"))
                days_str = f", planted {days} days ago" if days is not None else ""
                lines.append(f"• **{c['crop_name']}**{variety_str}{farm_str} — Growth Stage: **{c.get('growth_status', 'Newly Planted')}**{days_str} ({c.get('cultivated_area', '')} {c.get('area_unit', 'acre')}).")
            lines.append("\nFeel free to ask for specific care or harvest advice for any of these crops.")
            return {"category": "crop", "reply": "\n".join(lines), "is_custom_localized": True}

    # =========================================================================
    # INTENT 2: HARVEST REMINDERS & INQUIRIES
    # =========================================================================
    is_harvest_query = any(k in text for k in (
        "harvest reminder", "harvest reminders", "when is my crop expected to be harvested",
        "which crops are ready for harvest", "ready for harvest", "when will my crop be harvested",
        "harvest date", "expected harvest", "when will it be harvested", "काढणी", "कापणी", "कटाई"
    ))

    if is_harvest_query:
        if not crops:
            msg = "You have no crops registered yet to check harvest dates." if language == "en" else \
                  "काढणीची तारीख तपासण्यासाठी आपल्याकडे अद्याप कोणतीही पिके नोंदवलेली नाहीत." if language == "mr" else \
                  "कटाई की तारीख जानने के लिए आपके पास अभी कोई फसल पंजीकृत नहीं है।"
            return {"category": "harvest", "reply": msg, "is_custom_localized": True}

        # If a specific or inferred crop is targeted
        if matched_crop:
            c_name = matched_crop["crop_name"]
            h_date = matched_crop.get("expected_harvest_date")
            days_until = _calculate_days_until(h_date)
            status = matched_crop.get("growth_status")

            if not h_date:
                reply = f"No expected harvest date was recorded for your {c_name}. You can update it in Farm & Crop Management." if language == "en" else \
                        f"आपल्या {c_name} पिकासाठी अपेक्षित काढणी तारीख नोंदवलेली नाही. आपण Farm & Crop Management मध्ये ती तारीख नोंदवू शकता." if language == "mr" else \
                        f"आपकी {c_name} फसल के लिए अपेक्षित कटाई तिथि दर्ज नहीं है। आप Farm & Crop Management में इसे अपडेट कर सकते हैं।"
                return {"category": "harvest", "reply": reply, "is_custom_localized": True}

            if days_until is not None and days_until < 0:
                reply = f"Your **{c_name}** reached its expected harvest date on **{_format_date(h_date)}** ({abs(days_until)} days ago). If ready, proceed with harvesting in cool morning hours." if language == "en" else \
                        f"आपले **{c_name}** पीक **{_format_date(h_date)}** रोजी काढणीच्या तारखेस पोहोचले आहे ({abs(days_until)} दिवसांपूर्वी). तयार असल्यास सकाळी थंड वेळेत काढणी करा." if language == "mr" else \
                        f"आपकी **{c_name}** फसल **{_format_date(h_date)}** को अपेक्षित कटाई तिथि पर पहुँच चुकी है ({abs(days_until)} दिन पहले)। तैयार होने पर सुबह के समय कटाई करें।"
            elif days_until is not None and days_until <= 7:
                reply = f"Your **{c_name}** is approaching harvest! Expected date is **{_format_date(h_date)}** (in {days_until} days). Current growth status: **{status}**." if language == "en" else \
                        f"आपले **{c_name}** पीक काढणीच्या जवळ आले आहे! अपेक्षित तारीख: **{_format_date(h_date)}** ({days_until} दिवसांत). सद्य वाढ स्थिती: **{status}**." if language == "mr" else \
                        f"आपकी **{c_name}** फसल कटाई के करीब है! अपेक्षित तिथि: **{_format_date(h_date)}** ({days_until} दिनों में)। वर्तमान स्थिति: **{status}**।"
            else:
                reply = f"Your **{c_name}** is scheduled for harvest on **{_format_date(h_date)}** (in {days_until} days). Current stage: **{status}**." if language == "en" else \
                        f"आपल्या **{c_name}** पिकाची काढणी तारीख **{_format_date(h_date)}** आहे (आणखी {days_until} दिवस). सध्याचा टप्पा: **{status}**." if language == "mr" else \
                        f"आपकी **{c_name}** फसल की कटाई **{_format_date(h_date)}** को निर्धारित है ({days_until} दिन बाकी)। वर्तमान चरण: **{status}**।"
            return {"category": "harvest", "reply": reply, "is_custom_localized": True}

        # Otherwise list all crops' harvest statuses
        ready_crops = [c for c in crops if c.get("growth_status") == "Ready for Harvest" or (_calculate_days_until(c.get("expected_harvest_date")) is not None and _calculate_days_until(c.get("expected_harvest_date")) <= 0)]
        approaching_crops = [c for c in crops if _calculate_days_until(c.get("expected_harvest_date")) is not None and 0 < _calculate_days_until(c.get("expected_harvest_date")) <= 14]

        if language == "mr":
            lines = ["आपल्या पिकांची काढणी माहिती:"]
            if ready_crops:
                lines.append("\n🌾 **काढणीसाठी तयार पिके:**")
                for c in ready_crops:
                    lines.append(f"• **{c['crop_name']}** (शेत: {c.get('farm_name', 'शेतात')}) — अपेक्षित तारीख: {_format_date(c.get('expected_harvest_date')) or 'नोंद नाही'}.")
            if approaching_crops:
                lines.append("\n⏱️ **लवकरच काढणीस येणारी पिके:**")
                for c in approaching_crops:
                    d_left = _calculate_days_until(c.get("expected_harvest_date"))
                    lines.append(f"• **{c['crop_name']}** — {_format_date(c.get('expected_harvest_date'))} ({d_left} दिवसांत).")
            if not ready_crops and not approaching_crops:
                lines.append("सध्या कोणतीही पिके काढणीच्या टप्प्यावर नाहीत. सर्व पिके नियमित वाढीमध्ये आहेत.")
            return {"category": "harvest", "reply": "\n".join(lines), "is_custom_localized": True}

        elif language == "hi":
            lines = ["आपकी फसलों की कटाई जानकारी:"]
            if ready_crops:
                lines.append("\n🌾 **कटाई के लिए तैयार फसलें:**")
                for c in ready_crops:
                    lines.append(f"• **{c['crop_name']}** (खेत: {c.get('farm_name', 'खेत')}) — अपेक्षित तिथि: {_format_date(c.get('expected_harvest_date')) or 'दर्ज नहीं'}।")
            if approaching_crops:
                lines.append("\n⏱️ **शीघ्र कटाई योग्य फसलें:**")
                for c in approaching_crops:
                    d_left = _calculate_days_until(c.get("expected_harvest_date"))
                    lines.append(f"• **{c['crop_name']}** — {_format_date(c.get('expected_harvest_date'))} ({d_left} दिनों में)।")
            if not ready_crops and not approaching_crops:
                lines.append("वर्तमान में कोई भी फसल कटाई के चरण में नहीं है। सभी फसलें सामान्य रूप से बढ़ रही हैं।")
            return {"category": "harvest", "reply": "\n".join(lines), "is_custom_localized": True}

        else:
            lines = ["Harvest status for your crops:"]
            if ready_crops:
                lines.append("\n🌾 **Crops Ready for Harvest:**")
                for c in ready_crops:
                    lines.append(f"• **{c['crop_name']}** (at {c.get('farm_name', 'Farm')}) — Expected Date: {_format_date(c.get('expected_harvest_date')) or 'Not set'}.")
            if approaching_crops:
                lines.append("\n⏱️ **Approaching Harvest (next 14 days):**")
                for c in approaching_crops:
                    d_left = _calculate_days_until(c.get("expected_harvest_date"))
                    lines.append(f"• **{c['crop_name']}** — {_format_date(c.get('expected_harvest_date'))} ({d_left} days left).")
            if not ready_crops and not approaching_crops:
                lines.append("None of your registered crops are currently ready for harvest. All crops are in healthy active growth stages.")
            return {"category": "harvest", "reply": "\n".join(lines), "is_custom_localized": True}

    # =========================================================================
    # INTENT 3: SPECIFIC CROP CARE / PRECAUTIONS
    # =========================================================================
    is_care_query = any(k in text for k in (
        "what should i do", "what to do", "how to care", "care for", "precautions",
        "precaution", "care recommendation", "protect my crop", "growing properly",
        "काळजी", "काय करावे", "सावधगिरी", "देखभाल", "क्या करना चाहिए", "सुरक्षा"
    ))

    if matched_crop and is_care_query:
        c_name = matched_crop["crop_name"]
        stage = matched_crop.get("growth_status", "Growing")
        farm = matched_crop.get("farm_name", "your farm")
        advice = _get_growth_stage_advice(c_name, stage, language)

        prefix_en = f"Based on your records, your **{c_name}** at {farm} is currently in the **{stage}** stage.\n\n"
        prefix_mr = f"आपल्या नोंदींनुसार, {farm} येथील आपले **{c_name}** पीक सध्या **{stage}** टप्प्यात आहे.\n\n"
        prefix_hi = f"आपके रिकॉर्ड के अनुसार, {farm} में आपकी **{c_name}** फसल वर्तमान में **{stage}** चरण में है।\n\n"

        disclaimer_en = "\n\n*Note: Cultural practices should be adapted to local soil moisture and weather conditions.*"
        disclaimer_mr = "\n\n*टीप: हवामान आणि जमिनीतील ओलाव्यानुसार आवश्यकतेनुसार योग्य बदल करा.*"
        disclaimer_hi = "\n\n*नोट: मौसम और मिट्टी की नमी के अनुसार कृषि पद्धतियों में आवश्यक बदलाव करें।*"

        if language == "mr":
            return {"category": "care", "reply": prefix_mr + advice + disclaimer_mr, "is_custom_localized": True}
        elif language == "hi":
            return {"category": "care", "reply": prefix_hi + advice + disclaimer_hi, "is_custom_localized": True}
        return {"category": "care", "reply": prefix_en + advice + disclaimer_en, "is_custom_localized": True}

    # If user asks care advice for an unregistered crop (e.g. "What should I do for my cotton crop?")
    if is_care_query and not matched_crop and "___" not in text:
        potential_crop_words = ["wheat", "rice", "tomato", "cotton", "sugarcane", "potato", "maize", "soybean", "onion", "banana", "chilli"]
        for w in potential_crop_words:
            if re.search(rf"\b{w}\b", text):
                w_cap = w.capitalize()
                reg_crops_str = ", ".join([c["crop_name"] for c in crops]) if crops else ("none" if language == "en" else "काहीही नाही" if language == "mr" else "कोई नहीं")
                if language == "mr":
                    reply = f"आपल्या शेतात **{w_cap}** पीक नोंदवलेले नाही (आपली नोंदणीकृत पिके: {reg_crops_str}). {w_cap} पिकाच्या लागवडीसाठी योग्य जमीन, पाण्याचा निचरा आणि संतुलित खतांचे व्यवस्थापन आवश्यक आहे. आपण हे पीक Farm & Crop Management मध्ये नोंदवू शकता."
                elif language == "hi":
                    reply = f"आपके खेतों में **{w_cap}** फसल पंजीकृत नहीं है (आपकी पंजीकृत फसलें: {reg_crops_str})। {w_cap} फसल के लिए उपयुक्त मिट्टी, जल निकासी और संतुलित खाद जरूरी है। आप इस फसल को Farm & Crop Management में दर्ज कर सकते हैं।"
                else:
                    reply = f"You do not have **{w_cap}** registered under your farms (your registered crops are: {reg_crops_str}). For general {w_cap} care, ensure adequate drainage, balanced fertilization, and monitor for common pests. Would you like to register {w_cap} in Farm & Crop Management?"
                return {"category": "crop", "reply": reply, "is_custom_localized": True}

    # =========================================================================
    # INTENT 4: RECENT DISEASE DIAGNOSIS INQUIRIES
    # =========================================================================
    is_diagnosis_query = any(k in text for k in (
        "recent disease diagnosis", "recent diagnosis", "show my diagnosis", "my disease diagnosis",
        "what diseases were found", "previous disease", "disease history", "disease prevention",
        "रोगनिदान", "माझे रोगनिदान", "मागील रोग", "बीमारी जांच", "रोग निदान"
    ))

    if is_diagnosis_query:
        if not diagnoses:
            msg = "You have not recorded any disease diagnosis checks yet. You can upload a photo of a suspicious leaf in the Disease Detection section." if language == "en" else \
                  "आपण अद्याप कोणतीही रोगनिदान तपासणी केलेली नाही. आपण Disease Detection विभागात पानाचा फोटो स्कॅन करू शकता." if language == "mr" else \
                  "आपने अभी तक कोई रोग निदान जांच दर्ज नहीं की है। आप Disease Detection अनुभाग में पत्ते की तस्वीर अपलोड कर सकते हैं।"
            return {"category": "disease", "reply": msg, "is_custom_localized": True}

        if language == "mr":
            lines = ["आपल्या खात्यातील मागील रोगनिदान नोंदी:"]
            for d in diagnoses[:3]:
                pred = d.get("predicted_class") or "Plant condition"
                clean_name = pred.split("___")[-1].replace("_", " ") if "___" in pred else pred
                is_healthy = "healthy" in clean_name.lower()
                status_str = "निरोगी (Healthy)" if is_healthy else f"लक्षण: {clean_name}"
                lines.append(f"• **{status_str}** — तपासणी तारीख: {_format_date(d.get('diagnosis_date'))} (विश्वासार्हता: {d.get('confidence')}%)")
            lines.append("\n*टीप: फोटोवरील अंदाज हा प्राथमिक माहितीसाठी असतो; गंभीर समस्येसाठी स्थानिक कृषी तज्ज्ञांचा सल्ला घ्या.*")
            return {"category": "disease", "reply": "\n".join(lines), "is_custom_localized": True}

        elif language == "hi":
            lines = ["आपके खाते में हालिया रोग निदान रिकॉर्ड:"]
            for d in diagnoses[:3]:
                pred = d.get("predicted_class") or "Plant condition"
                clean_name = pred.split("___")[-1].replace("_", " ") if "___" in pred else pred
                is_healthy = "healthy" in clean_name.lower()
                status_str = "स्वस्थ (Healthy)" if is_healthy else f"लक्षण: {clean_name}"
                lines.append(f"• **{status_str}** — जांच तिथि: {_format_date(d.get('diagnosis_date'))} (विश्वसनीयता: {d.get('confidence')}%)")
            lines.append("\n*नोट: तस्वीर पर आधारित अनुमान प्रारंभिक मार्गदर्शन है; गंभीर समस्या होने पर स्थानीय कृषि विशेषज्ञ से सलाह लें।*")
            return {"category": "disease", "reply": "\n".join(lines), "is_custom_localized": True}

        else:
            lines = ["Here are your recent plant disease diagnosis records:"]
            for d in diagnoses[:3]:
                pred = d.get("predicted_class") or "Plant condition"
                clean_name = pred.split("___")[-1].replace("_", " ") if "___" in pred else pred
                is_healthy = "healthy" in clean_name.lower()
                status_str = "Healthy Plant" if is_healthy else f"Condition: {clean_name}"
                lines.append(f"• **{status_str}** — Checked on: {_format_date(d.get('diagnosis_date'))} (Confidence: {d.get('confidence')}%)")
            lines.append("\n*Disclaimer: Photo predictions are screening aids, not certified laboratory diagnoses. For serious infestations, consult a qualified agricultural extension officer.*")
            return {"category": "disease", "reply": "\n".join(lines), "is_custom_localized": True}

    # =========================================================================
    # INTENT 5: IRRIGATION RECOMMENDATION INQUIRIES
    # =========================================================================
    is_irrig_query = any(k in text for k in (
        "irrigation recommendation did i receive", "what irrigation recommendation",
        "recent irrigation", "irrigation guidance", "how much water did", "my irrigation status",
        "does my crop need water", "सिंचन मार्गदर्शन", "सिंचन शिफारस", "सिंचाई मार्गदर्शन", "सिंचाई सिफारिश"
    ))

    if is_irrig_query:
        if not irrigations:
            msg = "You have no irrigation assessment records saved yet. Visit the Smart Irrigation section to enter soil and weather conditions for customized guidance." if language == "en" else \
                  "आपल्याकडे अद्याप कोणतीही सिंचन नोंद नाही. योग्य पाण्याचे नियोजन मिळवण्यासाठी Smart Irrigation विभागात माती व हवामानाची माहिती प्रविष्ट करा." if language == "mr" else \
                  "आपके पास अभी कोई सिंचाई रिकॉर्ड नहीं है। सटीक मार्गदर्शन प्राप्त करने के लिए Smart Irrigation अनुभाग में मिट्टी और मौसम की जानकारी दर्ज करें।"
            return {"category": "irrigation", "reply": msg, "is_custom_localized": True}

        latest_i = irrigations[0]
        c_name = latest_i.get("crop", "Crop")
        moisture = latest_i.get("soil_moisture")
        status = latest_i.get("recommendation_status", "Logged")
        water_mm = latest_i.get("water_quantity_mm", 0.0)
        i_date = _format_date(latest_i.get("created_at"))

        if language == "mr":
            reply = (
                f"आपल्या **{c_name}** पिकासाठी सर्वात अलीकडील सिंचन नोंद ({i_date}):\n"
                f"• मातीतील ओलावा: **{moisture}%**\n"
                f"• शिफारस: **{status}**\n"
                f"• पाण्याचे अंदाजे प्रमाण: **{water_mm} mm**\n\n"
                f"पाणी देण्यापूर्वी नेहमी मुळांजवळील माती तपासा आणि जास्त पाणी साचू देऊ नका."
            )
        elif language == "hi":
            reply = (
                f"आपकी **{c_name}** फसल के लिए हालिया सिंचाई रिकॉर्ड ({i_date}):\n"
                f"• मिट्टी की नमी: **{moisture}%**\n"
                f"• सिफारिश: **{status}**\n"
                f"• सुझाई गई पानी की मात्रा: **{water_mm} mm**\n\n"
                f"सिंचाई करने से पहले हमेशा जड़ों के पास मिट्टी की जांच करें और जलभराव से बचें।"
            )
        else:
            reply = (
                f"According to your latest irrigation record for **{c_name}** on **{i_date}**:\n"
                f"• Soil Moisture: **{moisture}%**\n"
                f"• Guidance: **{status}**\n"
                f"• Suggested Water Quantity: **{water_mm} mm**\n\n"
                f"Always check topsoil moisture near the root zone before applying water to prevent root suffocation."
            )
        return {"category": "irrigation", "reply": reply, "is_custom_localized": True}

    # =========================================================================
    # INTENT 6: FARM SUMMARY
    # =========================================================================
    is_farm_query = any(k in text for k in (
        "my farm summary", "farm summary", "my farms", "tell me about my farms",
        "where is my farm", "registered farms", "माझी शेते", "शेताचा सारांश", "मेरे खेत", "खेत सारांश"
    ))

    if is_farm_query:
        if not farms:
            msg = "You have not registered any farms yet. Add your first farm in Farm & Crop Management to track field locations and area." if language == "en" else \
                  "आपण अद्याप कोणतेही शेत नोंदवले नाही. शेताची माहिती जोडण्यासाठी Farm & Crop Management विभागात '➕ शेत जोडा' वर क्लिक करा." if language == "mr" else \
                  "आपने अभी तक कोई खेत पंजीकृत नहीं किया है। अपने खेत दर्ज करने के लिए Farm & Crop Management में '➕ खेत जोड़ें' पर क्लिक करें।"
            return {"category": "general", "reply": msg, "is_custom_localized": True}

        if language == "mr":
            lines = [f"आपल्याकडे **{len(farms)} नोंदणीकृत शेत/शेते** आहेत:"]
            for f in farms:
                farm_crops = [c["crop_name"] for c in crops if c.get("farm_id") == f["id"]]
                crops_str = ", ".join(farm_crops) if farm_crops else "सध्या कोणतीही पिके नाहीत"
                lines.append(f"• **{f['farm_name']}** — ठिकाण: {f['location']}, एकूण क्षेत्र: {f['total_area']} {f.get('area_unit', 'एकर')} (पिके: {crops_str}).")
            return {"category": "general", "reply": "\n".join(lines), "is_custom_localized": True}

        elif language == "hi":
            lines = [f"आपके पास **{len(farms)} पंजीकृत खेत** हैं:"]
            for f in farms:
                farm_crops = [c["crop_name"] for c in crops if c.get("farm_id") == f["id"]]
                crops_str = ", ".join(farm_crops) if farm_crops else "वर्तमान में कोई फसल नहीं"
                lines.append(f"• **{f['farm_name']}** — स्थान: {f['location']}, कुल क्षेत्रफल: {f['total_area']} {f.get('area_unit', 'एकड़')} (फसलें: {crops_str})।")
            return {"category": "general", "reply": "\n".join(lines), "is_custom_localized": True}

        else:
            lines = [f"You have **{len(farms)} registered farm(s)**:"]
            for f in farms:
                farm_crops = [c["crop_name"] for c in crops if c.get("farm_id") == f["id"]]
                crops_str = ", ".join(farm_crops) if farm_crops else "No active crops"
                lines.append(f"• **{f['farm_name']}** — Location: {f['location']}, Total Area: {f['total_area']} {f.get('area_unit', 'acre')} (Crops: {crops_str}).")
            return {"category": "general", "reply": "\n".join(lines), "is_custom_localized": True}

    # =========================================================================
    # INTENT 7: WEATHER INFORMATION FOR FARM
    # =========================================================================
    is_weather_farm_query = any(k in text for k in (
        "weather information", "weather on my farm", "forecast for my farm", "weather for my crop",
        "हवामान माहिती", "माझ्या शेताचे हवामान", "मौसम जानकारी", "मेरे खेत का मौसम"
    ))

    if is_weather_farm_query and farms:
        loc = farms[0].get("location")
        w_key = os.getenv("WEATHER_API_KEY", "").strip()

        if loc and w_key:
            clean_city = loc.split(",")[0].strip()
            try:
                url = f"{WEATHER_API_BASE_URL}/forecast.json"
                resp = requests.get(url, params={"key": w_key, "q": clean_city, "days": 1}, timeout=3)
                if resp.ok:
                    wdata = resp.json()
                    curr = wdata.get("current", {})
                    temp_c = curr.get("temp_c")
                    condition = curr.get("condition", {}).get("text", "")
                    humidity = curr.get("humidity")

                    if language == "mr":
                        reply = (
                            f"आपल्या **{farms[0]['farm_name']}** शेतासाठी ({clean_city}) सद्य हवामान:\n"
                            f"• हवामान: **{condition}**\n"
                            f"• तापमान: **{temp_c}°C** (आर्द्रता: {humidity}%)\n"
                            f"सिंचन किंवा फवारणीपूर्वी स्थानिक पावसाचा अंदाज लक्षात घ्या."
                        )
                    elif language == "hi":
                        reply = (
                            f"आपके **{farms[0]['farm_name']}** खेत ({clean_city}) का वर्तमान मौसम:\n"
                            f"• मौसम: **{condition}**\n"
                            f"• तापमान: **{temp_c}°C** (नमी: {humidity}%)\n"
                            f"सिंचाई या छिड़काव से पहले बारिश की संभावना पर ध्यान दें।"
                        )
                    else:
                        reply = (
                            f"Current weather for **{farms[0]['farm_name']}** ({clean_city}):\n"
                            f"• Condition: **{condition}**\n"
                            f"• Temperature: **{temp_c}°C** (Humidity: {humidity}%)\n"
                            f"Check rainfall forecasts in the Weather section before scheduling irrigation or spray operations."
                        )
                    return {"category": "weather", "reply": reply, "is_custom_localized": True}
            except Exception:
                pass

        # If weather API failed or not configured, return clear message without fake data
        if language == "mr":
            reply = f"{farms[0]['farm_name']} साठी थेट हवामान सेवा उपलब्ध नाही. अधिकृत हवामान विभागाचा अंदाज तपासा."
        elif language == "hi":
            reply = f"{farms[0]['farm_name']} के लिए लाइव मौसम सेवा वर्तमान में उपलब्ध नहीं है। कृपया Weather अनुभाग देखें।"
        else:
            reply = f"Live weather data for {farms[0]['farm_name']} is currently unavailable. Please open the Weather section for regional forecasts."
        return {"category": "weather", "reply": reply, "is_custom_localized": True}

    return None
