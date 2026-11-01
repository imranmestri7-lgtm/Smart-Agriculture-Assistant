const fs = require('fs');

const currentContent = fs.readFileSync('js/i18n.js', 'utf8');
const vm = require('vm');
const sandbox = { window: {}, document: { querySelectorAll: () => [], getElementById: () => null, addEventListener: () => {} }, localStorage: { getItem: () => "en", setItem: () => {} } };
vm.createContext(sandbox);
vm.runInContext(currentContent.replace('const translations =', 'var translations ='), sandbox);
const en = sandbox.translations.en;
const mr = sandbox.translations.mr;
const hi = sandbox.translations.hi;

const extra = {
  // Page action buttons and links
  "for_farmers_label": { en: "FOR FARMERS", mr: "शेतकऱ्यांसाठी", hi: "किसानों के लिए" },
  "what_would_you_like_title": { en: "What Would You Like to Do?", mr: "तुम्हाला काय करायचे आहे?", hi: "आप क्या करना चाहते हैं?" },
  "what_would_you_like_desc": { en: "Choose what you need help with.", mr: "तुम्हाला कशासाठी मदत हवी आहे ते निवडा.", hi: "चुनें कि आपको किस सहायता की आवश्यकता है।" },
  "farmer_action_crops": { en: "\"I want to manage my crops\"", mr: "\"मला माझी पिके व्यवस्थापित करायची आहेत\"", hi: "\"मैं अपनी फसलों का प्रबंधन करना चाहता हूँ\"" },
  "farmer_action_crops_desc": { en: "Add and manage your crop information.", mr: "तुमच्या पिकांची माहिती जोडा आणि व्यवस्थापित करा.", hi: "अपनी फसलों की जानकारी जोड़ें और प्रबंधित करें।" },
  "farmer_action_disease": { en: "\"My plant looks unhealthy\"", mr: "\"माझे झाड आजारी दिसत आहे\"", hi: "\"मेरा पौधा अस्वस्थ दिख रहा है\"" },
  "farmer_action_disease_desc": { en: "Check a plant image for possible problems.", mr: "संभाव्य समस्यांसाठी झाडाचा फोटो तपासा.", hi: "संभावित समस्याओं के लिए पौधे की तस्वीर जाँचें।" },
  "farmer_action_irrigation": { en: "\"I want irrigation guidance\"", mr: "\"मला सिंचनाचे मार्गदर्शन हवे आहे\"", hi: "\"मुझे सिंचाई मार्गदर्शन चाहिए\"" },
  "farmer_action_irrigation_desc": { en: "Get useful information about watering crops.", mr: "पिकांना पाणी देण्याबाबत उपयुक्त माहिती मिळवा.", hi: "फसलों को पानी देने के बारे में उपयोगी जानकारी प्राप्त करें।" },
  "farmer_action_weather": { en: "\"I want to check the weather\"", mr: "\"मला हवामान तपासायचे आहे\"", hi: "\"मुझे मौसम देखना है\"" },
  "farmer_action_weather_desc": { en: "View weather information for farming.", mr: "शेतीसाठी हवामानाची माहिती पहा.", hi: "खेती के लिए मौसम की जानकारी देखें।" },
  "farmer_action_assistant": { en: "\"I have a farming question\"", mr: "\"मला शेतीविषयी प्रश्न विचारायचा आहे\"", hi: "\"मेरा खेती से जुड़ा एक सवाल है\"" },
  "farmer_action_assistant_desc": { en: "Ask the AgriSmart Farmer Assistant.", mr: "AgriSmart शेतकरी सहाय्यकाला विचारा.", hi: "AgriSmart किसान सहायक से पूछें।" },
  "farmer_action_history": { en: "\"I want to see my history\"", mr: "\"मला माझा इतिहास पहायचा आहे\"", hi: "\"मुझे अपना इतिहास देखना है\"" },
  "farmer_action_history_desc": { en: "Review your previous plant health checks.", mr: "मागील झाडांच्या तपासणीच्या नोंदी पहा.", hi: "पिछली पौधों की स्वास्थ्य जाँच की समीक्षा करें।" },
  "btn_open": { en: "Open →", mr: "उघडा →", hi: "खोलें →" },
  "btn_check": { en: "Check →", mr: "तपासा →", hi: "जाँचें →" },
  "btn_explore": { en: "Explore →", mr: "पहा →", hi: "देखें →" },
  "btn_ask": { en: "Ask →", mr: "विचारा →", hi: "पूछें →" },
  "btn_view": { en: "View →", mr: "पहा →", hi: "देखें →" },

  // Why AgriSmart Section
  "why_agrismart_label": { en: "WHY AGRISMART?", mr: "AGRISMART का?", hi: "AGRISMART क्यों?" },
  "why_agrismart_title": { en: "One Simple Platform for Everyday Farming Support", mr: "दैनंदिन शेती मदतीसाठी एकच सोपे व्यासपीठ", hi: "दैनिक कृषि सहायता के लिए एक सरल मंच" },
  "why_agrismart_desc": { en: "AgriSmart brings useful farming tools together so farmers can access crop information, plant health guidance, weather information, irrigation support and farming assistance from one place.", mr: "AgriSmart सर्व उपयुक्त शेती साधने एकत्र आणते जेणेकरून शेतकऱ्यांना पीक माहिती, झाडांचे आरोग्य, हवामान, सिंचन आणि शेती सहाय्य एकाच ठिकाणाहून मिळू शकेल.", hi: "AgriSmart उपयोगी कृषि उपकरणों को एक साथ लाता है ताकि किसान एक ही स्थान से फसल की जानकारी, पौधों का स्वास्थ्य, मौसम, सिंचाई और कृषि सहायता प्राप्त कर सकें।" },
  "why_point1_title": { en: "Simple Interface", mr: "सोपा आणि सुलभ इंटरफेस", hi: "सरल और सुगम इंटरफ़ेस" },
  "why_point1_desc": { en: "Designed to be easy to understand and use.", mr: "समजण्यास आणि वापरण्यास अत्यंत सोपे.", hi: "समझने और उपयोग करने में अत्यंत आसान।" },
  "why_point2_title": { en: "Farmer Focused", mr: "शेतकऱ्यांच्या गरजांवर आधारित", hi: "किसानों की ज़रूरतों पर केंद्रित" },
  "why_point2_desc": { en: "Built around common farming needs.", mr: "दैनंदिन शेती गरजा लक्षात घेऊन तयार केलेले.", hi: "सामान्य कृषि आवश्यकताओं को ध्यान में रखकर निर्मित।" },
  "why_point3_title": { en: "Multiple Farming Tools", mr: "विविध शेती साधने", hi: "अनेक कृषि उपकरण" },
  "why_point3_desc": { en: "Crop, plant health, weather, irrigation and assistance.", mr: "पीक, झाडांचे आरोग्य, हवामान, सिंचन आणि सहाय्य एकाच ठिकाणी.", hi: "फसल, पौधों का स्वास्थ्य, मौसम, सिंचाई और सहायता एक ही स्थान पर।" },
  "why_point4_title": { en: "Language Support", mr: "मातृभाषेत सहाय्य", hi: "मातृभाषा में सहायता" },
  "why_point4_desc": { en: "Designed with multilingual support in mind.", mr: "मराठी, हिंदी आणि इंग्रजी भाषेमध्ये उपलब्ध.", hi: "मराठी, हिंदी और अंग्रेजी भाषा में उपलब्ध।" },

  // About & CTA
  "about_tech_title": { en: "Technology Designed Around Farmers", mr: "शेतकऱ्यांसाठी डिझाइन केलेले तंत्रज्ञान", hi: "किसानों के लिए डिज़ाइन की गई तकनीक" },
  "about_tech_desc": { en: "AgriSmart is a farmer-focused digital platform designed to make everyday farming information easier to access and understand.", mr: "AgriSmart हे शेतकऱ्यांच्या गरजांवर आधारित डिजिटल प्लॅटफॉर्म आहे जे दैनंदिन शेती माहिती अधिक सुलभ आणि सोपी बनवते.", hi: "AgriSmart किसानों पर केंद्रित एक डिजिटल मंच है जो दैनिक कृषि जानकारी को आसान और सुलभ बनाता है।" },
  "about_feat_crops": { en: "Crop Management", mr: "पीक व्यवस्थापन", hi: "फसल प्रबंधन" },
  "about_feat_health": { en: "Plant Health", mr: "झाडांचे आरोग्य", hi: "पौधों का स्वास्थ्य" },
  "about_feat_weather": { en: "Weather", mr: "हवामान", hi: "मौसम" },
  "about_feat_irrigation": { en: "Irrigation", mr: "सिंचन", hi: "सिंचाई" },
  "about_feat_assistant": { en: "Farmer Assistance", mr: "शेतकरी सहाय्य", hi: "किसान सहायता" },
  "ready_start_title": { en: "Ready to Start?", mr: "सुरुवात करण्यास तयार आहात?", hi: "शुरू करने के लिए तैयार हैं?" },
  "ready_start_desc": { en: "Create your account and start exploring AgriSmart farming tools.", mr: "तुमचे खाते तयार करा आणि AgriSmart शेती साधनांचा वापर सुरू करा.", hi: "अपना खाता बनाएं और AgriSmart कृषि उपकरणों का उपयोग शुरू करें।" },
  "get_started_arrow": { en: "Get Started →", mr: "सुरुवात करा →", hi: "शुरू करें →" },

  // Analysis Flow
  "flow_title": { en: "Plant Health Analysis Flow", mr: "झाड आरोग्य विश्लेषण प्रक्रिया", hi: "पौध स्वास्थ्य विश्लेषण प्रक्रिया" },
  "flow_desc": { en: "Understand what happens when you check a plant image.", mr: "जेव्हा तुम्ही झाडाचा फोटो तपासता तेव्हा काय होते ते समजून घ्या.", hi: "जब आप पौधे की तस्वीर जाँचते हैं तो क्या होता है, इसे समझें।" },
  "flow_upload": { en: "Upload Image", mr: "फोटो अपलोड करा", hi: "फ़ोटो अपलोड करें" },
  "flow_analyze": { en: "Analyze", mr: "विश्लेषण", hi: "विश्लेषण" },
  "flow_problem": { en: "Possible Problem", mr: "संभाव्य समस्या", hi: "संभावित समस्या" },
  "flow_symptoms": { en: "Symptoms & Causes", mr: "लक्षणे आणि कारणे", hi: "लक्षण और कारण" },
  "flow_treatment": { en: "Treatment & Prevention", mr: "उपचार आणि प्रतिबंध", hi: "उपचार और रोकथाम" },

  // Login & Register Form Extras
  "login_phone_option": { en: "📱 Phone Number", mr: "📱 मोबाईल नंबर", hi: "📱 मोबाइल नंबर" },
  "login_email_option": { en: "📧 Email", mr: "📧 ईमेल", hi: "📧 ईमेल" },
  "reg_phone_option": { en: "📱 Phone Number", mr: "📱 मोबाईल नंबर", hi: "📱 मोबाइल नंबर" },
  "reg_email_option": { en: "📧 Email", mr: "📧 ईमेल", hi: "📧 ईमेल" },
  "reg_mobile_label": { en: "Mobile Number", mr: "मोबाईल नंबर", hi: "मोबाइल नंबर" },
  "reg_mobile_placeholder": { en: "Enter 10-digit mobile number", mr: "१०-अंकी मोबाईल नंबर प्रविष्ट करा", hi: "१०-अंकीय मोबाइल नंबर दर्ज करें" },
  "reg_email_label": { en: "Email Address", mr: "ईमेल पत्ता", hi: "ईमेल पता" },
  "reg_email_placeholder": { en: "Enter your email", mr: "तुमचा ईमेल प्रविष्ट करा", hi: "अपना ईमेल दर्ज करें" },
  "reg_password_label": { en: "Password", mr: "पासवर्ड", hi: "पासवर्ड" },
  "reg_password_placeholder": { en: "Enter a strong password", mr: "सुरक्षित पासवर्ड प्रविष्ट करा", hi: "मजबूत पासवर्ड दर्ज करें" },

  // Weather page extras
  "weather_partly_cloudy": { en: "Partly Cloudy", mr: "अंशतः ढगाळ", hi: "आंशिक रूप से बादलमय" },
  "weather_sunny": { en: "Sunny", mr: "सूर्यप्रकाश / स्वच्छ", hi: "धूप / साफ़" },
  "weather_rainy": { en: "Rainy", mr: "पावसाळी", hi: "बारिश" },
  "weather_cloudy": { en: "Cloudy", mr: "ढगाळ", hi: "बादल छाए रहेंगे" },
  "weather_day_mon": { en: "Mon", mr: "सोम", hi: "सोम" },
  "weather_day_tue": { en: "Tue", mr: "मंगळ", hi: "मंगल" },
  "weather_day_wed": { en: "Wed", mr: "बुध", hi: "बुध" },
  "weather_day_thu": { en: "Thu", mr: "गुरू", hi: "गुरु" },
  "weather_day_fri": { en: "Fri", mr: "शुक्र", hi: "शुक्र" },
  "weather_day_sat": { en: "Sat", mr: "शनि", hi: "शनि" },
  "weather_day_sun": { en: "Sun", mr: "रवि", hi: "रवि" },

  // Toast and Feedback Messages
  "msg_login_success": { en: "Login successful! Redirecting...", mr: "लॉगिन यशस्वी झाले! पुनर्निर्देशित करत आहे...", hi: "लॉगिन सफल रहा! पुनर्निर्देशित किया जा रहा है..." },
  "msg_invalid_mobile": { en: "Please enter a valid 10-digit mobile number.", mr: "कृपया वैध १०-अंकी मोबाईल नंबर प्रविष्ट करा.", hi: "कृपया मान्य १०-अंकीय मोबाइल नंबर दर्ज करें।" },
  "msg_enter_otp": { en: "Please enter the 6-digit OTP.", mr: "कृपया ६-अंकी OTP प्रविष्ट करा.", hi: "कृपया ६-अंकीय OTP दर्ज करें।" },
  "msg_otp_sent": { en: "OTP sent successfully.", mr: "OTP यशस्वीरित्या पाठवला गेला.", hi: "OTP सफलतापूर्वक भेजा गया।" },
  "msg_enter_email": { en: "Please enter your email address.", mr: "कृपया तुमचा ईमेल पत्ता प्रविष्ट करा.", hi: "कृपया अपना ईमेल पता दर्ज करें।" },
  "msg_enter_password": { en: "Please enter your password.", mr: "कृपया तुमचा पासवर्ड प्रविष्ट करा.", hi: "कृपया अपना पासवर्ड दर्ज करें।" },
  "msg_reg_success": { en: "Account created successfully! Redirecting to login...", mr: "खाते यशस्वीरित्या तयार झाले! लॉगिन पृष्ठावर जात आहे...", hi: "खाता सफलतापूर्वक बन गया! लॉगिन पर जा रहे हैं..." },
  "msg_passwords_mismatch": { en: "Passwords do not match.", mr: "पासवर्ड जुळत नाहीत.", hi: "पासवर्ड मेल नहीं खाते।" },
  "msg_fill_all_fields": { en: "Please fill in all required fields.", mr: "कृपया सर्व आवश्यक माहिती भरा.", hi: "कृपया सभी आवश्यक फ़ील्ड भरें।" },
  "msg_key_copied": { en: "Device key copied to clipboard!", mr: "डिव्हाइस की क्लिपबोर्डवर कॉपी केली!", hi: "डिवाइस कुंजी क्लिपबोर्ड पर कॉपी की गई!" },
  "msg_demo_injected": { en: "Demo telemetry reading injected successfully!", mr: "डेमो टेलीमेट्री यशस्वीरित्या जोडली गेली!", hi: "डेमो टेलीमेट्री सफलतापूर्वक जोड़ दी गई!" },
  "msg_demo_cleared": { en: "All demo records cleared.", mr: "सर्व डेमो नोंदी हटवल्या.", hi: "सभी डेमो रिकॉर्ड हटा दिए गए।" },
  "msg_chat_cleared": { en: "Chat history cleared.", mr: "चॅट इतिहास साफ केला.", hi: "चैट इतिहास साफ़ कर दिया गया।" },
  "msg_language_updated": { en: "Language updated.", mr: "भाषा अद्यतन केली.", hi: "भाषा अपडेट की गई।" },
  "msg_bot_thinking": { en: "AgriSmart is typing...", mr: "AgriSmart टाईप करत आहे...", hi: "AgriSmart टाइप कर रहा है..." }
};

for (const [key, val] of Object.entries(extra)) {
  en[key] = val.en;
  mr[key] = val.mr;
  hi[key] = val.hi;
}

const out = currentContent
  .replace(/en:\s*\{[\s\S]*?\n\s*\},?\s*mr:/, 'en: ' + JSON.stringify(en, null, 2) + ',\nmr:')
  .replace(/mr:\s*\{[\s\S]*?\n\s*\},?\s*hi:/, 'mr: ' + JSON.stringify(mr, null, 2) + ',\nhi:')
  .replace(/hi:\s*\{[\s\S]*?\n\s*\}/, 'hi: ' + JSON.stringify(hi, null, 2));

fs.writeFileSync('js/i18n.js', out);
console.log('Appended extra keys to js/i18n.js. Total keys:', Object.keys(en).length);
