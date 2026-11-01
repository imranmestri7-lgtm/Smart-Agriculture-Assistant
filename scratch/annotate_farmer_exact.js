const fs = require('fs');

// 1. Update i18n.js
const currentI18n = fs.readFileSync('js/i18n.js', 'utf8');
const vm = require('vm');
const sandbox = { window: {}, document: { querySelectorAll: () => [], getElementById: () => null, addEventListener: () => {} }, localStorage: { getItem: () => "en", setItem: () => {} } };
vm.createContext(sandbox);
vm.runInContext(currentI18n.replace('const translations =', 'var translations ='), sandbox);
const en = sandbox.translations.en;
const mr = sandbox.translations.mr;
const hi = sandbox.translations.hi;

const farmerExtra = {
  "card_crops_title": { en: "My Crops", mr: "माझी पिके", hi: "मेरी फसलें" },
  "card_crops_desc": { en: "Add and manage your crops, varieties, planting dates and field information.", mr: "तुमची पिके, वाण, लागवडीची तारीख आणि शेताची माहिती जोडा व व्यवस्थापित करा.", hi: "अपनी फसलें, किस्में, बुवाई की तारीख और खेत की जानकारी जोड़ें व प्रबंधित करें।" },
  "card_crops_link": { en: "Manage Crops →", mr: "पिके व्यवस्थापित करा →", hi: "फसल प्रबंधन करें →" },
  "card_disease_title": { en: "Disease Detection", mr: "रोगनिदान", hi: "रोग निदान" },
  "card_disease_desc": { en: "Upload a plant image and get information about possible crop problems.", mr: "झाडाचा फोटो अपलोड करा आणि संभाव्य रोगांविषयी माहिती मिळवा.", hi: "पौधे की तस्वीर अपलोड करें और संभावित बीमारियों की जानकारी प्राप्त करें।" },
  "card_disease_link": { en: "Check Plant →", mr: "झाड तपासा →", hi: "पौधा जाँचें →" },
  "card_irrigation_title": { en: "Irrigation", mr: "सिंचन", hi: "सिंचाई" },
  "card_irrigation_desc": { en: "Get irrigation guidance and manage your crop water requirements.", mr: "सिंचन मार्गदर्शन मिळवा आणि पिकांच्या पाण्याची गरज व्यवस्थापित करा.", hi: "सिंचाई मार्गदर्शन प्राप्त करें और फसलों की पानी की ज़रूरत को प्रबंधित करें।" },
  "card_irrigation_link": { en: "View Irrigation →", mr: "सिंचन पहा →", hi: "सिंचाई देखें →" },
  "card_weather_title": { en: "Weather", mr: "हवामान", hi: "मौसम" },
  "card_weather_desc": { en: "Check weather information to support better farming decisions.", mr: "शेतीविषयक चांगले निर्णय घेण्यासाठी हवामान माहिती तपासा.", hi: "बेहतर कृषि निर्णयों के लिए मौसम की जानकारी देखें।" },
  "card_weather_link": { en: "Check Weather →", mr: "हवामान पहा →", hi: "मौसम देखें →" },
  "card_assistant_title": { en: "Farmer Assistant", mr: "शेतकरी सहाय्यक", hi: "किसान सहायक" },
  "card_assistant_desc": { en: "Ask questions about crops, pests, irrigation, weather and farming.", mr: "पिके, कीड, सिंचन, हवामान आणि शेतीविषयक प्रश्न विचारा.", hi: "फसलों, कीटों, सिंचाई, मौसम और खेती के बारे में सवाल पूछें।" },
  "card_assistant_link": { en: "Ask Assistant →", mr: "सहाय्यकाला विचारा →", hi: "सहायक से पूछें →" },
  "badge_iot_ready": { en: "IoT Ready", mr: "IoT सज्ज", hi: "IoT सक्षम" },
  "badge_my_farms_crops": { en: "MY FARMS & CROPS", mr: "माझी शेते आणि पिके", hi: "मेरे खेत और फसलें" },
  "lbl_filter_by_farm": { en: "Filter by Farm:", mr: "शेतानुसार फिल्टर करा:", hi: "खेत अनुसार फ़िल्टर करें:" },
  "opt_all_farms": { en: "All Farms", mr: "सर्व शेते", hi: "सभी खेत" },
  "badge_smart_analytics": { en: "SMART ANALYTICS & INSIGHTS", mr: "स्मार्ट विश्लेषण आणि माहिती", hi: "स्मार्ट विश्लेषण और इनसाइट्स" },
  "btn_refresh_data": { en: "🔄 Refresh Data", mr: "🔄 डेटा रिफ्रेश करा", hi: "🔄 डेटा रीफ़्रेश करें" },
  "stat_total_water": { en: "Total Water Usage", mr: "एकूण पाण्याचा वापर", hi: "कुल पानी का उपयोग" },
  "stat_irrigation_needed": { en: "Irrigation Needed", mr: "सिंचनाची गरज", hi: "सिंचाई की आवश्यकता" },
  "stat_sufficient_moisture": { en: "Sufficient Moisture", mr: "पुरेसा ओलावा", hi: "पर्याप्त नमी" },
  "badge_smart_alerts": { en: "SMART ALERTS & REMINDERS", mr: "स्मार्ट सूचना आणि स्मरणपत्रे", hi: "स्मार्ट अलर्ट और रिमाइंडर" },
  "btn_refresh": { en: "🔄 Refresh", mr: "🔄 रिफ्रेश करा", hi: "🔄 रीफ़्रेश करें" },
  "badge_iot_network": { en: "IoT-READY SENSOR NETWORK", mr: "IoT-सज्ज सेन्सर नेटवर्क", hi: "IoT-सक्षम सेंसर नेटवर्क" },
  "title_telemetry_hub": { en: "IoT Telemetry Hub", mr: "IoT टेलीमेट्री केंद्र", hi: "IoT टेलीमेट्री केंद्र" },
  "btn_refresh_telemetry": { en: "Refresh Telemetry", mr: "टेलीमेट्री रिफ्रेश करा", hi: "टेलीमेट्री रीफ़्रेश करें" },
  "telemetry_no_sensor": { en: "No Sensor", mr: "सेन्सर नाही", hi: "सेंसर नहीं" },
  "telemetry_demo_badge": { en: "DEMO", mr: "डेमो", hi: "डेमो" },
  "telemetry_not_assigned": { en: "Not assigned", mr: "नियुक्त केलेले नाही", hi: "असाइन नहीं किया गया" },
  "telemetry_never": { en: "Never", mr: "कधीही नाही", hi: "कभी नहीं" },
  "opt_choose_sensor": { en: "-- Choose a sensor --", mr: "-- सेन्सर निवडा --", hi: "-- सेंसर चुनें --" },
  "filter_24h": { en: "24 Hours", mr: "२४ तास", hi: "२४ घंटे" },
  "filter_7d": { en: "7 Days", mr: "७ दिवस", hi: "७ दिन" },
  "filter_30d": { en: "30 Days", mr: "३० दिवस", hi: "३० दिन" },
  "filter_all": { en: "All", mr: "सर्व", hi: "सभी" },
  "stat_min": { en: "Min:", mr: "किमान:", hi: "न्यूनतम:" },
  "stat_avg": { en: "Avg:", mr: "सरासरी:", hi: "औसत:" },
  "stat_max": { en: "Max:", mr: "कमाल:", hi: "अधिकतम:" },
  "stat_readings": { en: "Readings:", mr: "नोंदी:", hi: "रीडिंग्स:" },
  "th_datetime": { en: "Date & Time", mr: "तारीख आणि वेळ", hi: "तारीख और समय" },
  "th_measurement": { en: "Measurement", mr: "मापन", hi: "माप" },
  "th_status": { en: "Status", mr: "स्थिती", hi: "स्थिति" },
  "th_type": { en: "Type", mr: "प्रकार", hi: "प्रकार" },
  "hw_spec_title": { en: "🔌 ESP32 & Arduino Integration Specifications", mr: "🔌 ESP32 आणि Arduino जोडणी सूचना", hi: "🔌 ESP32 और Arduino एकीकरण विनिर्देश" },
  "hw_spec_desc": { en: "Hardware microcontrollers can transmit telemetry directly to AgriSmart using the secure device API key.", mr: "हार्डवेअर मायक्रोकंट्रोलर्स सुरक्षित डिव्हाइस की वापरून थेट AgriSmart ला माहिती पाठवू शकतात.", hi: "हार्डवेयर माइक्रोकंट्रोलर सुरक्षित डिवाइस कुंजी का उपयोग करके सीधे AgriSmart पर डेटा भेज सकते हैं।" },
  "hw_endpoint_label": { en: "Endpoint:", mr: "एंडपॉइंट:", hi: "एंडपॉइंट:" },
  "hw_headers_label": { en: "Headers:", mr: "हेडर्स:", hi: "हेडर्स:" },
  "hw_sample_payload": { en: "Sample Soil Moisture JSON Payload:", mr: "मातीतील ओलावा नमुना JSON डेटा:", hi: "मिट्टी की नमी का नमूना JSON डेटा:" },
  "hw_sample_dht22": { en: "Sample Combined DHT22 Payload:", mr: "एकत्रित DHT22 नमुना डेटा:", hi: "संयुक्त DHT22 नमूना डेटा:" },
  "assistant_tag": { en: "AGRICULTURE ASSISTANT", mr: "कृषी सहाय्यक", hi: "कृषि सहायक" },
  "msg_think": { en: "Think", mr: "विचार करा", hi: "सोचें" },
  "btn_upload_leaf": { en: "🍃 Upload Leaf Image", mr: "🍃 पानाचा फोटो अपलोड करा", hi: "🍃 पत्ती की तस्वीर अपलोड करें" },
  "btn_upload_file": { en: "📎 Upload File", mr: "📎 फाइल जोडा", hi: "📎 फ़ाइल जोड़ें" },
  "prefs_desc": { en: "Choose which categories of smart agricultural alerts and reminders you want to receive on your dashboard.", mr: "तुम्हाला तुमच्या डॅशबोर्डवर कोणत्या प्रकारच्या कृषी सूचना आणि स्मरणपत्रे हवी आहेत ते निवडा.", hi: "चुनें कि आप अपने डैशबोर्ड पर किस प्रकार के कृषि अलर्ट और रिमाइंडर प्राप्त करना चाहते हैं।" },
  "prefs_crop_desc": { en: "Harvest readiness, growth stage care, and crop record updates.", mr: "काढणीची तयारी, वाढीच्या टप्प्यातील काळजी आणि पीक अद्यतने.", hi: "कटाई की तैयारी, विकास चरण की देखभाल और फसल रिकॉर्ड अपडेट।" },
  "prefs_irrigation_desc": { en: "Soil moisture deficit warnings and water recommendations.", mr: "मातीतील पाण्याचा ताण आणि सिंचन शिफारसी.", hi: "मिट्टी में पानी की कमी और सिंचाई सिफारिशें।" },
  "prefs_weather_desc": { en: "Heavy rain advisories and high temperature warnings.", mr: "मुसळधार पाऊस आणि अति उच्च तापमानाचा इशारा.", hi: "भारी बारिश की सलाह और उच्च तापमान की चेतावनी।" },
  "prefs_disease_desc": { en: "Diagnosis follow-ups, field sanitation, and inspection advice.", mr: "रोगनिदान पाठपुरावा, शेताची स्वच्छता आणि पाहणी सल्ला.", hi: "रोग निदान फॉलो-अप, खेत की स्वच्छता और निरीक्षण सलाह।" },
  "opt_choose_farm": { en: "-- Choose Farm --", mr: "-- शेत निवडा --", hi: "-- खेत चुनें --" },
  "opt_loading_farms": { en: "Loading farms...", mr: "शेते लोड करत आहे...", hi: "खेत लोड हो रहे हैं..." },
  "lbl_assigned_crop": { en: "🌾 Assigned Crop (Optional)", mr: "🌾 संबंधित पीक (पर्यायी)", hi: "🌾 संबंधित फसल (वैकल्पिक)" },
  "opt_optional_assign_crop": { en: "-- Optional: Assign Crop --", mr: "-- पर्यायी: पीक जोडा --", hi: "-- वैकल्पिक: फसल जोड़ें --" },
  "opt_sensor_soil_moisture": { en: "💧 Soil Moisture Sensor (%)", mr: "💧 मातीतील ओलावा सेन्सर (%)", hi: "💧 मिट्टी की नमी सेंसर (%)" },
  "opt_sensor_dht22": { en: "🌡️ Air Temp & Humidity (DHT22 / SHT30)", mr: "🌡️ हवेचे तापमान आणि आर्द्रता (DHT22)", hi: "🌡️ हवा का तापमान और नमी (DHT22)" },
  "opt_sensor_soil_temp": { en: "🌱 Soil Temperature (°C)", mr: "🌱 मातीचे तापमान (°C)", hi: "🌱 मिट्टी का तापमान (°C)" },
  "opt_sensor_water_level": { en: "🚰 Water Level Sensor (%)", mr: "🚰 पाण्याची पातळी सेन्सर (%)", hi: "🚰 जल स्तर सेंसर (%)" },
  "sensor_id_hint": { en: "Must be unique across your hardware devices (letters, digits, dashes).", mr: "तुमच्या सर्व डिव्हाइसेसमध्ये हा आयडी एकमेव असावा (अक्षरे, अंक, डॅश).", hi: "आपके सभी उपकरणों में यह आईडी अद्वितीय होना चाहिए (अक्षर, अंक, डैश)।" },
  "modal_credentials_title": { en: "🔑 Device Credentials Generated", mr: "🔑 डिव्हाइस क्रेडेंशियल्स तयार झाली", hi: "🔑 डिवाइस क्रेडेंशियल्स उत्पन्न हुई" },
  "security_notice_title": { en: "⚠️ Important Security Notice:", mr: "⚠️ महत्त्वाची सुरक्षा सूचना:", hi: "⚠️ महत्वपूर्ण सुरक्षा सूचना:" },
  "lbl_device_id": { en: "Device ID:", mr: "डिव्हाइस आयडी:", hi: "डिवाइस आईडी:" },
  "lbl_secret_key": { en: "Secret Device API Key:", mr: "गुप्त डिव्हाइस API की:", hi: "गुप्त डिवाइस API कुंजी:" },
  "btn_copy": { en: "📋 Copy", mr: "📋 कॉपी करा", hi: "📋 कॉपी करें" },
  "btn_saved_key": { en: "I Have Saved This Key", mr: "मी ही की सुरक्षित ठेवली आहे", hi: "मैंने यह कुंजी सुरक्षित कर ली है" },
  "modal_demo_title": { en: "🧪 Manual IoT Demo Mode", mr: "🧪 मॅन्युअल IoT डेमो मोड", hi: "🧪 मैन्युअल IoT डेमो मोड" },
  "demo_data_badge": { en: "[Demo Data]", mr: "[डेमो डेटा]", hi: "[डेमो डेटा]" },
  "btn_clear_demo": { en: "🗑️ Clear Demo Data", mr: "🗑️ डेमो डेटा साफ करा", hi: "🗑️ डेमो डेटा साफ़ करें" },
  "btn_inject_reading": { en: "Inject Reading", mr: "रिडिंग जोडा", hi: "रीडिंग जोड़ें" }
};

