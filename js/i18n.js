// i18n.js - simple client-side internationalization
// Supports English (en), Marathi (mr) and Hindi (hi)
// Translation dictionaries
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
    // Add more keys as needed
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
    "smart_farming": "स्मार्ट फसलींग",
    "made_simple": "सोपे बनवले",
    "welcome_message": "AgriSmart शेतकऱ्यांना पिके व्यवस्थापित करण्यास, संभाव्य रोग समजून घेण्यास, हवामानाची माहिती तपासण्यास, पाण्याच्या मार्गदर्शन मिळवण्यास आणि एक साधी प्लॅटफॉर्म वापरून समर्थन मिळवण्यास मदत करते.",
    "get_started_btn": "🌱 सुरू करा",
    "how_it_works_btn": "▶ कसे कार्य करते",
    "login_button": "लॉगिन",
    "signup_button": "नोंदणी",
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
  }
};

// Retrieve current language, default to English
// Retrieve current language, default to English
function getCurrentLang() {
  return localStorage.getItem('lang') || 'en';
}

function setCurrentLang(lang) {
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;
}

// Apply translations
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
  // Set language selector value
  const sel = document.getElementById('lang-select');
  if (sel) {
    sel.value = getCurrentLang();
    sel.addEventListener('change', e => {
      setCurrentLang(e.target.value);
      location.reload();
    });
  }
}

// Auto-apply on DOM load
document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
});
  return localStorage.getItem('lang') || 'en';
}

function setCurrentLang(lang) {
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;
}

function t(key) {
  const lang = getCurrentLang();
  return translations[lang][key] || translations['en'][key] || key;
}

// Apply translations to elements with data-i18n attribute
function applyTranslations() {
  const elements = document.querySelectorAll('[data-i18n]');
  elements.forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  });
  // Placeholders
  const placeholders = document.querySelectorAll('[data-i18n-placeholder]');
  placeholders.forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.setAttribute('placeholder', t(key));
  });
  // Titles
  const titles = document.querySelectorAll('[data-i18n-title]');
  titles.forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    el.setAttribute('title', t(key));
  });
}

// Expose functions globally
window.i18n = {
  t,
  setLang: setCurrentLang,
  applyTranslations,
  getLang: getCurrentLang
};

// Auto-apply on DOM load
document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
});
