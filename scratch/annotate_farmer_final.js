const fs = require('fs');

// 1. Add keys to i18n.js
const currentI18n = fs.readFileSync('js/i18n.js', 'utf8');
const vm = require('vm');
const sandbox = { window: {}, document: { querySelectorAll: () => [], getElementById: () => null, addEventListener: () => {} }, localStorage: { getItem: () => "en", setItem: () => {} } };
vm.createContext(sandbox);
vm.runInContext(currentI18n.replace('const translations =', 'var translations ='), sandbox);
const en = sandbox.translations.en;
const mr = sandbox.translations.mr;
const hi = sandbox.translations.hi;

const extra = {
  "lbl_sensor_name": { en: "🏷️ Sensor Name", mr: "🏷️ सेन्सरचे नाव", hi: "🏷️ सेंसर का नाम" },
  "lbl_sensor_type": { en: "📡 Sensor Type", mr: "📡 सेन्सरचा प्रकार", hi: "📡 सेंसर का प्रकार" },
  "lbl_target_sensor": { en: "Target Sensor", mr: "लक्षित सेन्सर", hi: "लक्षित सेंसर" },
  "lbl_sample_telemetry": { en: "Sample Telemetry Value", mr: "चाचणी टेलीमेट्री मूल्य", hi: "परीक्षण टेलीमेट्री मान" }
};