for (const [k, v] of Object.entries(farmerExtra)) {
  en[k] = v.en;
  mr[k] = v.mr;
  hi[k] = v.hi;
}

const updatedI18n = currentI18n
  .replace(/en:\s*\{[\s\S]*?\n\s*\},?\s*mr:/, 'en: ' + JSON.stringify(en, null, 2) + ',\nmr:')
  .replace(/mr:\s*\{[\s\S]*?\n\s*\},?\s*hi:/, 'mr: ' + JSON.stringify(mr, null, 2) + ',\nhi:')
  .replace(/hi:\s*\{[\s\S]*?\n\s*\}/, 'hi: ' + JSON.stringify(hi, null, 2));
fs.writeFileSync('js/i18n.js', updatedI18n);

// 2. Update farmer.html
let html = fs.readFileSync('farmer.html', 'utf8');

const reps = [
  [/<span class="user-greeting">\s*Welcome, Farmer\s*<\/span>/, '<span class="user-greeting" data-i18n="welcome_farmer">\n            Welcome, Farmer\n        </span>'],
  [/<span class="farmer-badge">\s*Farmer\s*<\/span>/, '<span class="farmer-badge" data-i18n="farmer_role">Farmer</span>'],
  [/<button class="logout-btn" id="logoutButton">\s*Logout\s*<\/button>/, '<button class="logout-btn" id="logoutButton" data-i18n="logout">Logout</button>'],
  [/<span class="dashboard-badge">\s*FARMER DASHBOARD\s*<\/span>/, '<span class="dashboard-badge" data-i18n="farmer_dashboard_badge">\n                    FARMER DASHBOARD\n                </span>'],
  [/<p>\s*Manage your crops, check farming information,\s*and get guidance from your farming assistant\.\s*<\/p>/, '<p data-i18n="farmer_dashboard_desc">\n                    Manage your crops, check farming information,\n                    and get guidance from your farming assistant.\n                </p>'],
  [/<span class="section-tag">\s*FARMING TOOLS\s*<\/span>/, '<span class="section-tag" data-i18n="farming_tools_badge">\n                    FARMING TOOLS\n                </span>'],
  [/<h2>\s*What would you like to do\?\s*<\/h2>/, '<h2 data-i18n="farming_tools_heading">\n                    What would you like to do?\n                </h2>'],
  [/<h3>\s*My Crops\s*<\/h3>/, '<h3 data-i18n="card_crops_title">My Crops</h3>'],
  [/<p>\s*Add and manage your crops, varieties,\s*planting dates and field information\.\s*<\/p>/, '<p data-i18n="card_crops_desc">\n                            Add and manage your crops, varieties,\n                            planting dates and field information.\n                        </p>'],
  [/<span class="card-link">\s*Manage Crops →\s*<\/span>/, '<span class="card-link" data-i18n="card_crops_link">\n                            Manage Crops →\n                        </span>'],
  [/<h3>\s*Disease Detection\s*<\/h3>/, '<h3 data-i18n="card_disease_title">Disease Detection</h3>'],
  [/<p>\s*Upload a plant image and get information\s*about possible crop problems\.\s*<\/p>/, '<p data-i18n="card_disease_desc">\n                            Upload a plant image and get information\n                            about possible crop problems.\n                        </p>'],
  [/<span class="card-link">\s*Check Plant →\s*<\/span>/, '<span class="card-link" data-i18n="card_disease_link">\n                            Check Plant →\n                        </span>'],
  [/<h3>\s*Irrigation\s*<\/h3>/, '<h3 data-i18n="card_irrigation_title">Irrigation</h3>'],
  [/<p>\s*Get irrigation guidance and manage\s*your crop water requirements\.\s*<\/p>/, '<p data-i18n="card_irrigation_desc">\n                            Get irrigation guidance and manage\n                            your crop water requirements.\n                        </p>'],
  [/<span class="card-link">\s*View Irrigation →\s*<\/span>/, '<span class="card-link" data-i18n="card_irrigation_link">\n                            View Irrigation →\n                        </span>'],
  [/<h3>\s*Weather\s*<\/h3>/, '<h3 data-i18n="card_weather_title">Weather</h3>'],
  [/<p>\s*Check weather information to support\s*better farming decisions\.\s*<\/p>/, '<p data-i18n="card_weather_desc">\n                            Check weather information to support\n                            better farming decisions.\n                        </p>'],
  [/<span class="card-link">\s*Check Weather →\s*<\/span>/, '<span class="card-link" data-i18n="card_weather_link">\n                            Check Weather →\n                        </span>'],
  [/<span class="card-pill">\s*IoT Ready\s*<\/span>/, '<span class="card-pill" data-i18n="badge_iot_ready">IoT Ready</span>'],
  [/<h3>\s*Farmer Assistant\s*<\/h3>/, '<h3 data-i18n="card_assistant_title">Farmer Assistant</h3>'],
  [/<p>\s*Ask questions about crops, pests,\s*irrigation, weather and farming\.\s*<\/p>/, '<p data-i18n="card_assistant_desc">\n                            Ask questions about crops, pests,\n                            irrigation, weather and farming.\n                        </p>'],
  [/<span class="card-link">\s*Ask Assistant →\s*<\/span>/, '<span class="card-link" data-i18n="card_assistant_link">\n                            Ask Assistant →\n                        </span>'],
  [/<span class="section-tag">\s*MY FARMS &amp; CROPS\s*<\/span>/, '<span class="section-tag" data-i18n="badge_my_farms_crops">MY FARMS &amp; CROPS</span>'],
  [/<label for="farmFilterSelect">Filter by Farm:<\/label>/, '<label for="farmFilterSelect" data-i18n="lbl_filter_by_farm">Filter by Farm:</label>'],
  [/<option value="">All Farms<\/option>/, '<option value="" data-i18n="opt_all_farms">All Farms</option>'],
  [/<span class="section-tag">\s*SMART ANALYTICS &amp; INSIGHTS\s*<\/span>/, '<span class="section-tag" data-i18n="badge_smart_analytics">SMART ANALYTICS &amp; INSIGHTS</span>'],
  [/<button id="refreshAnalyticsBtn" class="btn-farm-action btn-refresh"[^>]*>\s*🔄 Refresh Data\s*<\/button>/, '<button id="refreshAnalyticsBtn" class="btn-farm-action btn-refresh" type="button" style="background:#ecfdf5; color:#059669; border:1px solid #a7f3d0;" data-i18n="btn_refresh_data">🔄 Refresh Data</button>'],
  [/<span class="summary-label">Total Water Usage<\/span>/, '<span class="summary-label" data-i18n="stat_total_water">Total Water Usage</span>'],
  [/<span class="summary-label">Irrigation Needed<\/span>/, '<span class="summary-label" data-i18n="stat_irrigation_needed">Irrigation Needed</span>'],
  [/<span class="summary-label">Sufficient Moisture<\/span>/, '<span class="summary-label" data-i18n="stat_sufficient_moisture">Sufficient Moisture</span>'],
  [/<span class="section-tag">\s*SMART ALERTS &amp; REMINDERS\s*<\/span>/, '<span class="section-tag" data-i18n="badge_smart_alerts">SMART ALERTS &amp; REMINDERS</span>'],
  [/<button id="refreshNotificationsBtn" class="btn-farm-action btn-refresh"[^>]*>\s*🔄 Refresh\s*<\/button>/, '<button id="refreshNotificationsBtn" class="btn-farm-action btn-refresh" type="button" style="background:#ecfdf5; color:#059669; border:1px solid #a7f3d0;" data-i18n="btn_refresh">🔄 Refresh</button>'],
  [/<span class="section-tag">\s*IoT-READY SENSOR NETWORK\s*<\/span>/, '<span class="section-tag" data-i18n="badge_iot_network">IoT-READY SENSOR NETWORK</span>'],
  [/<strong>IoT Telemetry Hub<\/strong>/, '<strong data-i18n="title_telemetry_hub">IoT Telemetry Hub</strong>'],
  [/<span>Refresh Telemetry<\/span>/, '<span data-i18n="btn_refresh_telemetry">Refresh Telemetry</span>'],
  [/<option value="">-- Choose a sensor --<\/option>/, '<option value="" data-i18n="opt_choose_sensor">-- Choose a sensor --</option>'],
  [/<button type="button" class="btn-range active" data-range="24h">24 Hours<\/button>/, '<button type="button" class="btn-range active" data-range="24h" data-i18n="filter_24h">24 Hours</button>'],
  [/<button type="button" class="btn-range" data-range="7d">7 Days<\/button>/, '<button type="button" class="btn-range" data-range="7d" data-i18n="filter_7d">7 Days</button>'],
  [/<button type="button" class="btn-range" data-range="30d">30 Days<\/button>/, '<button type="button" class="btn-range" data-range="30d" data-i18n="filter_30d">30 Days</button>'],
  [/<button type="button" class="btn-range" data-range="all">All<\/button>/, '<button type="button" class="btn-range" data-range="all" data-i18n="filter_all">All</button>'],
  [/<th>Date &amp; Time<\/th>/, '<th data-i18n="th_datetime">Date &amp; Time</th>'],
  [/<th>Measurement<\/th>/, '<th data-i18n="th_measurement">Measurement</th>'],
  [/<th>Status<\/th>/, '<th data-i18n="th_status">Status</th>'],
  [/<th>Type<\/th>/, '<th data-i18n="th_type">Type</th>'],
  [/<h3>🔌 ESP32 &amp; Arduino Integration Specifications<\/h3>/, '<h3 data-i18n="hw_spec_title">🔌 ESP32 &amp; Arduino Integration Specifications</h3>'],
  [/<span class="assistant-tag">\s*AGRICULTURE ASSISTANT\s*<\/span>/, '<span class="assistant-tag" data-i18n="assistant_tag">\n                        AGRICULTURE ASSISTANT\n                    </span>'],
  [/<button type="button" class="btn-chat-attach" id="btnUploadLeaf"[^>]*>\s*🍃 Upload Leaf Image\s*<\/button>/, '<button type="button" class="btn-chat-attach" id="btnUploadLeaf" style="font-size:12px; padding:6px 12px; border-radius:18px; border:1px solid #86efac; background:#f0fdf4; color:#15803d; cursor:pointer;" data-i18n="btn_upload_leaf">🍃 Upload Leaf Image</button>'],
  [/<button type="button" class="btn-chat-attach" id="btnUploadFile"[^>]*>\s*📎 Upload File\s*<\/button>/, '<button type="button" class="btn-chat-attach" id="btnUploadFile" style="font-size:12px; padding:6px 12px; border-radius:18px; border:1px solid #cbd5e1; background:#f8fafc; color:#334155; cursor:pointer;" data-i18n="btn_upload_file">📎 Upload File</button>'],
  [/<button type="button" class="btn-chat-attach" id="btnUseCamera"[^>]*>\s*📷 Use Camera\s*<\/button>/, '<button type="button" class="btn-chat-attach" id="btnUseCamera" style="font-size:12px; padding:6px 12px; border-radius:18px; border:1px solid #cbd5e1; background:#f8fafc; color:#334155; cursor:pointer;" data-i18n="btn_use_camera">📷 Use Camera</button>'],
  [/<option value="">-- Choose Farm --<\/option>/, '<option value="" data-i18n="opt_choose_farm">-- Choose Farm --</option>'],
  [/<label for="sensorCropId">🌾 Assigned Crop \(Optional\)<\/label>/, '<label for="sensorCropId" data-i18n="lbl_assigned_crop">🌾 Assigned Crop (Optional)</label>'],
  [/<option value="">-- Optional: Assign Crop --<\/option>/, '<option value="" data-i18n="opt_optional_assign_crop">-- Optional: Assign Crop --</option>'],
  [/<option value="soil_moisture">💧 Soil Moisture Sensor \(%\)<\/option>/, '<option value="soil_moisture" data-i18n="opt_sensor_soil_moisture">💧 Soil Moisture Sensor (%)</option>'],
  [/<option value="air_temp_humidity">🌡️ Air Temp &amp; Humidity \(DHT22 \/ SHT30\)<\/option>/, '<option value="air_temp_humidity" data-i18n="opt_sensor_dht22">🌡️ Air Temp &amp; Humidity (DHT22 / SHT30)</option>'],
  [/<option value="soil_temp">🌱 Soil Temperature \(°C\)<\/option>/, '<option value="soil_temp" data-i18n="opt_sensor_soil_temp">🌱 Soil Temperature (°C)</option>'],
  [/<option value="water_level">🚰 Water Level Sensor \(%\)<\/option>/, '<option value="water_level" data-i18n="opt_sensor_water_level">🚰 Water Level Sensor (%)</option>'],
  [/<h3>🔑 Device Credentials Generated<\/h3>/, '<h3 data-i18n="modal_credentials_title">🔑 Device Credentials Generated</h3>'],
  [/<strong>⚠️ Important Security Notice:<\/strong>/, '<strong data-i18n="security_notice_title">⚠️ Important Security Notice:</strong>'],
  [/<label style="display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:4px;">Device ID:<\/label>/, '<label style="display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:4px;" data-i18n="lbl_device_id">Device ID:</label>'],
  [/<label style="display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:4px;">Secret Device API Key:<\/label>/, '<label style="display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:4px;" data-i18n="lbl_secret_key">Secret Device API Key:</label>'],
  [/<button type="button" id="copyDeviceKeyBtn"[^>]*>📋 Copy<\/button>/, '<button type="button" id="copyDeviceKeyBtn" style="padding:10px 18px; border-radius:10px; background:#059669; color:#fff; border:none; font-weight:700; cursor:pointer;" data-i18n="btn_copy">📋 Copy</button>'],
  [/<button type="button" class="btn-farm-action" id="closeDeviceKeyModalBtn"[^>]*>I Have Saved This Key<\/button>/, '<button type="button" class="btn-farm-action" id="closeDeviceKeyModalBtn" style="width:100%; padding:12px; background:#1e293b; color:#fff; border-radius:12px;" data-i18n="btn_saved_key">I Have Saved This Key</button>'],
  [/<h3>🧪 Manual IoT Demo Mode<\/h3>/, '<h3 data-i18n="modal_demo_title">🧪 Manual IoT Demo Mode</h3>'],
  [/<button type="button" id="clearDemoDataBtn"[^>]*>🗑️ Clear Demo Data<\/button>/, '<button type="button" id="clearDemoDataBtn" style="padding:10px 16px; border-radius:10px; border:1px solid #fca5a5; background:#fff; color:#dc2626; font-weight:600; cursor:pointer;" data-i18n="btn_clear_demo">🗑️ Clear Demo Data</button>'],
  [/<button type="submit" class="btn-farm-action btn-add-farm" style="padding:10px 18px;">Inject Reading<\/button>/, '<button type="submit" class="btn-farm-action btn-add-farm" style="padding:10px 18px;" data-i18n="btn_inject_reading">Inject Reading</button>']
];

for (const [regex, repl] of reps) {
  if (regex.test(html)) {
    html = html.replace(regex, repl);
  } else {
    console.log('Regex failed in farmer.html:', regex);
  }
}

// Also add placeholders
html = html
  .replace('id="farmName" placeholder="e.g. North Orchard"', 'id="farmName" data-i18n-placeholder="ph_farm_name" placeholder="e.g. North Orchard"')
  .replace('id="farmLocation" placeholder="e.g. Pune, Maharashtra"', 'id="farmLocation" data-i18n-placeholder="ph_farm_location" placeholder="e.g. Pune, Maharashtra"');

fs.writeFileSync('farmer.html', html);
console.log('Annotated farmer.html successfully');
