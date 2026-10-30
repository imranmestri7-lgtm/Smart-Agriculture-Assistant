// i18n.js - client-side internationalization
// Supports English (en), Marathi (mr) and Hindi (hi)
const translations = {
  en: {
    "choose_language": "Choose Your Language",
    "english": "English",
    "marathi": "मराठी",
    "hindi": "हिन्दी",
    "login": "Login",
    "get_started": "Get Started",
    "home": "Home",
    "features": "Features",
    "how_it_works": "How It Works",
    "about": "About",
    "smart_farming": "Smart Farming",
    "made_simple": "Made Simple",
    "welcome_message": "AgriSmart helps farmers manage crops, understand possible plant problems, check weather information, get irrigation guidance, and access farming support from one simple platform.",
    "get_started_btn": "🌱 Get Started",
    "how_it_works_btn": "▶ How It Works",
    "login_button": "Login",
    "signup_button": "Sign Up",
    "brand_name": "AgriSmart",

    // Irrigation Page Translations
    "smart_irrigation_badge": "💧 Smart Agriculture",
    "smart_irrigation_title": "Smart Irrigation",
    "smart_irrigation_title_sub": "Management",
    "smart_irrigation_desc": "Make better irrigation decisions using soil, weather and crop conditions.",
    "check_irrigation_hero_btn": "Check Irrigation →",
    "irrigation_info_heading": "Irrigation Information",
    "irrigation_info_sub": "Enter your field conditions to check irrigation requirements.",
    "select_crop_label": "🌾 Select Crop",
    "select_crop_placeholder": "Select your crop",
    "soil_moisture_label": "💧 Soil Moisture (%)",
    "temperature_label": "🌡️ Temperature (°C)",
    "humidity_label": "☁️ Humidity (%)",
    "rainfall_label": "🌧️ Recent Rainfall (mm)",
    "location_label": "📍 Location",
    "select_location_placeholder": "Select location",
    "check_irrigation_btn": "💧 Check Irrigation Requirement",
    "checking_irrigation": "Analyzing field conditions...",
    "irrigation_recommendation_title": "Irrigation Recommendation",
    "irrigation_initial_msg": "Your irrigation recommendation will appear here after the irrigation system is connected.",
    "why_smart_irrigation": "WHY SMART IRRIGATION?",
    "use_water_efficiently": "Use Water More Efficiently",
    "smart_irrigation_benefits_desc": "Smart irrigation helps farmers make informed water management decisions.",
    "save_water_title": "Save Water",
    "save_water_desc": "Reduce unnecessary water usage by understanding soil moisture.",
    "healthy_crops_title": "Healthy Crops",
    "healthy_crops_desc": "Provide crops with suitable amounts of water.",
    "weather_based_title": "Weather Based",
    "weather_based_desc": "Consider rainfall and weather conditions for better decisions.",
    "data_driven_title": "Data Driven",
    "data_driven_desc": "Use field data to support irrigation planning.",
    "how_it_works_title": "HOW IT WORKS",
    "smart_irrigation_process": "Smart Irrigation Process",
    "step_1_title": "Enter Field Data",
    "step_1_desc": "Provide crop, soil moisture and weather information.",
    "step_2_title": "Analyze Conditions",
    "step_2_desc": "The system analyzes the available field conditions.",
    "step_3_title": "Get Recommendation",
    "step_3_desc": "Receive an irrigation recommendation.",

    // Result Card Labels
    "status_urgent": "Urgent",
    "status_recommended": "Recommended",
    "status_adequate": "Adequate",
    "status_overwatered": "Overwatered",
    "water_needed_yes": "Irrigation Needed: Yes",
    "water_needed_no": "Irrigation Needed: No",
    "quantity_label": "Suggested Water Quantity",
    "duration_label": "Irrigation Duration Note",
    "explanation_label": "Agronomic Explanation",
    "weather_warning_label": "Weather Advisory",
    "next_steps_label": "Recommended Actions",
    "assumptions_label": "Assumptions & Limitations",
    "reset_btn": "Check Another Field",

    // Form Validation Messages
    "err_crop_required": "Please select a valid crop.",
    "err_moisture_range": "Soil moisture must be a number between 0% and 100%.",
    "err_temp_range": "Temperature must be a number between -10°C and 60°C.",
    "err_humidity_range": "Humidity must be a number between 0% and 100%.",
    "err_rainfall_range": "Recent rainfall must be 0 mm or greater.",
    "err_network": "Network connection error. Please make sure the backend server is running.",

    // Diagnosis History Translations
    "diagnosis_history_title": "Diagnosis History",
    "diagnosis_history_desc": "View your previous plant checks and diagnosis information.",
    "view_history_btn": "View History →",
    "my_diagnosis_history": "📋 My Diagnosis History",
    "diagnosis_history_subtitle": "Previous plant disease predictions saved to your account.",
    "refresh_history_btn": "🔄 Refresh history",
    "history_login_required": "Please log in to view and save your diagnosis history.",
    "history_empty": "No saved diagnoses yet. Scan a plant leaf image while logged in to begin your history.",
    "history_loading": "Loading your saved diagnoses...",
    "history_view_details": "View Details",
    "history_close": "Close",
    "confidence_label": "Confidence",
    "treatment_summary": "Recommended Treatment",
    "prevention_summary": "Prevention Advice",
    "clear_chat": "Clear Chat",
    "clear_chat_title": "Clear Chat History",
    "clear_chat_confirm": "Are you sure you want to clear your conversation history?",
    "clear_chat_success": "Conversation history cleared.",
    "previous_conversations": "Previous Conversations",
    "voice_not_supported": "Voice input is not supported in this browser.",
    "mic_permission_denied": "Microphone access was denied. Please allow microphone permissions in your browser.",
    "no_speech_detected": "No speech was detected. Please try speaking again."
  },
  mr: {
    "choose_language": "तुमची भाषा निवडा",
    "english": "English",
    "marathi": "मराठी",
    "hindi": "हिन्दी",
    "login": "लॉगिन",
    "get_started": "सुरू करा",
    "home": "मुख्य पृष्ठ",
    "features": "वैशिष्ट्ये",
    "how_it_works": "कसे कार्य करते",
    "about": "बद्दल",
    "smart_farming": "स्मार्ट शेती",
    "made_simple": "सोपे बनवले",
    "welcome_message": "AgriSmart शेतकऱ्यांना पिके व्यवस्थापित करण्यास, संभाव्य रोग समजून घेण्यास, हवामानाची माहिती तपासण्यास, पाण्याच्या मार्गदर्शन मिळवण्यास आणि एक साधी प्लॅटफॉर्म वापरून समर्थन मिळवण्यास मदत करते.",
    "get_started_btn": "🌱 सुरू करा",
    "how_it_works_btn": "▶ कसे कार्य करते",
    "login_button": "लॉगिन",
    "signup_button": "नोंदणी",
    "brand_name": "AgriSmart",

    // Irrigation Page Translations
    "smart_irrigation_badge": "💧 स्मार्ट शेती",
    "smart_irrigation_title": "स्मार्ट सिंचन",
    "smart_irrigation_title_sub": "व्यवस्थापन",
    "smart_irrigation_desc": "माती, हवामान आणि पिकांच्या स्थितीनुसार पाण्याचे योग्य व अचूक नियोजन करा.",
    "check_irrigation_hero_btn": "सिंचन तपासा →",
    "irrigation_info_heading": "सिंचन माहिती",
    "irrigation_info_sub": "सिंचन आवश्यकता तपासण्यासाठी आपल्या शेतातील परिस्थिती प्रविष्ट करा.",
    "select_crop_label": "🌾 पीक निवडा",
    "select_crop_placeholder": "तुमचे पीक निवडा",
    "soil_moisture_label": "💧 मातीतील ओलावा (%)",
    "temperature_label": "🌡️ तापमान (°C)",
    "humidity_label": "☁️ आर्द्रता (%)",
    "rainfall_label": "🌧️ अलीकडील पाऊस (मिमी)",
    "location_label": "📍 स्थान",
    "select_location_placeholder": "स्थान निवडा",
    "check_irrigation_btn": "💧 सिंचन आवश्यकता तपासा",
    "checking_irrigation": "शेताच्या स्थितीचे विश्लेषण करत आहे...",
    "irrigation_recommendation_title": "सिंचन शिफारस",
    "irrigation_initial_msg": "माहिती भरल्यानंतर आपली सिंचन शिफारस येथे दिसेल.",
    "why_smart_irrigation": "स्मार्ट सिंचन का महत्वाचे?",
    "use_water_efficiently": "पाण्याचा अधिक कार्यक्षम वापर करा",
    "smart_irrigation_benefits_desc": "स्मार्ट सिंचन शेतकऱ्यांना पाण्याच्या अचूक नियोजनासाठी माहितीपूर्ण निर्णय घेण्यास मदत करते.",
    "save_water_title": "पाणी वाचवा",
    "save_water_desc": "मातीतील ओलावा समजून अनावश्यक पाणी देणे टाळा.",
    "healthy_crops_title": "निरोगी पिके",
    "healthy_crops_desc": "पिकांना आवश्यकतेनुसार योग्य प्रमाणात पाणी द्या.",
    "weather_based_title": "हवामानावर आधारित",
    "weather_based_desc": "चांगल्या निर्णयांसाठी पाऊस आणि हवामान परिस्थितीचा विचार करा.",
    "data_driven_title": "तथ्यांवर आधारित",
    "data_driven_desc": "शेतातील वास्तविक आकडेवारीवर आधारित सिंचन नियोजन करा.",
    "how_it_works_title": "कसे कार्य करते",
    "smart_irrigation_process": "स्मार्ट सिंचन प्रक्रिया",
    "step_1_title": "शेताची माहिती भरा",
    "step_1_desc": "पीक, मातीतील ओलावा आणि हवामानाची माहिती प्रविष्ट करा.",
    "step_2_title": "स्थितीचे विश्लेषण",
    "step_2_desc": "प्रणाली शेतातील उपलब्ध परिस्थितीचे विश्लेषण करते.",
    "step_3_title": "शिफारस मिळवा",
    "step_3_desc": "पाण्याच्या अचूक नियोजनाची शिफारस प्राप्त करा.",

    // Result Card Labels
    "status_urgent": "तातडीचे (Urgent)",
    "status_recommended": "शिफारस केलेले (Recommended)",
    "status_adequate": "पुरेसे (Adequate)",
    "status_overwatered": "अतिपाणी (Overwatered)",
    "water_needed_yes": "पाण्याची गरज: होय",
    "water_needed_no": "पाण्याची गरज: नाही",
    "quantity_label": "पाण्याचे अंदाजे प्रमाण",
    "duration_label": "सिंचन कालावधी नोंद",
    "explanation_label": "कृषी विश्लेषण आणि स्पष्टीकरण",
    "weather_warning_label": "हवामान इशारा / सल्ला",
    "next_steps_label": "शेतकऱ्यांसाठी पुढील पायऱ्या",
    "assumptions_label": "गृहितके व मर्यादा",
    "reset_btn": "दुसऱ्या शेतासाठी तपासा",

    // Form Validation Messages
    "err_crop_required": "कृपया एक वैध पीक निवडा.",
    "err_moisture_range": "मातीतील ओलावा 0% ते 100% दरम्यान असावा.",
    "err_temp_range": "तापमान -10°C ते 60°C दरम्यान असावे.",
    "err_humidity_range": "आर्द्रता 0% ते 100% दरम्यान असावी.",
    "err_rainfall_range": "पाऊस 0 मिमी किंवा त्याहून अधिक असावा.",
    "err_network": "सर्व्हरशी संपर्क होऊ शकला नाही. कृपया बॅकएंड सुरू असल्याची खात्री करा.",

    // Diagnosis History Translations
    "diagnosis_history_title": "रोगनिदान इतिहास",
    "diagnosis_history_desc": "आपल्या मागील वनस्पती तपासणी आणि रोगनिदान माहिती पहा.",
    "view_history_btn": "इतिहास पहा →",
    "my_diagnosis_history": "📋 माझा रोगनिदान इतिहास",
    "diagnosis_history_subtitle": "आपल्या खात्यात जतन केलेली मागील वनस्पती रोगनिदान माहिती.",
    "refresh_history_btn": "🔄 इतिहास ताजा करा",
    "history_login_required": "आपला जतन केलेला इतिहास पाहण्यासाठी कृपया लॉगिन करा.",
    "history_empty": "अद्याप कोणताही जतन केलेला इतिहास नाही. सुरुवात करण्यासाठी वनस्पतीचे पान स्कॅन करा.",
    "history_loading": "जतन केलेले इतिहास लोड करत आहे...",
    "history_view_details": "तपशील पहा",
    "history_close": "बंद करा",
    "confidence_label": "विश्वासार्हता",
    "treatment_summary": "शिफारस केलेले उपचार",
    "prevention_summary": "प्रतिबंधात्मक सल्ला",
    "clear_chat": "संभाषण साफ करा",
    "clear_chat_title": "मागील संभाषण हटवा",
    "clear_chat_confirm": "तुम्हाला तुमचे संभाषण इतिहास हटवायचे आहे का?",
    "clear_chat_success": "संभाषण इतिहास हटवला गेला आहे.",
    "previous_conversations": "मागील संभाषण",
    "voice_not_supported": "या ब्राउझरमध्ये व्हॉइस इनपुट समर्थित नाही.",
    "mic_permission_denied": "मायक्रोफोन परवानगी नाकारली गेली. कृपया ब्राउझरमध्ये मायक्रोफोन परवानगी द्या.",
    "no_speech_detected": "कोणताही आवाज आढळला नाही. कृपया पुन्हा बोला."
  },
  hi: {
    "choose_language": "अपनी भाषा चुनें",
    "english": "English",
    "marathi": "मराठी",
    "hindi": "हिन्दी",
    "login": "लॉगिन",
    "get_started": "शुरू करें",
    "home": "मुख पृष्ठ",
    "features": "फ़ीचर",
    "how_it_works": "कैसे काम करता है",
    "about": "के बारे में",
    "smart_farming": "स्मार्ट खेती",
    "made_simple": "सरल बनाएं",
    "welcome_message": "AgriSmart किसानों को फसलों का प्रबंधन करने, संभावित रोग समझने, मौसम की जानकारी जांचने, सिंचन मार्गदर्शन प्राप्त करने और एक सरल प्लेटफ़ॉर्म से सहायता प्राप्त करने में मदद करता है।",
    "get_started_btn": "🌱 शुरू करें",
    "how_it_works_btn": "▶ कैसे काम करता है",
    "login_button": "लॉगिन",
    "signup_button": "साइन अप",
    "brand_name": "AgriSmart",

    // Irrigation Page Translations
    "smart_irrigation_badge": "💧 स्मार्ट कृषि",
    "smart_irrigation_title": "स्मार्ट सिंचाई",
    "smart_irrigation_title_sub": "प्रबंधन",
    "smart_irrigation_desc": "मिट्टी, मौसम और फसल की स्थिति के आधार पर सिंचाई का सही निर्णय लें।",
    "check_irrigation_hero_btn": "सिंचाई जांचें →",
    "irrigation_info_heading": "सिंचाई जानकारी",
    "irrigation_info_sub": "सिंचाई आवश्यकता जानने के लिए अपने खेत की स्थिति दर्ज करें।",
    "select_crop_label": "🌾 फसल चुनें",
    "select_crop_placeholder": "अपनी फसल चुनें",
    "soil_moisture_label": "💧 मिट्टी की नमी (%)",
    "temperature_label": "🌡️ तापमान (°C)",
    "humidity_label": "☁️ आर्द्रता (%)",
    "rainfall_label": "🌧️ हाल की बारिश (मिमी)",
    "location_label": "📍 स्थान",
    "select_location_placeholder": "स्थान चुनें",
    "check_irrigation_btn": "💧 सिंचाई आवश्यकता जांचें",
    "checking_irrigation": "खेत की स्थिति का विश्लेषण हो रहा है...",
    "irrigation_recommendation_title": "सिंचाई अनुशंसा",
    "irrigation_initial_msg": "खेत की जानकारी दर्ज करने के बाद आपकी सिंचाई अनुशंसा यहाँ दिखाई देगी।",
    "why_smart_irrigation": "स्मार्ट सिंचाई क्यों आवश्यक है?",
    "use_water_efficiently": "पानी का अधिक कुशलता से उपयोग करें",
    "smart_irrigation_benefits_desc": "स्मार्ट सिंचाई किसानों को पानी के बेहतर प्रबंधन के लिए सही निर्णय लेने में मदद करती है।",
    "save_water_title": "पानी बचाएं",
    "save_water_desc": "मिट्टी की नमी को समझकर अनावश्यक पानी देने से बचें।",
    "healthy_crops_title": "स्वस्थ फसलें",
    "healthy_crops_desc": "फसलों को उनकी आवश्यकतानुसार उचित मात्रा में पानी दें।",
    "weather_based_title": "मौसम आधारित",
    "weather_based_desc": "बेहतर निर्णयों के लिए वर्षा और मौसम की स्थिति को ध्यान में रखें।",
    "data_driven_title": "तथ्य आधारित",
    "data_driven_desc": "खेत के वास्तविक आंकड़ों के आधार पर सिंचाई की योजना बनाएं।",
    "how_it_works_title": "यह कैसे काम करता है",
    "smart_irrigation_process": "स्मार्ट सिंचाई प्रक्रिया",
    "step_1_title": "खेत की जानकारी दर्ज करें",
    "step_1_desc": "फसल, मिट्टी की नमी और मौसम की जानकारी प्रदान करें।",
    "step_2_title": "स्थिति का विश्लेषण",
    "step_2_desc": "प्रणाली खेत की उपलब्ध परिस्थितियों का विश्लेषण करती है।",
    "step_3_title": "अनुशंसा प्राप्त करें",
    "step_3_desc": "पानी की सटीक आवश्यकता की अनुशंसा प्राप्त करें।",

    // Result Card Labels
    "status_urgent": "अति आवश्यक (Urgent)",
    "status_recommended": "अनुशंसित (Recommended)",
    "status_adequate": "पर्याप्त (Adequate)",
    "status_overwatered": "अधिक पानी (Overwatered)",
    "water_needed_yes": "सिंचाई आवश्यक: हाँ",
    "water_needed_no": "सिंचाई आवश्यक: नहीं",
    "quantity_label": "सुझाई गई पानी की मात्रा",
    "duration_label": "सिंचाई अवधि विवरण",
    "explanation_label": "कृषि विश्लेषण एवं स्पष्टीकरण",
    "weather_warning_label": "मौसम चेतावनी / परामर्श",
    "next_steps_label": "किसान के लिए अगले कदम",
    "assumptions_label": "मान्यताएं एवं सीमाएं",
    "reset_btn": "अन्य खेत के लिए जांचें",

    // Form Validation Messages
    "err_crop_required": "कृपया एक वैध फसल चुनें।",
    "err_moisture_range": "मिट्टी की नमी 0% से 100% के बीच होनी चाहिए।",
    "err_temp_range": "तापमान -10°C से 60°C के बीच होना चाहिए।",
    "err_humidity_range": "आर्द्रता 0% से 100% के बीच होनी चाहिए।",
    "err_rainfall_range": "बारिश 0 मिमी या उससे अधिक होनी चाहिए।",
    "err_network": "सर्वर से संपर्क नहीं हो सका। कृपया सुनिश्चित करें कि बैकएंड चल रहा है।",

    // Diagnosis History Translations
    "diagnosis_history_title": "रोग निदान इतिहास",
    "diagnosis_history_desc": "अपने पिछले पौधों की जांच और रोग निदान की जानकारी देखें।",
    "view_history_btn": "इतिहास देखें →",
    "my_diagnosis_history": "📋 मेरा रोग निदान इतिहास",
    "diagnosis_history_subtitle": "आपके खाते में सहेजी गई पिछली फसल रोग निदान जानकारी।",
    "refresh_history_btn": "🔄 इतिहास रीफ्रेश करें",
    "history_login_required": "अपना सहेजा गया इतिहास देखने के लिए कृपया लॉगिन करें।",
    "history_empty": "अभी तक कोई निदान सहेजा नहीं गया है। शुरुआत करने के लिए किसी पत्ती की जांच करें।",
    "history_loading": "सहेजा गया इतिहास लोड हो रहा है...",
    "history_view_details": "विवरण देखें",
    "history_close": "बंद करें",
    "confidence_label": "विश्वसनीयता",
    "treatment_summary": "अनुशंसित उपचार",
    "prevention_summary": "रोकथाम सलाह",
    "clear_chat": "बातचीत साफ़ करें",
    "clear_chat_title": "पिछली बातचीत साफ़ करें",
    "clear_chat_confirm": "क्या आप वाकई अपना बातचीत इतिहास साफ़ करना चाहते हैं?",
    "clear_chat_success": "बातचीत इतिहास साफ़ कर दिया गया है।",
    "previous_conversations": "पिछली बातचीत",
    "voice_not_supported": "इस ब्राउज़र में आवाज़ इनपुट समर्थित नहीं है।",
    "mic_permission_denied": "माइक्रोफ़ोन अनुमति अस्वीकृत कर दी गई। कृपया ब्राउज़र में अनुमति दें।",
    "no_speech_detected": "कोई आवाज़ नहीं मिली। कृपया दोबारा बोलें।"
  }
};

function getCurrentLang() {
  return localStorage.getItem('lang') || 'en';
}

function setCurrentLang(lang) {
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;
}

function t(key) {
  const lang = getCurrentLang();
  return (translations[lang] && translations[lang][key]) ||
         (translations['en'] && translations['en'][key]) ||
         key;
}

function applyTranslations() {
  const elements = document.querySelectorAll('[data-i18n]');
  elements.forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  });
  const placeholders = document.querySelectorAll('[data-i18n-placeholder]');
  placeholders.forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.setAttribute('placeholder', t(key));
  });
  const titles = document.querySelectorAll('[data-i18n-title]');
  titles.forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    el.setAttribute('title', t(key));
  });

  const sel = document.getElementById('lang-select');
  if (sel) {
    sel.value = getCurrentLang();
    if (!sel.dataset.listenerAttached) {
      sel.dataset.listenerAttached = 'true';
      sel.addEventListener('change', e => {
        setCurrentLang(e.target.value);
        applyTranslations();
        // Dispatch custom event so dynamic modules (like irrigation result) can re-render
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: e.target.value } }));
      });
    }
  }
}

window.i18n = {
  t,
  setLang: setCurrentLang,
  applyTranslations,
  getLang: getCurrentLang
};

document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
});
