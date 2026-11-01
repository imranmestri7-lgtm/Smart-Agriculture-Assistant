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

const diseaseExtra = {
  "lbl_add_leaf_image": { en: "Add Leaf Image", mr: "पानाचा फोटो जोडा", hi: "पत्ती की तस्वीर जोड़ें" },
  "desc_choose_clear_image": { en: "Choose a clear image of the affected leaf.", mr: "प्रभावित पानाचा स्पष्ट फोटो निवडा.", hi: "प्रभावित पत्ती की स्पष्ट तस्वीर चुनें।" },
  "btn_upload_image": { en: "📁 Upload Image", mr: "📁 फोटो अपलोड करा", hi: "📁 फ़ोटो अपलोड करें" },
  "btn_use_camera": { en: "📷 Use Camera", mr: "📷 कॅमेरा वापरा", hi: "📷 कैमरा उपयोग करें" },
  "lbl_image_ready": { en: "Image Ready", mr: "फोटो तयार आहे", hi: "तस्वीर तैयार है" },
  "desc_image_ready": { en: "Your leaf image is ready for analysis.", mr: "तुमच्या पानाचा फोटो विश्लेषणासाठी तयार आहे.", hi: "आपकी पत्ती की तस्वीर विश्लेषण के लिए तैयार है।" },
  "btn_capture_leaf": { en: "📸 Capture Leaf", mr: "📸 पानाचा फोटो काढा", hi: "📸 पत्ती की तस्वीर लें" },
  "btn_close_camera": { en: "✕ Close Camera", mr: "✕ कॅमेरा बंद करा", hi: "✕ कैमरा बंद करें" },
  "btn_analyze_disease": { en: "🔍 Analyze Disease", mr: "🔍 रोगाचे विश्लेषण करा", hi: "🔍 रोग का विश्लेषण करें" },
  "note_model_analysis": { en: "Your image will be analyzed using our agricultural disease model.", mr: "तुमच्या फोटोचे कृषी रोग मॉडेलद्वारे विश्लेषण केले जाईल.", hi: "आपकी तस्वीर का कृषि रोग मॉडल द्वारा विश्लेषण किया जाएगा।" },
  "badge_better_results": { en: "BETTER RESULTS", mr: "उत्तम परिणामांसाठी", hi: "बेहतर परिणामों के लिए" },
  "title_detection_tips": { en: "Tips for Better Detection", mr: "उत्तम रोगनिदानासाठी उपयुक्त टिप्स", hi: "बेहतर रोग पहचान के लिए सुझाव" },
  "tip_lighting_title": { en: "Good Lighting", mr: "योग्य प्रकाश", hi: "अच्छी रोशनी" },
  "tip_lighting_desc": { en: "Take the photo in clear daylight without harsh shadows.", mr: "स्पष्ट सूर्यप्रकाशात सावली नसताना फोटो घ्या.", hi: "बिना छाया के स्पष्ट दिन के उजाले में तस्वीर लें।" },
  "tip_focus_title": { en: "Focus on Leaf", mr: "पानावर लक्ष केंद्रित करा", hi: "पत्ती पर ध्यान दें" },
  "tip_focus_desc": { en: "Make sure the affected leaf is centered and in sharp focus.", mr: "प्रभावित पान मध्यभागी आणि स्पष्ट दिसत असल्याची खात्री करा.", hi: "प्रभावित पत्ती केंद्र में और स्पष्ट होनी चाहिए।" },
  "tip_clear_title": { en: "Clear Image", mr: "स्पष्ट फोटो", hi: "साफ तस्वीर" },
  "tip_clear_desc": { en: "Avoid blurry or low-quality photos.", mr: "अस्पष्ट किंवा अंधुक फोटो टाळा.", hi: "धुंधली या खराब गुणवत्ता वाली तस्वीर से बचें।" },
  "tip_symptoms_title": { en: "Show Symptoms", mr: "लक्षणे दाखवा", hi: "लक्षण दिखाएं" },
  "tip_symptoms_desc": { en: "Capture spots or damage clearly on the leaf surface.", mr: "पानावरील डाग किंवा रोगाची लक्षणे स्पष्टपणे टिपून घ्या.", hi: "पत्ती की सतह पर धब्बे या नुकसान स्पष्ट रूप से दिखाएं।" },
  "badge_protect_crop": { en: "PROTECT YOUR CROP", mr: "पिकाचे रक्षण करा", hi: "फसल की रक्षा करें" },
  "title_why_early": { en: "Why Early Detection?", mr: "लवकर रोगनिदान का महत्त्वाचे?", hi: "जल्दी पहचान क्यों ज़रूरी है?" },
  "early_step1_title": { en: "Identify Problems Early", mr: "समस्या लवकर ओळखा", hi: "समस्या जल्दी पहचानें" },
  "early_step1_desc": { en: "Detect possible diseases before they spread across the field.", mr: "शेतात रोग पसरण्यापूर्वी त्याची वेळेवर ओळख करा.", hi: "खेत में बीमारी फैलने से पहले उसकी समय पर पहचान करें।" },
  "early_step2_title": { en: "Get Suitable Guidance", mr: "योग्य मार्गदर्शन मिळवा", hi: "उपयुक्त मार्गदर्शन पाएं" },
  "early_step2_desc": { en: "Understand possible treatment options and precautions.", mr: "उपचारांचे पर्याय आणि आवश्यक खबरदारी समजून घ्या.", hi: "उपचार के विकल्प और जरूरी सावधानियां समझें।" },
  "early_step3_title": { en: "Protect Your Crop", mr: "पिकाचे रक्षण करा", hi: "फसल की रक्षा करें" },
  "early_step3_desc": { en: "Take timely action and reduce yield loss.", mr: "वेळेवर पावले उचला आणि संभाव्य नुकसान टाळा.", hi: "समय पर कदम उठाएं और संभावित नुकसान से बचें।" },
  "badge_smart_assistant": { en: "SMART FARMER ASSISTANT", mr: "स्मार्ट शेतकरी सहाय्यक", hi: "स्मार्ट किसान सहायक" },
  "title_guidance_awaiting": { en: "Get Your Disease Guidance", mr: "तुमचे रोगनिदान मार्गदर्शन मिळवा", hi: "अपना रोग मार्गदर्शन प्राप्त करें" },
  "desc_guidance_awaiting": { en: "After disease analysis, the model prediction, symptoms, and care recommendations will appear here.", mr: "रोग विश्लेषणा नंतर मॉडेलचा अंदाज, लक्षणे आणि काळजी मार्गदर्शक तत्त्वे येथे दिसतील.", hi: "रोग विश्लेषण के बाद मॉडल का अनुमान, लक्षण और देखभाल संबंधी सुझाव यहाँ दिखाई देंगे।" },
  "btn_scan_another": { en: "🔄 Scan Another Leaf", mr: "🔄 दुसऱ्या पानाचा फोटो तपासा", hi: "🔄 दूसरी पत्ती की जाँच करें" },
  "history_loading": { en: "Loading diagnosis history...", mr: "निदान इतिहास लोड करत आहे...", hi: "निदान इतिहास लोड हो रहा है..." }
};

