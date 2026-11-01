const fs = require('fs');

// Read current i18n.js
const currentContent = fs.readFileSync('js/i18n.js', 'utf8');

// Extract translations object
const vm = require('vm');
const sandbox = { window: {}, document: { querySelectorAll: () => [], getElementById: () => null, addEventListener: () => {} }, localStorage: { getItem: () => "en", setItem: () => {} } };
vm.createContext(sandbox);
vm.runInContext(currentContent.replace('const translations =', 'var translations ='), sandbox);
const existingEn = sandbox.translations.en;
const existingMr = sandbox.translations.mr;
const existingHi = sandbox.translations.hi;

// New Phase 11 translations
const newTranslations = {
  // Navigation & Shared
  "dashboard": { en: "Dashboard", mr: "डॅशबोर्ड", hi: "डैशबोर्ड" },
  "farmer_role": { en: "Farmer", mr: "शेतकरी", hi: "किसान" },
  "logout": { en: "Logout", mr: "लॉगआउट", hi: "लॉगआउट" },
  "welcome_farmer": { en: "Welcome, Farmer", mr: "स्वागत आहे, शेतकरी बंधू", hi: "स्वागत है, किसान साथी" },
  "farmer_dashboard_badge": { en: "FARMER DASHBOARD", mr: "शेतकरी डॅशबोर्ड", hi: "किसान डैशबोर्ड" },
  "farmer_dashboard_title": { en: "Farmer Dashboard", mr: "शेतकरी डॅशबोर्ड", hi: "किसान डैशबोर्ड" },
  "farmer_dashboard_desc": { en: "Manage your crops, check farming information, and get guidance from your farming assistant.", mr: "पिकांचे व्यवस्थापन करा, शेती माहिती तपासा आणि शेती सहाय्यकाकडून मार्गदर्शन मिळवा.", hi: "फसलों का प्रबंधन करें, कृषि जानकारी देखें और कृषि सहायक से मार्गदर्शन प्राप्त करें।" },
  "farming_tools_badge": { en: "FARMING TOOLS", mr: "शेती साधने", hi: "कृषि उपकरण" },
  "farming_tools_heading": { en: "What would you like to do?", mr: "तुम्हाला काय करायचे आहे?", hi: "आप क्या करना चाहते हैं?" },
  "check_plant_link": { en: "Check Plant →", mr: "झाड तपासा →", hi: "पौधा जाँचें →" },
  "check_weather_link": { en: "Check Weather →", mr: "हवामान पहा →", hi: "मौसम देखें →" },
  "ask_assistant_link": { en: "Ask Assistant →", mr: "सहाय्यकाला विचारा →", hi: "सहायक से पूछें →" },
  "view_telemetry_link": { en: "View Telemetry →", mr: "निरीक्षण पहा →", hi: "निगरानी देखें →" },
  "view_analytics_link": { en: "View Analytics →", mr: "विश्लेषण पहा →", hi: "विश्लेषण देखें →" },
  "view_notifications_link": { en: "View Notifications →", mr: "सूचना पहा →", hi: "सूचनाएं देखें →" },

  // Landing Page (index.html)
  "hero_badge": { en: "🌱 Smart Farming Support", mr: "🌱 स्मार्ट शेती सहाय्य", hi: "🌱 स्मार्ट कृषि सहायता" },
  "assistant_preview_desc": { en: "Manage your crops and get useful farming information in one place.", mr: "तुमची पिके व्यवस्थापित करा आणि शेतीविषयक उपयुक्त माहिती एकाच ठिकाणी मिळवा.", hi: "अपनी फसलों का प्रबंधन करें और कृषि संबंधी उपयोगी जानकारी एक ही स्थान पर प्राप्त करें।" },
  "preview_crops": { en: "My Crops", mr: "माझी पिके", hi: "मेरी फसलें" },
  "preview_health": { en: "Plant Health", mr: "झाडांचे आरोग्य", hi: "पौधों का स्वास्थ्य" },
  "preview_weather": { en: "Weather", mr: "हवामान", hi: "मौसम" },
  "preview_irrigation": { en: "Irrigation", mr: "सिंचन", hi: "सिंचाई" },
  "features_label": { en: "FARMING FEATURES", mr: "शेती वैशिष्ट्ये", hi: "खेती की विशेषताएं" },
  "features_title": { en: "Everything You Need for Better Farming", mr: "उत्कृष्ट शेतीसाठी सर्वकाही एकाच ठिकाणी", hi: "बेहतर खेती के लिए सब कुछ एक स्थान पर" },
  "features_subtitle": { en: "Explore the main tools available through AgriSmart.", mr: "AgriSmart मधील मुख्य शेती साधनांची माहिती घ्या.", hi: "AgriSmart के मुख्य कृषि उपकरणों की जानकारी लें।" },
  "feature_crops_desc": { en: "Add and manage your crops, varieties, planting dates and field information.", mr: "तुमची पिके, वाण, लागवडीची तारीख आणि शेताची माहिती जोडा व व्यवस्थापित करा.", hi: "अपनी फसलें, किस्में, बुवाई की तारीख और खेत की जानकारी जोड़ें व प्रबंधित करें।" },
  "feature_manage_crops_link": { en: "Manage Crops →", mr: "पिके व्यवस्थापित करा →", hi: "फसल प्रबंधन करें →" },
  "feature_disease_title": { en: "Disease Detection", mr: "रोगनिदान", hi: "रोग निदान" },
  "feature_disease_desc": { en: "Upload a plant image to identify possible plant health problems.", mr: "झाडांच्या संभाव्य आरोग्य समस्या ओळखण्यासाठी पानाचा फोटो अपलोड करा.", hi: "पौधों की संभावित स्वास्थ्य समस्याओं की पहचान के लिए पत्ती की तस्वीर अपलोड करें।" },
  "feature_learn_more_link": { en: "Learn More →", mr: "अधिक जाणून घ्या →", hi: "और जानें →" },
  "feature_irrigation_title": { en: "Irrigation Guidance", mr: "सिंचन मार्गदर्शन", hi: "सिंचाई मार्गदर्शन" },
  "feature_irrigation_desc": { en: "Get useful information about watering your crops using field data.", mr: "शेतातील माहितीचा वापर करून पिकांना पाणी देण्याबाबत उपयुक्त मार्गदर्शन मिळवा.", hi: "खेत के आंकड़ों का उपयोग करके फसलों को पानी देने के संबंध में उपयोगी मार्गदर्शन प्राप्त करें।" },
  "feature_weather_title": { en: "Weather Information", mr: "हवामान माहिती", hi: "मौसम की जानकारी" },
  "feature_weather_desc": { en: "Check weather information that can help you plan farm activities.", mr: "शेती कामांचे नियोजन करण्यासाठी उपयुक्त हवामान माहिती तपासा.", hi: "कृषि कार्यों की योजना बनाने के लिए उपयोगी मौसम की जानकारी देखें।" },
  "feature_check_weather_link": { en: "Check Weather →", mr: "हवामान तपासा →", hi: "मौसम देखें →" },
  "feature_assistant_title": { en: "Farmer Assistant", mr: "शेतकरी सहाय्यक", hi: "किसान सहायक" },
  "feature_assistant_desc": { en: "Ask farming-related questions and get useful practical answers.", mr: "शेतीविषयक प्रश्न विचारा आणि उपयुक्त व्यावहारिक उत्तरे मिळवा.", hi: "खेती से जुड़े प्रश्न पूछें और उपयोगी व्यावहारिक उत्तर प्राप्त करें।" },
  "feature_ask_assistant_link": { en: "Ask Assistant →", mr: "सहाय्यकाला विचारा →", hi: "सहायक से पूछें →" },
  "feature_history_title": { en: "Diagnosis History", mr: "निदान इतिहास", hi: "निदान इतिहास" },
  "feature_history_desc": { en: "Keep a record of your previous plant checks for future reference.", mr: "पुढील संदर्भासाठी तुमच्या मागील झाड तपासणीच्या नोंदी ठेवा.", hi: "भविष्य के संदर्भ के लिए अपनी पिछली पौधों की जाँच का रिकॉर्ड रखें।" },
  "how_it_works_label": { en: "SIMPLE PROCESS", mr: "सोपी प्रक्रिया", hi: "सरल प्रक्रिया" },
  "how_it_works_title": { en: "How AgriSmart Works", mr: "AgriSmart कसे कार्य करते", hi: "AgriSmart कैसे काम करता है" },
  "how_it_works_subtitle": { en: "Four simple steps to support your everyday farming decisions.", mr: "तुमच्या दैनंदिन शेती निर्णयांसाठी ४ सोप्या पायऱ्या.", hi: "आपके दैनिक कृषि निर्णयों के लिए ४ सरल चरण।" },
  "step_1_heading": { en: "Create Account", mr: "खाते तयार करा", hi: "खाता बनाएं" },
  "step_1_text": { en: "Sign up using your phone number or email address.", mr: "तुमचा मोबाईल नंबर किंवा ईमेल पत्ता वापरून नोंदणी करा.", hi: "अपने मोबाइल नंबर या ईमेल पते का उपयोग करके पंजीकरण करें।" },
  "step_2_heading": { en: "Add Your Farm & Crops", mr: "तुमचे शेत आणि पिके जोडा", hi: "अपना खेत और फसलें जोड़ें" },
  "step_2_text": { en: "Enter your crop details to keep track of your field activities.", mr: "शेतातील कामांचा मागोवा घेण्यासाठी तुमच्या पिकांचे तपशील प्रविष्ट करा.", hi: "खेत की गतिविधियों पर नज़र रखने के लिए अपनी फसलों का विवरण दर्ज करें।" },
  "step_3_heading": { en: "Use Farming Tools", mr: "शेती साधने वापरा", hi: "कृषि उपकरण उपयोग करें" },
  "step_3_text": { en: "Check plant health, weather updates, and irrigation advice.", mr: "झाडांचे आरोग्य, हवामान अंदाज आणि सिंचन सल्ला तपासा.", hi: "पौधों का स्वास्थ्य, मौसम का हाल और सिंचाई सलाह देखें।" },
  "step_4_heading": { en: "Get Useful Support", mr: "उपयुक्त मार्गदर्शन मिळवा", hi: "उपयोगी सहायता प्राप्त करें" },
  "step_4_text": { en: "Ask questions to the assistant and review previous records anytime.", mr: "सहाय्यकाला प्रश्न विचारा आणि कोणत्याही वेळी मागील नोंदी तपासा.", hi: "सहायक से प्रश्न पूछें और कभी भी पिछले रिकॉर्ड की समीक्षा करें।" },
  "about_label": { en: "ABOUT US", mr: "आमच्याबद्दल", hi: "हमारे बारे में" },
  "about_title": { en: "Built for Farmers", mr: "शेतकऱ्यांसाठी समर्पित", hi: "किसानों के लिए समर्पित" },
  "about_p1": { en: "AgriSmart is designed to provide practical and accessible farming tools in one place. By combining field data, weather forecasts, and crop knowledge, we help farmers make timely decisions.", mr: "AgriSmart ची रचना शेतकऱ्यांना एकाच ठिकाणी व्यावहारिक आणि सुलभ शेती साधने देण्यासाठी केली आहे. शेतातील डेटा, हवामान अंदाज आणि पीक ज्ञानाचा मेळ घालून आम्ही शेतकऱ्यांना वेळेवर निर्णय घेण्यास मदत करतो.", hi: "AgriSmart को किसानों को एक ही स्थान पर व्यावहारिक और सुलभ कृषि उपकरण प्रदान करने के लिए डिज़ाइन किया गया है। खेत के आंकड़ों, मौसम के पूर्वानुमान और फसल ज्ञान को मिलाकर, हम किसानों को समय पर निर्णय लेने में मदद करते हैं।" },
  "about_p2": { en: "Whether checking a suspicious crop leaf, planning next week's watering, or asking everyday farming questions, AgriSmart is here to assist.", mr: "पिकाच्या पानांवरील रोगाची तपासणी असो, पुढील आठवड्यातील पाण्याचे नियोजन असो किंवा दैनंदिन शेतीचे प्रश्न असोत, AgriSmart नेहमी तुमच्या मदतीसाठी तत्पर आहे.", hi: "चाहे फसल की पत्ती की जाँच हो, अगले सप्ताह की सिंचाई की योजना हो, या दैनिक खेती के प्रश्न हों, AgriSmart आपकी सहायता के लिए हमेशा तैयार है।" },
  "about_badge_smart": { en: "Practical Technology", mr: "व्यावहारिक तंत्रज्ञान", hi: "व्यावहारिक तकनीक" },
  "about_badge_multilingual": { en: "Multilingual Support", mr: "बहुभाषिक सहाय्य", hi: "बहुभाषी सहायता" },
  "about_badge_crops": { en: "Crop Management", mr: "पीक व्यवस्थापन", hi: "फसल प्रबंधन" },
  "about_badge_secure": { en: "Secure Farmer Data", mr: "सुरक्षित शेतकरी डेटा", hi: "सुरक्षित किसान डेटा" },
  "cta_title": { en: "Start Using AgriSmart Today", mr: "आजच AgriSmart वापरण्यास सुरुवात करा", hi: "आज ही AgriSmart का उपयोग शुरू करें" },
  "cta_desc": { en: "Join farmers using simple digital tools to support crop health and farm planning.", mr: "पिकांचे आरोग्य आणि शेती नियोजनासाठी डिजिटल साधनांचा वापर करणाऱ्या शेतकऱ्यांमध्ये सामील व्हा.", hi: "फसल स्वास्थ्य और कृषि योजना के लिए सरल डिजिटल उपकरणों का उपयोग करने वाले किसानों से जुड़ें।" },
  "footer_desc": { en: "A simple and helpful smart agriculture platform designed to support farmers.", mr: "शेतकऱ्यांना मदत करण्यासाठी डिझाइन केलेले एक साधे आणि उपयुक्त स्मार्ट कृषी प्लॅटफॉर्म.", hi: "किसानों की सहायता के लिए डिज़ाइन किया गया एक सरल और उपयोगी स्मार्ट कृषि मंच।" },
  "footer_quick_links": { en: "Quick Links", mr: "द्रुत दुवे", hi: "त्वरित लिंक" },
  "footer_tools": { en: "Farming Tools", mr: "शेती साधने", hi: "कृषि उपकरण" },
  "footer_contact": { en: "Platform Support", mr: "प्लॅटफॉर्म सहाय्य", hi: "मंच सहायता" },
  "footer_rights": { en: "All rights reserved.", mr: "सर्व हक्क राखीव.", hi: "सर्वाधिकार सुरक्षित।" },

  // Login Page (login.html)
  "login_heading": { en: "How would you like to login?", mr: "तुम्ही कसे लॉगिन करू इच्छिता?", hi: "आप कैसे लॉगिन करना चाहते हैं?" },
  "login_subtitle": { en: "Access your crops, plant checks and farming tools.", mr: "तुमची पिके, झाडांची तपासणी आणि शेती साधनांमध्ये प्रवेश करा.", hi: "अपनी फसलों, पौधों की जाँच और कृषि उपकरणों तक पहुँचें।" },
  "login_phone_tab": { en: "📱 Phone Number", mr: "📱 मोबाईल नंबर", hi: "📱 मोबाइल नंबर" },
  "login_email_tab": { en: "📧 Email", mr: "📧 ईमेल", hi: "📧 ईमेल" },
  "login_mobile_label": { en: "Mobile Number", mr: "मोबाईल नंबर", hi: "मोबाइल नंबर" },
  "login_mobile_placeholder": { en: "Enter 10-digit mobile number", mr: "१०-अंकी मोबाईल नंबर प्रविष्ट करा", hi: "१०-अंकीय मोबाइल नंबर दर्ज करें" },
  "login_send_otp_btn": { en: "Send OTP", mr: "OTP पाठवा", hi: "OTP भेजें" },
  "login_otp_label": { en: "Enter 6-digit OTP", mr: "६-अंकी OTP प्रविष्ट करा", hi: "६-अंकीय OTP दर्ज करें" },
  "login_otp_placeholder": { en: "Enter OTP", mr: "OTP प्रविष्ट करा", hi: "OTP दर्ज करें" },
  "login_verify_otp_btn": { en: "Verify OTP & Login", mr: "OTP पडताळा आणि लॉगिन करा", hi: "OTP सत्यापित करें और लॉगिन करें" },
  "login_change_number": { en: "Change mobile number", mr: "मोबाईल नंबर बदला", hi: "मोबाइल नंबर बदलें" },
  "login_email_label": { en: "Email Address", mr: "ईमेल पत्ता", hi: "ईमेल पता" },
  "login_email_placeholder": { en: "Enter your email", mr: "तुमचा ईमेल प्रविष्ट करा", hi: "अपना ईमेल दर्ज करें" },
  "login_password_label": { en: "Password", mr: "पासवर्ड", hi: "पासवर्ड" },
  "login_password_placeholder": { en: "Enter your password", mr: "तुमचा पासवर्ड प्रविष्ट करा", hi: "अपना पासवर्ड दर्ज करें" },
  "login_submit_btn": { en: "Login", mr: "लॉगिन", hi: "लॉगिन" },
  "login_no_account": { en: "Don't have an account?", mr: "खाते नाही?", hi: "खाता नहीं है?" },
  "login_create_account": { en: "Create Account", mr: "खाते तयार करा", hi: "खाता बनाएं" },
  "dev_otp_label": { en: "Development OTP:", mr: "चाचणी OTP:", hi: "परीक्षण OTP:" },
  "dev_otp_note": { en: "Use this test OTP in local development mode.", mr: "स्थानिक चाचणी मोडमध्ये हा OTP वापरा.", hi: "स्थानीय परीक्षण मोड में इस OTP का उपयोग करें।" },

  // Register Page (register.html)
  "register_title": { en: "Create Account", mr: "खाते तयार करा", hi: "खाता बनाएं" },
  "register_subtitle": { en: "Choose how you want to create your AgriSmart account.", mr: "AgriSmart खाते कसे तयार करायचे ते निवडा.", hi: "AgriSmart खाता कैसे बनाना चाहते हैं, चुनें।" },
  "register_tab_heading": { en: "How would you like to register?", mr: "तुम्ही नोंदणी कशी करू इच्छिता?", hi: "आप पंजीकरण कैसे करना चाहते हैं?" },
  "reg_fullname_label": { en: "Full Name", mr: "पूर्ण नाव", hi: "पूरा नाम" },
  "reg_fullname_placeholder": { en: "Enter your full name", mr: "तुमचे पूर्ण नाव प्रविष्ट करा", hi: "अपना पूरा नाम दर्ज करें" },
  "reg_confirm_password_label": { en: "Confirm Password", mr: "पासवर्डची पुष्टी करा", hi: "पासवर्ड की पुष्टि करें" },
  "reg_confirm_password_placeholder": { en: "Re-enter your password", mr: "पासवर्ड पुन्हा प्रविष्ट करा", hi: "पासवर्ड पुनः दर्ज करें" },
  "reg_lang_label": { en: "Preferred Language", mr: "पसंतीची भाषा", hi: "पसंदीदा भाषा" },
  "reg_submit_btn": { en: "Create Account", mr: "खाते तयार करा", hi: "खाता बनाएं" },
  "reg_has_account": { en: "Already have an account?", mr: "आधीच खाते आहे?", hi: "पहले से खाता है?" },
  "reg_login_link": { en: "Login", mr: "लॉगिन", hi: "लॉगिन" },

  // Disease Page (disease.html)
  "disease_badge": { en: "🌿 AI-Powered Agriculture", mr: "🌿 एआय-आधारित कृषी तंत्रज्ञान", hi: "🌿 एआई-संचालित कृषि तकनीक" },
  "disease_hero_title": { en: "Plant Disease Detection", mr: "वनस्पती रोगनिदान", hi: "पौधों का रोग निदान" },
  "disease_hero_desc": { en: "Upload or capture a crop leaf image and let our AI system help identify possible plant problems.", mr: "पिकाच्या पानाचा फोटो अपलोड करा किंवा काढा आणि आमच्या AI प्रणालीला वनस्पतींच्या समस्या ओळखू द्या.", hi: "फसल की पत्ती की तस्वीर अपलोड करें या खींचें और हमारी AI प्रणाली को पौधों की समस्याओं की पहचान करने दें।" },
  "disease_hero_btn": { en: "Start Disease Scan →", mr: "रोगनिदान सुरू करा →", hi: "रोग निदान शुरू करें →" },
  "scanner_badge": { en: "SMART SCANNER", mr: "स्मार्ट स्कॅनर", hi: "स्मार्ट स्कैनर" },
  "scanner_title": { en: "Disease Scanner", mr: "रोग स्कॅनर", hi: "रोग स्कैनर" },
  "scanner_desc": { en: "Provide a clear image of the affected leaf.", mr: "प्रभावित पानाचा स्पष्ट फोटो प्रदान करा.", hi: "प्रभावित पत्ती की स्पष्ट तस्वीर प्रदान करें।" },
  "lbl_select_crop_optional": { en: "Select Crop", mr: "पीक निवडा", hi: "फसल चुनें" },
  "lbl_optional": { en: "(Optional)", mr: "(पर्यायी)", hi: "(वैकल्पिक)" },
  "opt_select_crop": { en: "Select Crop", mr: "पीक निवडा", hi: "फसल चुनें" },
  "opt_crop_tomato": { en: "Tomato", mr: "टोमॅटो", hi: "टमाटर" },
  "opt_crop_potato": { en: "Potato", mr: "बटाटा", hi: "आलू" },
  "opt_crop_rice": { en: "Rice", mr: "भात / तांदूळ", hi: "चावल / धान" },
  "opt_crop_wheat": { en: "Wheat", mr: "गहू", hi: "गेहूं" },
  "opt_crop_corn": { en: "Corn / Maize", mr: "मका", hi: "मक्का" },
  "opt_crop_apple": { en: "Apple", mr: "सफरचंद", hi: "सेब" },
  "opt_crop_grape": { en: "Grape", mr: "द्राक्ष", hi: "अंगूर" },
  "upload_instruction": { en: "Drag and drop a crop image here or click to browse", mr: "पिकाचा फोटो येथे ड्रॅग आणि ड्रॉप करा किंवा निवडण्यासाठी क्लिक करा", hi: "फसल की तस्वीर यहाँ खींचें या चुनने के लिए क्लिक करें" },
  "upload_hint": { en: "Supports JPG, PNG (Max 5MB)", mr: "JPG, PNG फॉरमॅट स्वीकार्य (कमाल ५MB)", hi: "JPG, PNG प्रारूप समर्थित (अधिकतम ५MB)" },
  "btn_open_camera": { en: "📷 Open Camera", mr: "📷 कॅमेरा उघडा", hi: "📷 कैमरा खोलें" },
  "btn_capture_photo": { en: "📸 Capture Photo", mr: "📸 फोटो काढा", hi: "📸 फ़ोटो खींचें" },
  "btn_retake_photo": { en: "🔄 Retake Photo", mr: "🔄 पुन्हा फोटो घ्या", hi: "🔄 दोबारा फ़ोटो लें" },
  "btn_detect_disease": { en: "🔍 Detect Plant Disease", mr: "🔍 रोगनिदान करा", hi: "🔍 रोग का पता लगाएं" },
  "how_scanner_works_title": { en: "How Disease Detection Works", mr: "रोगनिदान कसे कार्य करते", hi: "रोग निदान कैसे काम करता है" },
  "disease_step1_title": { en: "Take a Clear Photo", mr: "स्पष्ट फोटो काढा", hi: "साफ फ़ोटो लें" },
  "disease_step1_desc": { en: "Focus on the damaged leaf in good lighting.", mr: "चांगल्या प्रकाशात बाधित पानावर लक्ष केंद्रित करा.", hi: "अच्छी रोशनी में प्रभावित पत्ती पर ध्यान केंद्रित करें।" },
  "disease_step2_title": { en: "AI Visual Analysis", mr: "एआय विश्लेषण", hi: "एआई विश्लेषण" },
  "disease_step2_desc": { en: "Our model evaluates visible leaf patterns and spots.", mr: "आमचे मॉडेल पानांवरील दृश्य डाग आणि पॅटर्नचे विश्लेषण करते.", hi: "हमारा मॉडल पत्ती पर दिखाई देने वाले धब्बों और पैटर्न का विश्लेषण करता है।" },
  "disease_step3_title": { en: "Receive Care Guidance", mr: "काळजी मार्गदर्शन मिळवा", hi: "देखभाल मार्गदर्शन प्राप्त करें" },
  "disease_step3_desc": { en: "Get disease details, symptoms, prevention, and safe treatment steps.", mr: "रोगाचे तपशील, लक्षणे, प्रतिबंध आणि सुरक्षित उपचारांच्या पायऱ्या मिळवा.", hi: "रोग का विवरण, लक्षण, रोकथाम और सुरक्षित उपचार के चरण प्राप्त करें।" },

  // Crop Recommendation Page (crop.html)
  "crop_rec_badge": { en: "SMART AGRICULTURE", mr: "स्मार्ट शेती", hi: "स्मार्ट कृषि" },
  "crop_rec_title_main": { en: "Crop Recommendation", mr: "पीक शिफारस", hi: "फसल सिफारिश" },
  "crop_rec_title_sub": { en: "for Your Soil", mr: "तुमच्या मातीसाठी", hi: "आपकी मिट्टी के लिए" },
  "crop_rec_desc": { en: "Make smarter farming decisions using soil, weather and agricultural data.", mr: "माती, हवामान आणि कृषी डेटाचा वापर करून हुशारीने शेतीचे निर्णय घ्या.", hi: "मिट्टी, मौसम और कृषि आंकड़ों का उपयोग करके बेहतर कृषि निर्णय लें।" },
  "pill_soil_analysis": { en: "✓ Soil Analysis", mr: "✓ माती परीक्षण", hi: "✓ मिट्टी विश्लेषण" },
  "pill_smart_rec": { en: "✓ Smart Recommendation", mr: "✓ योग्य शिफारस", hi: "✓ सटीक सिफारिश" },
  "pill_data_driven": { en: "✓ Data Driven", mr: "✓ डेटा-आधारित", hi: "✓ डेटा-संचालित" },
  "crop_form_title": { en: "Soil & Environmental Data", mr: "माती आणि पर्यावरण डेटा", hi: "मिट्टी और पर्यावरण डेटा" },
  "crop_form_desc": { en: "Provide accurate field conditions for a smarter crop recommendation.", mr: "अचूक पीक शिफारसीसाठी शेतातील योग्य परिस्थिती प्रविष्ट करा.", hi: "सटीक फसल सिफारिश के लिए खेत की सही स्थिति दर्ज करें।" },
  "step_nutrients": { en: "Soil Nutrients", mr: "मातीतील पोषक घटक", hi: "मिट्टी के पोषक तत्व" },
  "step_nutrients_desc": { en: "Enter the nutrient levels available in your soil.", mr: "तुमच्या मातीत उपलब्ध पोषक घटकांची पातळी प्रविष्ट करा.", hi: "अपनी मिट्टी में उपलब्ध पोषक तत्वों का स्तर दर्ज करें।" },
  "lbl_nitrogen": { en: "Nitrogen (N)", mr: "नायट्रोजन (N)", hi: "नाइट्रोजन (N)" },
  "lbl_phosphorus": { en: "Phosphorus (P)", mr: "फॉस्फरस (P)", hi: "फॉस्फोरस (P)" },
  "lbl_potassium": { en: "Potassium (K)", mr: "पोटॅशियम (K)", hi: "पोटेशियम (K)" },
  "step_climate": { en: "Climate Conditions", mr: "हवामान स्थिती", hi: "जलवायु स्थिति" },
  "step_climate_desc": { en: "Enter temperature, humidity, and rainfall.", mr: "तापमान, आर्द्रता आणि पाऊस प्रविष्ट करा.", hi: "तापमान, नमी और बारिश दर्ज करें।" },
  "lbl_crop_temp": { en: "Temperature (°C)", mr: "तापमान (°C)", hi: "तापमान (°C)" },
  "lbl_crop_humidity": { en: "Humidity (%)", mr: "आर्द्रता (%)", hi: "नमी (%)" },
  "lbl_crop_ph": { en: "Soil pH", mr: "मातीचा सामू (pH)", hi: "मिट्टी का पीएच (pH)" },
  "lbl_crop_rainfall": { en: "Rainfall (mm)", mr: "पाऊस (मिमी)", hi: "बारिश (मिमी)" },
  "btn_recommend_crop": { en: "🌱 Get Crop Recommendation", mr: "🌱 योग्य पीक शिफारस मिळवा", hi: "🌱 उपयुक्त फसल सिफारिश प्राप्त करें" },

  // Weather Page (weather.html)
  "weather_hero_title": { en: "Weather Information", mr: "हवामान माहिती", hi: "मौसम की जानकारी" },
  "weather_hero_desc": { en: "Check weather conditions and make better farming decisions.", mr: "हवामानाची स्थिती तपासा आणि शेतीचे चांगले निर्णय घ्या.", hi: "मौसम की स्थिति देखें और बेहतर कृषि निर्णय लें।" },
  "lbl_search_location": { en: "📍 Search Location", mr: "📍 स्थान शोधा", hi: "📍 स्थान खोजें" },
  "ph_search_city": { en: "Enter city or district (e.g. Pune, Nashik)", mr: "शहर किंवा जिल्हा प्रविष्ट करा (उदा. पुणे, नाशिक)", hi: "शहर या जिला दर्ज करें (उदा. पुणे, नासिक)" },
  "btn_search_weather": { en: "Search Weather", mr: "हवामान शोधा", hi: "मौसम खोजें" },
  "forecast_title": { en: "5-Day Forecast", mr: "५ दिवसांचा हवामान अंदाज", hi: "५ दिनों का मौसम पूर्वानुमान" },
  "weather_humidity": { en: "Humidity", mr: "आर्द्रता", hi: "नमी" },
  "weather_wind": { en: "Wind Speed", mr: "वाऱ्याचा वेग", hi: "हवा की गति" },
  "weather_rain": { en: "Rainfall", mr: "पाऊस", hi: "बारिश" },
  "weather_pressure": { en: "Pressure", mr: "हवेचा दाब", hi: "हवा का दबाव" },
  "weather_advisory_title": { en: "Agricultural Advisory", mr: "कृषी हवामान सल्ला", hi: "कृषि मौसम सलाह" },

  // Irrigation Options (irrigation.html)
  "opt_crop_cotton": { en: "Cotton", mr: "कापूस", hi: "कपास" },
  "opt_crop_sugarcane": { en: "Sugarcane", mr: "ऊस", hi: "गन्ना" },
  "opt_crop_soybean": { en: "Soybean", mr: "सोयाबीन", hi: "सोयाबीन" },
  "opt_loc_maharashtra": { en: "Maharashtra", mr: "महाराष्ट्र", hi: "महाराष्ट्र" },
  "opt_loc_karnataka": { en: "Karnataka", mr: "कर्नाटक", hi: "कर्नाटक" },
  "opt_loc_goa": { en: "Goa", mr: "गोवा", hi: "गोवा" },
  "opt_loc_gujarat": { en: "Gujarat", mr: "गुजरात", hi: "गुजरात" },
  "opt_loc_mp": { en: "Madhya Pradesh", mr: "मध्य प्रदेश", hi: "मध्य प्रदेश" },
  "opt_loc_other": { en: "Other", mr: "इतर", hi: "अन्य" },
  "sync_iot_btn": { en: "📡 Use Live IoT Sensor Moisture", mr: "📡 थेट IoT सेन्सर ओलावा वापरा", hi: "📡 लाइव IoT सेंसर नमी का उपयोग करें" },

  // Modals & Forms in farmer.html
  "modal_add_farm_title": { en: "Add New Farm", mr: "नवीन शेत जोडा", hi: "नया खेत जोड़ें" },
  "modal_edit_farm_title": { en: "Edit Farm", mr: "शेत संपादित करा", hi: "खेत संपादित करें" },
  "lbl_farm_name": { en: "Farm Name", mr: "शेताचे नाव", hi: "खेत का नाम" },
  "ph_farm_name": { en: "e.g. North Orchard", mr: "उदा. उत्तर वावर", hi: "उदा. उत्तर बाग" },
  "lbl_farm_location": { en: "Location / Village", mr: "स्थान / गाव", hi: "स्थान / गाँव" },
  "ph_farm_location": { en: "e.g. Pune, Maharashtra", mr: "उदा. पुणे, महाराष्ट्र", hi: "उदा. पुणे, महाराष्ट्र" },
  "lbl_farm_area": { en: "Total Area", mr: "एकूण क्षेत्र", hi: "कुल क्षेत्रफल" },
  "lbl_area_unit": { en: "Area Unit", mr: "क्षेत्राचे एकक", hi: "क्षेत्रफल इकाई" },
  "unit_acre": { en: "Acre", mr: "एकर", hi: "एकड़" },
  "unit_hectare": { en: "Hectare", mr: "हेक्टर", hi: "हेक्टेयर" },
  "modal_add_crop_title": { en: "Register New Crop", mr: "नवीन पीक नोंदवा", hi: "नई फसल दर्ज करें" },
  "modal_edit_crop_title": { en: "Edit Crop", mr: "पीक संपादित करा", hi: "फसल संपादित करें" },
  "lbl_select_farm": { en: "Select Farm", mr: "शेत निवडा", hi: "खेत चुनें" },
  "lbl_crop_name": { en: "Crop Name", mr: "पिकाचे नाव", hi: "फसल का नाम" },
  "lbl_variety": { en: "Variety (Optional)", mr: "वाण (पर्यायी)", hi: "किस्म (वैकल्पिक)" },
  "lbl_planting_date": { en: "Planting Date", mr: "लागवडीची तारीख", hi: "बुवाई की तारीख" },
  "lbl_harvest_date": { en: "Expected Harvest Date", mr: "अपेक्षित काढणी तारीख", hi: "अपेक्षित कटाई तारीख" },
  "lbl_cultivated_area": { en: "Cultivated Area", mr: "लागवड क्षेत्र", hi: "बोया गया क्षेत्रफल" },
  "lbl_growth_status": { en: "Growth Status", mr: "वाढीची स्थिती", hi: "वृद्धि की स्थिति" },
  "lbl_notes": { en: "Field Notes (Optional)", mr: "शेतातील नोंदी (पर्यायी)", hi: "खेत के नोट्स (वैकल्पिक)" },
  "btn_save": { en: "Save", mr: "जतन करा", hi: "सुरक्षित करें" },
  "btn_cancel": { en: "Cancel", mr: "रद्द करा", hi: "रद्द करें" },
  "btn_delete": { en: "Delete", mr: "हटवा", hi: "हटाएं" },
  "btn_edit": { en: "Edit", mr: "संपादित करा", hi: "संपादित करें" },

  // Chatbot UI
  "assistant_heading": { en: "Farmer Assistant", mr: "शेतकरी सहाय्यक", hi: "किसान सहायक" },
  "assistant_subtitle": { en: "Ask farming-related questions and get practical guidance.", mr: "शेतीविषयक प्रश्न विचारा आणि उपयुक्त मार्गदर्शन मिळवा.", hi: "खेती से जुड़े प्रश्न पूछें और व्यावहारिक मार्गदर्शन प्राप्त करें।" },
  "assistant_welcome_msg": { en: "Hello! I am your AgriSmart farming assistant. Ask me about your crops, irrigation advice, disease symptoms, or weather.", mr: "नमस्कार! मी तुमचा AgriSmart शेती सहाय्यक आहे. तुमच्या पिकांबद्दल, सिंचनाबद्दल, रोगांच्या लक्षणांबद्दल किंवा हवामानाबद्दल विचारा.", hi: "नमस्ते! मैं आपका AgriSmart खेती सहायक हूँ। अपनी फसलों, सिंचाई सलाह, रोग लक्षणों या मौसम के बारे में पूछें।" },
  "btn_clear_chat": { en: "🗑️ Clear Chat", mr: "🗑️ चॅट साफ करा", hi: "🗑️ चैट साफ़ करें" },
  "chat_input_placeholder": { en: "Ask a farming question...", mr: "शेतीविषयक प्रश्न विचारा...", hi: "खेती से जुड़ा प्रश्न पूछें..." },
  "chat_send_btn": { en: "Send", mr: "पाठवा", hi: "भेजें" },
  "chat_voice_btn": { en: "🎤 Voice", mr: "🎤 आवाज", hi: "🎤 आवाज़" },

  // Confirmations & Dialogs
  "confirm_logout": { en: "Are you sure you want to logout?", mr: "तुम्हाला नक्की लॉगआउट करायचे आहे का?", hi: "क्या आप वाकई लॉगआउट करना चाहते हैं?" },
  "confirm_clear_chat": { en: "Are you sure you want to clear your chat history?", mr: "तुम्हाला नक्की चॅट इतिहास साफ करायचा आहे का?", hi: "क्या आप वाकई चैट इतिहास साफ़ करना चाहते हैं?" },
  "confirm_delete_farm": { en: "Are you sure you want to delete this farm?", mr: "तुम्हाला हे शेत नक्की हटवायचे आहे का?", hi: "क्या आप वाकई इस खेत को हटाना चाहते हैं?" },
  "confirm_delete_crop": { en: "Are you sure you want to delete this crop?", mr: "तुम्हाला हे पीक नक्की हटवायचे आहे का?", hi: "क्या आप वाकई इस फसल को हटाना चाहते हैं?" },
  "confirm_delete_sensor": { en: "Are you sure you want to delete this sensor?", mr: "तुम्हाला हा सेन्सर नक्की हटवायचा आहे का?", hi: "क्या आप वाकई इस सेंसर को हटाना चाहते हैं?" },
  "confirm_clear_notifications": { en: "Are you sure you want to clear all notifications?", mr: "तुम्हाला सर्व सूचना नक्की हटवायच्या आहेत का?", hi: "क्या आप वाकई सभी सूचनाएं हटाना चाहते हैं?" },
  "confirm_clear_history": { en: "Are you sure you want to clear your diagnosis history?", mr: "तुम्हाला नक्की निदान इतिहास साफ करायचा आहे का?", hi: "क्या आप वाकई निदान इतिहास साफ़ करना चाहते हैं?" },

  // Relative Time Labels
  "time_just_now": { en: "just now", mr: "आत्ताच", hi: "अभी-अभी" },
  "time_minutes_ago": { en: "minutes ago", mr: "मिनिटांपूर्वी", hi: "मिनट पहले" },
  "time_hours_ago": { en: "hours ago", mr: "तासांपूर्वी", hi: "घंटे पहले" },
  "time_yesterday": { en: "Yesterday", mr: "काल", hi: "कल" },
  "time_days_ago": { en: "days ago", mr: "दिवसांपूर्वी", hi: "दिन पहले" }
};

