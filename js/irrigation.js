/**
 * AgriSmart - Smart Irrigation Frontend Controller
 * Feature Upgrade 3: Smart Irrigation Recommendation System
 *
 * Handles:
 * - Crop, soil type, and growth-stage-aware input validation
 * - Live IoT sensor moisture sync & manual input
 * - Qualitative / unmeasured moisture fallback for farmers without sensors
 * - Server-side WeatherAPI proxy auto-fetch (temperature, humidity, recent rain, 48h rain forecast)
 * - 1-Click quick load from farmer's registered crops
 * - Real-time smart recommendation rendering with timing schedule, water savings, and conservation tips
 * - Farmer history & water-saving analytics with delete capability
 * - Full English / Marathi / Hindi multilingual synchronization
 */

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("irrigationForm");
    const checkBtn = document.getElementById("checkIrrigationButton");
    const resetBtn = document.getElementById("resetIrrigationButton");
    const buttonText = document.getElementById("buttonText");
    const alertBox = document.getElementById("irrigationAlert");
    const initialPlaceholder = document.getElementById("initialPlaceholder");
    const dynamicResultCard = document.getElementById("dynamicResultCard");
    const startHeroBtn = document.getElementById("startIrrigationButton");

    // Inputs
    const cropSelect = document.getElementById("crop");
    const soilTypeSelect = document.getElementById("soilType");
    const growthStageSelect = document.getElementById("growthStage");
    const soilMoistureInput = document.getElementById("soilMoisture");
    const toggleNoSensor = document.getElementById("toggleNoSensor");
    const noSensorNotice = document.getElementById("noSensorNotice");
    const tempInput = document.getElementById("temperature");
    const humidityInput = document.getElementById("humidity");
    const rainfallInput = document.getElementById("rainfall");
    const forecastRainInput = document.getElementById("forecastRain");
    const locationInput = document.getElementById("location");

    // Live IoT & Weather buttons
    const btnSyncIoT = document.getElementById("btnSyncIoTMmoisture");
    const iotNotice = document.getElementById("iotMoistureNotice");
    const btnFetchWeather = document.getElementById("btnFetchLiveWeather");
    const weatherNotice = document.getElementById("weatherFetchNotice");

    // Quick-load registered crop
    const registeredCropWrapper = document.getElementById("registeredCropWrapper");
    const registeredCropSelect = document.getElementById("registeredCropSelect");

    // History & Stats elements
    const statTotalChecks = document.getElementById("statTotalChecks");
    const statWaterSaved = document.getElementById("statWaterSaved");
    const statNeeded = document.getElementById("statNeeded");
    const statPostponed = document.getElementById("statPostponed");
    const historyList = document.getElementById("historyList");
    const historyLoading = document.getElementById("historyLoading");
    const historyEmpty = document.getElementById("historyEmpty");

    // In-memory active recommendation
    let currentRecommendationData = null;

    // Helper for internationalization
    function t(key, fallback) {
        if (window.i18n && typeof window.i18n.t === "function") {
            return window.i18n.t(key);
        }
        return fallback || key;
    }

    // Scroll hero button to form
    if (startHeroBtn) {
        startHeroBtn.addEventListener("click", function () {
            const formSection = document.getElementById("irrigationFormSection");
            if (formSection) {
                formSection.scrollIntoView({ behavior: "smooth" });
            }
        });
    }

    // Alerts
    function showAlert(message, type = "error") {
        if (!alertBox) return;
        alertBox.textContent = message;
        alertBox.style.display = "block";
        if (type === "error") {
            alertBox.style.backgroundColor = "#fee2e2";
            alertBox.style.color = "#991b1b";
            alertBox.style.border = "1px solid #f87171";
        } else {
            alertBox.style.backgroundColor = "#dcfce7";
            alertBox.style.color = "#166534";
            alertBox.style.border = "1px solid #86efac";
        }
    }

    function clearAlert() {
        if (!alertBox) return;
        alertBox.textContent = "";
        alertBox.style.display = "none";
    }

    // =========================================================================
    // 1. QUALITATIVE / NO SENSOR TOGGLE
    // =========================================================================
    if (toggleNoSensor && soilMoistureInput) {
        toggleNoSensor.addEventListener("change", function () {
            if (toggleNoSensor.checked) {
                soilMoistureInput.value = "";
                soilMoistureInput.disabled = true;
                soilMoistureInput.removeAttribute("required");
                if (noSensorNotice) noSensorNotice.style.display = "block";
                if (iotNotice) iotNotice.style.display = "none";
            } else {
                soilMoistureInput.disabled = false;
                soilMoistureInput.setAttribute("required", "required");
                if (noSensorNotice) noSensorNotice.style.display = "none";
            }
        });
    }

    // =========================================================================
    // 2. LIVE IOT SOIL MOISTURE SYNC
    // =========================================================================
    if (btnSyncIoT) {
        btnSyncIoT.addEventListener("click", async function () {
            const cropVal = cropSelect ? cropSelect.value.trim() : "";
            const token = localStorage.getItem("token") || localStorage.getItem("agriSmartToken");
            if (!token) {
                showAlert(t("err_login_required", "Please log in to sync real IoT sensor readings."), "error");
                return;
            }

            if (toggleNoSensor && toggleNoSensor.checked) {
                toggleNoSensor.checked = false;
                soilMoistureInput.disabled = false;
                soilMoistureInput.setAttribute("required", "required");
                if (noSensorNotice) noSensorNotice.style.display = "none";
            }

            btnSyncIoT.disabled = true;
            btnSyncIoT.textContent = "Checking sensors...";
            try {
                let url = "/api/iot/irrigation-sync?";
                if (cropVal) url += `crop=${encodeURIComponent(cropVal)}`;
                const res = await fetch(url, {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                const data = await res.json();
                if (data.status === "success" && data.has_sensor_data) {
                    if (soilMoistureInput) soilMoistureInput.value = data.soil_moisture;
                    if (iotNotice) {
                        iotNotice.style.display = "block";
                        const tag = data.is_demo ? "[Demo Data]" : "[Live Hardware]";
                        iotNotice.textContent = `✓ Applied ${data.soil_moisture}% from '${data.sensor_name}' (${data.recorded_at}) ${tag}`;
                        iotNotice.style.color = data.is_demo ? "#7c3aed" : "#059669";
                    }
                } else {
                    if (iotNotice) {
                        iotNotice.style.display = "block";
                        iotNotice.textContent = "ℹ️ No recent soil moisture readings found for this crop. Enter manually.";
                        iotNotice.style.color = "#d97706";
                    }
                }
            } catch (err) {
                console.error("IoT sync error:", err);
            } finally {
                btnSyncIoT.disabled = false;
                btnSyncIoT.textContent = t("iot_sync_irrigation_btn", "📡 Use Live IoT Sensor Moisture");
            }
        });
    }

    // =========================================================================
    // 3. FETCH LIVE WEATHER & 48H RAIN FORECAST
    // =========================================================================
    if (btnFetchWeather) {
        btnFetchWeather.addEventListener("click", async function () {
            const locVal = locationInput ? locationInput.value.trim() : "";
            const targetLoc = locVal || "Maharashtra";

            btnFetchWeather.disabled = true;
            btnFetchWeather.textContent = "Fetching weather...";

            try {
                const res = await fetch(`/api/irrigation/weather-preview?location=${encodeURIComponent(targetLoc)}`);
                const data = await res.json();

                if (res.ok && data.status === "success" && data.weather) {
                    const w = data.weather;
                    if (tempInput) tempInput.value = w.temperature;
                    if (humidityInput) humidityInput.value = w.humidity;
                    if (rainfallInput) rainfallInput.value = w.rainfall;
                    if (forecastRainInput) forecastRainInput.value = w.forecast_rain_mm;
                    if (locationInput && !locVal) locationInput.value = w.location_name || targetLoc;

                    if (weatherNotice) {
                        weatherNotice.style.display = "block";
                        weatherNotice.textContent = `✓ Live weather updated: ${w.temperature}°C, ${w.humidity}% RH, Rain: ${w.rainfall}mm, Forecast 48h Rain: ${w.forecast_rain_mm}mm (${w.condition})`;
                    }
                } else {
                    if (weatherNotice) {
                        weatherNotice.style.display = "block";
                        weatherNotice.textContent = `⚠️ Could not fetch live weather: ${data.message || "Provider unavailable"}`;
                        weatherNotice.style.color = "#b91c1c";
                    }
                }
            } catch (err) {
                console.error("Weather preview error:", err);
            } finally {
                btnFetchWeather.disabled = false;
                btnFetchWeather.textContent = t("fetch_live_weather_btn", "⛅ Fetch Live Weather & 48h Rain");
            }
        });
    }

    // =========================================================================
    // 4. LOAD CONTEXT CROPS & REGISTERED FARMS
    // =========================================================================
    async function loadFarmerContextCrops() {
        const token = localStorage.getItem("token") || localStorage.getItem("agriSmartToken");
        try {
            const headers = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch("/api/irrigation/context-crops", { headers });
            const data = await res.json();

            if (res.ok && data.status === "success") {
                const userCrops = data.user_crops || [];
                if (userCrops.length > 0 && registeredCropWrapper && registeredCropSelect) {
                    registeredCropWrapper.style.display = "block";
                    registeredCropSelect.innerHTML = `<option value="">-- ${t("opt_select_registered_crop", "Select a registered crop to auto-fill")} --</option>`;

                    userCrops.forEach(c => {
                        const opt = document.createElement("option");
                        opt.value = JSON.stringify(c);
                        const farmTxt = c.farm_name ? ` (${c.farm_name})` : "";
                        const stageTxt = c.growth_status ? ` • Stage: ${c.growth_status}` : "";
                        opt.textContent = `${c.crop_name} ${c.variety || ""}${farmTxt}${stageTxt}`;
                        registeredCropSelect.appendChild(opt);
                    });

                    registeredCropSelect.addEventListener("change", function () {
                        if (!registeredCropSelect.value) return;
                        try {
                            const selected = JSON.parse(registeredCropSelect.value);
                            // Auto-populate crop
                            if (cropSelect && selected.crop_name) {
                                // Match crop options
                                const valLower = selected.crop_name.toLowerCase();
                                for (let i = 0; i < cropSelect.options.length; i++) {
                                    if (valLower.includes(cropSelect.options[i].value.toLowerCase())) {
                                        cropSelect.selectedIndex = i;
                                        break;
                                    }
                                }
                            }
                            // Auto-populate location
                            if (locationInput && selected.location) {
                                locationInput.value = selected.location;
                            }
                            // Map growth stage if provided
                            if (growthStageSelect && selected.growth_status) {
                                const stLower = selected.growth_status.toLowerCase();
                                if (stLower.includes("seed") || stLower.includes("plant") || stLower.includes("sow")) {
                                    growthStageSelect.value = "seedling";
                                } else if (stLower.includes("flower") || stLower.includes("bloom")) {
                                    growthStageSelect.value = "flowering";
                                } else if (stLower.includes("fruit") || stLower.includes("pod") || stLower.includes("grain")) {
                                    growthStageSelect.value = "fruiting";
                                } else if (stLower.includes("harvest") || stLower.includes("matur")) {
                                    growthStageSelect.value = "near_harvest";
                                } else {
                                    growthStageSelect.value = "vegetative";
                                }
                            }
                        } catch (e) {
                            console.error("Error parsing registered crop selection:", e);
                        }
                    });
                }
            }
        } catch (err) {
            console.warn("Could not load registered crop context:", err);
        }
    }

    loadFarmerContextCrops();

    // =========================================================================
    // 5. FORM SUBMISSION & DECISION ANALYSIS
    // =========================================================================
    if (form) {
        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            clearAlert();

            const crop = cropSelect ? cropSelect.value.trim() : "";
            const soilType = soilTypeSelect ? soilTypeSelect.value.trim() : "loamy";
            const growthStage = growthStageSelect ? growthStageSelect.value.trim() : "vegetative";
            const soilMoistureVal = soilMoistureInput ? soilMoistureInput.value.trim() : "";
            const tempVal = tempInput ? tempInput.value.trim() : "";
            const humidityVal = humidityInput ? humidityInput.value.trim() : "";
            const rainfallVal = rainfallInput ? rainfallInput.value.trim() : "";
            const forecastRainVal = forecastRainInput ? forecastRainInput.value.trim() : "0";
            const location = locationInput ? locationInput.value.trim() : "";

            const isMoistureUnmeasured = toggleNoSensor ? toggleNoSensor.checked : false;

            // Client Validation
            if (!crop) {
                showAlert(t("err_crop_required", "Please select a valid crop."));
                if (cropSelect) cropSelect.focus();
                return;
            }

            let soilMoisture = null;
            if (!isMoistureUnmeasured) {
                if (soilMoistureVal === "" || isNaN(soilMoistureVal)) {
                    showAlert(t("err_moisture_range", "Soil moisture must be a number between 0% and 100%."));
                    if (soilMoistureInput) soilMoistureInput.focus();
                    return;
                }
                soilMoisture = parseFloat(soilMoistureVal);
                if (soilMoisture < 0 || soilMoisture > 100) {
                    showAlert(t("err_moisture_range", "Soil moisture must be a number between 0% and 100%."));
                    if (soilMoistureInput) soilMoistureInput.focus();
                    return;
                }
            }

            if (tempVal === "" || isNaN(tempVal)) {
                showAlert(t("err_temp_range", "Temperature must be a number between -10°C and 60°C."));
                if (tempInput) tempInput.focus();
                return;
            }
            const temperature = parseFloat(tempVal);
            if (temperature < -10 || temperature > 60) {
                showAlert(t("err_temp_range", "Temperature must be a number between -10°C and 60°C."));
                if (tempInput) tempInput.focus();
                return;
            }

            if (humidityVal === "" || isNaN(humidityVal)) {
                showAlert(t("err_humidity_range", "Humidity must be a number between 0% and 100%."));
                if (humidityInput) humidityInput.focus();
                return;
            }
            const humidity = parseFloat(humidityVal);
            if (humidity < 0 || humidity > 100) {
                showAlert(t("err_humidity_range", "Humidity must be a number between 0% and 100%."));
                if (humidityInput) humidityInput.focus();
                return;
            }

            if (rainfallVal === "" || isNaN(rainfallVal)) {
                showAlert(t("err_rainfall_range", "Recent rainfall must be 0 mm or greater."));
                if (rainfallInput) rainfallInput.focus();
                return;
            }
            const rainfall = parseFloat(rainfallVal);
            if (rainfall < 0) {
                showAlert(t("err_rainfall_range", "Recent rainfall must be 0 mm or greater."));
                if (rainfallInput) rainfallInput.focus();
                return;
            }

            const forecastRain = parseFloat(forecastRainVal) || 0.0;

            // Lock UI and show loading indicator
            checkBtn.disabled = true;
            buttonText.textContent = t("checking_irrigation", "Analyzing field conditions...");

            const payload = {
                crop: crop,
                soilType: soilType,
                growthStage: growthStage,
                soilMoisture: soilMoisture,
                moisture_unmeasured: isMoistureUnmeasured,
                allow_unmeasured: isMoistureUnmeasured,
                temperature: temperature,
                humidity: humidity,
                rainfall: rainfall,
                forecastRain: forecastRain,
                location: location || null
            };

            const headers = {
                "Content-Type": "application/json"
            };

            const token = localStorage.getItem("token") || localStorage.getItem("agriSmartToken");
            if (token) {
                headers["Authorization"] = "Bearer " + token;
            }

            try {
                const response = await fetch("/api/irrigation/recommend", {
                    method: "POST",
                    headers: headers,
                    body: JSON.stringify(payload)
                });

                const data = await response.json();

                if (!response.ok || data.status !== "success") {
                    const errorMsg = data.message || "Failed to analyze irrigation requirements.";
                    showAlert(errorMsg);
                    return;
                }

                currentRecommendationData = data;
                renderRecommendation(data);

                // Refresh history & stats if logged in
                fetchHistoryAndStats();

                // Smooth scroll to results
                const resultSection = document.getElementById("irrigationResult");
                if (resultSection) {
                    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
                }

            } catch (err) {
                console.error("Irrigation API Error:", err);
                showAlert(t("err_network", "Network error. Please make sure the backend server is running."));
            } finally {
                checkBtn.disabled = false;
                buttonText.textContent = t("check_irrigation_btn", "💧 Check Irrigation Requirement");
            }
        });
    }

    // Reset Form button
    if (resetBtn) {
        resetBtn.addEventListener("click", function () {
            if (form) form.reset();
            clearAlert();
            if (toggleNoSensor) toggleNoSensor.checked = false;
            if (soilMoistureInput) {
                soilMoistureInput.disabled = false;
                soilMoistureInput.setAttribute("required", "required");
            }
            if (noSensorNotice) noSensorNotice.style.display = "none";
            if (weatherNotice) weatherNotice.style.display = "none";
            if (iotNotice) iotNotice.style.display = "none";

            currentRecommendationData = null;
            if (dynamicResultCard) {
                dynamicResultCard.style.display = "none";
                dynamicResultCard.innerHTML = "";
            }
            if (initialPlaceholder) {
                initialPlaceholder.style.display = "block";
            }
        });
    }

    // =========================================================================
    // 6. RENDER STRUCTURED SMART RECOMMENDATION CARD
    // =========================================================================
    function renderRecommendation(data) {
        if (!dynamicResultCard || !data || !data.recommendation) return;

        const rec = data.recommendation;
        const cropInfo = rec.crop_info || {};
        const soilInfo = rec.soil_info || {};
        const stageInfo = rec.stage_info || {};
        const water = rec.water_quantity || {};
        const duration = rec.duration_info || {};
        const tips = rec.water_saving_tips || [];
        const nextSteps = rec.next_steps || [];

        if (initialPlaceholder) {
            initialPlaceholder.style.display = "none";
        }
        dynamicResultCard.style.display = "block";

        // Status badge configuration
        let statusKey = "status_adequate";
        let statusColor = "#15803d";
        let statusBg = "#dcfce7";
        let statusIcon = "✅";

        if (rec.status === "Urgent") {
            statusKey = "status_urgent";
            statusColor = "#b91c1c";
            statusBg = "#fee2e2";
            statusIcon = "🚨";
        } else if (rec.status === "Recommended") {
            statusKey = "status_recommended";
            statusColor = "#b45309";
            statusBg = "#fef3c7";
            statusIcon = "💧";
        } else if (rec.status === "Overwatered") {
            statusKey = "status_overwatered";
            statusColor = "#4338ca";
            statusBg = "#e0e7ff";
            statusIcon = "⚠️";
        } else if (rec.status && rec.status.includes("Postpone")) {
            statusKey = "status_postpone";
            statusColor = "#7e22ce";
            statusBg = "#f3e8ff";
            statusIcon = "🌧️";
        } else if (rec.status && rec.status.includes("Guidance")) {
            statusKey = "status_unmeasured";
            statusColor = "#0369a1";
            statusBg = "#e0f2fe";
            statusIcon = "📋";
        }

        const isNeededText = rec.is_irrigation_needed
            ? t("water_needed_yes", "Irrigation Needed: Yes")
            : t("water_needed_no", "Irrigation Needed: No");

        const statusLabel = t(statusKey, rec.status);

        // Water saved alert pill
        let waterSavedBanner = "";
        if (rec.water_saved_mm > 0) {
            waterSavedBanner = `
                <div style="background:#f3e8ff; border:1px solid #d8b4fe; border-radius:14px; padding:14px 18px; margin-bottom:24px; display:flex; align-items:center; gap:12px;">
                    <span style="font-size:24px;">💡</span>
                    <div>
                        <strong style="color:#6b21a8; font-size:14px;" data-i18n="water_saved_metric">Water Conserved via Rain Postponement:</strong>
                        <div style="font-size:15px; font-weight:800; color:#581c87; margin-top:2px;">
                            ~${rec.water_saved_mm} mm depth (${rec.water_saved_litres_ha.toLocaleString()} Litres / hectare)
                        </div>
                    </div>
                </div>
            `;
        }

        // Timing schedule pill
        const timingHtml = `
            <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:16px; padding:16px 20px; margin-bottom:24px; display:flex; align-items:flex-start; gap:14px;">
                <span style="font-size:26px;">⏰</span>
                <div>
                    <div style="font-size:12px; font-weight:800; color:#166534; text-transform:uppercase; letter-spacing:0.5px;" data-i18n="next_timing_label">
                        Next Suggested Watering Time
                    </div>
                    <div style="font-size:18px; font-weight:800; color:#14532d; margin:4px 0;">
                        ${escapeHtml(rec.suggested_time || "Early Morning or Evening")}
                    </div>
                    <div style="font-size:13px; color:#15803d; line-height:1.5;">
                        ${escapeHtml(rec.timing_reason || "")}
                    </div>
                </div>
            </div>
        `;

        // Water saving tips cards
        const tipsHtml = tips.map(tip => `
            <li style="margin-bottom:8px; line-height:1.6;">${escapeHtml(tip)}</li>
        `).join("");

        // Next steps list
        const nextStepsHtml = nextSteps.map(step => `
            <li style="margin-bottom:8px; line-height:1.6;">${escapeHtml(step)}</li>
        `).join("");

        dynamicResultCard.innerHTML = `
            <div class="result-card" style="text-align:left; background:#ffffff; border:2px solid #bbf7d0; box-shadow:0 12px 36px rgba(0,0,0,0.06); padding:32px; border-radius:24px;">

                <!-- Status Header -->
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px; margin-bottom:24px; border-bottom:1px solid #e5e7eb; padding-bottom:20px;">
                    <div>
                        <span style="font-size:12px; font-weight:800; letter-spacing:1px; color:#15803d; text-transform:uppercase;">
                            ${escapeHtml(cropInfo.profile_name || cropInfo.crop || "Crop Recommendation")} • ${escapeHtml(stageInfo.display_name || "")}
                        </span>
                        <h2 style="margin:6px 0 0; color:#1f2937; font-size:26px;">
                            ${escapeHtml(t("irrigation_recommendation_title", "Irrigation Recommendation"))}
                        </h2>
                    </div>

                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
                        <span style="display:inline-flex; align-items:center; gap:6px; padding:8px 18px; border-radius:30px; font-weight:800; font-size:15px; background:${statusBg}; color:${statusColor}; border:1px solid ${statusColor}40;">
                            <span>${statusIcon}</span>
                            <span>${escapeHtml(statusLabel)}</span>
                        </span>
                        <span style="font-size:13px; font-weight:700; color:${rec.is_irrigation_needed ? '#b91c1c' : '#15803d'};">
                            ${escapeHtml(isNeededText)}
                        </span>
                    </div>
                </div>

                <!-- Water Saved Alert Banner (if rain postponed) -->
                ${waterSavedBanner}

                <!-- Suggested Watering Timing Schedule -->
                ${timingHtml}

                <!-- Metrics Highlights Grid -->
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:16px; margin-bottom:28px;">
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:18px;">
                        <div style="font-size:12px; font-weight:700; color:#64748b; margin-bottom:4px;" data-i18n="quantity_label">
                            Suggested Water Quantity
                        </div>
                        <div style="font-size:17px; font-weight:800; color:#0f172a;">
                            ${escapeHtml(water.display || "0 mm")}
                        </div>
                        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
                            ${escapeHtml(water.units || "")}
                        </div>
                    </div>

                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:18px;">
                        <div style="font-size:12px; font-weight:700; color:#64748b; margin-bottom:4px;">
                            Soil &amp; Moisture Range
                        </div>
                        <div style="font-size:17px; font-weight:800; color:#0f172a;">
                            ${escapeHtml(soilInfo.display_name || "Loamy")} (${escapeHtml(cropInfo.optimal_range || "50%–70%")})
                        </div>
                        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
                            Infiltration: ${escapeHtml(soilInfo.infiltration || "Moderate")}
                        </div>
                    </div>

                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:18px;">
                        <div style="font-size:12px; font-weight:700; color:#64748b; margin-bottom:4px;">
                            Stage &amp; Sensitivity
                        </div>
                        <div style="font-size:17px; font-weight:800; color:#0f172a;">
                            ${escapeHtml(stageInfo.display_name || "Vegetative")}
                        </div>
                        <div style="font-size:11px; color:${stageInfo.critical_stage ? '#b91c1c' : '#94a3b8'}; font-weight:${stageInfo.critical_stage ? '700' : 'normal'}; margin-top:4px;">
                            ${stageInfo.critical_stage ? '⚠️ Critical Sensitivity Stage' : `Sensitivity: ${escapeHtml(cropInfo.water_sensitivity || "Moderate")}`}
                        </div>
                    </div>
                </div>

                <!-- Explanation Section -->
                <div style="margin-bottom:24px;">
                    <h3 style="font-size:15px; font-weight:700; color:#1e293b; margin:0 0 8px 0; display:flex; align-items:center; gap:8px;">
                        <span>📋</span> <span data-i18n="explanation_label">Agronomic Explanation</span>
                    </h3>
                    <p style="margin:0; font-size:14px; line-height:1.6; color:#334155; background:#f0fdf4; border-left:4px solid #22c55e; padding:12px 16px; border-radius:0 10px 10px 0;">
                        ${escapeHtml(rec.explanation)}
                    </p>
                </div>

                <!-- Weather Warning Advisory -->
                <div style="margin-bottom:24px;">
                    <h3 style="font-size:15px; font-weight:700; color:#1e293b; margin:0 0 8px 0; display:flex; align-items:center; gap:8px;">
                        <span>🌦️</span> <span data-i18n="weather_warning_label">Weather Advisory</span>
                    </h3>
                    <p style="margin:0; font-size:14px; line-height:1.6; color:#475569; background:#fffbeb; border-left:4px solid #f59e0b; padding:12px 16px; border-radius:0 10px 10px 0;">
                        ${escapeHtml(rec.weather_advisory)}
                    </p>
                </div>

                <!-- Water Saving Conservation Tips -->
                <div style="margin-bottom:24px;">
                    <h3 style="font-size:15px; font-weight:700; color:#1e293b; margin:0 0 8px 0; display:flex; align-items:center; gap:8px;">
                        <span>💡</span> <span data-i18n="water_saving_tips_title">Water-Saving Conservation Tips</span>
                    </h3>
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:14px 18px;">
                        <ul style="margin:0; padding-left:20px; font-size:13.5px; color:#334155;">
                            ${tipsHtml}
                        </ul>
                    </div>
                </div>

                <!-- Recommended Actions -->
                <div style="margin-bottom:24px;">
                    <h3 style="font-size:15px; font-weight:700; color:#1e293b; margin:0 0 8px 0; display:flex; align-items:center; gap:8px;">
                        <span>✅</span> <span data-i18n="next_steps_label">Recommended Actions</span>
                    </h3>
                    <ul style="margin:0; padding-left:20px; font-size:13.5px; line-height:1.7; color:#334155;">
                        ${nextStepsHtml}
                    </ul>
                </div>

                <!-- Transparent Assumptions & Duration Notice -->
                <div style="background:#f8fafc; border:1px dashed #cbd5e1; border-radius:14px; padding:16px; font-size:12px; color:#64748b; line-height:1.6;">
                    <strong style="color:#475569;" data-i18n="duration_label">Irrigation Duration Note:</strong>
                    ${escapeHtml(duration.explanation || "")}
                    <div style="margin-top:6px;">
                        <strong style="color:#475569;" data-i18n="assumptions_label">Model Assumptions:</strong>
                        ${escapeHtml(water.assumptions || "")}
                    </div>
                </div>

            </div>
        `;

        // Apply translations for newly inserted data-i18n elements
        if (window.i18n && typeof window.i18n.applyTranslations === "function") {
            window.i18n.applyTranslations();
        }
    }

    // =========================================================================
    // 7. IRRIGATION HISTORY & STATS MANAGEMENT
    // =========================================================================
    async function fetchHistoryAndStats() {
        const token = localStorage.getItem("token") || localStorage.getItem("agriSmartToken");
        if (!token) {
            if (historyLoading) historyLoading.style.display = "none";
            if (historyEmpty) {
                historyEmpty.style.display = "block";
                historyEmpty.textContent = "Log in to track your irrigation recommendation history and water savings.";
            }
            return;
        }

        // Fetch stats
        try {
            const statsRes = await fetch("/api/irrigation/stats", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const statsData = await statsRes.json();
            if (statsRes.ok && statsData.status === "success" && statsData.stats) {
                const s = statsData.stats;
                if (statTotalChecks) statTotalChecks.textContent = s.total_checks;
                if (statWaterSaved) statWaterSaved.textContent = `${(s.total_water_saved_litres || 0).toLocaleString()} L`;
                if (statNeeded) statNeeded.textContent = s.needed_count;
                if (statPostponed) statPostponed.textContent = s.postponed_count;
            }
        } catch (e) {
            console.warn("Could not load irrigation stats:", e);
        }

        // Fetch history
        try {
            if (historyLoading) historyLoading.style.display = "block";
            const histRes = await fetch("/api/irrigation/history?limit=15", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const histData = await histRes.json();
            if (historyLoading) historyLoading.style.display = "none";

            if (histRes.ok && histData.status === "success" && Array.isArray(histData.history)) {
                if (histData.history.length === 0) {
                    if (historyEmpty) historyEmpty.style.display = "block";
                    if (historyList) historyList.innerHTML = "";
                } else {
                    if (historyEmpty) historyEmpty.style.display = "none";
                    renderHistoryList(histData.history);
                }
            }
        } catch (e) {
            if (historyLoading) historyLoading.style.display = "none";
            console.warn("Could not load irrigation history:", e);
        }
    }

    function renderHistoryList(records) {
        if (!historyList) return;
        historyList.innerHTML = "";

        records.forEach(r => {
            const card = document.createElement("div");
            card.style.cssText = "background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; transition:all 0.2s;";

            // Status color
            let statusColor = "#15803d";
            let statusBg = "#dcfce7";
            if (r.recommendation_status === "Urgent") {
                statusColor = "#b91c1c";
                statusBg = "#fee2e2";
            } else if (r.recommendation_status === "Recommended") {
                statusColor = "#b45309";
                statusBg = "#fef3c7";
            } else if (r.recommendation_status && r.recommendation_status.includes("Postpone")) {
                statusColor = "#7e22ce";
                statusBg = "#f3e8ff";
            }

            const moistureText = r.soil_moisture !== null ? `${r.soil_moisture}% moisture` : "Unmeasured";
            const dateStr = r.created_at ? new Date(r.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
            const waterSavedPill = r.water_saved_mm > 0 ? `<span style="font-size:11px; background:#f3e8ff; color:#7e22ce; padding:2px 8px; border-radius:10px; font-weight:700;">💧 Saved ${(r.water_saved_mm * 10000).toLocaleString()} L/ha</span>` : "";

            card.innerHTML = `
                <div style="flex:1; min-width:240px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <strong style="color:#0f172a; font-size:16px;">${escapeHtml(r.crop)}</strong>
                        <span style="font-size:12px; color:#64748b; text-transform:capitalize;">(${escapeHtml(r.soil_type || "loamy")} • ${escapeHtml(r.growth_stage || "vegetative")})</span>
                        ${waterSavedPill}
                    </div>
                    <div style="font-size:13px; color:#475569; display:flex; gap:12px; flex-wrap:wrap;">
                        <span>💧 ${moistureText}</span>
                        <span>🌡️ ${r.temperature}°C</span>
                        <span>☁️ ${r.humidity}%</span>
                        <span>🌧️ ${r.rainfall}mm</span>
                        ${r.forecast_rain_mm > 0 ? `<span>🌧️ 48h Rain: ${r.forecast_rain_mm}mm</span>` : ""}
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
                        ⏰ ${escapeHtml(r.timing_recommendation || "Morning or Evening")} • ${dateStr}
                    </div>
                </div>

                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="display:inline-block; padding:6px 14px; border-radius:20px; font-weight:700; font-size:13px; background:${statusBg}; color:${statusColor};">
                        ${escapeHtml(r.recommendation_status)}
                    </span>
                    <button type="button" class="btn-delete-history" data-record-id="${r.id}" style="background:transparent; border:1px solid #fecaca; color:#ef4444; border-radius:8px; padding:6px 10px; font-size:12px; cursor:pointer; font-weight:600;" title="Delete Record">
                        🗑️
                    </button>
                </div>
            `;

            // Delete record handler
            const deleteBtn = card.querySelector(".btn-delete-history");
            if (deleteBtn) {
                deleteBtn.addEventListener("click", async function () {
                    const recordId = deleteBtn.getAttribute("data-record-id");
                    const token = localStorage.getItem("token") || localStorage.getItem("agriSmartToken");
                    if (!token || !recordId) return;

                    if (!confirm("Are you sure you want to delete this irrigation record?")) return;

                    try {
                        const delRes = await fetch(`/api/irrigation/history/${recordId}`, {
                            method: "DELETE",
                            headers: { "Authorization": `Bearer ${token}` }
                        });
                        if (delRes.ok) {
                            card.remove();
                            fetchHistoryAndStats();
                        }
                    } catch (err) {
                        console.error("Delete record error:", err);
                    }
                });
            }

            historyList.appendChild(card);
        });
    }

    // Fetch initial history & stats on page load
    fetchHistoryAndStats();

    // Language Change Listener - re-render active recommendation if language changes
    window.addEventListener("languageChanged", function () {
        if (currentRecommendationData) {
            renderRecommendation(currentRecommendationData);
        }
    });

    // Simple HTML escape utility to avoid XSS
    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
