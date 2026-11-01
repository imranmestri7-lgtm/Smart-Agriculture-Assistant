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

const cropExtra = {
  "step_label": { en: "STEP", mr: "पायरी", hi: "चरण" },
  "range_n": { en: "Recommended range: 0–140 kg/ha", mr: "शिफारस केलेली श्रेणी: ०–१४० किलो/हेक्टर", hi: "अनुशंसित सीमा: ०–१४० किग्रा/हेक्टेयर" },
  "range_p": { en: "Recommended range: 0–145 kg/ha", mr: "शिफारस केलेली श्रेणी: ०–१४५ किलो/हेक्टर", hi: "अनुशंसित सीमा: ०–१४५ किग्रा/हेक्टेयर" },
  "range_k": { en: "Recommended range: 0–205 kg/ha", mr: "शिफारस केलेली श्रेणी: ०–२०५ किलो/हेक्टर", hi: "अनुशंसित सीमा: ०–२०५ किग्रा/हेक्टेयर" },
  "scale_ph": { en: "Scale: 0–14", mr: "प्रमाण: ०–१४", hi: "पैमाना: ०–१४" },
  "unit_c": { en: "Unit: °C", mr: "एकक: °C", hi: "इकाई: °C" },
  "unit_pct": { en: "Unit: %", mr: "एकक: %", hi: "इकाई: %" },
  "unit_mm": { en: "Unit: mm", mr: "एकक: मिमी", hi: "इकाई: मिमी" },
  "desc_location": { en: "Select your farming region", mr: "तुमचा शेती प्रदेश निवडा", hi: "अपना कृषि क्षेत्र चुनें" },
  "btn_reset": { en: "↺ Reset", mr: "↺ रीसेट", hi: "↺ रीसेट" },
  "btn_analyze_recommend": { en: "🌱 Analyze & Recommend", mr: "🌱 विश्लेषण आणि शिफारस करा", hi: "🌱 विश्लेषण और सिफारिश करें" },
  "why_need_info_title": { en: "Why do we need this information?", mr: "आम्हाला ही माहिती का हवी आहे?", hi: "हमें इस जानकारी की आवश्यकता क्यों है?" },
  "why_need_info_desc": { en: "Soil nutrients, pH, temperature, humidity and rainfall help us recommend the most suitable crop for your field.", mr: "मातीतील पोषक घटक, सामू, तापमान, आर्द्रता आणि पाऊस तुमच्या शेतासाठी सर्वात योग्य पीक सुचवण्यास मदत करतात.", hi: "मिट्टी के पोषक तत्व, पीएच, तापमान, नमी और बारिश आपके खेत के लिए सबसे उपयुक्त फसल सुझाने में मदद करते हैं।" },
  "benefit_better_crop": { en: "🌱 Better crop selection", mr: "🌱 योग्य पीक निवड", hi: "🌱 बेहतर फसल चयन" },
  "benefit_understand_soil": { en: "💧 Understand soil conditions", mr: "💧 मातीची स्थिती समजून घ्या", hi: "💧 मिट्टी की स्थिति समझें" },
  "benefit_data_driven": { en: "📊 Data-driven recommendation", mr: "📊 डेटा-आधारित शिफारस", hi: "📊 डेटा-संचालित सिफारिश" },
  "ph_nitrogen": { en: "e.g. 50", mr: "उदा. ५०", hi: "उदा. ५०" },
  "ph_phosphorus": { en: "e.g. 50", mr: "उदा. ५०", hi: "उदा. ५०" },
  "ph_potassium": { en: "e.g. 50", mr: "उदा. ५०", hi: "उदा. ५०" },
  "ph_ph": { en: "e.g. 6.5", mr: "उदा. ६.५", hi: "उदा. ६.५" },
  "ph_temp": { en: "e.g. 26", mr: "उदा. २६", hi: "उदा. २६" },
  "ph_humidity": { en: "e.g. 80", mr: "उदा. ८०", hi: "उदा. ८०" },
  "ph_rainfall": { en: "e.g. 200", mr: "उदा. २००", hi: "उदा. २००" }
};

for (const [k, v] of Object.entries(cropExtra)) {
  en[k] = v.en;
  mr[k] = v.mr;
  hi[k] = v.hi;
}

const updatedI18n = currentI18n
  .replace(/en:\s*\{[\s\S]*?\n\s*\},?\s*mr:/, 'en: ' + JSON.stringify(en, null, 2) + ',\nmr:')
  .replace(/mr:\s*\{[\s\S]*?\n\s*\},?\s*hi:/, 'mr: ' + JSON.stringify(mr, null, 2) + ',\nhi:')
  .replace(/hi:\s*\{[\s\S]*?\n\s*\}/, 'hi: ' + JSON.stringify(hi, null, 2));
fs.writeFileSync('js/i18n.js', updatedI18n);