// Merge into dictionaries
const mergedEn = Object.assign({}, existingEn);
const mergedMr = Object.assign({}, existingMr);
const mergedHi = Object.assign({}, existingHi);

for (const [key, val] of Object.entries(newTranslations)) {
  mergedEn[key] = val.en;
  mergedMr[key] = val.mr;
  mergedHi[key] = val.hi;
}

console.log("Total En keys:", Object.keys(mergedEn).length);
console.log("Total Mr keys:", Object.keys(mergedMr).length);
console.log("Total Hi keys:", Object.keys(mergedHi).length);

// Generate updated i18n.js
const out = `// i18n.js - client-side internationalization
// Supports English (en), Marathi (mr) and Hindi (hi)
const translations = {
  en: ${JSON.stringify(mergedEn, null, 2)},
  mr: ${JSON.stringify(mergedMr, null, 2)},
  hi: ${JSON.stringify(mergedHi, null, 2)}
};

function getCurrentLang() {
  return localStorage.getItem('lang') || 'en';
}

function setCurrentLang(lang) {
  if (!['en', 'mr', 'hi'].includes(lang)) {
    lang = 'en';
  }
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;

  // Persist preference to database if farmer is logged in
  const token = localStorage.getItem('agriSmartToken') || localStorage.getItem('token');
  if (token) {
    fetch('/api/auth/preferred-language', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token,
        'X-Language': lang
      },
      body: JSON.stringify({ preferred_language: lang })
    }).catch(err => {
      // Non-blocking background sync
    });
  }
}

function t(key) {
  const lang = getCurrentLang();
  return (translations[lang] && translations[lang][key]) ||
         (translations['en'] && translations['en'][key]) ||
         key;
}

function formatNumber(num, lang = getCurrentLang()) {
  if (num === null || num === undefined || isNaN(num)) return '--';
  try {
    const localeMap = { en: 'en-IN', mr: 'mr-IN', hi: 'hi-IN' };
    return new Intl.NumberFormat(localeMap[lang] || 'en-IN').format(num);
  } catch (e) {
    return String(num);
  }
}

function formatDate(dateInput, lang = getCurrentLang()) {
  if (!dateInput) return '--';
  try {
    const d = new Date(dateInput);
    if (isNaN(d.getTime())) return String(dateInput);
    const localeMap = { en: 'en-IN', mr: 'mr-IN', hi: 'hi-IN' };
    return new Intl.DateTimeFormat(localeMap[lang] || 'en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(d);
  } catch (e) {
    return String(dateInput);
  }
}

function formatRelativeTime(dateInput, lang = getCurrentLang()) {
  if (!dateInput) return '--';
  try {
    const d = new Date(dateInput);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diffSec < 60) {
      return t('time_just_now');
    }
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) {
      return diffMin + ' ' + t('time_minutes_ago');
    }
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) {
      return diffHours + ' ' + t('time_hours_ago');
    }
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) {
      return t('time_yesterday');
    }
    if (diffDays < 7) {
      return diffDays + ' ' + t('time_days_ago');
    }
    return formatDate(d, lang);
  } catch (e) {
    return String(dateInput);
  }
}

function applyTranslations(container = document) {
  const elements = container.querySelectorAll('[data-i18n]');
  elements.forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  });
  const htmlElements = container.querySelectorAll('[data-i18n-html]');
  htmlElements.forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    el.innerHTML = t(key);
  });
  const placeholders = container.querySelectorAll('[data-i18n-placeholder]');
  placeholders.forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.setAttribute('placeholder', t(key));
  });
  const titles = container.querySelectorAll('[data-i18n-title]');
  titles.forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    el.setAttribute('title', t(key));
  });
  const ariaLabels = container.querySelectorAll('[data-i18n-aria-label]');
  ariaLabels.forEach(el => {
    const key = el.getAttribute('data-i18n-aria-label');
    el.setAttribute('aria-label', t(key));
  });

  const sel = document.getElementById('lang-select');
  if (sel) {
    sel.value = getCurrentLang();
    if (!sel.dataset.listenerAttached) {
      sel.dataset.listenerAttached = 'true';
      sel.addEventListener('change', e => {
        setCurrentLang(e.target.value);
        applyTranslations();
        // Dispatch custom event so dynamic modules can re-render immediately
        window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: e.target.value } }));
      });
    }
  }
}

window.i18n = {
  t,
  setLang: setCurrentLang,
  applyTranslations,
  getLang: getCurrentLang,
  formatNumber,
  formatDate,
  formatRelativeTime
};

document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
});
`;

fs.writeFileSync('js/i18n.js', out);
console.log('Successfully wrote expanded js/i18n.js');