for (const [k, v] of Object.entries(diseaseExtra)) {
  en[k] = v.en;
  mr[k] = v.mr;
  hi[k] = v.hi;
}

const updatedI18n = currentI18n
  .replace(/en:\s*\{[\s\S]*?\n\s*\},?\s*mr:/, 'en: ' + JSON.stringify(en, null, 2) + ',\nmr:')
  .replace(/mr:\s*\{[\s\S]*?\n\s*\},?\s*hi:/, 'mr: ' + JSON.stringify(mr, null, 2) + ',\nhi:')
  .replace(/hi:\s*\{[\s\S]*?\n\s*\}/, 'hi: ' + JSON.stringify(hi, null, 2));
fs.writeFileSync('js/i18n.js', updatedI18n);

// 2. Update disease.html
let html = fs.readFileSync('disease.html', 'utf8');

const diseaseReplacements = [
  ['<a href="farmer.html">Dashboard</a>', '<a href="farmer.html" data-i18n="dashboard">Dashboard</a>'],
  ['<button class="profile-btn" onclick="window.location.href=\'farmer.html\'">Farmer</button>', '<button class="profile-btn" onclick="window.location.href=\'farmer.html\'" data-i18n="farmer_role">Farmer</button>'],
  ['<span class="hero-badge">🌿 AI-Powered Agriculture</span>', '<span class="hero-badge" data-i18n="disease_badge">🌿 AI-Powered Agriculture</span>'],
  ['<h1>Plant Disease Detection</h1>', '<h1 data-i18n="disease_hero_title">Plant Disease Detection</h1>'],
  ['<p>\n                Upload or capture a crop leaf image\n                and let our AI system help identify possible plant problems.\n            </p>', '<p data-i18n="disease_hero_desc">\n                Upload or capture a crop leaf image\n                and let our AI system help identify possible plant problems.\n            </p>'],
  ['<a href="#scanner" class="hero-btn">\n                Start Disease Scan →\n            </a>', '<a href="#scanner" class="hero-btn" data-i18n="disease_hero_btn">\n                Start Disease Scan →\n            </a>'],
  ['<span class="section-tag">SMART SCANNER</span>', '<span class="section-tag" data-i18n="scanner_badge">SMART SCANNER</span>'],
  ['<h2>Disease Scanner</h2>', '<h2 data-i18n="scanner_title">Disease Scanner</h2>'],
  ['<p>\n                    Provide a clear image of the\n                    affected leaf.\n                </p>', '<p data-i18n="scanner_desc">\n                    Provide a clear image of the\n                    affected leaf.\n                </p>'],
  ['<span>(Optional)</span>', '<span data-i18n="lbl_optional">(Optional)</span>'],
  ['<option value="">Select Crop</option>', '<option value="" data-i18n="opt_select_crop">Select Crop</option>'],
  ['<option value="Tomato">Tomato</option>', '<option value="Tomato" data-i18n="opt_crop_tomato">Tomato</option>'],
  ['<option value="Potato">Potato</option>', '<option value="Potato" data-i18n="opt_crop_potato">Potato</option>'],
  ['<option value="Rice">Rice</option>', '<option value="Rice" data-i18n="opt_crop_rice">Rice</option>'],
  ['<option value="Wheat">Wheat</option>', '<option value="Wheat" data-i18n="opt_crop_wheat">Wheat</option>'],
  ['<option value="Corn">Maize</option>', '<option value="Corn" data-i18n="opt_crop_corn">Maize</option>'],
  ['<option value="Cotton">Cotton</option>', '<option value="Cotton" data-i18n="opt_crop_cotton">Cotton</option>'],
  ['<h3>Add Leaf Image</h3>', '<h3 data-i18n="lbl_add_leaf_image">Add Leaf Image</h3>'],
  ['<p>\n                          Choose a clear image of\n                          the affected leaf.\n                      </p>', '<p data-i18n="desc_choose_clear_image">\n                          Choose a clear image of\n                          the affected leaf.\n                      </p>'],
  ['<span class="btn-icon">📁</span> Upload Image', '<span class="btn-icon">📁</span> <span data-i18n="btn_upload_image">📁 Upload Image</span>'],
  ['<span class="btn-icon">📷</span> Use Camera', '<span class="btn-icon">📷</span> <span data-i18n="btn_use_camera">📷 Use Camera</span>'],
  ['<h3>Image Ready</h3>', '<h3 data-i18n="lbl_image_ready">Image Ready</h3>'],
  ['<p>\n                         Your leaf image is ready\n                         for analysis.\n                     </p>', '<p data-i18n="desc_image_ready">\n                         Your leaf image is ready\n                         for analysis.\n                     </p>'],
  ['<button type="button" class="camera-btn capture-btn" id="captureBtn">\n                     📸 Capture Leaf\n                 </button>', '<button type="button" class="camera-btn capture-btn" id="captureBtn" data-i18n="btn_capture_leaf">\n                     📸 Capture Leaf\n                 </button>'],
  ['<button type="button" class="camera-btn close-btn" id="closeCameraBtn">\n                     ✕ Close Camera\n                 </button>', '<button type="button" class="camera-btn close-btn" id="closeCameraBtn" data-i18n="btn_close_camera">\n                     ✕ Close Camera\n                 </button>'],
  ['<button type="button" class="scan-btn" id="scanBtn">\n                🔍 Analyze Disease\n            </button>', '<button type="button" class="scan-btn" id="scanBtn" data-i18n="btn_analyze_disease">\n                🔍 Analyze Disease\n            </button>'],
  ['<p class="scan-note">\n                Your image will be analyzed using\n                our agricultural disease model.\n            </p>', '<p class="scan-note" data-i18n="note_model_analysis">\n                Your image will be analyzed using\n                our agricultural disease model.\n            </p>'],
  ['<span class="card-tag">BETTER RESULTS</span>', '<span class="card-tag" data-i18n="badge_better_results">BETTER RESULTS</span>'],
  ['<h3>Tips for Better Detection</h3>', '<h3 data-i18n="title_detection_tips">Tips for Better Detection</h3>'],
  ['<h4>Good Lighting</h4>', '<h4 data-i18n="tip_lighting_title">Good Lighting</h4>'],
  ['<p>\n                          Take the photo in clear\n                          daylight without harsh shadows.\n                      </p>', '<p data-i18n="tip_lighting_desc">\n                          Take the photo in clear\n                          daylight without harsh shadows.\n                      </p>'],
  ['<h4>Focus on Leaf</h4>', '<h4 data-i18n="tip_focus_title">Focus on Leaf</h4>'],
  ['<p>\n                          Make sure the affected leaf\n                          is centered and in sharp focus.\n                      </p>', '<p data-i18n="tip_focus_desc">\n                          Make sure the affected leaf\n                          is centered and in sharp focus.\n                      </p>'],
  ['<h4>Clear Image</h4>', '<h4 data-i18n="tip_clear_title">Clear Image</h4>'],
  ['<p>\n                          Avoid blurry or low-quality\n                          photos.\n                      </p>', '<p data-i18n="tip_clear_desc">\n                          Avoid blurry or low-quality\n                          photos.\n                      </p>'],
  ['<h4>Show Symptoms</h4>', '<h4 data-i18n="tip_symptoms_title">Show Symptoms</h4>'],
  ['<p>\n                          Capture spots or damage\n                          clearly on the leaf surface.\n                      </p>', '<p data-i18n="tip_symptoms_desc">\n                          Capture spots or damage\n                          clearly on the leaf surface.\n                      </p>'],
  ['<span class="card-tag">PROTECT YOUR CROP</span>', '<span class="card-tag" data-i18n="badge_protect_crop">PROTECT YOUR CROP</span>'],
  ['<h3>Why Early Detection?</h3>', '<h3 data-i18n="title_why_early">Why Early Detection?</h3>'],
  ['<h4>Identify Problems Early</h4>', '<h4 data-i18n="early_step1_title">Identify Problems Early</h4>'],
  ['<p>\n                  Detect possible diseases before\n                  they spread across the field.\n              </p>', '<p data-i18n="early_step1_desc">\n                  Detect possible diseases before\n                  they spread across the field.\n              </p>'],
  ['<h4>Get Suitable Guidance</h4>', '<h4 data-i18n="early_step2_title">Get Suitable Guidance</h4>'],
  ['<p>\n                  Understand possible treatment\n                  options and precautions.\n              </p>', '<p data-i18n="early_step2_desc">\n                  Understand possible treatment\n                  options and precautions.\n              </p>'],
  ['<h4>Protect Your Crop</h4>', '<h4 data-i18n="early_step3_title">Protect Your Crop</h4>'],
  ['<p>\n                  Take timely action and reduce\n                  potential yield loss.\n              </p>', '<p data-i18n="early_step3_desc">\n                  Take timely action and reduce\n                  potential yield loss.\n              </p>'],
  ['<span class="card-tag">SMART FARMER ASSISTANT</span>', '<span class="card-tag" data-i18n="badge_smart_assistant">SMART FARMER ASSISTANT</span>'],
  ['<h3>\n                        Get Your Disease Guidance\n                    </h3>', '<h3 data-i18n="title_guidance_awaiting">\n                        Get Your Disease Guidance\n                    </h3>'],
  ['<p>\n                        After disease analysis, the\n                        model prediction, symptoms, causes,\n                        prevention and safe treatment guidance\n                        will appear here.\n                    </p>', '<p data-i18n="desc_guidance_awaiting">\n                        After disease analysis, the\n                        model prediction, symptoms, causes,\n                        prevention and safe treatment guidance\n                        will appear here.\n                    </p>'],
  ['<button class="reset-btn" id="resetBtn">\n                🔄 Scan Another Leaf\n            </button>', '<button class="reset-btn" id="resetBtn" data-i18n="btn_scan_another">\n                🔄 Scan Another Leaf\n            </button>'],
  ['<div id="historyLoading" class="history-state">\n                    Loading diagnosis history...\n                </div>', '<div id="historyLoading" class="history-state" data-i18n="history_loading">\n                    Loading diagnosis history...\n                </div>']
];

for (const [target, repl] of diseaseReplacements) {
  if (html.includes(target)) {
    html = html.replace(target, repl);
  } else {
    console.log('Disease target not found:', target.slice(0, 40));
  }
}

fs.writeFileSync('disease.html', html);
console.log('Annotated disease.html successfully');