for (const [k, v] of Object.entries(extra)) {
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
  ['<span id="profileName">Farmer</span>', '<span id="profileName" data-i18n="farmer_role">Farmer</span>'],
  ['Welcome back, <span id="farmerName">Farmer</span>', 'Welcome back, <span id="farmerName" data-i18n="farmer_role">Farmer</span>'],
  ['<span class="card-pill" style="background:#ecfdf5; color:#059669; border-color:#a7f3d0; margin-left:8px;">IoT Ready</span>', '<span class="card-pill" style="background:#ecfdf5; color:#059669; border-color:#a7f3d0; margin-left:8px;" data-i18n="badge_iot_ready">IoT Ready</span>'],
  ['<span>MY FARMS &amp; CROPS</span>', '<span data-i18n="badge_my_farms_crops">MY FARMS &amp; CROPS</span>'],
  ['<label for="farmFilterSelect" style="font-size:13px; font-weight:600; color:#334155;">Filter by Farm:</label>', '<label for="farmFilterSelect" style="font-size:13px; font-weight:600; color:#334155;" data-i18n="lbl_filter_by_farm">Filter by Farm:</label>'],
  ['<span>SMART ANALYTICS &amp; INSIGHTS</span>', '<span data-i18n="badge_smart_analytics">SMART ANALYTICS &amp; INSIGHTS</span>'],
  ['<span class="summary-label">Total Water Usage</span>', '<span class="summary-label" data-i18n="stat_total_water">Total Water Usage</span>'],
  ['<span class="summary-label">Irrigation Needed</span>', '<span class="summary-label" data-i18n="stat_irrigation_needed">Irrigation Needed</span>'],
  ['<span class="summary-label">Sufficient Moisture</span>', '<span class="summary-label" data-i18n="stat_sufficient_moisture">Sufficient Moisture</span>'],
  ['<span>SMART ALERTS &amp; REMINDERS</span>', '<span data-i18n="badge_smart_alerts">SMART ALERTS &amp; REMINDERS</span>'],
  ['<span>IoT-READY SENSOR NETWORK</span>', '<span data-i18n="badge_iot_network">IoT-READY SENSOR NETWORK</span>'],
  ['<strong style="color:#0f172a; font-size:15px;">IoT Telemetry Hub</strong>', '<strong style="color:#0f172a; font-size:15px;" data-i18n="title_telemetry_hub">IoT Telemetry Hub</strong>'],
  ['<button type="button" class="btn-range active" data-range="24h">24 Hours</button>', '<button type="button" class="btn-range active" data-range="24h" data-i18n="filter_24h">24 Hours</button>'],
  ['<button type="button" class="btn-range" data-range="7d">7 Days</button>', '<button type="button" class="btn-range" data-range="7d" data-i18n="filter_7d">7 Days</button>'],
  ['<button type="button" class="btn-range" data-range="30d">30 Days</button>', '<button type="button" class="btn-range" data-range="30d" data-i18n="filter_30d">30 Days</button>'],
  ['<button type="button" class="btn-range" data-range="all">All</button>', '<button type="button" class="btn-range" data-range="all" data-i18n="filter_all">All</button>'],
  ['<span>Min:</span>', '<span data-i18n="stat_min">Min:</span>'],
  ['<span>Avg:</span>', '<span data-i18n="stat_avg">Avg:</span>'],
  ['<span>Max:</span>', '<span data-i18n="stat_max">Max:</span>'],
  ['<span>Readings:</span>', '<span data-i18n="stat_readings">Readings:</span>'],
  ['Hardware microcontrollers can transmit telemetry directly to AgriSmart via HTTP/HTTPS POST without exposing farmer accounts or database credentials.', '<span data-i18n="hw_spec_desc">Hardware microcontrollers can transmit telemetry directly to AgriSmart via HTTP/HTTPS POST without exposing farmer accounts or database credentials.</span>'],
  ['<strong>Endpoint:</strong>', '<strong data-i18n="hw_endpoint_label">Endpoint:</strong>'],
  ['<strong>Headers:</strong>', '<strong data-i18n="hw_headers_label">Headers:</strong>'],
  ['<strong>Sample Soil Moisture JSON Payload:</strong>', '<strong data-i18n="hw_sample_payload">Sample Soil Moisture JSON Payload:</strong>'],
  ['<strong>Sample Combined DHT22 Payload:</strong>', '<strong data-i18n="hw_sample_dht22">Sample Combined DHT22 Payload:</strong>'],
  ['<span class="message-sender">Farmer</span>', '<span class="message-sender" data-i18n="farmer_role">Farmer</span>'],
  ['<span style="font-size:11px; color:#64748b; font-style:italic;">Think</span>', '<span style="font-size:11px; color:#64748b; font-style:italic;" data-i18n="msg_think">Think</span>'],
  ['Harvest readiness, growth stage care, and crop record updates.', '<span data-i18n="prefs_crop_desc">Harvest readiness, growth stage care, and crop record updates.</span>'],
  ['Soil moisture deficit warnings and water recommendations.', '<span data-i18n="prefs_irrigation_desc">Soil moisture deficit warnings and water recommendations.</span>'],
  ['Heavy rain advisories and high temperature warnings.', '<span data-i18n="prefs_weather_desc">Heavy rain advisories and high temperature warnings.</span>'],
  ['Diagnosis follow-ups, field sanitation, and inspection advice.', '<span data-i18n="prefs_disease_desc">Diagnosis follow-ups, field sanitation, and inspection advice.</span>'],
  ['<label for="sensorFarmId">🏡 Farm</label>', '<label for="sensorFarmId" data-i18n="lbl_select_farm">🏡 Farm</label>'],
  ['<option value="">Loading farms...</option>', '<option value="" data-i18n="opt_loading_farms">Loading farms...</option>'],
  ['<label for="sensorCropId">🌾 Assigned Crop (Optional)</label>', '<label for="sensorCropId" data-i18n="lbl_assigned_crop">🌾 Assigned Crop (Optional)</label>'],
  ['<label for="sensorName">🏷️ Sensor Name</label>', '<label for="sensorName" data-i18n="lbl_sensor_name">🏷️ Sensor Name</label>'],
  ['<label for="sensorType">📡 Sensor Type</label>', '<label for="sensorType" data-i18n="lbl_sensor_type">📡 Sensor Type</label>'],
  ['<label for="sensorDeviceId">🆔 Unique Device ID</label>', '<label for="sensorDeviceId" data-i18n="lbl_device_id">🆔 Unique Device ID</label>'],
  ['Must be unique across your hardware devices (letters, digits, dashes).', '<span data-i18n="sensor_id_hint">Must be unique across your hardware devices (letters, digits, dashes).</span>'],
  ['<strong>⚠️ Important Security Notice:</strong>', '<strong data-i18n="security_notice_title">⚠️ Important Security Notice:</strong>'],
  ['<label style="display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:4px;">Device ID:</label>', '<label style="display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:4px;" data-i18n="lbl_device_id">Device ID:</label>'],
  ['<label style="display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:4px;">Secret Device API Key:</label>', '<label style="display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:4px;" data-i18n="lbl_secret_key">Secret Device API Key:</label>'],
  ['<button type="button" id="copyDeviceKeyBtn" style="padding:10px 18px; border-radius:10px; background:#059669; color:#fff; border:none; font-weight:700; cursor:pointer;">📋 Copy</button>', '<button type="button" id="copyDeviceKeyBtn" style="padding:10px 18px; border-radius:10px; background:#059669; color:#fff; border:none; font-weight:700; cursor:pointer;" data-i18n="btn_copy">📋 Copy</button>'],
  ['<button type="button" class="btn-farm-action" id="closeDeviceKeyModalBtn" style="width:100%; padding:12px; background:#1e293b; color:#fff; border-radius:12px;">I Have Saved This Key</button>', '<button type="button" class="btn-farm-action" id="closeDeviceKeyModalBtn" style="width:100%; padding:12px; background:#1e293b; color:#fff; border-radius:12px;" data-i18n="btn_saved_key">I Have Saved This Key</button>'],
  ['<strong>[Demo Data]</strong>', '<strong data-i18n="demo_data_badge">[Demo Data]</strong>'],
  ['<label for="demoSensorSelect">Target Sensor</label>', '<label for="demoSensorSelect" data-i18n="lbl_target_sensor">Target Sensor</label>'],
  ['<option value="">-- Choose Sensor --</option>', '<option value="" data-i18n="opt_choose_sensor">-- Choose Sensor --</option>'],
  ['<label for="demoReadingValue">Sample Telemetry Value</label>', '<label for="demoReadingValue" data-i18n="lbl_sample_telemetry">Sample Telemetry Value</label>'],
  ['<button type="submit" class="btn-farm-action btn-add-farm" style="padding:10px 18px;">Inject Reading</button>', '<button type="submit" class="btn-farm-action btn-add-farm" style="padding:10px 18px;" data-i18n="btn_inject_reading">Inject Reading</button>']
];

