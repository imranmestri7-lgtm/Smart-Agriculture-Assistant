/**
 * AgriSmart - Smart Irrigation Frontend Controller
 * Handles form validation, asynchronous API communication with the Flask backend,
 * dynamic UI rendering, and multilingual state synchronization.
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

    // Store latest recommendation in memory for language switching re-renders
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

    // Display validation or network error alert
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

    // Form submission
    if (form) {
        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            clearAlert();

            const crop = document.getElementById("crop").value.trim();
            const soilMoistureVal = document.getElementById("soilMoisture").value.trim();
            const tempVal = document.getElementById("temperature").value.trim();
            const humidityVal = document.getElementById("humidity").value.trim();
            const rainfallVal = document.getElementById("rainfall").value.trim();
            const location = document.getElementById("location").value.trim();

            // Client-Side Validation
            if (!crop) {
                showAlert(t("err_crop_required", "Please select a valid crop."));
                document.getElementById("crop").focus();
                return;
            }

            if (soilMoistureVal === "" || isNaN(soilMoistureVal)) {
                showAlert(t("err_moisture_range", "Soil moisture must be a number between 0% and 100%."));
                document.getElementById("soilMoisture").focus();
                return;
            }
            const soilMoisture = parseFloat(soilMoistureVal);
            if (soilMoisture < 0 || soilMoisture > 100) {
                showAlert(t("err_moisture_range", "Soil moisture must be a number between 0% and 100%."));
                document.getElementById("soilMoisture").focus();
                return;
            }

            if (tempVal === "" || isNaN(tempVal)) {
                showAlert(t("err_temp_range", "Temperature must be a number between -10°C and 60°C."));
                document.getElementById("temperature").focus();
                return;
            }
            const temperature = parseFloat(tempVal);
            if (temperature < -10 || temperature > 60) {
                showAlert(t("err_temp_range", "Temperature must be a number between -10°C and 60°C."));
                document.getElementById("temperature").focus();
                return;
            }

            if (humidityVal === "" || isNaN(humidityVal)) {
                showAlert(t("err_humidity_range", "Humidity must be a number between 0% and 100%."));
                document.getElementById("humidity").focus();
                return;
            }
            const humidity = parseFloat(humidityVal);
            if (humidity < 0 || humidity > 100) {
                showAlert(t("err_humidity_range", "Humidity must be a number between 0% and 100%."));
                document.getElementById("humidity").focus();
                return;
            }

            if (rainfallVal === "" || isNaN(rainfallVal)) {
                showAlert(t("err_rainfall_range", "Recent rainfall must be 0 mm or greater."));
                document.getElementById("rainfall").focus();
                return;
            }
            const rainfall = parseFloat(rainfallVal);
            if (rainfall < 0) {
                showAlert(t("err_rainfall_range", "Recent rainfall must be 0 mm or greater."));
                document.getElementById("rainfall").focus();
                return;
            }

            // Lock UI and show loading indicator
            checkBtn.disabled = true;
            buttonText.textContent = t("checking_irrigation", "Analyzing field conditions...");

            const payload = {
                crop: crop,
                soilMoisture: soilMoisture,
                temperature: temperature,
                humidity: humidity,
                rainfall: rainfall,
                location: location || null
            };

            const headers = {
                "Content-Type": "application/json"
            };

            // Include JWT if farmer is logged in
            const token = localStorage.getItem("token");
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

    // Render structured recommendation card
    function renderRecommendation(data) {
        if (!dynamicResultCard || !data || !data.recommendation) return;

        const rec = data.recommendation;
        const cropInfo = rec.crop_info || {};
        const water = rec.water_quantity || {};
        const duration = rec.duration_info || {};

        if (initialPlaceholder) {
            initialPlaceholder.style.display = "none";
        }
        dynamicResultCard.style.display = "block";

        // Status badge color and localization
        let statusBadgeClass = "badge-adequate";
        let statusKey = "status_adequate";
        let statusColor = "#15803d";
        let statusBg = "#dcfce7";

        if (rec.status === "Urgent") {
            statusKey = "status_urgent";
            statusColor = "#b91c1c";
            statusBg = "#fee2e2";
        } else if (rec.status === "Recommended") {
            statusKey = "status_recommended";
            statusColor = "#b45309";
            statusBg = "#fef3c7";
        } else if (rec.status === "Overwatered") {
            statusKey = "status_overwatered";
            statusColor = "#4338ca";
            statusBg = "#e0e7ff";
        }

        const isNeededText = rec.is_irrigation_needed
            ? t("water_needed_yes", "Irrigation Needed: Yes")
            : t("water_needed_no", "Irrigation Needed: No");

        const statusLabel = t(statusKey, rec.status);

        // Build list of next steps
        const nextStepsHtml = Array.isArray(rec.next_steps)
            ? rec.next_steps.map(step => `<li>${escapeHtml(step)}</li>`).join("")
            : "";

        dynamicResultCard.innerHTML = `
            <div class="result-card" style="text-align:left; background:#ffffff; border:2px solid #bbf7d0; box-shadow:0 10px 30px rgba(0,0,0,0.06); padding:32px; border-radius:24px;">
                
                <!-- Status Header -->
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px; margin-bottom:24px; border-bottom:1px solid #e5e7eb; padding-bottom:20px;">
                    <div>
                        <span style="font-size:12px; font-weight:800; letter-spacing:1px; color:#15803d; text-transform:uppercase;">
                            ${escapeHtml(cropInfo.profile_name || cropInfo.crop || "Crop Recommendation")}
                        </span>
                        <h2 style="margin:6px 0 0; color:#1f2937; font-size:28px;">
                            ${escapeHtml(t("irrigation_recommendation_title", "Irrigation Recommendation"))}
                        </h2>
                    </div>

                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px;">
                        <span style="display:inline-block; padding:8px 18px; border-radius:30px; font-weight:800; font-size:15px; background:${statusBg}; color:${statusColor}; border:1px solid ${statusColor}40;">
                            ${escapeHtml(statusLabel)}
                        </span>
                        <span style="font-size:14px; font-weight:700; color:${rec.is_irrigation_needed ? '#b91c1c' : '#15803d'};">
                            ${escapeHtml(isNeededText)}
                        </span>
                    </div>
                </div>

                <!-- Metrics Highlights Grid -->
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:18px; margin-bottom:28px;">
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:18px;">
                        <div style="font-size:13px; font-weight:700; color:#64748b; margin-bottom:4px;" data-i18n="quantity_label">
                            Suggested Water Quantity
                        </div>
                        <div style="font-size:18px; font-weight:800; color:#0f172a;">
                            ${escapeHtml(water.display || "0 mm")}
                        </div>
                        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
                            ${escapeHtml(water.units || "")}
                        </div>
                    </div>

                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:18px;">
                        <div style="font-size:13px; font-weight:700; color:#64748b; margin-bottom:4px;">
                            Target Optimal Moisture
                        </div>
                        <div style="font-size:18px; font-weight:800; color:#0f172a;">
                            ${escapeHtml(cropInfo.optimal_range || "50%–70%")}
                        </div>
                        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
                            Sensitivity: ${escapeHtml(cropInfo.water_sensitivity || "Moderate")}
                        </div>
                    </div>
                </div>

                <!-- Explanation Section -->
                <div style="margin-bottom:24px;">
                    <h3 style="font-size:16px; font-weight:700; color:#1e293b; margin:0 0 8px 0; display:flex; align-items:center; gap:8px;">
                        <span>📋</span> <span data-i18n="explanation_label">Agronomic Explanation</span>
                    </h3>
                    <p style="margin:0; font-size:15px; line-height:1.6; color:#334155; background:#f0fdf4; border-left:4px solid #22c55e; padding:12px 16px; border-radius:0 10px 10px 0;">
                        ${escapeHtml(rec.explanation)}
                    </p>
                </div>

                <!-- Weather Warning Advisory -->
                <div style="margin-bottom:24px;">
                    <h3 style="font-size:16px; font-weight:700; color:#1e293b; margin:0 0 8px 0; display:flex; align-items:center; gap:8px;">
                        <span>🌦️</span> <span data-i18n="weather_warning_label">Weather Advisory</span>
                    </h3>
                    <p style="margin:0; font-size:14px; line-height:1.6; color:#475569; background:#fffbeb; border-left:4px solid #f59e0b; padding:12px 16px; border-radius:0 10px 10px 0;">
                        ${escapeHtml(rec.weather_advisory)}
                    </p>
                </div>

                <!-- Recommended Next Steps -->
                <div style="margin-bottom:24px;">
                    <h3 style="font-size:16px; font-weight:700; color:#1e293b; margin:0 0 8px 0; display:flex; align-items:center; gap:8px;">
                        <span>✅</span> <span data-i18n="next_steps_label">Recommended Actions</span>
                    </h3>
                    <ul style="margin:0; padding-left:20px; font-size:14px; line-height:1.7; color:#334155;">
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
