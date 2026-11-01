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

const weatherExtra = {
  "farming_advice_title": { en: "🌱 Farming Advice", mr: "🌱 शेतीविषयक सल्ला", hi: "🌱 कृषि सलाह" },
  "advice_irrigation_title": { en: "Irrigation", mr: "सिंचन", hi: "सिंचाई" },
  "advice_irrigation_desc": { en: "Recommended", mr: "शिफारस केली", hi: "सिफारिश की गई" },
  "advice_rain_title": { en: "Rain Alert", mr: "पाऊस इशारा", hi: "बारिश चेतावनी" },
  "advice_rain_desc": { en: "Rain expected tomorrow", mr: "उद्या पाऊस अपेक्षित आहे", hi: "कल बारिश की संभावना है" },
  "advice_protection_title": { en: "Crop Protection", mr: "पीक संरक्षण", hi: "फसल सुरक्षा" },
  "advice_protection_desc": { en: "Protect crops from excess moisture.", mr: "जास्त ओलाव्यापासून पिकांचे संरक्षण करा.", hi: "अत्यधिक नमी से फसलों की रक्षा करें।" },
  "advice_activity_title": { en: "Farm Activity", mr: "शेती कामे", hi: "कृषि कार्य" },
  "advice_activity_desc": { en: "Morning is suitable for farm activities.", mr: "सकाळची वेळ शेती कामांसाठी योग्य आहे.", hi: "सुबह का समय कृषि कार्यों के लिए उपयुक्त है।" },
  "additional_info_title": { en: "📊 Additional Information", mr: "📊 अतिरिक्त माहिती", hi: "📊 अतिरिक्त जानकारी" },
  "weather_sunrise": { en: "Sunrise", mr: "सूर्योदय", hi: "सूर्योदय" },
  "weather_sunset": { en: "Sunset", mr: "सूर्यास्त", hi: "सूर्यास्त" },
  "weather_visibility": { en: "Visibility", mr: "दृश्यता", hi: "दृश्यता" }
};

for (const [k, v] of Object.entries(weatherExtra)) {
  en[k] = v.en;
  mr[k] = v.mr;
  hi[k] = v.hi;
}

const updatedI18n = currentI18n
  .replace(/en:\s*\{[\s\S]*?\n\s*\},?\s*mr:/, 'en: ' + JSON.stringify(en, null, 2) + ',\nmr:')
  .replace(/mr:\s*\{[\s\S]*?\n\s*\},?\s*hi:/, 'mr: ' + JSON.stringify(mr, null, 2) + ',\nhi:')
  .replace(/hi:\s*\{[\s\S]*?\n\s*\}/, 'hi: ' + JSON.stringify(hi, null, 2));
fs.writeFileSync('js/i18n.js', updatedI18n);

// 2. Update weather.html
let html = fs.readFileSync('weather.html', 'utf8');

const weatherReplacements = [
  ['<a href="farmer.html">Dashboard</a>', '<a href="farmer.html" data-i18n="dashboard">Dashboard</a>'],
  ['<button class="profile-btn" onclick="window.location.href=\'farmer.html\'">\n                Farmer\n            </button>', '<button class="profile-btn" onclick="window.location.href=\'farmer.html\'" data-i18n="farmer_role">\n                Farmer\n            </button>'],
  ['<h1>Weather Information</h1>', '<h1 data-i18n="weather_hero_title">Weather Information</h1>'],
  ['<p>\n                Check weather conditions and make better farming decisions.\n            </p>', '<p data-i18n="weather_hero_desc">\n                Check weather conditions and make better farming decisions.\n            </p>'],
  ['<label for="location">\n        📍 Search Location\n    </label>', '<label for="location" data-i18n="lbl_search_location">\n        📍 Search Location\n    </label>'],
  ['placeholder="Enter city, village or location"', 'data-i18n-placeholder="ph_search_city" placeholder="Enter city, village or location"'],
  ['<p>Partly Cloudy</p>', '<p data-i18n="weather_partly_cloudy">Partly Cloudy</p>'],
  ['<small>Humidity</small>', '<small data-i18n="weather_humidity">Humidity</small>'],
  ['<small>Wind Speed</small>', '<small data-i18n="weather_wind">Wind Speed</small>'],
  ['<small>Rainfall</small>', '<small data-i18n="weather_rain">Rainfall</small>'],
  ['<h2>5-Day Forecast</h2>', '<h2 data-i18n="forecast_title">5-Day Forecast</h2>'],
  ['<h3>Mon</h3>', '<h3 data-i18n="weather_day_mon">Mon</h3>'],
  ['<h3>Tue</h3>', '<h3 data-i18n="weather_day_tue">Tue</h3>'],
  ['<h3>Wed</h3>', '<h3 data-i18n="weather_day_wed">Wed</h3>'],
  ['<h3>Thu</h3>', '<h3 data-i18n="weather_day_thu">Thu</h3>'],
  ['<h3>Fri</h3>', '<h3 data-i18n="weather_day_fri">Fri</h3>'],
  ['<h2>🌱 Farming Advice</h2>', '<h2 data-i18n="farming_advice_title">🌱 Farming Advice</h2>'],
  ['<h3>Irrigation</h3>\n                        <p>Recommended</p>', '<h3 data-i18n="advice_irrigation_title">Irrigation</h3>\n                        <p data-i18n="advice_irrigation_desc">Recommended</p>'],
  ['<h3>Rain Alert</h3>\n                        <p>Rain expected tomorrow</p>', '<h3 data-i18n="advice_rain_title">Rain Alert</h3>\n                        <p data-i18n="advice_rain_desc">Rain expected tomorrow</p>'],
  ['<h3>Crop Protection</h3>\n                        <p>Protect crops from excess moisture.</p>', '<h3 data-i18n="advice_protection_title">Crop Protection</h3>\n                        <p data-i18n="advice_protection_desc">Protect crops from excess moisture.</p>'],
  ['<h3>Farm Activity</h3>\n                        <p>Morning is suitable for farm activities.</p>', '<h3 data-i18n="advice_activity_title">Farm Activity</h3>\n                        <p data-i18n="advice_activity_desc">Morning is suitable for farm activities.</p>'],
  ['<h2>📊 Additional Information</h2>', '<h2 data-i18n="additional_info_title">📊 Additional Information</h2>'],
  ['<small>Sunrise</small>', '<small data-i18n="weather_sunrise">Sunrise</small>'],
  ['<small>Sunset</small>', '<small data-i18n="weather_sunset">Sunset</small>'],
  ['<small>Pressure</small>', '<small data-i18n="weather_pressure">Pressure</small>'],
  ['<small>Visibility</small>', '<small data-i18n="weather_visibility">Visibility</small>']
];

for (const [target, repl] of weatherReplacements) {
  if (html.includes(target)) {
    html = html.replace(target, repl);
  } else {
    console.log('Weather target not found:', target.slice(0, 40));
  }
}

fs.writeFileSync('weather.html', html);
console.log('Annotated weather.html successfully');
