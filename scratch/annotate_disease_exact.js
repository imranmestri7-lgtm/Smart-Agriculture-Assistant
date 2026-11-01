const fs = require('fs');

let html = fs.readFileSync('disease.html', 'utf8');

// Replace using flexible whitespace regexes or multiline strings
const reps = [
  [/<span class="hero-badge">\s*🌿 AI-Powered Agriculture\s*<\/span>/, '<span class="hero-badge" data-i18n="disease_badge">\n                    🌿 AI-Powered Agriculture\n                </span>'],
  [/<h1>\s*Plant Disease Detection\s*<\/h1>/, '<h1 data-i18n="disease_hero_title">\n                    Plant Disease Detection\n                </h1>'],
  [/<p>\s*Upload or capture a crop leaf image\s*and let our AI system help identify\s*possible plant diseases\.\s*<\/p>/, '<p data-i18n="disease_hero_desc">\n                    Upload or capture a crop leaf image\n                    and let our AI system help identify\n                    possible plant diseases.\n                </p>'],
  [/<a\s+href="#scanner"\s+class="hero-button">\s*Start Disease Scan →\s*<\/a>/, '<a\n                    href="#scanner"\n                    class="hero-button"\n                    data-i18n="disease_hero_btn">\n\n                    Start Disease Scan →\n\n                </a>'],
  [/<span class="small-title">\s*SMART SCANNER\s*<\/span>/, '<span class="small-title" data-i18n="scanner_badge">\n                            SMART SCANNER\n                        </span>'],
  [/<h2>\s*Disease Scanner\s*<\/h2>/, '<h2 data-i18n="scanner_title">\n                            Disease Scanner\n                        </h2>'],
  [/<p>\s*Provide a clear image of the\s*affected leaf\.\s*<\/p>/, '<p data-i18n="scanner_desc">\n                            Provide a clear image of the\n                            affected leaf.\n                        </p>'],
  [/<span>\s*\(Optional\)\s*<\/span>/, '<span data-i18n="lbl_optional">\n                            (Optional)\n                        </span>'],
  [/<option value="">\s*Select Crop\s*<\/option>/, '<option value="" data-i18n="opt_select_crop">\n                            Select Crop\n                        </option>'],
  [/<option value="tomato">\s*Tomato\s*<\/option>/, '<option value="tomato" data-i18n="opt_crop_tomato">\n                            Tomato\n                        </option>'],
  [/<option value="potato">\s*Potato\s*<\/option>/, '<option value="potato" data-i18n="opt_crop_potato">\n                            Potato\n                        </option>'],
  [/<option value="rice">\s*Rice\s*<\/option>/, '<option value="rice" data-i18n="opt_crop_rice">\n                            Rice\n                        </option>'],
  [/<option value="wheat">\s*Wheat\s*<\/option>/, '<option value="wheat" data-i18n="opt_crop_wheat">\n                            Wheat\n                        </option>'],
  [/<option value="maize">\s*Maize\s*<\/option>/, '<option value="maize" data-i18n="opt_crop_corn">\n                            Maize\n                        </option>'],
  [/<option value="cotton">\s*Cotton\s*<\/option>/, '<option value="cotton" data-i18n="opt_crop_cotton">\n                            Cotton\n                        </option>'],
  [/<h3>\s*Add Leaf Image\s*<\/h3>/, '<h3 data-i18n="lbl_add_leaf_image">\n                            Add Leaf Image\n                        </h3>'],
  [/<p>\s*Choose a clear image of\s*the affected leaf\.\s*<\/p>/, '<p data-i18n="desc_choose_clear_image">\n                            Choose a clear image of\n                            the affected leaf.\n                        </p>'],
  [/<label\s+for="leafImage"\s+class="upload-btn">\s*📁 Upload Image\s*<\/label>/, '<label\n                            for="leafImage"\n                            class="upload-btn"\n                            data-i18n="btn_upload_image">\n\n                            📁 Upload Image\n\n                        </label>'],
  [/<button\s+type="button"\s+class="camera-btn"\s+id="cameraButton">\s*📷 Use Camera\s*<\/button>/, '<button\n                            type="button"\n                            class="camera-btn"\n                            id="cameraButton"\n                            data-i18n="btn_use_camera">\n\n                            📷 Use Camera\n\n                        </button>'],
  [/<h3>\s*Image Ready\s*<\/h3>/, '<h3 data-i18n="lbl_image_ready">\n                            Image Ready\n                        </h3>'],
  [/<p>\s*Your leaf image is ready\s*for analysis\.\s*<\/p>/, '<p data-i18n="desc_image_ready">\n                            Your leaf image is ready\n                            for analysis.\n                        </p>'],
  [/<button\s+type="button"\s+id="captureButton"\s+class="capture-btn">\s*📸 Capture Leaf\s*<\/button>/, '<button\n                            type="button"\n                            id="captureButton"\n                            class="capture-btn"\n                            data-i18n="btn_capture_leaf">\n\n                            📸 Capture Leaf\n\n                        </button>'],
  [/<button\s+type="button"\s+id="closeCameraButton"\s+class="close-camera-btn">\s*✕ Close Camera\s*<\/button>/, '<button\n                            type="button"\n                            id="closeCameraButton"\n                            class="close-camera-btn"\n                            data-i18n="btn_close_camera">\n\n                            ✕ Close Camera\n\n                        </button>'],
  [/<button\s+type="button"\s+class="analyze-btn"\s+id="analyzeButton">\s*🔍 Analyze Disease\s*<\/button>/, '<button\n                    type="button"\n                    class="analyze-btn"\n                    id="analyzeButton"\n                    data-i18n="btn_analyze_disease">\n\n                    🔍 Analyze Disease\n\n                </button>'],
  [/<p class="analysis-note">\s*Your image will be analyzed using\s*the AI disease detection system\.\s*<\/p>/, '<p class="analysis-note" data-i18n="note_model_analysis">\n\n                    Your image will be analyzed using\n                    the AI disease detection system.\n\n                </p>'],
  [/<span class="small-title">\s*BETTER RESULTS\s*<\/span>/, '<span class="small-title" data-i18n="badge_better_results">\n                            BETTER RESULTS\n                        </span>'],
  [/<h2>\s*Tips for Better Detection\s*<\/h2>/, '<h2 data-i18n="title_detection_tips">\n                            Tips for Better Detection\n                        </h2>'],
  [/<h3>\s*Good Lighting\s*<\/h3>/, '<h3 data-i18n="tip_lighting_title">\n                            Good Lighting\n                        </h3>'],
  [/<p>\s*Take the photo in clear\s*natural light\.\s*<\/p>/, '<p data-i18n="tip_lighting_desc">\n                            Take the photo in clear\n                            natural light.\n                        </p>'],
  [/<h3>\s*Focus on Leaf\s*<\/h3>/, '<h3 data-i18n="tip_focus_title">\n                            Focus on Leaf\n                        </h3>'],
  [/<p>\s*Make sure the affected leaf\s*is clearly visible\.\s*<\/p>/, '<p data-i18n="tip_focus_desc">\n                            Make sure the affected leaf\n                            is clearly visible.\n                        </p>'],
  [/<h3>\s*Clear Image\s*<\/h3>/, '<h3 data-i18n="tip_clear_title">\n                            Clear Image\n                        </h3>'],
  [/<p>\s*Avoid blurry or low-quality\s*photos\.\s*<\/p>/, '<p data-i18n="tip_clear_desc">\n                            Avoid blurry or low-quality\n                            photos.\n                        </p>'],
  [/<h3>\s*Show Symptoms\s*<\/h3>/, '<h3 data-i18n="tip_symptoms_title">\n                            Show Symptoms\n                        </h3>'],
  [/<p>\s*Capture spots or damage\s*clearly\.\s*<\/p>/, '<p data-i18n="tip_symptoms_desc">\n                            Capture spots or damage\n                            clearly.\n                        </p>'],
  [/<span class="small-title">\s*PROTECT YOUR CROP\s*<\/span>/, '<span class="small-title" data-i18n="badge_protect_crop">\n                            PROTECT YOUR CROP\n                        </span>'],
  [/<h2>\s*Why Early Detection\?\s*<\/h2>/, '<h2 data-i18n="title_why_early">\n                            Why Early Detection?\n                        </h2>'],
  [/<h3>\s*Identify Problems Early\s*<\/h3>/, '<h3 data-i18n="early_step1_title">\n                            Identify Problems Early\n                        </h3>'],
  [/<p>\s*Detect possible diseases before\s*they spread throughout the crop\.\s*<\/p>/, '<p data-i18n="early_step1_desc">\n                            Detect possible diseases before\n                            they spread throughout the crop.\n                        </p>'],
  [/<h3>\s*Get Suitable Guidance\s*<\/h3>/, '<h3 data-i18n="early_step2_title">\n                            Get Suitable Guidance\n                        </h3>'],
  [/<p>\s*Understand possible treatment\s*and management practices\.\s*<\/p>/, '<p data-i18n="early_step2_desc">\n                            Understand possible treatment\n                            and management practices.\n                        </p>'],
  [/<h3>\s*Protect Your Crop\s*<\/h3>/, '<h3 data-i18n="early_step3_title">\n                            Protect Your Crop\n                        </h3>'],
  [/<p>\s*Take timely action and reduce\s*the risk of disease spreading\.\s*<\/p>/, '<p data-i18n="early_step3_desc">\n                            Take timely action and reduce\n                            the risk of disease spreading.\n                        </p>'],
  [/<span class="small-title">\s*SMART FARMER ASSISTANT\s*<\/span>/, '<span class="small-title" data-i18n="badge_smart_assistant">\n                        SMART FARMER ASSISTANT\n                    </span>'],
  [/<h2>\s*Get Your Disease Guidance\s*Through Farmer Assistant\s*<\/h2>/, '<h2 data-i18n="title_guidance_awaiting">\n                        Get Your Disease Guidance\n                        Through Farmer Assistant\n                    </h2>'],
  [/<p>\s*After disease analysis, the\s*Farmer Assistant will provide\s*disease information, symptoms,\s*treatment and prevention guidance\.\s*<\/p>/, '<p data-i18n="desc_guidance_awaiting">\n                        After disease analysis, the\n                        Farmer Assistant will provide\n                        disease information, symptoms,\n                        treatment and prevention guidance.\n                    </p>'],
  [/<button\s+type="button"\s+class="scan-again-btn"\s+id="scanAgainButton">\s*🔄 Scan Another Leaf\s*<\/button>/, '<button\n                type="button"\n                class="scan-again-btn"\n                id="scanAgainButton"\n                data-i18n="btn_scan_another">\n\n                🔄 Scan Another Leaf\n\n            </button>'],
  [/<p id="diagnosisHistoryMessage" role="status" aria-live="polite"[^>]*>\s*Loading diagnosis history\.\.\.\s*<\/p>/, '<p id="diagnosisHistoryMessage" role="status" aria-live="polite" style="font-size:14px; color:#475569; margin:15px 0;" data-i18n="history_loading">\n            Loading diagnosis history...\n        </p>']
];

for (const [regex, replacement] of reps) {
  if (regex.test(html)) {
    html = html.replace(regex, replacement);
  } else {
    console.log('Regex did not match in disease.html:', regex);
  }
}

fs.writeFileSync('disease.html', html);
console.log('Finished updating disease.html');
