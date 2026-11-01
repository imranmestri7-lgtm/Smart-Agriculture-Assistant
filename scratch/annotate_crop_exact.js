const fs = require('fs');

let html = fs.readFileSync('crop.html', 'utf8');

const reps = [
  ['<button class="profile-btn" onclick="window.location.href=\'farmer.html\'">\n                Farmer\n            </button>', '<button class="profile-btn" onclick="window.location.href=\'farmer.html\'" data-i18n="farmer_role">\n                Farmer\n            </button>'],
  ['<span class="hero-tag">\n                    SMART AGRICULTURE\n                </span>', '<span class="hero-tag" data-i18n="crop_rec_badge">\n                    SMART AGRICULTURE\n                </span>'],
  ['<h1>\n                    Find the Best Crop\n                    <span>for Your Soil</span>\n                </h1>', '<h1>\n                    <span data-i18n="crop_rec_title_main">Crop Recommendation</span>\n                    <span data-i18n="crop_rec_title_sub">for Your Soil</span>\n                </h1>'],
  ['<p>\n                    Make smarter farming decisions using soil,\n                    weather and agricultural data.\n                </p>', '<p data-i18n="crop_rec_desc">\n                    Make smarter farming decisions using soil,\n                    weather and agricultural data.\n                </p>'],
  ['<span>✓ Soil Analysis</span>', '<span data-i18n="pill_soil_analysis">✓ Soil Analysis</span>'],
  ['<span>✓ Smart Recommendation</span>', '<span data-i18n="pill_smart_rec">✓ Smart Recommendation</span>'],
  ['<span>✓ Data Driven</span>', '<span data-i18n="pill_data_driven">✓ Data Driven</span>'],
  ['<span class="header-label">\n                        SMART AGRICULTURE\n                    </span>', '<span class="header-label" data-i18n="crop_rec_badge">\n                        SMART AGRICULTURE\n                    </span>'],
  ['<h2>\n                        Soil & Environmental Data\n                    </h2>', '<h2 data-i18n="crop_form_title">\n                        Soil & Environmental Data\n                    </h2>'],
  ['<p>\n                        Provide accurate field conditions for a smarter crop recommendation.\n                    </p>', '<p data-i18n="crop_form_desc">\n                        Provide accurate field conditions for a smarter crop recommendation.\n                    </p>'],
  ['<span>STEP</span>', '<span data-i18n="step_label">STEP</span>'],
  ['<h3>\n                                Soil Nutrients\n                            </h3>', '<h3 data-i18n="step_nutrients">\n                                Soil Nutrients\n                            </h3>'],
  ['<p>\n                                Enter the nutrient levels available in your soil.\n                            </p>', '<p data-i18n="step_nutrients_desc">\n                                Enter the nutrient levels available in your soil.\n                            </p>'],
  ['<label for="nitrogen">\n                                Nitrogen (N)\n                            </label>', '<label for="nitrogen" data-i18n="lbl_nitrogen">\n                                Nitrogen (N)\n                            </label>'],
  ['<small>\n                                Recommended range: 0–140 kg/ha\n                            </small>', '<small data-i18n="range_n">\n                                Recommended range: 0–140 kg/ha\n                            </small>'],
  ['<label for="phosphorus">\n                                Phosphorus (P)\n                            </label>', '<label for="phosphorus" data-i18n="lbl_phosphorus">\n                                Phosphorus (P)\n                            </label>'],
  ['<small>\n                                Recommended range: 0–145 kg/ha\n                            </small>', '<small data-i18n="range_p">\n                                Recommended range: 0–145 kg/ha\n                            </small>'],
  ['<label for="potassium">\n                                Potassium (K)\n                            </label>', '<label for="potassium" data-i18n="lbl_potassium">\n                                Potassium (K)\n                            </label>'],
  ['<small>\n                                Recommended range: 0–205 kg/ha\n                            </small>', '<small data-i18n="range_k">\n                                Recommended range: 0–205 kg/ha\n                            </small>'],
  ['<label for="ph">\n                                Soil pH\n                            </label>', '<label for="ph" data-i18n="lbl_crop_ph">\n                                Soil pH\n                            </label>'],
  ['<small>\n                                Scale: 0–14\n                            </small>', '<small data-i18n="scale_ph">\n                                Scale: 0–14\n                            </small>'],
  ['<h3>\n                                Environmental Conditions\n                            </h3>', '<h3 data-i18n="step_climate">\n                                Environmental Conditions\n                            </h3>'],
  ['<p>\n                                Enter the current environmental conditions.\n                            </p>', '<p data-i18n="step_climate_desc">\n                                Enter the current environmental conditions.\n                            </p>'],
  ['<label for="temperature">\n                                🌡️ Temperature\n                            </label>', '<label for="temperature" data-i18n="lbl_crop_temp">\n                                🌡️ Temperature\n                            </label>'],
  ['<small>\n                                Unit: °C\n                            </small>', '<small data-i18n="unit_c">\n                                Unit: °C\n                            </small>'],
  ['<label for="humidity">\n                                💧 Humidity\n                            </label>', '<label for="humidity" data-i18n="lbl_crop_humidity">\n                                💧 Humidity\n                            </label>'],
  ['<small>\n                                Unit: %\n                            </small>', '<small data-i18n="unit_pct">\n                                Unit: %\n                            </small>'],
  ['<label for="rainfall">\n                                🌧️ Rainfall\n                            </label>', '<label for="rainfall" data-i18n="lbl_crop_rainfall">\n                                🌧️ Rainfall\n                            </label>'],
  ['<small>\n                                Unit: mm\n                            </small>', '<small data-i18n="unit_mm">\n                                Unit: mm\n                            </small>'],
  ['<label for="location">\n                                📍 Location\n                            </label>', '<label for="location" data-i18n="location_label">\n                                📍 Location\n                            </label>'],
  ['<option value="">\n                                    Select location\n                                </option>', '<option value="" data-i18n="select_location_placeholder">\n                                    Select location\n                                </option>'],
  ['<option value="maharashtra">\n                                    Maharashtra\n                                </option>', '<option value="maharashtra" data-i18n="opt_loc_maharashtra">\n                                    Maharashtra\n                                </option>'],
  ['<option value="karnataka">\n                                    Karnataka\n                                </option>', '<option value="karnataka" data-i18n="opt_loc_karnataka">\n                                    Karnataka\n                                </option>'],
  ['<option value="goa">\n                                    Goa\n                                </option>', '<option value="goa" data-i18n="opt_loc_goa">\n                                    Goa\n                                </option>'],
  ['<option value="gujarat">\n                                    Gujarat\n                                </option>', '<option value="gujarat" data-i18n="opt_loc_gujarat">\n                                    Gujarat\n                                </option>'],
  ['<option value="other">\n                                    Other\n                                </option>', '<option value="other" data-i18n="opt_loc_other">\n                                    Other\n                                </option>'],
  ['<small>\n                                Select your farming region\n                            </small>', '<small data-i18n="desc_location">\n                                Select your farming region\n                            </small>'],
  ['<button\n                        type="reset"\n                        class="reset-button"\n                    >\n                        ↺ Reset\n                    </button>', '<button\n                        type="reset"\n                        class="reset-button"\n                        data-i18n="btn_reset"\n                    >\n                        ↺ Reset\n                    </button>'],
  ['<button\n                        type="submit"\n                        class="recommend-button"\n                    >\n                        🌱 Analyze & Recommend\n                    </button>', '<button\n                        type="submit"\n                        class="recommend-button"\n                        data-i18n="btn_analyze_recommend"\n                    >\n                        🌱 Analyze & Recommend\n                    </button>'],
  ['<h3>\n                        Why do we need this information?\n                    </h3>', '<h3 data-i18n="why_need_info_title">\n                        Why do we need this information?\n                    </h3>'],
  ['<p>\n                        Soil nutrients, pH, temperature, humidity and rainfall\n                        influence crop growth. These values help our system\n                        understand the farming conditions and recommend a\n                        suitable crop.\n                    </p>', '<p data-i18n="why_need_info_desc">\n                        Soil nutrients, pH, temperature, humidity and rainfall help us recommend the most suitable crop for your field.\n                    </p>'],
  ['<span>\n                            🌱 Better crop selection\n                        </span>', '<span data-i18n="benefit_better_crop">\n                            🌱 Better crop selection\n                        </span>'],
  ['<span>\n                            💧 Understand soil conditions\n                        </span>', '<span data-i18n="benefit_understand_soil">\n                            💧 Understand soil conditions\n                        </span>'],
  ['<span>\n                            📊 Data-driven recommendation\n                        </span>', '<span data-i18n="benefit_data_driven">\n                            📊 Data-driven recommendation\n                        </span>']
];

for (const [target, repl] of reps) {
  if (html.includes(target)) {
    html = html.replace(target, repl);
  } else {
    console.log('Target not found in crop.html:', target.slice(0, 40));
  }
}

// Add placeholders
html = html
  .replace('placeholder="Enter nitrogen level"', 'data-i18n-placeholder="ph_nitrogen" placeholder="Enter nitrogen level"')
  .replace('placeholder="Enter phosphorus level"', 'data-i18n-placeholder="ph_phosphorus" placeholder="Enter phosphorus level"')
  .replace('placeholder="Enter potassium level"', 'data-i18n-placeholder="ph_potassium" placeholder="Enter potassium level"')
  .replace('placeholder="Enter soil pH"', 'data-i18n-placeholder="ph_ph" placeholder="Enter soil pH"')
  .replace('placeholder="Enter temperature"', 'data-i18n-placeholder="ph_temp" placeholder="Enter temperature"')
  .replace('placeholder="Enter humidity"', 'data-i18n-placeholder="ph_humidity" placeholder="Enter humidity"')
  .replace('placeholder="Enter rainfall"', 'data-i18n-placeholder="ph_rainfall" placeholder="Enter rainfall"');

fs.writeFileSync('crop.html', html);
console.log('Annotated crop.html successfully');
