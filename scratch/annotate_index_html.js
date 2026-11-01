const fs = require('fs');

let html = fs.readFileSync('index.html', 'utf8');

// Replacements for index.html
const replacements = [
  // Hero
  ['<div class="hero-badge">', '<div class="hero-badge" data-i18n="hero_badge">'],
  ['<h1>\n                        Smart Farming\n                        <span>Made Simple</span>\n                    </h1>', '<h1>\n                        <span data-i18n="smart_farming">Smart Farming</span>\n                        <span data-i18n="made_simple">Made Simple</span>\n                    </h1>'],
  ['<p>\n                        AgriSmart helps farmers manage crops, understand\n                        possible plant problems, check weather information,\n                        get irrigation guidance, and access farming support\n                        from one simple platform.\n                    </p>', '<p data-i18n="welcome_message">\n                        AgriSmart helps farmers manage crops, understand\n                        possible plant problems, check weather information,\n                        get irrigation guidance, and access farming support\n                        from one simple platform.\n                    </p>'],
  ['<a href="login.html" class="primary-button">\n                            🌱 Get Started\n                        </a>', '<a href="login.html" class="primary-button" data-i18n="get_started_btn">\n                            🌱 Get Started\n                        </a>'],
  ['<a href="#how-it-works" class="secondary-button">\n                            ▶ How It Works\n                        </a>', '<a href="#how-it-works" class="secondary-button" data-i18n="how_it_works_btn">\n                            ▶ How It Works\n                        </a>'],
  ['<h3>\n                            Your Farming Assistant\n                        </h3>', '<h3 data-i18n="your_farming_assistant">\n                            Your Farming Assistant\n                        </h3>'],
  ['<p>\n                            Manage your crops and get useful farming\n                            information in one place.\n                        </p>', '<p data-i18n="assistant_preview_desc">\n                            Manage your crops and get useful farming\n                            information in one place.\n                        </p>'],
  ['<small>My Crops</small>', '<small data-i18n="preview_crops">My Crops</small>'],
  ['<small>Plant Health</small>', '<small data-i18n="preview_health">Plant Health</small>'],
  ['<small>Weather</small>', '<small data-i18n="preview_weather">Weather</small>'],
  ['<small>Irrigation</small>', '<small data-i18n="preview_irrigation">Irrigation</small>'],

  // Features
  ['<span class="section-label">\n                        FARMING FEATURES\n                    </span>', '<span class="section-label" data-i18n="features_label">\n                        FARMING FEATURES\n                    </span>'],
  ['<h2>\n                        Everything You Need for Better Farming\n                    </h2>', '<h2 data-i18n="features_title">\n                        Everything You Need for Better Farming\n                    </h2>'],
  ['<p>\n                        Explore the main tools available through\n                        AgriSmart.\n                    </p>', '<p data-i18n="features_subtitle">\n                        Explore the main tools available through\n                        AgriSmart.\n                    </p>'],
  ['<h3>\n                            My Crops\n                        </h3>', '<h3 data-i18n="card_crops_title">\n                            My Crops\n                        </h3>'],
  ['<p>\n                            Add and manage your crops, varieties,\n                            planting dates, field information and notes.\n                        </p>', '<p data-i18n="feature_crops_desc">\n                            Add and manage your crops, varieties,\n                            planting dates, field information and notes.\n                        </p>'],
  ['<a href="login.html" class="feature-link">\n                            Manage Crops →\n                        </a>', '<a href="login.html" class="feature-link" data-i18n="feature_manage_crops_link">\n                            Manage Crops →\n                        </a>'],

  ['<h3>\n                            Disease Detection\n                        </h3>', '<h3 data-i18n="feature_disease_title">\n                            Disease Detection\n                        </h3>'],
  ['<p>\n                            Upload a plant image to identify possible\n                            plant health problems and learn about symptoms,\n                            causes and prevention.\n                        </p>', '<p data-i18n="feature_disease_desc">\n                            Upload a plant image to identify possible\n                            plant health problems and learn about symptoms,\n                            causes and prevention.\n                        </p>'],
  ['<a href="login.html" class="feature-link">\n                            Learn More →\n                        </a>', '<a href="login.html" class="feature-link" data-i18n="feature_learn_more_link">\n                            Learn More →\n                        </a>'],

  ['<h3>\n                            Irrigation Guidance\n                        </h3>', '<h3 data-i18n="feature_irrigation_title">\n                            Irrigation Guidance\n                        </h3>'],
  ['<p>\n                            Get useful information about watering your\n                            crops and managing irrigation.\n                        </p>', '<p data-i18n="feature_irrigation_desc">\n                            Get useful information about watering your\n                            crops and managing irrigation.\n                        </p>'],

  ['<h3>\n                            Weather Information\n                        </h3>', '<h3 data-i18n="feature_weather_title">\n                            Weather Information\n                        </h3>'],
  ['<p>\n                            Check weather information that can help you\n                            make better farming decisions.\n                        </p>', '<p data-i18n="feature_weather_desc">\n                            Check weather information that can help you\n                            make better farming decisions.\n                        </p>'],
  ['<a href="login.html" class="feature-link">\n                            Check Weather →\n                        </a>', '<a href="login.html" class="feature-link" data-i18n="feature_check_weather_link">\n                            Check Weather →\n                        </a>'],

  ['<h3>\n                            Farmer Assistant\n                        </h3>', '<h3 data-i18n="feature_assistant_title">\n                            Farmer Assistant\n                        </h3>'],
  ['<p>\n                            Ask farming-related questions and get useful\n                            guidance through the AgriSmart Assistant.\n                        </p>', '<p data-i18n="feature_assistant_desc">\n                            Ask farming-related questions and get useful\n                            guidance through the AgriSmart Assistant.\n                        </p>'],
  ['<a href="login.html" class="feature-link">\n                            Ask Assistant →\n                        </a>', '<a href="login.html" class="feature-link" data-i18n="feature_ask_assistant_link">\n                            Ask Assistant →\n                        </a>'],

  ['<h3>\n                            Diagnosis History\n                        </h3>', '<h3 data-i18n="feature_history_title">\n                            Diagnosis History\n                        </h3>'],
  ['<p>\n                            Keep track of previous plant health checks\n                            and review your farming history.\n                        </p>', '<p data-i18n="feature_history_desc">\n                            Keep track of previous plant health checks\n                            and review your farming history.\n                        </p>'],
  ['<a href="login.html" class="feature-link">\n                            View History →\n                        </a>', '<a href="login.html" class="feature-link" data-i18n="card_history_link">\n                            View History →\n                        </a>'],

  // How it works
  ['<span class="section-label">\n                        HOW IT WORKS\n                    </span>', '<span class="section-label" data-i18n="how_it_works_label">\n                        HOW IT WORKS\n                    </span>'],
  ['<h2>\n                        Start Using AgriSmart in Four Simple Steps\n                    </h2>', '<h2 data-i18n="how_it_works_title">\n                        Start Using AgriSmart in Four Simple Steps\n                    </h2>'],
  ['<p>\n                        The platform is designed to keep the farming\n                        process simple and easy to understand.\n                    </p>', '<p data-i18n="how_it_works_subtitle">\n                        The platform is designed to keep the farming\n                        process simple and easy to understand.\n                    </p>'],
  ['<h3>\n                            Create Your Account\n                        </h3>', '<h3 data-i18n="step_1_heading">\n                            Create Your Account\n                        </h3>'],
  ['<p>\n                            Register using your mobile number or\n                            email address and access your farmer dashboard.\n                        </p>', '<p data-i18n="step_1_text">\n                            Register using your mobile number or\n                            email address and access your farmer dashboard.\n                        </p>'],
  ['<h3>\n                            Add Your Crop\n                        </h3>', '<h3 data-i18n="step_2_heading">\n                            Add Your Crop\n                        </h3>'],
  ['<p>\n                            Add crop details such as crop name,\n                            variety, planting date and field information.\n                        </p>', '<p data-i18n="step_2_text">\n                            Add crop details such as crop name,\n                            variety, planting date and field information.\n                        </p>'],
  ['<h3>\n                            Check or Ask\n                        </h3>', '<h3 data-i18n="step_3_heading">\n                            Check or Ask\n                        </h3>'],
  ['<p>\n                            Upload a plant image, check farming\n                            information or ask the Farmer Assistant.\n                        </p>', '<p data-i18n="step_3_text">\n                            Upload a plant image, check farming\n                            information or ask the Farmer Assistant.\n                        </p>'],
  ['<h3>\n                            Get Useful Guidance\n                        </h3>', '<h3 data-i18n="step_4_heading">\n                            Get Useful Guidance\n                        </h3>'],
  ['<p>\n                            View possible plant problems, farming\n                            information, treatment options and prevention.\n                        </p>', '<p data-i18n="step_4_text">\n                            View possible plant problems, farming\n                            information, treatment options and prevention.\n                        </p>'],

  // Flow
  ['<h3>\n                                Plant Health Analysis Flow\n                            </h3>', '<h3 data-i18n="flow_title">\n                                Plant Health Analysis Flow\n                            </h3>'],
  ['<p>\n                                Understand what happens when you check\n                                a plant image.\n                            </p>', '<p data-i18n="flow_desc">\n                                Understand what happens when you check\n                                a plant image.\n                            </p>'],
  ['<strong>Upload Image</strong>', '<strong data-i18n="flow_upload">Upload Image</strong>'],
  ['<strong>Analyze</strong>', '<strong data-i18n="flow_analyze">Analyze</strong>'],
  ['<strong>Possible Problem</strong>', '<strong data-i18n="flow_problem">Possible Problem</strong>'],
  ['<strong>Symptoms & Causes</strong>', '<strong data-i18n="flow_symptoms">Symptoms & Causes</strong>'],
  ['<strong>Treatment & Prevention</strong>', '<strong data-i18n="flow_treatment">Treatment & Prevention</strong>'],

  // For farmers actions
  ['<span class="section-label">\n                        FOR FARMERS\n                    </span>', '<span class="section-label" data-i18n="for_farmers_label">\n                        FOR FARMERS\n                    </span>'],
  ['<h2>\n                        What Would You Like to Do?\n                    </h2>', '<h2 data-i18n="what_would_you_like_title">\n                        What Would You Like to Do?\n                    </h2>'],
  ['<p>\n                        Choose what you need help with.\n                    </p>', '<p data-i18n="what_would_you_like_desc">\n                        Choose what you need help with.\n                    </p>'],
  ['<h3>\n                                "I want to manage my crops"\n                            </h3>', '<h3 data-i18n="farmer_action_crops">\n                                "I want to manage my crops"\n                            </h3>'],
  ['<p>\n                                Add and manage your crop information.\n                            </p>', '<p data-i18n="farmer_action_crops_desc">\n                                Add and manage your crop information.\n                            </p>'],
  ['<a href="login.html">\n                            Open →\n                        </a>', '<a href="login.html" data-i18n="btn_open">\n                            Open →\n                        </a>'],

  ['<h3>\n                                "My plant looks unhealthy"\n                            </h3>', '<h3 data-i18n="farmer_action_disease">\n                                "My plant looks unhealthy"\n                            </h3>'],
  ['<p>\n                                Check a plant image for possible problems.\n                            </p>', '<p data-i18n="farmer_action_disease_desc">\n                                Check a plant image for possible problems.\n                            </p>'],
  ['<a href="login.html">\n                            Check →\n                        </a>', '<a href="login.html" data-i18n="btn_check">\n                            Check →\n                        </a>'],

  ['<h3>\n                                "I want irrigation guidance"\n                            </h3>', '<h3 data-i18n="farmer_action_irrigation">\n                                "I want irrigation guidance"\n                            </h3>'],
  ['<p>\n                                Get useful information about watering crops.\n                            </p>', '<p data-i18n="farmer_action_irrigation_desc">\n                                Get useful information about watering crops.\n                            </p>'],
  ['<a href="login.html">\n                            Explore →\n                        </a>', '<a href="login.html" data-i18n="btn_explore">\n                            Explore →\n                        </a>'],

  ['<h3>\n                                "I want to check the weather"\n                            </h3>', '<h3 data-i18n="farmer_action_weather">\n                                "I want to check the weather"\n                            </h3>'],
  ['<p>\n                                View weather information for farming.\n                            </p>', '<p data-i18n="farmer_action_weather_desc">\n                                View weather information for farming.\n                            </p>'],

  ['<h3>\n                                "I have a farming question"\n                            </h3>', '<h3 data-i18n="farmer_action_assistant">\n                                "I have a farming question"\n                            </h3>'],
  ['<p>\n                                Ask the AgriSmart Farmer Assistant.\n                            </p>', '<p data-i18n="farmer_action_assistant_desc">\n                                Ask the AgriSmart Farmer Assistant.\n                            </p>'],
  ['<a href="login.html">\n                            Ask →\n                        </a>', '<a href="login.html" data-i18n="btn_ask">\n                            Ask →\n                        </a>'],

  ['<h3>\n                                "I want to see my history"\n                            </h3>', '<h3 data-i18n="farmer_action_history">\n                                "I want to see my history"\n                            </h3>'],
  ['<p>\n                                Review your previous plant health checks.\n                            </p>', '<p data-i18n="farmer_action_history_desc">\n                                Review your previous plant health checks.\n                            </p>'],
  ['<a href="login.html">\n                            View →\n                        </a>', '<a href="login.html" data-i18n="btn_view">\n                            View →\n                        </a>'],

  // Why
  ['<span class="section-label">\n                            WHY AGRISMART?\n                        </span>', '<span class="section-label" data-i18n="why_agrismart_label">\n                            WHY AGRISMART?\n                        </span>'],
  ['<h2>\n                            One Simple Platform for Everyday Farming Support\n                        </h2>', '<h2 data-i18n="why_agrismart_title">\n                            One Simple Platform for Everyday Farming Support\n                        </h2>'],
  ['<p>\n                            AgriSmart brings useful farming tools together\n                            so farmers can access crop information,\n                            plant health guidance, weather information,\n                            irrigation support and farming assistance\n                            from one place.\n                        </p>', '<p data-i18n="why_agrismart_desc">\n                            AgriSmart brings useful farming tools together\n                            so farmers can access crop information,\n                            plant health guidance, weather information,\n                            irrigation support and farming assistance\n                            from one place.\n                        </p>'],
  ['<strong>Simple Interface</strong>', '<strong data-i18n="why_point1_title">Simple Interface</strong>'],
  ['<p>\n                                    Designed to be easy to understand\n                                    and use.\n                                </p>', '<p data-i18n="why_point1_desc">\n                                    Designed to be easy to understand\n                                    and use.\n                                </p>'],
  ['<strong>Farmer Focused</strong>', '<strong data-i18n="why_point2_title">Farmer Focused</strong>'],
  ['<p>\n                                    Built around common farming needs.\n                                </p>', '<p data-i18n="why_point2_desc">\n                                    Built around common farming needs.\n                                </p>'],
  ['<strong>Multiple Farming Tools</strong>', '<strong data-i18n="why_point3_title">Multiple Farming Tools</strong>'],
  ['<p>\n                                    Crop, plant health, weather,\n                                    irrigation and assistance.\n                                </p>', '<p data-i18n="why_point3_desc">\n                                    Crop, plant health, weather,\n                                    irrigation and assistance.\n                                </p>'],
  ['<strong>Language Support</strong>', '<strong data-i18n="why_point4_title">Language Support</strong>'],
  ['<p>\n                                    Designed with multilingual support\n                                    in mind.\n                                </p>', '<p data-i18n="why_point4_desc">\n                                    Designed with multilingual support\n                                    in mind.\n                                </p>'],

  // About
  ['<span class="section-label">\n                        ABOUT AGRISMART\n                    </span>', '<span class="section-label" data-i18n="about_label">\n                        ABOUT AGRISMART\n                    </span>'],
  ['<h2>\n                        Technology Designed Around Farmers\n                    </h2>', '<h2 data-i18n="about_tech_title">\n                        Technology Designed Around Farmers\n                    </h2>'],
  ['<p>\n                        AgriSmart is a farmer-focused digital platform\n                        designed to make everyday farming information\n                        easier to access and understand.\n                    </p>', '<p data-i18n="about_tech_desc">\n                        AgriSmart is a farmer-focused digital platform\n                        designed to make everyday farming information\n                        easier to access and understand.\n                    </p>'],
  ['<h3>Crop Management</h3>', '<h3 data-i18n="about_feat_crops">Crop Management</h3>'],
  ['<h3>Plant Health</h3>', '<h3 data-i18n="about_feat_health">Plant Health</h3>'],
  ['<h3>Weather</h3>', '<h3 data-i18n="about_feat_weather">Weather</h3>'],
  ['<h3>Irrigation</h3>', '<h3 data-i18n="about_feat_irrigation">Irrigation</h3>'],
  ['<h3>Farmer Assistance</h3>', '<h3 data-i18n="about_feat_assistant">Farmer Assistance</h3>'],

  // CTA
  ['<h2>\n                    Ready to Start?\n                </h2>', '<h2 data-i18n="ready_start_title">\n                    Ready to Start?\n                </h2>'],
  ['<p>\n                    Create your account and start exploring\n                    AgriSmart farming tools.\n                </p>', '<p data-i18n="ready_start_desc">\n                    Create your account and start exploring\n                    AgriSmart farming tools.\n                </p>'],
  ['<a href="login.html" class="cta-button">\n                    Get Started →\n                </a>', '<a href="login.html" class="cta-button" data-i18n="get_started_arrow">\n                    Get Started →\n                </a>'],

  // Footer
  ['<p>\n                    Smart Farming Made Simple.\n                </p>', '<p data-i18n="made_simple">\n                    Smart Farming Made Simple.\n                </p>']
];

for (const [target, replacement] of replacements) {
  if (html.includes(target)) {
    html = html.replace(target, replacement);
  } else {
    console.log('Target not found:', target.slice(0, 40));
  }
}

fs.writeFileSync('index.html', html);
console.log('Annotated index.html successfully');