// Globally replace "No Sensor" and "DEMO" in initial empty cards
html = html
  .split('<span class="metric-status" id="moistStatus">No Sensor</span>').join('<span class="metric-status" id="moistStatus" data-i18n="telemetry_no_sensor">No Sensor</span>')
  .split('<span class="metric-status" id="airTempStatus">No Sensor</span>').join('<span class="metric-status" id="airTempStatus" data-i18n="telemetry_no_sensor">No Sensor</span>')
  .split('<span class="metric-status" id="humidityStatus">No Sensor</span>').join('<span class="metric-status" id="humidityStatus" data-i18n="telemetry_no_sensor">No Sensor</span>')
  .split('<span class="metric-status" id="soilTempStatus">No Sensor</span>').join('<span class="metric-status" id="soilTempStatus" data-i18n="telemetry_no_sensor">No Sensor</span>')
  .split('<span class="metric-status" id="waterLevelStatus">No Sensor</span>').join('<span class="metric-status" id="waterLevelStatus" data-i18n="telemetry_no_sensor">No Sensor</span>')
  .split('<span class="telemetry-badge-demo">DEMO</span>').join('<span class="telemetry-badge-demo" data-i18n="telemetry_demo_badge">DEMO</span>');

for (const [target, repl] of reps) {
  if (html.includes(target)) {
    html = html.replace(target, repl);
  } else {
    console.log('Farmer final target not found:', target.slice(0, 40));
  }
}

fs.writeFileSync('farmer.html', html);
console.log('Annotated farmer.html successfully');
