/**
 * js/analytics.js
 * Smart Agriculture Assistant - Phase 7 Smart Analytics Controller
 */

(function () {
    "use strict";

    // Chart Color Palettes
    const PALETTE = [
        "#16a34a", "#0284c7", "#f59e0b", "#ec4899", 
        "#8b5cf6", "#14b8a6", "#e11d48", "#84cc16", "#64748b"
    ];

    const STAGE_COLORS = {
        "Newly Planted": "#10b981",
        "Growing": "#16a34a",
        "Flowering": "#ec4899",
        "Fruiting": "#f59e0b",
        "Ready for Harvest": "#84cc16",
        "Harvested": "#64748b"
    };

    let latestAnalyticsData = null;

    function getAuthToken() {
        return localStorage.getItem("token");
    }

    function t(key, fallback) {
        if (window.i18n && typeof window.i18n.t === "function") {
            const val = window.i18n.t(key);
            if (val && val !== key) return val;
        }
        return fallback || key;
    }

    /**
     * Escape HTML string for safe insertion
     */
    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     * Load farm and crop options into filter selects
     */
    async function loadFilterOptions() {
        const token = getAuthToken();
        if (!token) return;

        const farmSelect = document.getElementById("analyticsFilterFarm");
        const cropSelect = document.getElementById("analyticsFilterCrop");

        try {
            const resp = await fetch("/api/analytics/filter-options", {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (!resp.ok) return;
            const data = await resp.json();

            if (data.status === "success") {
                const currentFarmVal = farmSelect ? farmSelect.value : "";
                const currentCropVal = cropSelect ? cropSelect.value : "";

                if (farmSelect) {
                    const allFarmsLabel = t("filter_all_farms", "All Farms");
                    let farmHtml = `<option value="">${escapeHtml(allFarmsLabel)}</option>`;
                    (data.farms || []).forEach(f => {
                        farmHtml += `<option value="${f.id}">${escapeHtml(f.farm_name)}</option>`;
                    });
                    farmSelect.innerHTML = farmHtml;
                    if (currentFarmVal) farmSelect.value = currentFarmVal;
                }

                if (cropSelect) {
                    const allCropsLabel = t("filter_all_crops", "All Crops");
                    let cropHtml = `<option value="">${escapeHtml(allCropsLabel)}</option>`;
                    (data.crops || []).forEach(c => {
                        cropHtml += `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`;
                    });
                    cropSelect.innerHTML = cropHtml;
                    if (currentCropVal) cropSelect.value = currentCropVal;
                }
            }
        } catch (err) {
            console.error("Could not load analytics filter options:", err);
        }
    }

    /**
     * Fetch analytics overview from API
     */
    async function loadAnalytics() {
        const token = getAuthToken();
        if (!token) {
            return;
        }

        const farmId = document.getElementById("analyticsFilterFarm")?.value || "";
        const cropName = document.getElementById("analyticsFilterCrop")?.value || "";
        const startDate = document.getElementById("analyticsStartDate")?.value || "";
        const endDate = document.getElementById("analyticsEndDate")?.value || "";

        const queryParams = new URLSearchParams();
        if (farmId) queryParams.append("farm_id", farmId);
        if (cropName) queryParams.append("crop_name", cropName);
        if (startDate) queryParams.append("start_date", startDate);
        if (endDate) queryParams.append("end_date", endDate);

        const url = `/api/analytics/overview${queryParams.toString() ? "?" + queryParams.toString() : ""}`;

        try {
            const resp = await fetch(url, {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (resp.status === 401) {
                return;
            }

            const data = await resp.json();
            if (data.status === "success") {
                latestAnalyticsData = data;
                renderAnalytics(data);
            } else {
                console.warn("Analytics error response:", data.message);
            }
        } catch (err) {
            console.error("Failed to load smart analytics:", err);
        }
    }

    /**
     * Render complete analytics dashboard
     */
    function renderAnalytics(data) {
        if (!data) return;

        // 1. Summary Metrics
        const s = data.summary || {};
        document.getElementById("metricTotalFarms").textContent = s.total_farms || 0;
        document.getElementById("metricTotalCrops").textContent = s.total_crops || 0;
        document.getElementById("metricTotalDiagnoses").textContent = s.total_diagnoses || 0;
        document.getElementById("metricTotalIrrigations").textContent = s.total_irrigations || 0;
        document.getElementById("metricCropsGrowing").textContent = s.crops_growing || 0;
        document.getElementById("metricCropsReady").textContent = s.crops_ready_for_harvest || 0;

        // 2. Crop Analytics
        const ca = data.crop_analytics || {};
        renderCropDistribution(ca.crops_by_name || []);
        renderGrowthStages(ca.growth_stages || []);
        renderCropsPerFarm(ca.crops_per_farm || []);
        renderCropTimeline(ca.timeline || []);

        // 3. Disease Analytics
        const da = data.disease_analytics || {};
        renderDiseaseBreakdown(da);
        renderTopDiseases(da.top_diseases || []);
        renderCropDiseaseDistribution(da.crop_distribution || []);
        renderDiseaseTrends(da.trends_over_time || []);

        // 4. Irrigation Analytics
        const ia = data.irrigation_analytics || {};
        renderIrrigationStats(ia);
        renderIrrigationActivity(ia.activity_over_time || []);
        renderCropIrrigationSummary(ia.crop_summaries || []);
    }

    /**
     * Render empty state in container
     */
    function renderEmptyState(container, message) {
        if (!container) return;
        const msg = message || t("no_data_label", "No records found for the selected criteria.");
        container.innerHTML = `
            <div class="empty-chart-state">
                <span class="empty-icon">📊</span>
                <p>${escapeHtml(msg)}</p>
            </div>
        `;
    }

    // =========================================================================
    // CROP CHARTS
    // =========================================================================

    function renderCropDistribution(crops) {
        const container = document.getElementById("cropDistByNameChart");
        if (!container) return;

        if (!crops || crops.length === 0) {
            renderEmptyState(container);
            return;
        }

        const maxCount = Math.max(...crops.map(c => c.count), 1);
        let html = '<div class="bar-chart-list">';

        crops.forEach((c, idx) => {
            const pct = Math.round((c.count / maxCount) * 100);
            const areaLabel = c.total_area > 0 ? `${c.total_area} ${c.area_unit || "acre"}` : "";
            html += `
                <div class="bar-row">
                    <div class="bar-label-row">
                        <span>${escapeHtml(c.crop_name)} <span class="bar-label-sub">(${areaLabel})</span></span>
                        <strong>${c.count}</strong>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    function renderGrowthStages(stages) {
        const container = document.getElementById("cropGrowthStageChart");
        if (!container) return;

        const nonZero = stages.filter(s => s.count > 0);
        if (nonZero.length === 0) {
            renderEmptyState(container);
            return;
        }

        const total = nonZero.reduce((acc, curr) => acc + curr.count, 0);
        const segments = nonZero.map(s => ({
            label: s.stage,
            value: s.count,
            color: STAGE_COLORS[s.stage] || "#16a34a"
        }));

        renderSvgDonut(container, segments, total);
    }

    function renderCropsPerFarm(farmList) {
        const container = document.getElementById("cropsPerFarmChart");
        if (!container) return;

        if (!farmList || farmList.length === 0) {
            renderEmptyState(container);
            return;
        }

        const maxCount = Math.max(...farmList.map(f => f.count), 1);
        let html = '<div class="bar-chart-list">';

        farmList.forEach(f => {
            const pct = Math.round((f.count / maxCount) * 100);
            html += `
                <div class="bar-row">
                    <div class="bar-label-row">
                        <span>🏡 ${escapeHtml(f.farm_name)}</span>
                        <strong>${f.count}</strong>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill bar-sky" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    function renderCropTimeline(timeline) {
        const container = document.getElementById("cropTimelineList");
        if (!container) return;

        if (!timeline || timeline.length === 0) {
            renderEmptyState(container);
            return;
        }

        let html = '<div class="timeline-container">';
        timeline.forEach(item => {
            const daysLabel = t("days_since_planting_label", "days since planting");
            const varietyText = item.variety ? ` • ${escapeHtml(item.variety)}` : "";
            const harvestText = item.expected_harvest_date ? `Harvest: ${item.expected_harvest_date}` : "";

            html += `
                <div class="timeline-card">
                    <div class="timeline-info">
                        <div class="timeline-crop-title">
                            🌾 ${escapeHtml(item.crop_name)}${varietyText}
                        </div>
                        <div class="timeline-meta">
                            <span>🏡 ${escapeHtml(item.farm_name)}</span> • 
                            <span>${item.days_since_planting} ${daysLabel}</span>
                            ${harvestText ? ` • <span>${harvestText}</span>` : ""}
                        </div>
                    </div>
                    <div class="timeline-badge">
                        ${escapeHtml(item.growth_status)}
                    </div>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    // =========================================================================
    // DISEASE CHARTS
    // =========================================================================

    function renderDiseaseBreakdown(da) {
        const container = document.getElementById("diseaseHealthBreakdownChart");
        if (!container) return;

        const healthy = da.healthy_count || 0;
        const diseased = da.diseased_count || 0;
        const total = healthy + diseased;

        if (total === 0) {
            renderEmptyState(container);
            return;
        }

        const segments = [
            { label: t("healthy_label", "Healthy"), value: healthy, color: "#16a34a" },
            { label: t("diseased_label", "Diseased"), value: diseased, color: "#e11d48" }
        ];

        renderSvgDonut(container, segments, total);
    }

    function renderTopDiseases(diseases) {
        const container = document.getElementById("topDiseasesChart");
        if (!container) return;

        if (!diseases || diseases.length === 0) {
            renderEmptyState(container);
            return;
        }

        const maxCount = Math.max(...diseases.map(d => d.count), 1);
        let html = '<div class="bar-chart-list">';

        diseases.forEach(d => {
            const pct = Math.round((d.count / maxCount) * 100);
            const confBadge = d.avg_confidence ? ` (${d.avg_confidence}%)` : "";
            html += `
                <div class="bar-row">
                    <div class="bar-label-row">
                        <span>🍃 ${escapeHtml(d.disease_name)} <span class="bar-label-sub">${confBadge}</span></span>
                        <strong>${d.count}</strong>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill bar-rose" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    function renderCropDiseaseDistribution(cropDist) {
        const container = document.getElementById("cropDiseaseDistChart");
        if (!container) return;

        if (!cropDist || cropDist.length === 0) {
            renderEmptyState(container);
            return;
        }

        const maxCount = Math.max(...cropDist.map(c => c.count), 1);
        let html = '<div class="bar-chart-list">';

        cropDist.forEach(c => {
            const pct = Math.round((c.count / maxCount) * 100);
            html += `
                <div class="bar-row">
                    <div class="bar-label-row">
                        <span>🌾 ${escapeHtml(c.crop_type)}</span>
                        <strong>${c.count}</strong>
                    </div>
                    <div class="bar-track">
                        <div class="bar-fill bar-amber" style="width: ${pct}%;"></div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    function renderDiseaseTrends(trends) {
        const container = document.getElementById("diseaseTrendsChart");
        if (!container) return;

        if (!trends || trends.length === 0) {
            renderEmptyState(container);
            return;
        }

        renderSvgLineChart(container, trends, {
            color: "#e11d48",
            yLabel: "Diagnoses"
        });
    }

    // =========================================================================
    // IRRIGATION CHARTS & STATS
    // =========================================================================

    function renderIrrigationStats(ia) {
        const totalWaterElem = document.getElementById("irrigStatTotalWater");
        const avgWaterElem = document.getElementById("irrigStatAvgWater");
        const neededElem = document.getElementById("irrigStatNeeded");
        const sufficientElem = document.getElementById("irrigStatSufficient");

        if (totalWaterElem) totalWaterElem.textContent = `${ia.total_estimated_water_mm || 0} mm`;
        if (avgWaterElem) avgWaterElem.textContent = `${ia.avg_water_mm || 0} mm`;
        if (neededElem) neededElem.textContent = ia.irrigation_needed_count || 0;
        if (sufficientElem) sufficientElem.textContent = ia.irrigation_not_needed_count || 0;
    }

    function renderIrrigationActivity(activity) {
        const container = document.getElementById("irrigationActivityChart");
        if (!container) return;

        if (!activity || activity.length === 0) {
            renderEmptyState(container);
            return;
        }

        renderSvgLineChart(container, activity, {
            color: "#0284c7",
            yLabel: "Events"
        });
    }

    function renderCropIrrigationSummary(summaries) {
        const container = document.getElementById("cropIrrigationSummaryTable");
        if (!container) return;

        if (!summaries || summaries.length === 0) {
            renderEmptyState(container);
            return;
        }

        let html = `
            <table class="crop-summary-table">
                <thead>
                    <tr>
                        <th>Crop</th>
                        <th>Records</th>
                        <th>Avg Moisture</th>
                        <th>Total Water (mm)</th>
                    </tr>
                </thead>
                <tbody>
        `;

        summaries.forEach(s => {
            html += `
                <tr>
                    <td><strong>${escapeHtml(s.crop)}</strong></td>
                    <td>${s.count}</td>
                    <td>${s.avg_soil_moisture}%</td>
                    <td><strong>${s.total_water_mm} mm</strong></td>
                </tr>
            `;
        });

        html += `
                </tbody>
            </table>
        `;

        container.innerHTML = html;
    }

    // =========================================================================
    // SVG VISUALIZATIONS (100% Native, Responsive & Offline)
    // =========================================================================

    /**
     * Render SVG Donut Chart with center count and legend
     */
    function renderSvgDonut(container, segments, total) {
        const size = 160;
        const strokeWidth = 26;
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;

        let accumulatedOffset = 0;
        let pathsHtml = "";

        segments.forEach(seg => {
            const fraction = total > 0 ? seg.value / total : 0;
            const strokeDasharray = `${fraction * circumference} ${circumference}`;
            const strokeDashoffset = -accumulatedOffset;
            accumulatedOffset += fraction * circumference;

            pathsHtml += `
                <circle
                    cx="${size / 2}"
                    cy="${size / 2}"
                    r="${radius}"
                    fill="transparent"
                    stroke="${seg.color}"
                    stroke-width="${strokeWidth}"
                    stroke-dasharray="${strokeDasharray}"
                    stroke-dashoffset="${strokeDashoffset}"
                    style="transition: stroke-dasharray 0.5s ease;"
                />
            `;
        });

        let legendHtml = '<div class="chart-legend">';
        segments.forEach(seg => {
            const pct = total > 0 ? Math.round((seg.value / total) * 100) : 0;
            legendHtml += `
                <div class="legend-item">
                    <span class="legend-dot" style="background: ${seg.color};"></span>
                    <span>${escapeHtml(seg.label)}: <strong>${seg.value}</strong> (${pct}%)</span>
                </div>
            `;
        });
        legendHtml += '</div>';

        container.innerHTML = `
            <div class="svg-chart-wrap">
                <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" class="svg-donut-svg">
                    ${pathsHtml}
                </svg>
                ${legendHtml}
            </div>
        `;
    }

    /**
     * Render Responsive SVG Line/Area Trend Chart
     */
    function renderSvgLineChart(container, dataPoints, options) {
        const width = 360;
        const height = 160;
        const padding = { top: 20, right: 25, bottom: 30, left: 35 };

        const graphWidth = width - padding.left - padding.right;
        const graphHeight = height - padding.top - padding.bottom;

        const maxVal = Math.max(...dataPoints.map(d => d.count), 1);
        const color = options.color || "#16a34a";

        const points = dataPoints.map((d, i) => {
            const x = padding.left + (dataPoints.length > 1 ? (i / (dataPoints.length - 1)) * graphWidth : graphWidth / 2);
            const y = padding.top + graphHeight - (d.count / maxVal) * graphHeight;
            return { x, y, date: d.date, count: d.count };
        });

        let pathD = "";
        points.forEach((pt, i) => {
            if (i === 0) pathD += `M ${pt.x} ${pt.y}`;
            else pathD += ` L ${pt.x} ${pt.y}`;
        });

        // Area under path
        const firstPt = points[0];
        const lastPt = points[points.length - 1];
        const areaD = `${pathD} L ${lastPt.x} ${padding.top + graphHeight} L ${firstPt.x} ${padding.top + graphHeight} Z`;

        // Dots & Date labels
        let dotsHtml = "";
        points.forEach((pt) => {
            dotsHtml += `
                <circle cx="${pt.x}" cy="${pt.y}" r="4" fill="${color}" stroke="#ffffff" stroke-width="2"/>
                <text x="${pt.x}" y="${pt.y - 7}" font-size="10" font-weight="700" fill="#334155" text-anchor="middle">${pt.count}</text>
            `;
        });

        // X-axis dates (first, middle, last)
        let xAxisHtml = "";
        if (points.length > 0) {
            const showIndices = [0];
            if (points.length > 2) showIndices.push(Math.floor(points.length / 2));
            if (points.length > 1) showIndices.push(points.length - 1);

            showIndices.forEach(idx => {
                const pt = points[idx];
                const dateLabel = pt.date.slice(5); // MM-DD
                xAxisHtml += `
                    <text x="${pt.x}" y="${height - 8}" font-size="10" fill="#64748b" text-anchor="middle">${dateLabel}</text>
                `;
            });
        }

        container.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto; max-height: 200px;">
                <!-- Grid Lines -->
                <line x1="${padding.left}" y1="${padding.top}" x2="${width - padding.right}" y2="${padding.top}" stroke="#f1f5f9" stroke-width="1"/>
                <line x1="${padding.left}" y1="${padding.top + graphHeight / 2}" x2="${width - padding.right}" y2="${padding.top + graphHeight / 2}" stroke="#f1f5f9" stroke-width="1"/>
                <line x1="${padding.left}" y1="${padding.top + graphHeight}" x2="${width - padding.right}" y2="${padding.top + graphHeight}" stroke="#e2e8f0" stroke-width="1"/>

                <!-- Area Fill -->
                <path d="${areaD}" fill="${color}" fill-opacity="0.12"/>

                <!-- Line Path -->
                <path d="${pathD}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/>

                <!-- Data Dots -->
                ${dotsHtml}

                <!-- X-Axis Labels -->
                ${xAxisHtml}
            </svg>
        `;
    }

    // =========================================================================
    // INITIALIZATION & EVENT LISTENERS
    // =========================================================================

    function initAnalytics() {
        const applyBtn = document.getElementById("applyAnalyticsFiltersBtn");
        const resetBtn = document.getElementById("resetAnalyticsFiltersBtn");
        const refreshBtn = document.getElementById("refreshAnalyticsBtn");

        if (applyBtn) {
            applyBtn.addEventListener("click", () => {
                loadAnalytics();
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener("click", () => {
                const farmSelect = document.getElementById("analyticsFilterFarm");
                const cropSelect = document.getElementById("analyticsFilterCrop");
                const startDate = document.getElementById("analyticsStartDate");
                const endDate = document.getElementById("analyticsEndDate");

                if (farmSelect) farmSelect.value = "";
                if (cropSelect) cropSelect.value = "";
                if (startDate) startDate.value = "";
                if (endDate) endDate.value = "";

                loadAnalytics();
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => {
                loadFilterOptions();
                loadAnalytics();
            });
        }

        // Re-render when language changes
        window.addEventListener("languageChanged", () => {
            if (latestAnalyticsData) {
                renderAnalytics(latestAnalyticsData);
            }
        });

        // Load data on page ready
        loadFilterOptions();
        loadAnalytics();
    }

    // Expose for external calls or testing
    window.agriSmartAnalytics = {
        loadFilterOptions,
        loadAnalytics,
        renderAnalytics
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAnalytics);
    } else {
        initAnalytics();
    }

})();