// 2. Update crop.html
let html = fs.readFileSync('crop.html', 'utf8');

const cropReplacements = [
  ['<a href="farmer.html">Dashboard</a>', '<a href="farmer.html" data-i18n="dashboard">Dashboard</a>'],
  ['<button class="profile-btn" onclick="window.location.href=\'farmer.html\'">Farmer</button>', '<button class="profile-btn" onclick="window.location.href=\'farmer.html\'" data-i18n="farmer_role">Farmer</button>'],
  ['<span class="hero-badge">SMART AGRICULTURE</span>', '<span class="hero-badge" data-i18n="crop_rec_badge">SMART AGRICULTURE</span>'],
  ['<h1 class="hero-title">\n                Crop Recommendation\n                <span class="hero-title-highlight">for Your Soil</span>\n            </h1>', '<h1 class="hero-title">\n                <span data-i18n="crop_rec_title_main">Crop Recommendation</span>\n                <span class="hero-title-highlight" data-i18n="crop_rec_title_sub">for Your Soil</span>\n            </h1>'],
  ['<p class="hero-subtitle">\n                Make smarter farming decisions using soil,\n                weather and agricultural data.\n            </p>', '<p class="hero-subtitle" data-i18n="crop_rec_desc">\n                Make smarter farming decisions using soil,\n                weather and agricultural data.\n            </p>'],
  ['<span class="hero-pill">✓ Soil Analysis</span>', '<span class="hero-pill" data-i18n="pill_soil_analysis">✓ Soil Analysis</span>'],
  ['<span class="hero-pill">✓ Smart Recommendation</span>', '<span class="hero-pill" data-i18n="pill_smart_rec">✓ Smart Recommendation</span>'],
  ['<span class="hero-pill">✓ Data Driven</span>', '<span class="hero-pill" data-i18n="pill_data_driven">✓ Data Driven</span>'],
  ['<span class="section-tag">SMART AGRICULTURE</span>', '<span class="section-tag" data-i18n="crop_rec_badge">SMART AGRICULTURE</span>'],
  ['<h2 class="section-title">Soil &amp; Environmental Data</h2>', '<h2 class="section-title" data-i18n="crop_form_title">Soil &amp; Environmental Data</h2>'],
  ['<p class="section-subtitle">\n                    Provide accurate field conditions for a smarter crop recommendation.\n                </p>', '<p class="section-subtitle" data-i18n="crop_form_desc">\n                    Provide accurate field conditions for a smarter crop recommendation.\n                </p>'],
  ['<span class="step-badge-text">STEP</span>', '<span class="step-badge-text" data-i18n="step_label">STEP</span>'],
  ['<h3 class="step-title">Soil Nutrients</h3>', '<h3 class="step-title" data-i18n="step_nutrients">Soil Nutrients</h3>'],
  ['<p class="step-description">\n                        Enter the nutrient levels available in your soil.\n                    </p>', '<p class="step-description" data-i18n="step_nutrients_desc">\n                        Enter the nutrient levels available in your soil.\n                    </p>'],
  ['<label for="nitrogen">Nitrogen (N)</label>', '<label for="nitrogen" data-i18n="lbl_nitrogen">Nitrogen (N)</label>'],
  ['<span class="field-hint">Recommended range: 0–140 kg/ha</span>', '<span class="field-hint" data-i18n="range_n">Recommended range: 0–140 kg/ha</span>'],
  ['<label for="phosphorus">Phosphorus (P)</label>', '<label for="phosphorus" data-i18n="lbl_phosphorus">Phosphorus (P)</label>'],
  ['<span class="field-hint">Recommended range: 0–145 kg/ha</span>', '<span class="field-hint" data-i18n="range_p">Recommended range: 0–145 kg/ha</span>'],
  ['<label for="potassium">Potassium (K)</label>', '<label for="potassium" data-i18n="lbl_potassium">Potassium (K)</label>'],
  ['<span class="field-hint">Recommended range: 0–205 kg/ha</span>', '<span class="field-hint" data-i18n="range_k">Recommended range: 0–205 kg/ha</span>'],
  ['<label for="ph">Soil pH</label>', '<label for="ph" data-i18n="lbl_crop_ph">Soil pH</label>'],
  ['<span class="field-hint">Scale: 0–14</span>', '<span class="field-hint" data-i18n="scale_ph">Scale: 0–14</span>'],
  ['<h3 class="step-title">Environmental Conditions</h3>', '<h3 class="step-title" data-i18n="step_climate">Environmental Conditions</h3>'],
  ['<p class="step-description">\n                        Enter the current environmental conditions.\n                    </p>', '<p class="step-description" data-i18n="step_climate_desc">\n                        Enter the current environmental conditions.\n                    </p>'],
  ['<label for="temperature">🌡️ Temperature</label>', '<label for="temperature" data-i18n="lbl_crop_temp">🌡️ Temperature</label>'],
  ['<span class="field-hint">Unit: °C</span>', '<span class="field-hint" data-i18n="unit_c">Unit: °C</span>'],
  ['<label for="humidity">💧 Humidity</label>', '<label for="humidity" data-i18n="lbl_crop_humidity">💧 Humidity</label>'],
  ['<span class="field-hint">Unit: %</span>', '<span class="field-hint" data-i18n="unit_pct">Unit: %</span>'],
  ['<label for="rainfall">🌧️ Rainfall</label>', '<label for="rainfall" data-i18n="lbl_crop_rainfall">🌧️ Rainfall</label>'],
  ['<span class="field-hint">Unit: mm</span>', '<span class="field-hint" data-i18n="unit_mm">Unit: mm</span>'],
  ['<label for="location">📍 Location</label>', '<label for="location" data-i18n="location_label">📍 Location</label>'],
  ['<option value="" disabled selected>Select location</option>', '<option value="" disabled selected data-i18n="select_location_placeholder">Select location</option>'],
  ['<option value="maharashtra">Maharashtra</option>', '<option value="maharashtra" data-i18n="opt_loc_maharashtra">Maharashtra</option>'],
  ['<option value="karnataka">Karnataka</option>', '<option value="karnataka" data-i18n="opt_loc_karnataka">Karnataka</option>'],
  ['<option value="goa">Goa</option>', '<option value="goa" data-i18n="opt_loc_goa">Goa</option>'],
  ['<option value="gujarat">Gujarat</option>', '<option value="gujarat" data-i18n="opt_loc_gujarat">Gujarat</option>'],
  ['<option value="other">Other</option>', '<option value="other" data-i18n="opt_loc_other">Other</option>'],
  ['<span class="field-hint">Select your farming region</span>', '<span class="field-hint" data-i18n="desc_location">Select your farming region</span>'],
  ['<button type="reset" class="btn-reset">↺ Reset</button>', '<button type="reset" class="btn-reset" data-i18n="btn_reset">↺ Reset</button>'],
  ['<button type="submit" class="btn-submit" id="recommendBtn">\n                            🌱 Analyze &amp; Recommend\n                        </button>', '<button type="submit" class="btn-submit" id="recommendBtn" data-i18n="btn_analyze_recommend">\n                            🌱 Analyze &amp; Recommend\n                        </button>'],
  ['<h3 class="info-box-title">Why do we need this information?</h3>', '<h3 class="info-box-title" data-i18n="why_need_info_title">Why do we need this information?</h3>'],
  ['<p class="info-box-text">\n                    Soil nutrients, pH, temperature, humidity and rainfall are key factors in determining crop suitability.\n                </p>', '<p class="info-box-text" data-i18n="why_need_info_desc">\n                    Soil nutrients, pH, temperature, humidity and rainfall are key factors in determining crop suitability.\n                </p>'],
  ['<span>🌱 Better crop selection</span>', '<span data-i18n="benefit_better_crop">🌱 Better crop selection</span>'],
  ['<span>💧 Understand soil conditions</span>', '<span data-i18n="benefit_understand_soil">💧 Understand soil conditions</span>'],
  ['<span>📊 Data-driven recommendation</span>', '<span data-i18n="benefit_data_driven">📊 Data-driven recommendation</span>']
];

