"""Multilingual utility for AgriSmart backend.

Provides language resolution and user-facing message localization
in English (en), Marathi (mr), and Hindi (hi).
"""

from flask import request


LANG_MAP = {
    "en": "en",
    "english": "en",
    "mr": "mr",
    "marathi": "mr",
    "hi": "hi",
    "hindi": "hi",
}


def normalize_language(lang_input):
    """Normalize input language string to 'en', 'mr', or 'hi'."""
    if not lang_input or not isinstance(lang_input, str):
        return "en"
    cleaned = lang_input.strip().lower()
    if cleaned.startswith("mr"):
        return "mr"
    if cleaned.startswith("hi"):
        return "hi"
    return LANG_MAP.get(cleaned, "en")


def get_request_language(user_id=None):
    """Resolve active language preference for the incoming Flask request.

    Checks in order:
    1. 'X-Language' header
    2. Query param 'lang' or 'language'
    3. JSON body 'language' (if present)
    4. 'Accept-Language' header
    5. User database preferred_language (if user_id provided)
    6. Fallback to 'en'
    """
    try:
        # 1. Custom header
        x_lang = request.headers.get("X-Language")
        if x_lang:
            norm = normalize_language(x_lang)
            if norm in ("en", "mr", "hi"):
                return norm

        # 2. Query param
        q_lang = request.args.get("lang") or request.args.get("language")
        if q_lang:
            norm = normalize_language(q_lang)
            if norm in ("en", "mr", "hi"):
                return norm

        # 3. JSON body
        if request.is_json:
            data = request.get_json(silent=True)
            if isinstance(data, dict):
                b_lang = data.get("language") or data.get("lang")
                if b_lang:
                    norm = normalize_language(b_lang)
                    if norm in ("en", "mr", "hi"):
                        return norm

        # 4. Accept-Language header
        accept = request.headers.get("Accept-Language", "").lower()
        if "mr" in accept:
            return "mr"
        if "hi" in accept:
            return "hi"

        # 5. Database lookup for authenticated user
        if user_id:
            from config import get_db_connection
            conn = None
            cur = None
            try:
                conn = get_db_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT preferred_language FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if row and row.get("preferred_language"):
                    norm = normalize_language(row["preferred_language"])
                    if norm in ("en", "mr", "hi"):
                        return norm
            except Exception:
                pass
            finally:
                if cur:
                    try:
                        cur.close()
                    except Exception:
                        pass
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass
    except Exception:
        pass

    return "en"


