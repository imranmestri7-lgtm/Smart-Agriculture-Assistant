/**
 * farm_crop.js - Farm & Crop Management & Growth Tracking for AgriSmart (Phase 6)
 * Handles authenticated CRUD operations for farms and crops, manual growth tracking,
 * and dashboard summary metrics with full multilingual support.
 */

(function () {
    "use strict";

    // Growth status badge color/style mapping
    const STATUS_CONFIG = {
        "Newly Planted": { color: "#0284c7", bg: "#e0f2fe", icon: "🌱", key: "status_newly_planted" },
        "Growing": { color: "#16a34a", bg: "#dcfce7", icon: "🌿", key: "status_growing" },
        "Flowering": { color: "#d97706", bg: "#fef3c7", icon: "🌸", key: "status_flowering" },
        "Fruiting": { color: "#ea580c", bg: "#ffedd5", icon: "🍅", key: "status_fruiting" },
        "Ready for Harvest": { color: "#059669", bg: "#ecfdf5", icon: "🌾", key: "status_ready_harvest" },
        "Harvested": { color: "#475569", bg: "#f1f5f9", icon: "📦", key: "status_harvested" }
    };

    let registeredFarms = [];
    let registeredCrops = [];
    let editingFarmId = null;
    let editingCropId = null;

    function getToken() {
        return localStorage.getItem("agriSmartToken") || localStorage.getItem("token") || "";
    }

    function getI18n(key, fallback) {
        if (window.i18n && typeof window.i18n.t === "function") {
            const val = window.i18n.t(key);
            if (val && val !== key) return val;
        }
        return fallback || key;
    }

    async function apiRequest(url, method = "GET", body = null) {
        const token = getToken();
        if (!token) {
            console.warn("No authentication token found.");
            return null;
        }

        const headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json"
        };

        const options = { method, headers };
        if (body) {
            options.body = JSON.stringify(body);
        }

        const res = await fetch(url, options);
        if (res.status === 401) {
            console.warn("Authentication required or expired.");
            return null;
        }
        return await res.json();
    }

    // =========================================================================
    // DASHBOARD SUMMARY
    // =========================================================================

    async function loadDashboardSummary() {
        const data = await apiRequest("/api/crops/dashboard-summary");
        if (!data || data.status !== "success" || !data.summary) return;

        const summary = data.summary;
        const totalFarmsEl = document.getElementById("summaryTotalFarms");
        const totalCropsEl = document.getElementById("summaryTotalCrops");
        const cropsGrowingEl = document.getElementById("summaryCropsGrowing");
        const cropsHarvestEl = document.getElementById("summaryCropsHarvest");

        if (totalFarmsEl) totalFarmsEl.textContent = summary.total_farms || 0;
        if (totalCropsEl) totalCropsEl.textContent = summary.total_crops || 0;
        if (cropsGrowingEl) cropsGrowingEl.textContent = summary.crops_growing || 0;
        if (cropsHarvestEl) cropsHarvestEl.textContent = summary.crops_ready_for_harvest || 0;
    }

    // =========================================================================
    // FARMS MANAGEMENT
    // =========================================================================

    async function loadFarms() {
        const data = await apiRequest("/api/farms");
        if (!data || data.status !== "success") return;

        registeredFarms = data.farms || [];
        renderFarms();
        updateFarmDropdowns();
    }

    function renderFarms() {
        const container = document.getElementById("farmsList");
        if (!container) return;

        if (registeredFarms.length === 0) {
            container.innerHTML = `
                <div class="farm-empty-state">
                    <div class="empty-icon">🏡</div>
                    <p data-i18n="empty_farms_msg">${getI18n("empty_farms_msg", "No farms registered yet. Add your first farm to start tracking crops!")}</p>
                    <button type="button" class="btn-primary" onclick="window.FarmCropApp.openFarmModal()">${getI18n("btn_add_farm", "➕ Add Farm")}</button>
                </div>
            `;
            return;
        }

        container.innerHTML = registeredFarms.map(f => {
            const unitText = f.area_unit === "hectare" ? getI18n("unit_hectare", "Hectare") : getI18n("unit_acre", "Acre");
            return `
                <div class="farm-item-card" data-farm-id="${f.id}">
                    <div class="farm-card-header">
                        <div class="farm-header-title">
                            <span class="farm-icon">🏡</span>
                            <h4>${escapeHtml(f.farm_name)}</h4>
                        </div>
                        <span class="crop-badge">${f.crop_count} ${getI18n("summary_total_crops", "Crops")}</span>
                    </div>
                    <div class="farm-card-body">
                        <div class="farm-meta-row">
                            <span class="meta-label">📍 ${getI18n("farm_location_label", "Location")}:</span>
                            <span class="meta-value">${escapeHtml(f.location)}</span>
                        </div>
                        <div class="farm-meta-row">
                            <span class="meta-label">📐 ${getI18n("total_area_label", "Total Area")}:</span>
                            <span class="meta-value">${f.total_area} ${unitText}</span>
                        </div>
                    </div>
                    <div class="farm-card-footer">
                        <button type="button" class="btn-action-edit" onclick="window.FarmCropApp.editFarm(${f.id})">✏️ ${getI18n("btn_edit", "Edit")}</button>
                        <button type="button" class="btn-action-delete" onclick="window.FarmCropApp.deleteFarm(${f.id})">🗑️ ${getI18n("btn_delete", "Delete")}</button>
                    </div>
                </div>
            `;
        }).join("");
    }

    function updateFarmDropdowns() {
        const cropFarmSelect = document.getElementById("cropFarmId");
        const filterCropFarm = document.getElementById("filterCropFarm");

        if (cropFarmSelect) {
            const placeholder = getI18n("select_farm_placeholder", "Select registered farm");
            cropFarmSelect.innerHTML = `<option value="">-- ${placeholder} --</option>` +
                registeredFarms.map(f => `<option value="${f.id}">${escapeHtml(f.farm_name)} (${f.total_area} ${f.area_unit})</option>`).join("");
        }

        if (filterCropFarm) {
            const currentFilter = filterCropFarm.value;
            filterCropFarm.innerHTML = `<option value="">All Farms</option>` +
                registeredFarms.map(f => `<option value="${f.id}">${escapeHtml(f.farm_name)}</option>`).join("");
            filterCropFarm.value = currentFilter;
        }
    }

    // =========================================================================
    // CROPS & GROWTH TRACKING MANAGEMENT
    // =========================================================================

    async function loadCrops() {
        const filterEl = document.getElementById("filterCropFarm");
        const farmId = filterEl ? filterEl.value : "";
        const url = farmId ? `/api/crops?farm_id=${encodeURIComponent(farmId)}` : "/api/crops";

        const data = await apiRequest(url);
        if (!data || data.status !== "success") return;

        registeredCrops = data.crops || [];
        renderCrops();
    }

    function renderCrops() {
        const container = document.getElementById("cropsList");
        if (!container) return;

        if (registeredCrops.length === 0) {
            container.innerHTML = `
                <div class="crop-empty-state">
                    <div class="empty-icon">🌾</div>
                    <p data-i18n="empty_crops_msg">${getI18n("empty_crops_msg", "No crops registered yet. Register a crop under your farm to track growth!")}</p>
                    <button type="button" class="btn-primary" onclick="window.FarmCropApp.openCropModal()">${getI18n("btn_add_crop", "➕ Register Crop")}</button>
                </div>
            `;
            return;
        }

        container.innerHTML = registeredCrops.map(c => {
            const cfg = STATUS_CONFIG[c.growth_status] || STATUS_CONFIG["Newly Planted"];
            const statusLabel = getI18n(cfg.key, c.growth_status);
            const unitText = c.area_unit === "hectare" ? getI18n("unit_hectare", "Hectare") : getI18n("unit_acre", "Acre");
            const daysText = c.days_since_planting === 1
                ? `1 day growing`
                : `${c.days_since_planting} days growing`;

            return `
                <div class="crop-item-card" data-crop-id="${c.id}">
                    <div class="crop-card-header">
                        <div class="crop-title-group">
                            <h4>${escapeHtml(c.crop_name)}</h4>
                            ${c.variety ? `<span class="variety-tag">${escapeHtml(c.variety)}</span>` : ""}
                        </div>
                        <span class="growth-status-pill" style="background:${cfg.bg}; color:${cfg.color}; border: 1px solid ${cfg.color}33;">
                            ${cfg.icon} ${statusLabel}
                        </span>
                    </div>

                    <div class="crop-card-body">
                        <div class="crop-info-row">
                            <span class="info-label">🏡 ${getI18n("farm_name_label", "Farm")}:</span>
                            <span class="info-value"><strong>${escapeHtml(c.farm_name)}</strong></span>
                        </div>
                        <div class="crop-info-row">
                            <span class="info-label">🌱 ${getI18n("planting_date_label", "Planted")}:</span>
                            <span class="info-value">${c.planting_date || "-"} <span class="days-pill">⏱️ ${daysText}</span></span>
                        </div>
                        ${c.cultivated_area ? `
                        <div class="crop-info-row">
                            <span class="info-label">📐 ${getI18n("cultivated_area_label", "Area")}:</span>
                            <span class="info-value">${c.cultivated_area} ${unitText}</span>
                        </div>` : ""}
                        ${c.expected_harvest_date ? `
                        <div class="crop-info-row">
                            <span class="info-label">🌾 ${getI18n("expected_harvest_label", "Expected Harvest")}:</span>
                            <span class="info-value">${c.expected_harvest_date}</span>
                        </div>` : ""}
                        ${c.notes ? `
                        <div class="crop-notes-box">
                            <span class="notes-label">📝 ${getI18n("crop_notes_label", "Notes")}:</span>
                            <p class="notes-text">${escapeHtml(c.notes)}</p>
                        </div>` : ""}
                    </div>

                    <!-- GROWTH TRACKING MANUAL STATUS UPDATE -->
                    <div class="crop-status-updater">
                        <label for="statusSelect_${c.id}" class="update-label">Update Stage:</label>
                        <select id="statusSelect_${c.id}" class="stage-select" onchange="window.FarmCropApp.updateGrowthStatus(${c.id}, this.value)">
                            ${Object.keys(STATUS_CONFIG).map(st => `
                                <option value="${st}" ${st === c.growth_status ? "selected" : ""}>
                                    ${STATUS_CONFIG[st].icon} ${getI18n(STATUS_CONFIG[st].key, st)}
                                </option>
                            `).join("")}
                        </select>
                    </div>

                    <div class="crop-card-footer">
                        <button type="button" class="btn-action-edit" onclick="window.FarmCropApp.editCrop(${c.id})">✏️ ${getI18n("btn_edit", "Edit")}</button>
                        <button type="button" class="btn-action-delete" onclick="window.FarmCropApp.deleteCrop(${c.id})">🗑️ ${getI18n("btn_delete", "Delete")}</button>
                    </div>
                </div>
            `;
        }).join("");
    }

    // =========================================================================
    // MODAL DIALOGS & ACTIONS
    // =========================================================================

    function openFarmModal(farm = null) {
        editingFarmId = farm ? farm.id : null;
        const modal = document.getElementById("farmModal");
        const title = document.getElementById("farmModalTitle");
        const form = document.getElementById("farmForm");
        if (!modal || !form) return;

        title.textContent = farm ? getI18n("btn_edit", "Edit Farm") : getI18n("btn_add_farm", "Add Farm");
        form.reset();

        if (farm) {
            document.getElementById("farmNameInput").value = farm.farm_name;
            document.getElementById("farmLocationInput").value = farm.location;
            document.getElementById("farmAreaInput").value = farm.total_area;
            document.getElementById("farmAreaUnitSelect").value = farm.area_unit || "acre";
        }

        modal.classList.add("open");
    }

    function closeFarmModal() {
        const modal = document.getElementById("farmModal");
        if (modal) modal.classList.remove("open");
        editingFarmId = null;
    }

    function openCropModal(crop = null) {
        editingCropId = crop ? crop.id : null;
        const modal = document.getElementById("cropModal");
        const title = document.getElementById("cropModalTitle");
        const form = document.getElementById("cropForm");
        if (!modal || !form) return;

        if (registeredFarms.length === 0) {
            alert(getI18n("empty_farms_msg", "Please add a farm first before registering crops."));
            openFarmModal();
            return;
        }

        title.textContent = crop ? getI18n("btn_edit", "Edit Crop") : getI18n("btn_add_crop", "Register Crop");
        form.reset();
        updateFarmDropdowns();

        if (crop) {
            document.getElementById("cropFarmId").value = crop.farm_id;
            document.getElementById("cropNameInput").value = crop.crop_name;
            document.getElementById("cropVarietyInput").value = crop.variety || "";
            document.getElementById("cropPlantingDate").value = crop.planting_date || "";
            document.getElementById("cropAreaInput").value = crop.cultivated_area || "";
            document.getElementById("cropAreaUnit").value = crop.area_unit || "acre";
            document.getElementById("cropHarvestDate").value = crop.expected_harvest_date || "";
            document.getElementById("cropGrowthStatus").value = crop.growth_status || "Newly Planted";
            document.getElementById("cropNotesInput").value = crop.notes || "";
        } else {
            // Default to today's date for planting date
            const today = new Date().toISOString().substring(0, 10);
            document.getElementById("cropPlantingDate").value = today;
        }

        modal.classList.add("open");
    }

    function closeCropModal() {
        const modal = document.getElementById("cropModal");
        if (modal) modal.classList.remove("open");
        editingCropId = null;
    }

    // =========================================================================
    // CRUD OPERATIONS
    // =========================================================================

    async function handleFarmSubmit(e) {
        e.preventDefault();
        const farm_name = document.getElementById("farmNameInput").value.trim();
        const location = document.getElementById("farmLocationInput").value.trim();
        const total_area = parseFloat(document.getElementById("farmAreaInput").value);
        const area_unit = document.getElementById("farmAreaUnitSelect").value;

        if (!farm_name || !location || isNaN(total_area) || total_area <= 0) {
            alert("Please provide valid farm name, location, and total area.");
            return;
        }

        const payload = { farm_name, location, total_area, area_unit };
        let res;
        if (editingFarmId) {
            res = await apiRequest(`/api/farms/${editingFarmId}`, "PUT", payload);
        } else {
            res = await apiRequest("/api/farms", "POST", payload);
        }

        if (res && res.status === "success") {
            closeFarmModal();
            await loadFarms();
            await loadDashboardSummary();
        } else {
            alert((res && res.message) || "Failed to save farm.");
        }
    }

    async function handleCropSubmit(e) {
        e.preventDefault();
        const farm_id = parseInt(document.getElementById("cropFarmId").value, 10);
        const crop_name = document.getElementById("cropNameInput").value.trim();
        const variety = document.getElementById("cropVarietyInput").value.trim();
        const planting_date = document.getElementById("cropPlantingDate").value;
        const cultivated_area = parseFloat(document.getElementById("cropAreaInput").value);
        const area_unit = document.getElementById("cropAreaUnit").value;
        const expected_harvest_date = document.getElementById("cropHarvestDate").value;
        const growth_status = document.getElementById("cropGrowthStatus").value;
        const notes = document.getElementById("cropNotesInput").value.trim();

        if (!farm_id || !crop_name || !planting_date || isNaN(cultivated_area) || cultivated_area <= 0) {
            alert("Please fill in required fields: Farm, Crop Name, Planting Date, and Cultivated Area.");
            return;
        }

        const payload = {
            farm_id,
            crop_name,
            variety,
            planting_date,
            cultivated_area,
            area_unit,
            expected_harvest_date: expected_harvest_date || null,
            growth_status,
            notes
        };

        let res;
        if (editingCropId) {
            res = await apiRequest(`/api/crops/${editingCropId}`, "PUT", payload);
        } else {
            res = await apiRequest("/api/crops", "POST", payload);
        }

        if (res && res.status === "success") {
            closeCropModal();
            await loadCrops();
            await loadFarms();
            await loadDashboardSummary();
        } else {
            alert((res && res.message) || "Failed to save crop.");
        }
    }

    async function updateGrowthStatus(cropId, newStatus) {
        const res = await apiRequest(`/api/crops/${cropId}/status`, "PATCH", { growth_status: newStatus });
        if (res && res.status === "success") {
            await loadCrops();
            await loadDashboardSummary();
        } else {
            alert((res && res.message) || "Failed to update growth status.");
        }
    }

    async function deleteFarm(farmId) {
        const confirmMsg = getI18n("confirm_delete_farm", "Are you sure you want to delete this farm and all its associated crops?");
        if (!confirm(confirmMsg)) return;

        const res = await apiRequest(`/api/farms/${farmId}`, "DELETE");
        if (res && res.status === "success") {
            await loadFarms();
            await loadCrops();
            await loadDashboardSummary();
        } else {
            alert((res && res.message) || "Failed to delete farm.");
        }
    }

    async function deleteCrop(cropId) {
        const confirmMsg = getI18n("confirm_delete_crop", "Are you sure you want to delete this crop?");
        if (!confirm(confirmMsg)) return;

        const res = await apiRequest(`/api/crops/${cropId}`, "DELETE");
        if (res && res.status === "success") {
            await loadCrops();
            await loadFarms();
            await loadDashboardSummary();
        } else {
            alert((res && res.message) || "Failed to delete crop.");
        }
    }

    function editFarm(farmId) {
        const farm = registeredFarms.find(f => f.id === farmId);
        if (farm) openFarmModal(farm);
    }

    function editCrop(cropId) {
        const crop = registeredCrops.find(c => c.id === cropId);
        if (crop) openCropModal(crop);
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
    // INITIALIZATION & TAB SWITCHING
    // =========================================================================

    function initTabs() {
        const tabCropsBtn = document.getElementById("tabCropsBtn");
        const tabFarmsBtn = document.getElementById("tabFarmsBtn");
        const cropsPane = document.getElementById("cropsPane");
        const farmsPane = document.getElementById("farmsPane");

        if (tabCropsBtn && tabFarmsBtn) {
            tabCropsBtn.addEventListener("click", () => {
                tabCropsBtn.classList.add("active");
                tabFarmsBtn.classList.remove("active");
                if (cropsPane) cropsPane.style.display = "block";
                if (farmsPane) farmsPane.style.display = "none";
            });

            tabFarmsBtn.addEventListener("click", () => {
                tabFarmsBtn.classList.add("active");
                tabCropsBtn.classList.remove("active");
                if (farmsPane) farmsPane.style.display = "block";
                if (cropsPane) cropsPane.style.display = "none";
            });
        }

        const filterCropFarm = document.getElementById("filterCropFarm");
        if (filterCropFarm) {
            filterCropFarm.addEventListener("change", () => loadCrops());
        }

        const openAddFarmBtn = document.getElementById("openAddFarmBtn");
        if (openAddFarmBtn) {
            openAddFarmBtn.addEventListener("click", () => openFarmModal());
        }

        const openAddCropBtn = document.getElementById("openAddCropBtn");
        if (openAddCropBtn) {
            openAddCropBtn.addEventListener("click", () => openCropModal());
        }

        // Close modal buttons
        document.querySelectorAll(".modal-close-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                closeFarmModal();
                closeCropModal();
            });
        });

        const farmForm = document.getElementById("farmForm");
        if (farmForm) farmForm.addEventListener("submit", handleFarmSubmit);

        const cropForm = document.getElementById("cropForm");
        if (cropForm) cropForm.addEventListener("submit", handleCropSubmit);

        // Language changed listener to re-render dynamic items
        window.addEventListener("languageChanged", () => {
            renderFarms();
            renderCrops();
        });
    }

    async function init() {
        initTabs();
        await loadFarms();
        await loadCrops();
        await loadDashboardSummary();
    }

    // Export public functions on window for inline handlers
    window.FarmCropApp = {
        init,
        openFarmModal,
        closeFarmModal,
        openCropModal,
        closeCropModal,
        editFarm,
        deleteFarm,
        editCrop,
        deleteCrop,
        updateGrowthStatus
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
