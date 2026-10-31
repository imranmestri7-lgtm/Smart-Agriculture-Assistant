/**
 * AgriSmart Phase 10: IoT-Ready Smart Farm Monitoring Frontend Module
 * Handles sensor telemetry, device management, manual demo mode, history charts,
 * and smart irrigation integration.
 */

(function () {
    "use strict";

    const API_BASE = "/api/iot";

    function getAuthHeaders() {
        const token = localStorage.getItem("token") || localStorage.getItem("agriSmartToken");
        return {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        };
    }

    function translate(key, defaultText) {
        if (window.i18n && typeof window.i18n.t === "function") {
            return window.i18n.t(key) || defaultText;
        }
        return defaultText;
    }

    // State
    let currentSensors = [];
    let activeHistorySensorId = null;
    let activeHistoryRange = "24h";

    // =========================================================================
    // 1. DASHBOARD OVERVIEW & METRIC CARDS
    // =========================================================================

    async function loadIoTOverview() {
        try {
            const res = await fetch(`${API_BASE}/overview`, { headers: getAuthHeaders() });
            if (!res.ok) return;
            const data = await res.json();
            if (data.status !== "success") return;

            renderOverviewSummary(data.summary);
            renderMetricCards(data.latest_readings);
        } catch (err) {
            console.error("Failed to load IoT overview:", err);
        }
    }

    function renderOverviewSummary(summary) {
        const countsEl = document.getElementById("iotDeviceCounts");
        if (countsEl && summary) {
            countsEl.textContent = `(${summary.connected} online, ${summary.disconnected + summary.stale} offline / stale)`;
        }

        const badgeEl = document.getElementById("cardIotBadge");
        if (badgeEl && summary) {
            badgeEl.textContent = summary.connected > 0 ? `${summary.connected} Active` : "IoT Ready";
            badgeEl.className = summary.connected > 0 ? "iot-card-badge active" : "iot-card-badge";
        }
    }

    function renderMetricCards(readings) {
        if (!readings) return;

        const metricsConfig = [
            { key: "soil_moisture", valId: "valSoilMoisture", statusId: "statusSoilMoisture", farmId: "farmSoilMoisture", cropId: "cropSoilMoisture", timeId: "timeSoilMoisture", demoId: "demoBadgeSoilMoisture" },
            { key: "air_temp", valId: "valAirTemp", statusId: "statusAirTemp", farmId: "farmAirTemp", timeId: "timeAirTemp", demoId: "demoBadgeAirTemp" },
            { key: "air_humidity", valId: "valAirHumidity", statusId: "statusAirHumidity", farmId: "farmAirHumidity", timeId: "timeAirHumidity", demoId: "demoBadgeAirHumidity" },
            { key: "soil_temp", valId: "valSoilTemp", statusId: "statusSoilTemp", farmId: "farmSoilTemp", timeId: "timeSoilTemp", demoId: "demoBadgeSoilTemp" },
            { key: "water_level", valId: "valWaterLevel", statusId: "statusWaterLevel", farmId: "farmWaterLevel", timeId: "timeWaterLevel", demoId: "demoBadgeWaterLevel" }
        ];

        metricsConfig.forEach(cfg => {
            const r = readings[cfg.key];
            const valEl = document.getElementById(cfg.valId);
            const statusEl = document.getElementById(cfg.statusId);
            const farmEl = document.getElementById(cfg.farmId);
            const cropEl = cfg.cropId ? document.getElementById(cfg.cropId) : null;
            const timeEl = document.getElementById(cfg.timeId);
            const demoEl = document.getElementById(cfg.demoId);

            if (!r || !r.has_reading) {
                if (valEl) valEl.textContent = "--";
                if (statusEl) {
                    statusEl.textContent = translate("iot_status_disconnected", "No Sensor");
                    statusEl.className = "iot-status-tag status-disconnected";
                }
                if (farmEl) farmEl.textContent = "Not assigned";
                if (cropEl) cropEl.textContent = "-";
                if (timeEl) timeEl.textContent = "Never";
                if (demoEl) demoEl.style.display = "none";
                return;
            }

            if (valEl) valEl.textContent = typeof r.value === "number" ? r.value.toFixed(1) : r.value;
            if (statusEl) {
                statusEl.textContent = r.status;
                const statusClass = r.status.toLowerCase();
                statusEl.className = `iot-status-tag status-${statusClass}`;
            }
            if (farmEl) farmEl.textContent = r.farm_name || "Assigned Farm";
            if (cropEl) cropEl.textContent = r.crop_name || "All Fields";
            if (timeEl) timeEl.textContent = r.recorded_at ? r.recorded_at.split(" ")[1] || r.recorded_at : "Recent";
            if (demoEl) demoEl.style.display = r.is_demo ? "inline-block" : "none";
        });
    }

    // =========================================================================
    // 2. SENSOR MANAGEMENT TAB
    // =========================================================================

    async function loadSensorsList() {
        const listContainer = document.getElementById("sensorsListContainer");
        const emptyState = document.getElementById("sensorsEmptyState");
        if (!listContainer) return;

        try {
            const res = await fetch(`${API_BASE}/sensors`, { headers: getAuthHeaders() });
            if (!res.ok) return;
            const data = await res.json();
            currentSensors = data.sensors || [];

            updateHistorySensorDropdown(currentSensors);
            updateDemoSensorDropdown(currentSensors);

            if (currentSensors.length === 0) {
                listContainer.innerHTML = "";
                if (emptyState) emptyState.style.display = "block";
                return;
            }

            if (emptyState) emptyState.style.display = "none";
            renderSensorCards(currentSensors, listContainer);
        } catch (err) {
            console.error("Failed to load sensors list:", err);
        }
    }

    function renderSensorCards(sensors, container) {
        container.innerHTML = sensors.map(s => {
            const isConnected = s.status === "connected";
            const isStale = s.status === "stale";
            const statusLabel = isConnected ? translate("iot_status_connected", "Connected") :
                                isStale ? translate("iot_status_stale", "Stale") :
                                translate("iot_status_disconnected", "Disconnected");
            const statusClass = isConnected ? "connected" : isStale ? "stale" : "disconnected";

            const readingVal = s.latest_reading ?
                `${s.latest_reading.value} ${s.latest_reading.unit}` : "No telemetry yet";
            const isDemo = s.latest_reading && s.latest_reading.is_demo;

            return `
                <div class="sensor-card" data-sensor-id="${s.id}">
                    <div class="sensor-card-header">
                        <div class="sensor-title-row">
                            <span class="sensor-type-icon">${getSensorIcon(s.sensor_type)}</span>
                            <div>
                                <h4 class="sensor-card-name">${escapeHtml(s.sensor_name)}</h4>
                                <span class="sensor-device-id">ID: <code>${escapeHtml(s.device_id)}</code></span>
                            </div>
                        </div>
                        <span class="sensor-status-pill ${statusClass}">
                            <i class="status-dot"></i> ${statusLabel}
                        </span>
                    </div>

                    <div class="sensor-card-meta">
                        <div class="sensor-meta-item">
                            <span class="meta-label">🏡 Farm:</span>
                            <strong>${escapeHtml(s.farm_name)}</strong>
                        </div>
                        <div class="sensor-meta-item">
                            <span class="meta-label">🌾 Crop:</span>
                            <strong>${escapeHtml(s.crop_name)}</strong>
                        </div>
                        <div class="sensor-meta-item">
                            <span class="meta-label">📊 Latest:</span>
                            <strong class="latest-val">${readingVal} ${isDemo ? '<span class="demo-chip">DEMO</span>' : ''}</strong>
                        </div>
                        <div class="sensor-meta-item">
                            <span class="meta-label">⏱️ Last seen:</span>
                            <span>${s.last_reading_at || 'Never'}</span>
                        </div>
                    </div>

                    <div class="sensor-card-actions">
                        <button type="button" class="btn-sensor-action btn-demo-inject" data-action="demo" data-id="${s.id}" title="Test with Demo Reading">
                            🧪 Demo
                        </button>
                        <button type="button" class="btn-sensor-action btn-history-view" data-action="history" data-id="${s.id}" title="View History Chart">
                            📈 History
                        </button>
                        <button type="button" class="btn-sensor-action btn-rotate-key" data-action="rotate-key" data-id="${s.id}" title="Rotate Device Key">
                            🔑 Key
                        </button>
                        <button type="button" class="btn-sensor-action btn-sensor-del" data-action="delete" data-id="${s.id}" title="Remove Sensor">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        }).join("");

        // Attach action listeners
        container.querySelectorAll(".btn-sensor-action").forEach(btn => {
            btn.addEventListener("click", handleSensorCardAction);
        });
    }

    function getSensorIcon(type) {
        switch (type) {
            case "soil_moisture": return "💧";
            case "air_temp_humidity": return "🌡️";
            case "air_temp": return "🌡️";
            case "air_humidity": return "☁️";
            case "soil_temp": return "🌱";
            case "water_level": return "🚰";
            default: return "📡";
        }
    }

    function handleSensorCardAction(e) {
        const btn = e.currentTarget;
        const action = btn.getAttribute("data-action");
        const sid = parseInt(btn.getAttribute("data-id"), 10);
        const sensor = currentSensors.find(s => s.id === sid);

        if (action === "demo") {
            openDemoModeModal(sid);
        } else if (action === "history") {
            switchToHistoryTab(sid);
        } else if (action === "rotate-key") {
            handleRotateKey(sid);
        } else if (action === "delete") {
            handleDeleteSensor(sid, sensor ? sensor.sensor_name : "Sensor");
        }
    }

    async function handleRotateKey(sensorId) {
        if (!confirm("Regenerate device key? You must flash this new key onto your ESP32 / Arduino.")) return;
        try {
            const res = await fetch(`${API_BASE}/sensors/${sensorId}/regenerate-key`, {
                method: "POST",
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (data.status === "success") {
                showDeviceKeyModal(data.device_id, data.device_key);
            } else {
                alert(data.message || "Key rotation failed.");
            }
        } catch (err) {
            console.error("Rotate key error:", err);
        }
    }

    async function handleDeleteSensor(sensorId, sensorName) {
        if (!confirm(`Are you sure you want to remove sensor '${sensorName}' and its reading history?`)) return;
        try {
            const res = await fetch(`${API_BASE}/sensors/${sensorId}`, {
                method: "DELETE",
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (data.status === "success") {
                await loadSensorsList();
                await loadIoTOverview();
            } else {
                alert(data.message || "Failed to remove sensor.");
            }
        } catch (err) {
            console.error("Delete sensor error:", err);
        }
    }

    // =========================================================================
    // 3. SENSOR REGISTRATION MODAL
    // =========================================================================

    function initAddSensorModal() {
        const btnOpen = document.getElementById("btnOpenAddSensorModal");
        const btnFirst = document.getElementById("btnRegisterFirstSensor");
        const modal = document.getElementById("sensorModal");
        const form = document.getElementById("sensorForm");

        if (btnOpen) btnOpen.addEventListener("click", () => openSensorModal());
        if (btnFirst) btnFirst.addEventListener("click", () => openSensorModal());

        if (form) {
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                await submitRegisterSensor();
            });
        }
    }

    async function openSensorModal() {
        const modal = document.getElementById("sensorModal");
        if (!modal) return;

        // Populate farms dropdown
        await populateFarmDropdown("sensorFarmSelect", "sensorCropSelect");

        modal.classList.add("active");
        modal.style.display = "flex";
    }

    async function populateFarmDropdown(farmSelectId, cropSelectId) {
        const farmSelect = document.getElementById(farmSelectId);
        const cropSelect = document.getElementById(cropSelectId);
        if (!farmSelect) return;

        try {
            const res = await fetch("/api/farms", { headers: getAuthHeaders() });
            const data = await res.json();
            const farms = data.farms || [];

            farmSelect.innerHTML = '<option value="">-- Select Farm --</option>' +
                farms.map(f => `<option value="${f.id}">${escapeHtml(f.farm_name)} (${f.total_area} ${f.area_unit})</option>`).join("");

            if (cropSelect) {
                farmSelect.addEventListener("change", async () => {
                    const fid = farmSelect.value;
                    if (!fid) {
                        cropSelect.innerHTML = '<option value="">-- Optional: Assign Crop --</option>';
                        return;
                    }
                    try {
                        const cres = await fetch(`/api/crops?farm_id=${fid}`, { headers: getAuthHeaders() });
                        const cdata = await cres.json();
                        const crops = cdata.crops || [];
                        cropSelect.innerHTML = '<option value="">-- Optional: Assign Crop --</option>' +
                            crops.map(c => `<option value="${c.id}">${escapeHtml(c.crop_name)} (${c.variety || 'Standard'})</option>`).join("");
                    } catch (e) {
                        console.error("Crop populate error:", e);
                    }
                });
            }
        } catch (e) {
            console.error("Farm populate error:", e);
        }
    }

    async function submitRegisterSensor() {
        const farmId = document.getElementById("sensorFarmSelect").value;
        const cropId = document.getElementById("sensorCropSelect") ? document.getElementById("sensorCropSelect").value : null;
        const name = document.getElementById("sensorNameInput").value.trim();
        const type = document.getElementById("sensorTypeSelect").value;
        const deviceId = document.getElementById("sensorDeviceIdInput").value.trim().toUpperCase();

        if (!farmId || !name || !type || !deviceId) {
            alert("Please fill in all required fields.");
            return;
        }

        const payload = {
            farm_id: parseInt(farmId, 10),
            crop_id: cropId ? parseInt(cropId, 10) : null,
            sensor_name: name,
            sensor_type: type,
            device_id: deviceId
        };

        try {
            const res = await fetch(`${API_BASE}/sensors`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.status === "success") {
                closeAllModals();
                // Show device key modal
                showDeviceKeyModal(data.sensor.device_id, data.sensor.device_key);
                await loadSensorsList();
                await loadIoTOverview();
            } else {
                alert(data.message || "Failed to register sensor.");
            }
        } catch (err) {
            console.error("Sensor register error:", err);
            alert("Network error while registering sensor.");
        }
    }

    function showDeviceKeyModal(deviceId, deviceKey) {
        const modal = document.getElementById("deviceKeyModal");
        const devIdEl = document.getElementById("modalKeyDeviceId");
        const keyEl = document.getElementById("modalKeySecret");
        const copyBtn = document.getElementById("btnCopyDeviceKey");

        if (!modal || !keyEl) return;
        if (devIdEl) devIdEl.textContent = deviceId;
        keyEl.value = deviceKey;

        if (copyBtn) {
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(deviceKey).then(() => {
                    copyBtn.textContent = "✓ Copied!";
                    setTimeout(() => { copyBtn.textContent = "📋 Copy Secret Key"; }, 2000);
                });
            };
        }

        modal.classList.add("active");
        modal.style.display = "flex";
    }

    // =========================================================================
    // 4. MANUAL DEMO MODE
    // =========================================================================

    function initDemoMode() {
        const btnOpen = document.getElementById("btnOpenDemoMode");
        const form = document.getElementById("demoModeForm");
        const btnClear = document.getElementById("btnClearDemoData");

        if (btnOpen) btnOpen.addEventListener("click", () => openDemoModeModal());

        if (form) {
            form.addEventListener("submit", async (e) => {
                e.preventDefault();
                await submitDemoReading();
            });
        }

        if (btnClear) {
            btnClear.addEventListener("click", async () => {
                const select = document.getElementById("demoSensorSelect");
                const sid = select ? select.value : null;
                if (!sid) {
                    alert("Please select a sensor to clear demo data.");
                    return;
                }
                if (!confirm("Clear all demo readings for this sensor? Real hardware readings will remain untouched.")) return;

                try {
                    const res = await fetch(`${API_BASE}/sensors/${sid}/demo`, {
                        method: "DELETE",
                        headers: getAuthHeaders()
                    });
                    const data = await res.json();
                    if (data.status === "success") {
                        alert(data.message);
                        closeAllModals();
                        await loadSensorsList();
                        await loadIoTOverview();
                    }
                } catch (e) {
                    console.error("Clear demo error:", e);
                }
            });
        }
    }

    function openDemoModeModal(preselectedSensorId) {
        const modal = document.getElementById("demoModeModal");
        const select = document.getElementById("demoSensorSelect");
        if (!modal || !select) return;

        updateDemoSensorDropdown(currentSensors);
        if (preselectedSensorId) {
            select.value = preselectedSensorId;
            updateDemoUnitLabel(preselectedSensorId);
        }

        select.onchange = () => updateDemoUnitLabel(select.value);

        modal.classList.add("active");
        modal.style.display = "flex";
    }

    function updateDemoSensorDropdown(sensors) {
        const select = document.getElementById("demoSensorSelect");
        if (!select) return;

        select.innerHTML = '<option value="">-- Choose Sensor --</option>' +
            sensors.map(s => `<option value="${s.id}">${escapeHtml(s.sensor_name)} (${s.device_id} - ${s.sensor_type_label})</option>`).join("");
    }

    function updateDemoUnitLabel(sensorId) {
        const unitEl = document.getElementById("demoUnitLabel");
        if (!unitEl) return;
        const s = currentSensors.find(x => x.id === parseInt(sensorId, 10));
        unitEl.textContent = s ? s.unit : "%";
    }

    async function submitDemoReading() {
        const sid = document.getElementById("demoSensorSelect").value;
        const valInput = document.getElementById("demoReadingValue");
        const val = valInput ? parseFloat(valInput.value) : null;

        if (!sid || isNaN(val)) {
            alert("Please select a sensor and enter a valid numeric reading.");
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/sensors/${sid}/demo`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify({ value: val })
            });
            const data = await res.json();

            if (data.status === "success") {
                closeAllModals();
                if (valInput) valInput.value = "";
                await loadSensorsList();
                await loadIoTOverview();
            } else {
                alert(data.message || "Failed to inject demo reading.");
            }
        } catch (err) {
            console.error("Demo inject error:", err);
        }
    }

    // =========================================================================
    // 5. SENSOR HISTORY & ANALYTICS TAB
    // =========================================================================

    function initHistoryTab() {
        const select = document.getElementById("historySensorSelect");
        if (select) {
            select.addEventListener("change", () => {
                activeHistorySensorId = select.value ? parseInt(select.value, 10) : null;
                if (activeHistorySensorId) loadSensorHistory();
            });
        }

        const rangePills = document.querySelectorAll("#historyRangePills .range-pill");
        rangePills.forEach(pill => {
            pill.addEventListener("click", () => {
                rangePills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                activeHistoryRange = pill.getAttribute("data-range");
                if (activeHistorySensorId) loadSensorHistory();
            });
        });
    }

    function updateHistorySensorDropdown(sensors) {
        const select = document.getElementById("historySensorSelect");
        if (!select) return;

        select.innerHTML = '<option value="">-- Choose a sensor --</option>' +
            sensors.map(s => `<option value="${s.id}">${escapeHtml(s.sensor_name)} (${s.device_id} - ${s.farm_name})</option>`).join("");

        if (activeHistorySensorId) select.value = activeHistorySensorId;
    }

    function switchToHistoryTab(sensorId) {
        const tabBtn = document.getElementById("tabBtnHistory");
        if (tabBtn) tabBtn.click();

        activeHistorySensorId = sensorId;
        const select = document.getElementById("historySensorSelect");
        if (select) select.value = sensorId;
        loadSensorHistory();
    }

    async function loadSensorHistory() {
        if (!activeHistorySensorId) return;

        const url = `${API_BASE}/sensors/${activeHistorySensorId}/history?range=${activeHistoryRange}&include_demo=true`;
        try {
            const res = await fetch(url, { headers: getAuthHeaders() });
            if (!res.ok) return;
            const data = await res.json();
            if (data.status !== "success") return;

            renderHistoryStats(data.stats);
            renderHistoryChart(data.readings, data.stats);
            renderHistoryTable(data.readings);
        } catch (err) {
            console.error("Failed to load sensor history:", err);
        }
    }

    function renderHistoryStats(stats) {
        const minEl = document.getElementById("statMinVal");
        const avgEl = document.getElementById("statAvgVal");
        const maxEl = document.getElementById("statMaxVal");
        const countEl = document.getElementById("statCountVal");

        if (minEl) minEl.textContent = stats && stats.min !== null ? `${stats.min} ${stats.unit}` : "--";
        if (avgEl) avgEl.textContent = stats && stats.avg !== null ? `${stats.avg} ${stats.unit}` : "--";
        if (maxEl) maxEl.textContent = stats && stats.max !== null ? `${stats.max} ${stats.unit}` : "--";
        if (countEl) countEl.textContent = stats ? stats.count : 0;
    }

    function renderHistoryChart(readings, stats) {
        const svg = document.getElementById("historyLineChart");
        if (!svg) return;

        if (!readings || readings.length === 0) {
            svg.innerHTML = `
                <text x="400" y="120" text-anchor="middle" fill="#94a3b8" font-size="14" font-family="system-ui">
                    No historical readings recorded in this time range.
                </text>
            `;
            return;
        }

        const width = 800;
        const height = 240;
        const padX = 40;
        const padY = 30;

        const minVal = stats.min !== null ? Math.floor(stats.min * 0.9) : 0;
        const maxVal = stats.max !== null ? Math.ceil(stats.max * 1.1) : 100;
        const valRange = maxVal - minVal || 1;

        const pts = readings.map((r, i) => {
            const x = padX + (i / (readings.length - 1 || 1)) * (width - padX * 2);
            const y = height - padY - ((r.value - minVal) / valRange) * (height - padY * 2);
            return { x, y, val: r.value, demo: r.is_demo, time: r.recorded_at };
        });

        const polylinePoints = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

        let dotsHtml = pts.map(p => `
            <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${p.demo ? 5 : 4}"
                    fill="${p.demo ? '#8b5cf6' : '#10b981'}" stroke="#ffffff" stroke-width="2">
                <title>${p.val} ${stats.unit || ''} (${p.demo ? 'Demo' : 'Live'}) at ${p.time}</title>
            </circle>
        `).join("");

        svg.innerHTML = `
            <!-- Gridlines -->
            <line x1="${padX}" y1="${padY}" x2="${width - padX}" y2="${padY}" stroke="#e2e8f0" stroke-dasharray="4" />
            <line x1="${padX}" y1="${height / 2}" x2="${width - padX}" y2="${height / 2}" stroke="#e2e8f0" stroke-dasharray="4" />
            <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="#cbd5e1" />
            
            <!-- Value Labels -->
            <text x="${padX - 8}" y="${padY + 4}" text-anchor="end" fill="#64748b" font-size="11">${maxVal}</text>
            <text x="${padX - 8}" y="${height / 2 + 4}" text-anchor="end" fill="#64748b" font-size="11">${((maxVal + minVal) / 2).toFixed(1)}</text>
            <text x="${padX - 8}" y="${height - padY + 4}" text-anchor="end" fill="#64748b" font-size="11">${minVal}</text>

            <!-- Line Path -->
            <polyline fill="none" stroke="#059669" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${polylinePoints}" />
            
            <!-- Data Points -->
            ${dotsHtml}
        `;
    }

    function renderHistoryTable(readings) {
        const tbody = document.getElementById("historyTableBody");
        if (!tbody) return;

        if (!readings || readings.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#94a3b8; padding:20px;">No telemetry records available.</td></tr>`;
            return;
        }

        // Show latest first in table
        const reversed = [...readings].reverse();
        tbody.innerHTML = reversed.map(r => `
            <tr>
                <td>${r.recorded_at}</td>
                <td><strong>${r.value.toFixed(1)} ${r.unit}</strong></td>
                <td><span class="iot-status-tag status-normal">Recorded</span></td>
                <td>${r.is_demo ? '<span class="demo-chip">DEMO</span>' : '<span class="hardware-chip">HARDWARE</span>'}</td>
            </tr>
        `).join("");
    }

    // =========================================================================
    // 6. TABS NAVIGATION & MODAL HELPERS
    // =========================================================================

    function initTabs() {
        const tabBtns = document.querySelectorAll(".iot-tab-btn");
        tabBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                tabBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                const targetId = btn.getAttribute("data-tab");
                document.querySelectorAll(".iot-tab-panel").forEach(p => {
                    p.style.display = p.id === targetId ? "block" : "none";
                });
            });
        });

        // Refresh button
        const btnRef = document.getElementById("btnRefreshIoT");
        if (btnRef) {
            btnRef.addEventListener("click", async () => {
                btnRef.disabled = true;
                await loadIoTOverview();
                await loadSensorsList();
                if (activeHistorySensorId) await loadSensorHistory();
                setTimeout(() => { btnRef.disabled = false; }, 1000);
            });
        }
    }

    function closeAllModals() {
        document.querySelectorAll(".farm-modal-backdrop").forEach(m => {
            m.classList.remove("active");
            m.style.display = "none";
        });
    }

    function initModalCloseEvents() {
        document.querySelectorAll(".modal-close-btn").forEach(btn => {
            btn.addEventListener("click", closeAllModals);
        });

        document.querySelectorAll(".farm-modal-backdrop").forEach(m => {
            m.addEventListener("click", (e) => {
                if (e.target === m) closeAllModals();
            });
        });
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // =========================================================================
    // 7. PUBLIC IRRIGATION INTEGRATION HOOK
    // =========================================================================

    window.AgriSmartIoT = {
        async getSoilMoistureReading(cropName, farmId) {
            try {
                let url = `${API_BASE}/irrigation-sync?`;
                if (cropName) url += `crop=${encodeURIComponent(cropName)}&`;
                if (farmId) url += `farm_id=${encodeURIComponent(farmId)}`;
                const res = await fetch(url, { headers: getAuthHeaders() });
                if (!res.ok) return null;
                return await res.json();
            } catch (err) {
                console.error("Irrigation sync error:", err);
                return null;
            }
        },
        refresh: async () => {
            await loadIoTOverview();
            await loadSensorsList();
        }
    };

    // =========================================================================
    // INIT ON LOAD
    // =========================================================================

    document.addEventListener("DOMContentLoaded", () => {
        initTabs();
        initAddSensorModal();
        initDemoMode();
        initHistoryTab();
        initModalCloseEvents();

        loadIoTOverview();
        loadSensorsList();
    });

    window.addEventListener("languageChanged", () => {
        loadIoTOverview();
        loadSensorsList();
        if (activeHistorySensorId) loadSensorHistory();
    });

})();