MESSAGES = {
    "en": {
        # Common & Auth
        "req_body_required": "Request body is required",
        "valid_mobile_required": "Please enter a valid 10-digit mobile number",
        "otp_required": "Please enter the 6-digit OTP",
        "invalid_otp": "Invalid or expired OTP",
        "no_account_mobile": "No account found with this mobile number",
        "otp_verified": "OTP verified successfully",
        "otp_sent": "OTP sent successfully",
        "invalid_credentials": "Invalid email or password",
        "login_success": "Login successful",
        "account_exists": "Account already exists with this mobile number or email",
        "reg_success": "Registration successful",
        "lang_updated": "Preferred language updated successfully",
        "invalid_lang": "Invalid language selection. Choose English, Marathi, or Hindi.",
        "auth_required": "Authentication required. Please log in.",
        "session_expired": "Session expired or invalid token.",

        # Disease Detection
        "upload_leaf_image": "Please upload a plant leaf image",
        "invalid_image_file": "Invalid image file format",
        "diagnosis_completed": "Disease diagnosis completed",
        "history_cleared": "Diagnosis history cleared successfully",
        "diagnosis_not_found": "Diagnosis record not found",

        # Irrigation
        "crop_required": "Crop name is required",
        "soil_moisture_range": "Soil moisture must be between 0% and 100%",
        "temp_range": "Temperature must be between -10°C and 60°C",
        "humidity_range": "Humidity must be between 0% and 100%",
        "rainfall_range": "Recent rainfall must be 0 mm or greater",
        "irrigation_success": "Irrigation recommendation generated successfully",

        # Crops & Farms
        "farm_name_required": "Farm name is required",
        "farm_area_positive": "Total farm area must be greater than 0",
        "farm_added": "Farm added successfully",
        "farm_updated": "Farm updated successfully",
        "farm_deleted": "Farm deleted successfully",
        "crop_added": "Crop registered successfully",
        "crop_updated": "Crop updated successfully",
        "crop_deleted": "Crop deleted successfully",
        "crop_name_required": "Crop name is required",
        "crop_area_positive": "Cultivated area must be greater than 0",

        # Notifications
        "notification_read": "Notification marked as read",
        "all_notifications_read": "All notifications marked as read",
        "notification_deleted": "Notification deleted",
        "all_notifications_cleared": "All notifications cleared",
        "prefs_updated": "Notification preferences updated successfully",

        # IoT
        "sensor_registered": "Sensor registered successfully",
        "sensor_updated": "Sensor updated successfully",
        "sensor_deleted": "Sensor deleted successfully",
        "demo_reading_created": "Demo reading generated successfully",
        "demo_readings_cleared": "Demo readings cleared successfully",
        "key_regenerated": "Device key regenerated successfully",
        "device_id_required": "Device ID is required",
        "sensor_not_found": "Sensor not found",
        "device_auth_failed": "Device authentication failed",
    },
    "mr": {
        # Common & Auth
        "req_body_required": "विनंती माहिती (Body) आवश्यक आहे",
        "valid_mobile_required": "कृपया वैध १०-अंकी मोबाईल नंबर प्रविष्ट करा",
        "otp_required": "कृपया ६-अंकी OTP प्रविष्ट करा",
        "invalid_otp": "अवैध किंवा कालबाह्य झालेला OTP",
        "no_account_mobile": "या मोबाईल नंबरसह कोणतेही खाते आढळले नाही",
        "otp_verified": "OTP यशस्वीरित्या पडताळला गेला",
        "otp_sent": "OTP यशस्वीरित्या पाठवला गेला",
        "invalid_credentials": "अवैध ईमेल किंवा पासवर्ड",
        "login_success": "लॉगिन यशस्वी झाले",
        "account_exists": "या मोबाईल नंबर किंवा ईमेलसह खाते आधीपासून अस्तित्वात आहे",
        "reg_success": "नोंदणी यशस्वी झाली",
        "lang_updated": "पसंतीची भाषा यशस्वीरित्या अद्यतनित केली",
        "invalid_lang": "अवैध भाषा निवड. इंग्रजी, मराठी किंवा हिंदी निवडा.",
        "auth_required": "प्रमाणीकरण आवश्यक आहे. कृपया लॉगिन करा.",
        "session_expired": "सत्र समाप्त झाले किंवा अवैध टोकन.",

        # Disease Detection
        "upload_leaf_image": "कृपया वनस्पती पानाचा फोटो अपलोड करा",
        "invalid_image_file": "अवैध फोटो फॉरमॅट",
        "diagnosis_completed": "रोगनिदान पूर्ण झाले",
        "history_cleared": "निदान इतिहास यशस्वीरित्या हटवला गेला",
        "diagnosis_not_found": "निदान नोंद आढळली नाही",

        # Irrigation
        "crop_required": "पिकाचे नाव आवश्यक आहे",
        "soil_moisture_range": "मातीतील ओलावा ०% ते १००% दरम्यान असावा",
        "temp_range": "तापमान -१०°C ते ६०°C दरम्यान असावे",
        "humidity_range": "हवेतील आर्द्रता ०% ते १००% दरम्यान असावी",
        "rainfall_range": "नुकताच झालेला पाऊस ० मिमी किंवा अधिक असावा",
        "irrigation_success": "सिंचन शिफारस यशस्वीरित्या तयार केली",

        # Crops & Farms
        "farm_name_required": "शेताचे नाव आवश्यक आहे",
        "farm_area_positive": "एकूण शेताचे क्षेत्र ० पेक्षा जास्त असावे",
        "farm_added": "शेत यशस्वीरित्या जोडले गेले",
        "farm_updated": "शेत यशस्वीरित्या अद्यतनित केले",
        "farm_deleted": "शेत यशस्वीरित्या हटवले",
        "crop_added": "पीक नोंदणी यशस्वीरित्या झाली",
        "crop_updated": "पीक यशस्वीरित्या अद्यतनित केले",
        "crop_deleted": "पीक यशस्वीरित्या हटवले",
        "crop_name_required": "पिकाचे नाव आवश्यक आहे",
        "crop_area_positive": "लागवड क्षेत्र ० पेक्षा जास्त असावे",

        # Notifications
        "notification_read": "सूचना वाचली म्हणून चिन्हांकित केली",
        "all_notifications_read": "सर्व सूचना वाचल्या म्हणून चिन्हांकित केल्या",
        "notification_deleted": "सूचना हटवली",
        "all_notifications_cleared": "सर्व सूचना हटवल्या",
        "prefs_updated": "सूचना प्राधान्ये यशस्वीरित्या अद्यतनित केली",

        # IoT
        "sensor_registered": "सेंसर यशस्वीरित्या नोंदणीकृत झाला",
        "sensor_updated": "सेंसर यशस्वीरित्या अद्यतनित केला",
        "sensor_deleted": "सेंसर यशस्वीरित्या हटवला",
        "demo_reading_created": "डेमो रिडिंग यशस्वीरित्या तयार केले",
        "demo_readings_cleared": "डेमो रिडिंग्ज यशस्वीरित्या हटवले",
        "key_regenerated": "डिव्हाइस की यशस्वीरित्या पुन्हा तयार केली",
        "device_id_required": "डिव्हाइस आयडी आवश्यक आहे",
        "sensor_not_found": "सेंसर आढळला नाही",
        "device_auth_failed": "डिव्हाइस प्रमाणीकरण अयशस्वी",
    },
    "hi": {
        # Common & Auth
        "req_body_required": "अनुरोध डेटा (Body) आवश्यक है",
        "valid_mobile_required": "कृपया मान्य १०-अंकीय मोबाइल नंबर दर्ज करें",
        "otp_required": "कृपया ६-अंकीय OTP दर्ज करें",
        "invalid_otp": "अमान्य या समाप्त हो चुका OTP",
        "no_account_mobile": "इस मोबाइल नंबर से कोई खाता नहीं मिला",
        "otp_verified": "OTP सफलतापूर्वक सत्यापित हुआ",
        "otp_sent": "OTP सफलतापूर्वक भेजा गया",
        "invalid_credentials": "अमान्य ईमेल या पासवर्ड",
        "login_success": "लॉगिन सफल रहा",
        "account_exists": "इस मोबाइल नंबर या ईमेल से खाता पहले से मौजूद है",
        "reg_success": "पंजीकरण सफल रहा",
        "lang_updated": "पसंदीदा भाषा सफलतापूर्वक अपडेट की गई",
        "invalid_lang": "अमान्य भाषा चयन। अंग्रेजी, मराठी या हिंदी चुनें।",
        "auth_required": "प्रमाणीकरण आवश्यक है। कृपया लॉगिन करें।",
        "session_expired": "सत्र समाप्त या अमान्य टोकन।",

        # Disease Detection
        "upload_leaf_image": "कृपया पौधे की पत्ती की तस्वीर अपलोड करें",
        "invalid_image_file": "अमान्य फ़ोटो प्रारूप",
        "diagnosis_completed": "रोग निदान पूरा हुआ",
        "history_cleared": "निदान इतिहास सफलतापूर्वक हटाया गया",
        "diagnosis_not_found": "निदान रिकॉर्ड नहीं मिला",

        # Irrigation
        "crop_required": "फसल का नाम आवश्यक है",
        "soil_moisture_range": "मिट्टी की नमी ०% से १००% के बीच होनी चाहिए",
        "temp_range": "तापमान -१०°C से ६०°C के बीच होना चाहिए",
        "humidity_range": "हवा की नमी ०% से १००% के बीच होनी चाहिए",
        "rainfall_range": "हालिया बारिश ० मिमी या अधिक होनी चाहिए",
        "irrigation_success": "सिंचाई सिफारिश सफलतापूर्वक तैयार की गई",

        # Crops & Farms
        "farm_name_required": "खेत का नाम आवश्यक है",
        "farm_area_positive": "कुल खेत का क्षेत्रफल ० से अधिक होना चाहिए",
        "farm_added": "खेत सफलतापूर्वक जोड़ा गया",
        "farm_updated": "खेत सफलतापूर्वक अपडेट किया गया",
        "farm_deleted": "खेत सफलतापूर्वक हटाया गया",
        "crop_added": "फसल सफलतापूर्वक पंजीकृत की गई",
        "crop_updated": "फसल सफलतापूर्वक अपडेट की गई",
        "crop_deleted": "फसल सफलतापूर्वक हटाई गई",
        "crop_name_required": "फसल का नाम आवश्यक है",
        "crop_area_positive": "बोया गया क्षेत्रफल ० से अधिक होना चाहिए",

        # Notifications
        "notification_read": "सूचना पढ़ी हुई चिह्नित की गई",
        "all_notifications_read": "सभी सूचनाएं पढ़ी हुई चिह्नित की गईं",
        "notification_deleted": "सूचना हटाई गई",
        "all_notifications_cleared": "सभी सूचनाएं हटा दी गईं",
        "prefs_updated": "सूचना प्राथमिकताएं सफलतापूर्वक अपडेट की गईं",

        # IoT
        "sensor_registered": "सेंसर सफलतापूर्वक पंजीकृत हुआ",
        "sensor_updated": "सेंसर सफलतापूर्वक अपडेट किया गया",
        "sensor_deleted": "सेंसर सफलतापूर्वक हटाया गया",
        "demo_reading_created": "डेमो रीडिंग सफलतापूर्वक बनाई गई",
        "demo_readings_cleared": "डेमो रीडिंग्स सफलतापूर्वक हटा दी गईं",
        "key_regenerated": "डिवाइस कुंजी सफलतापूर्वक पुनः बनाई गई",
        "device_id_required": "डिवाइस आईडी आवश्यक है",
        "sensor_not_found": "सेंसर नहीं मिला",
        "device_auth_failed": "डिवाइस प्रमाणीकरण विफल",
    }
}


def t_backend(key, lang=None, default=None):
    """Retrieve localized message string with fallback."""
    if not lang:
        lang = get_request_language()
    norm_lang = normalize_language(lang)
    lang_dict = MESSAGES.get(norm_lang, MESSAGES["en"])
    if key in lang_dict:
        return lang_dict[key]
    if key in MESSAGES["en"]:
        return MESSAGES["en"][key]
    return default or key