for (const [target, repl] of cropReplacements) {
  if (html.includes(target)) {
    html = html.replace(target, repl);
  } else {
    console.log('Crop target not found:', target.slice(0, 40));
  }
}

// Add placeholders
html = html
  .replace('id="nitrogen" placeholder="e.g. 50"', 'id="nitrogen" data-i18n-placeholder="ph_nitrogen" placeholder="e.g. 50"')
  .replace('id="phosphorus" placeholder="e.g. 50"', 'id="phosphorus" data-i18n-placeholder="ph_phosphorus" placeholder="e.g. 50"')
  .replace('id="potassium" placeholder="e.g. 50"', 'id="potassium" data-i18n-placeholder="ph_potassium" placeholder="e.g. 50"')
  .replace('id="ph" placeholder="e.g. 6.5"', 'id="ph" data-i18n-placeholder="ph_ph" placeholder="e.g. 6.5"')
  .replace('id="temperature" placeholder="e.g. 26"', 'id="temperature" data-i18n-placeholder="ph_temp" placeholder="e.g. 26"')
  .replace('id="humidity" placeholder="e.g. 80"', 'id="humidity" data-i18n-placeholder="ph_humidity" placeholder="e.g. 80"')
  .replace('id="rainfall" placeholder="e.g. 200"', 'id="rainfall" data-i18n-placeholder="ph_rainfall" placeholder="e.g. 200"');

fs.writeFileSync('crop.html', html);
console.log('Annotated crop.html successfully');
