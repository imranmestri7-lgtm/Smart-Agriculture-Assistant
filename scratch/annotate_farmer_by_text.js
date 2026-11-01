const fs = require('fs');

let html = fs.readFileSync('farmer.html', 'utf8');

const textToKey = [
  ["MY FARMS &amp; CROPS", "badge_my_farms_crops"],
  ["Filter by Farm:", "lbl_filter_by_farm"],
  ["SMART ANALYTICS &amp; INSIGHTS", "badge_smart_analytics"],
  ["Total Water Usage", "stat_total_water"],
  ["Irrigation Needed", "stat_irrigation_needed"],
  ["Sufficient Moisture", "stat_sufficient_moisture"],
  ["SMART ALERTS &amp; REMINDERS", "badge_smart_alerts"],
  ["IoT-READY SENSOR NETWORK", "badge_iot_network"],
  ["IoT Telemetry Hub", "title_telemetry_hub"],
  ["Refresh Telemetry", "btn_refresh_telemetry"],
  ["No Sensor", "telemetry_no_sensor"],
  ["DEMO", "telemetry_demo_badge"],
  ["24 Hours", "filter_24h"],
  ["7 Days", "filter_7d"],
  ["30 Days", "filter_30d"],
  ["All", "filter_all"],
  ["Min:", "stat_min"],
  ["Avg:", "stat_avg"],
  ["Max:", "stat_max"],
  ["Readings:", "stat_readings"],
  ["Endpoint:", "hw_endpoint_label"],
  ["Headers:", "hw_headers_label"],
  ["Sample Soil Moisture JSON Payload:", "hw_sample_payload"],
  ["Sample Combined DHT22 Payload:", "hw_sample_dht22"],
  ["AGRICULTURE ASSISTANT", "assistant_tag"],
  ["Think", "msg_think"],
  ["🍃 Upload Leaf Image", "btn_upload_leaf"],
  ["📎 Upload File", "btn_upload_file"],
  ["📷 Use Camera", "btn_use_camera"],
  ["-- Choose Farm --", "opt_choose_farm"],
  ["Loading farms...", "opt_loading_farms"],
  ["🌾 Assigned Crop (Optional)", "lbl_assigned_crop"],
  ["-- Optional: Assign Crop --", "opt_optional_assign_crop"],
  ["🏷️ Sensor Name", "lbl_sensor_name"],
  ["📡 Sensor Type", "lbl_sensor_type"],
  ["🆔 Unique Device ID", "lbl_device_id"],
  ["⚠️ Important Security Notice:", "security_notice_title"],
  ["Device ID:", "lbl_device_id"],
  ["Secret Device API Key:", "lbl_secret_key"],
  ["📋 Copy", "btn_copy"],
  ["I Have Saved This Key", "btn_saved_key"],
  ["[Demo Data]", "demo_data_badge"],
  ["Target Sensor", "lbl_target_sensor"],
  ["-- Choose Sensor --", "opt_choose_sensor"],
  ["Sample Telemetry Value", "lbl_sample_telemetry"],
  ["Inject Reading", "btn_inject_reading"],
  ["IoT Ready", "badge_iot_ready"],
  ["Farmer Assistant", "card_assistant_title"],
  ["Ask questions about crops, pests, irrigation, weather and farming.", "card_assistant_desc"],
  ["Ask Assistant →", "card_assistant_link"],
  ["Harvest readiness, growth stage care, and crop record updates.", "prefs_crop_desc"],
  ["Soil moisture deficit warnings and water recommendations.", "prefs_irrigation_desc"],
  ["Heavy rain advisories and high temperature warnings.", "prefs_weather_desc"],
  ["Diagnosis follow-ups, field sanitation, and inspection advice.", "prefs_disease_desc"],
  ["Must be unique across your hardware devices (letters, digits, dashes).", "sensor_id_hint"]
];

for (const [txt, key] of textToKey) {
  // Escape for regex
  const escaped = txt.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(<([a-zA-Z0-9]+)([^>]*)>\\s*)(${escaped})(\\s*<\\/\\2>)`, 'g');
  html = html.replace(regex, (match, p1, tag, attrs, text, p5) => {
    if (attrs.includes('data-i18n')) return match;
    return `${p1.replace(/>$/, ` data-i18n="${key}">`)}${text}${p5}`;
  });
}

fs.writeFileSync('farmer.html', html);
console.log('Successfully annotated farmer.html by text matching');
