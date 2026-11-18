/**
 * AgriSmart - Smart Crop Planning Foundation (Feature Upgrade 9, Prompt 1)
 * Client-Side Controller
 */

(function () {
    "use strict";

    // Module State
    let cropPlans = [];
    let upcomingPlans = [];
    let summaryData = null;
    let contextFarms = [];
    let contextCrops = [];
    let isSubmitting = false;

    // Filters
    const filters = {
        season: "all",
        status: "all",
        farm_id: "all",
        year: "all",
        search: ""
    };

    // Season Visual Metaphors & Icons
    const SEASON_CONFIG = {
        "Kharif": { icon: "🌧️", badgeClass: "season-badge-kharif", label: "Kharif (Monsoon)" },
        "Rabi": { icon: "❄️", badgeClass: "season-badge-rabi", label: "Rabi (Winter)" },
        "Zaid": { icon: "☀️", badgeClass: "season-badge-zaid", label: "Zaid (Summer)" },
        "Year-round": { icon: "🔄", badgeClass: "season-badge-yearround", label: "Year-round" }
    };

    const STATUS_BADGE_CLASS = {
        "Draft": "badge-status-draft",
        "Planned": "badge-status-planned",
        "In Progress": "badge-status-progress",
        "Completed": "badge-status-completed",
        "Cancelled": "badge-status-cancelled"
    };

    function getAuthToken() {
        return localStorage.getItem("agriSmartToken") || localStorage.getItem("token");
    }

    function t(key, fallback = "") {
        if (window.i18n && typeof window.i18n.t === "function") {
            return window.i18n.t(key);
        }
        return fallback || key;
    }

    function escapeHtml(text) {
        if (text === null || text === undefined) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function showToast(message, type = "success") {
        const toast = document.createElement("div");
        toast.className = `smart-toast smart-toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.classList.add("visible"), 50);
        setTimeout(() => {
            toast.classList.remove("visible");
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }

    /**
     * Fetch Form Context (Farms, Crops, Seasons, Units)
     */
    async function loadFormContext() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch("/api/crop-plans/form-context", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    contextFarms = data.farms || [];
                    contextCrops = data.crops || [];
                    populateFormContextUI(data);
                }
            }
        } catch (err) {
            console.error("Failed to load crop plan form context:", err);
        }
    }

    function populateFormContextUI(data) {
        // Populate Farm Select in Filter
        const filterFarm = document.getElementById("planFilterFarm");
        if (filterFarm) {
            const currentVal = filterFarm.value;
            filterFarm.innerHTML = `<option value="all">${t("lbl_filter_farm", "All Farms / Fields")}</option>` +
                contextFarms.map(f => `<option value="${f.id}">${escapeHtml(f.farm_name)} (${f.total_area} ${escapeHtml(f.area_unit)})</option>`).join("");
            filterFarm.value = currentVal || "all";
        }

        // Populate Farm Select in Modal Form
        const planFarm = document.getElementById("planFarmSelect");
        if (planFarm) {
            planFarm.innerHTML = `<option value="">-- ${t("select_farm_placeholder", "Select Farm / Field (Optional)")} --</option>` +
                contextFarms.map(f => `<option value="${f.id}">${escapeHtml(f.farm_name)} (${f.total_area} ${escapeHtml(f.area_unit)})</option>`).join("");
        }

        // Populate Common Crops Datalist
        const cropDatalist = document.getElementById("commonCropsList");
        if (cropDatalist && data.common_crops) {
            const allCrops = Array.from(new Set([
                ...contextCrops.map(c => c.crop_name),
                ...data.common_crops
            ])).sort();
            cropDatalist.innerHTML = allCrops.map(c => `<option value="${escapeHtml(c)}"></option>`).join("");
        }
    }

    /**
     * Load KPI Summary
     */
    async function loadSummary() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch(`/api/crop-plans/summary?_t=${Date.now()}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    summaryData = data.summary;
                    console.log("[loadSummary] Summary total_plans:", summaryData ? summaryData.total_plans : "none");
                    renderSummaryUI(summaryData);
                }
            }
        } catch (err) {
            console.error("Failed to load crop plan summary:", err);
        }
    }

    function renderSummaryUI(s) {
        if (!s) return;

        const setTxt = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        setTxt("kpiTotalCropPlans", s.total_plans || 0);
        setTxt("kpiKharifPlans", s.kharif_plans || 0);
        setTxt("kpiRabiPlans", s.rabi_plans || 0);
        setTxt("kpiZaidPlans", s.zaid_plans || 0);

        const areaEl = document.getElementById("kpiTotalPlannedArea");
        if (areaEl) {
            const area = Number(s.total_planned_area || 0);
            areaEl.textContent = area > 0 ? area.toFixed(1) : "0";
        }

        // Update dashboard card badge
        const badge = document.getElementById("cardCropPlanBadge");
        if (badge) {
            const activeCount = (s.planned_status_count || 0) + (s.in_progress_count || 0);
            if (activeCount > 0) {
                badge.textContent = activeCount;
                badge.style.display = "inline-flex";
            } else {
                badge.style.display = "none";
            }
        }
    }

    /**
     * Load Upcoming Crop Plans (for Dashboard Banner & Section List)
     */
    async function loadUpcomingPlans() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch(`/api/crop-plans/upcoming?limit=4&_t=${Date.now()}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    upcomingPlans = data.plans || data.upcoming_plans || [];
                    renderUpcomingDashboardUI(upcomingPlans);
                }
            }
        } catch (err) {
            console.error("Failed to load upcoming crop plans:", err);
        }
    }

    function renderUpcomingDashboardUI(plans) {
        // Dashboard widget on home screen
        const container = document.getElementById("dashboardUpcomingPlansContainer");
        const countSpan = document.getElementById("dashboardUpcomingPlansCount");
        if (countSpan) countSpan.textContent = plans.length;

        if (!container) return;

        if (!plans || plans.length === 0) {
            container.innerHTML = `
                <div class="upcoming-plan-empty">
                    <span class="empty-icon">🌱</span>
                    <p data-i18n="no_upcoming_crop_plans">${t("no_upcoming_crop_plans", "No upcoming crop plans scheduled.")}</p>
                    <button type="button" class="btn-sm btn-primary" onclick="CropPlanning.openCreateModal()">
                        ${t("btn_new_crop_plan", "➕ New Crop Plan")}
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = plans.map(p => {
            const seasonCfg = SEASON_CONFIG[p.season] || { icon: "🌱", badgeClass: "season-badge-kharif", label: p.season };
            let countdownText = "";
            let countdownBadgeClass = "countdown-chip-future";

            if (p.days_until_sowing !== null && p.days_until_sowing !== undefined) {
                if (p.days_until_sowing > 0) {
                    countdownText = t("sowing_in_days", `Sowing in ${p.days_until_sowing} days`).replace("{days}", p.days_until_sowing);
                } else if (p.days_until_sowing === 0) {
                    countdownText = t("sowing_today", "Sowing Scheduled Today");
                    countdownBadgeClass = "countdown-chip-today";
                } else {
                    const absDays = Math.abs(p.days_until_sowing);
                    countdownText = t("sown_days_ago", `Sown ${absDays} days ago`).replace("{days}", absDays);
                    countdownBadgeClass = "countdown-chip-past";
                }
            }

            return `
                <div class="upcoming-plan-card" onclick="CropPlanning.openEditModal(${p.id})">
                    <div class="upcoming-card-top">
                        <span class="season-badge ${seasonCfg.badgeClass}">
                            ${seasonCfg.icon} ${escapeHtml(p.season)}
                        </span>
                        <span class="countdown-chip ${countdownBadgeClass}">${escapeHtml(countdownText)}</span>
                    </div>
                    <div class="upcoming-card-body">
                        <h4 class="upcoming-crop-name">${escapeHtml(p.crop_name)} ${p.variety ? `<small class="crop-variety">(${escapeHtml(p.variety)})</small>` : ""}</h4>
                        <div class="upcoming-meta">
                            <span>📅 <strong>${escapeHtml(p.planned_sowing_date)}</strong></span>
                            ${p.farm_name ? `<span>🏡 ${escapeHtml(p.farm_name)}</span>` : ""}
                            ${p.land_area ? `<span>📐 ${p.land_area} ${escapeHtml(p.area_unit || "Acres")}</span>` : ""}
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    }

    /**
     * Load All Crop Plans with active filters
     */
    async function loadCropPlans() {
        const token = getAuthToken();
        if (!token) return;

        const listContainer = document.getElementById("cropPlansList");
        if (listContainer) {
            listContainer.innerHTML = `
                <div class="plans-loading-state">
                    <div class="smart-spinner"></div>
                    <p>${t("loading_crop_plans", "Loading crop plans...")}</p>
                </div>
            `;
        }

        const params = new URLSearchParams();
        params.append("_t", Date.now());
        if (filters.season !== "all") params.append("season", filters.season);
        if (filters.status !== "all") params.append("status", filters.status);
        if (filters.farm_id !== "all") params.append("farm_id", filters.farm_id);
        if (filters.year !== "all") params.append("year", filters.year);

        try {
            const res = await fetch(`/api/crop-plans?${params.toString()}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    cropPlans = data.plans || [];
                    console.log("[loadCropPlans] Loaded plans count:", cropPlans.length, "names:", cropPlans.map(p => p.crop_name).join(", "));
                    renderCropPlansUI(cropPlans);
                } else {
                    renderPlansError(data.error || "Failed to load crop plans");
                }
            } else {
                renderPlansError("Server returned error");
            }
        } catch (err) {
            console.error("Failed to load crop plans:", err);
            renderPlansError("Network connection error");
        }
    }

    function renderPlansError(msg) {
        const listContainer = document.getElementById("cropPlansList");
        if (listContainer) {
            listContainer.innerHTML = `<div class="plan-error-state"><p>⚠️ ${escapeHtml(msg)}</p></div>`;
        }
    }

    function renderCropPlansUI(plans) {
        const container = document.getElementById("cropPlansList");
        if (!container) return;

        // Apply client-side search if any
        let filtered = plans;
        if (filters.search && filters.search.trim()) {
            const q = filters.search.trim().toLowerCase();
            filtered = plans.filter(p =>
                (p.crop_name && p.crop_name.toLowerCase().includes(q)) ||
                (p.variety && p.variety.toLowerCase().includes(q)) ||
                (p.farm_name && p.farm_name.toLowerCase().includes(q)) ||
                (p.field_location && p.field_location.toLowerCase().includes(q)) ||
                (p.notes && p.notes.toLowerCase().includes(q))
            );
        }

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="crop-plans-empty">
                    <div class="empty-illustration">🌾</div>
                    <h4 data-i18n="no_crop_plans_found">${t("no_crop_plans_found", "No crop plans found for selected filters.")}</h4>
                    <p data-i18n="empty_crop_plans_sub">${t("empty_crop_plans_sub", "Create your first seasonal crop plan to schedule sowing dates, predict harvests, and track field allocation.")}</p>
                    <button type="button" class="btn-primary" onclick="CropPlanning.openCreateModal()">
                        ${t("btn_new_crop_plan", "➕ New Crop Plan")}
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(p => {
            const seasonCfg = SEASON_CONFIG[p.season] || { icon: "🌱", badgeClass: "season-badge-kharif", label: p.season };
            const statusClass = STATUS_BADGE_CLASS[p.status] || "badge-status-planned";

            let countdownHtml = "";
            if (p.days_until_sowing !== null && p.days_until_sowing !== undefined) {
                if (p.days_until_sowing > 0) {
                    countdownHtml = `<span class="timeline-chip chip-future">⏳ ${t("sowing_in_days", `Sowing in ${p.days_until_sowing} days`).replace("{days}", p.days_until_sowing)}</span>`;
                } else if (p.days_until_sowing === 0) {
                    countdownHtml = `<span class="timeline-chip chip-today">⚡ ${t("sowing_today", "Sowing Scheduled Today")}</span>`;
                } else {
                    const absDays = Math.abs(p.days_until_sowing);
                    countdownHtml = `<span class="timeline-chip chip-past">🌱 ${t("sown_days_ago", `Sown ${absDays} days ago`).replace("{days}", absDays)}</span>`;
                }
            }

            let durationHtml = "";
            if (p.crop_duration_days) {
                durationHtml = `<span class="duration-chip">⏱️ ${t("duration_days", `${p.crop_duration_days} days cycle`).replace("{days}", p.crop_duration_days)}</span>`;
            }

            return `
                <div class="crop-plan-card" id="crop-plan-${p.id}">
                    <div class="plan-card-header">
                        <div class="header-badges">
                            <span class="season-badge ${seasonCfg.badgeClass}">
                                ${seasonCfg.icon} ${escapeHtml(p.season)} (${p.planning_year || ""})
                            </span>
                            <span class="status-badge ${statusClass}">
                                ${escapeHtml(p.status)}
                            </span>
                        </div>
                        <div class="plan-card-actions">
                            <button type="button" class="btn-icon" title="${t("btn_edit", "Edit")}" onclick="CropPlanning.openEditModal(${p.id})">
                                ✏️
                            </button>
                            <button type="button" class="btn-icon btn-icon-delete" title="${t("btn_delete", "Delete")}" onclick="CropPlanning.confirmDeletePlan(${p.id})">
                                🗑️
                            </button>
                        </div>
                    </div>

                    <div class="plan-card-title-row">
                        <h3 class="plan-crop-name">
                            ${escapeHtml(p.crop_name)}
                            ${p.variety ? `<span class="plan-variety">(${escapeHtml(p.variety)})</span>` : ""}
                        </h3>
                    </div>

                    <div class="plan-timeline-bar">
                        ${countdownHtml}
                        ${durationHtml}
                    </div>

                    <div class="plan-details-grid">
                        <div class="detail-item">
                            <span class="detail-label">🏡 ${t("lbl_farm_field", "Farm / Field")}</span>
                            <span class="detail-val">${p.farm_name ? escapeHtml(p.farm_name) : "—"}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">📍 ${t("lbl_field_location", "Plot Location")}</span>
                            <span class="detail-val">${p.field_location ? escapeHtml(p.field_location) : "—"}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">🌱 ${t("lbl_planned_sowing_date", "Sowing Date")}</span>
                            <span class="detail-val font-semibold">${escapeHtml(p.planned_sowing_date)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">🌾 ${t("lbl_expected_harvest_date", "Harvest Date")}</span>
                            <span class="detail-val">${p.expected_harvest_date ? escapeHtml(p.expected_harvest_date) : "—"}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">📐 ${t("lbl_land_area", "Land Area")}</span>
                            <span class="detail-val highlight">${p.land_area ? `${p.land_area} ${escapeHtml(p.area_unit || "Acres")}` : "—"}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">🎯 ${t("lbl_target_yield", "Target Yield")}</span>
                            <span class="detail-val">${p.target_yield ? `${p.target_yield} ${escapeHtml(p.target_yield_unit || "")}` : "—"}</span>
                        </div>
                        ${p.estimated_budget ? `
                        <div class="detail-item">
                            <span class="detail-label">💰 ${t("lbl_estimated_budget", "Est. Budget")}</span>
                            <span class="detail-val">₹${Number(p.estimated_budget).toLocaleString("en-IN")}</span>
                        </div>
                        ` : ""}
                    </div>

                    ${p.notes ? `
                        <div class="plan-notes-box">
                            <small class="notes-label">📝 ${t("lbl_plan_notes", "Strategy / Notes")}:</small>
                            <p class="notes-text">${escapeHtml(p.notes)}</p>
                        </div>
                    ` : ""}
                </div>
            `;
        }).join("");
    }

    /**
     * Modal Operations
     */
    function openCreateModal() {
        const form = document.getElementById("cropPlanForm");
        if (form) form.reset();

        document.getElementById("cropPlanId").value = "";
        document.getElementById("cropPlanModalTitle").textContent = t("modal_add_crop_plan_title", "Create New Crop Plan");
        document.getElementById("planYear").value = new Date().getFullYear();

        // Default sowing date to today
        const todayStr = new Date().toISOString().split("T")[0];
        document.getElementById("planSowingDate").value = todayStr;

        const modal = document.getElementById("cropPlanModal");
        if (modal) modal.classList.add("open");
    }

    function openEditModal(planId) {
        const plan = cropPlans.find(p => p.id === planId) || upcomingPlans.find(p => p.id === planId);
        if (!plan) {
            // Fetch directly
            fetchPlanAndOpenModal(planId);
            return;
        }
        populateModalForm(plan);
    }

    async function fetchPlanAndOpenModal(planId) {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch(`/api/crop-plans/${planId}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success" && data.plan) {
                    populateModalForm(data.plan);
                }
            }
        } catch (err) {
            console.error("Failed to fetch plan:", err);
            showToast("Failed to fetch crop plan details", "error");
        }
    }

    function populateModalForm(p) {
        document.getElementById("cropPlanId").value = p.id;
        document.getElementById("cropPlanModalTitle").textContent = t("modal_edit_crop_plan_title", "Edit Crop Plan");
        document.getElementById("planCropName").value = p.crop_name || "";
        document.getElementById("planVariety").value = p.variety || "";
        document.getElementById("planFarmSelect").value = p.farm_id || "";
        document.getElementById("planSeason").value = p.season || "Kharif";
        document.getElementById("planYear").value = p.planning_year || new Date().getFullYear();
        document.getElementById("planSowingDate").value = p.planned_sowing_date || "";
        document.getElementById("planHarvestDate").value = p.expected_harvest_date || "";
        document.getElementById("planLandArea").value = p.land_area || "";
        document.getElementById("planAreaUnit").value = p.area_unit || "Acres";
        document.getElementById("planFieldLocation").value = p.field_location || "";
        document.getElementById("planTargetYield").value = p.target_yield || "";
        document.getElementById("planTargetYieldUnit").value = p.target_yield_unit || "Quintals";
        document.getElementById("planEstimatedBudget").value = p.estimated_budget || "";
        document.getElementById("planStatus").value = p.status || "Planned";
        document.getElementById("planNotes").value = p.notes || "";

        const modal = document.getElementById("cropPlanModal");
        if (modal) modal.classList.add("open");
    }

    function closeModal() {
        const modal = document.getElementById("cropPlanModal");
        if (modal) modal.classList.remove("open");
    }

    /**
     * Submit Create / Edit Form
     */
    async function handleFormSubmit(e) {
        if (e && e.preventDefault) e.preventDefault();
        console.log("[handleFormSubmit] called. Current isSubmitting =", isSubmitting);
        if (isSubmitting) {
            console.warn("[handleFormSubmit] Rejected submit because isSubmitting is true!");
            return;
        }

        const token = getAuthToken();
        if (!token) {
            showToast("Session expired. Please log in again.", "error");
            return;
        }

        const planId = document.getElementById("cropPlanId").value;
        const cropName = document.getElementById("planCropName").value.trim();
        const sowingDate = document.getElementById("planSowingDate").value;
        console.log("[handleFormSubmit] planId:", planId, "cropName:", cropName, "sowingDate:", sowingDate);

        if (!cropName) {
            showToast("Please enter crop name", "error");
            return;
        }
        if (!sowingDate) {
            showToast("Please select planned sowing date", "error");
            return;
        }

        const payload = {
            crop_name: cropName,
            variety: document.getElementById("planVariety").value.trim() || null,
            farm_id: document.getElementById("planFarmSelect").value ? parseInt(document.getElementById("planFarmSelect").value, 10) : null,
            season: document.getElementById("planSeason").value,
            planning_year: parseInt(document.getElementById("planYear").value, 10) || new Date().getFullYear(),
            planned_sowing_date: sowingDate,
            expected_harvest_date: document.getElementById("planHarvestDate").value || null,
            land_area: document.getElementById("planLandArea").value ? parseFloat(document.getElementById("planLandArea").value) : null,
            area_unit: document.getElementById("planAreaUnit").value || "Acres",
            field_location: document.getElementById("planFieldLocation").value.trim() || null,
            target_yield: document.getElementById("planTargetYield").value ? parseFloat(document.getElementById("planTargetYield").value) : null,
            target_yield_unit: document.getElementById("planTargetYieldUnit").value.trim() || null,
            estimated_budget: document.getElementById("planEstimatedBudget").value ? parseFloat(document.getElementById("planEstimatedBudget").value) : null,
            status: document.getElementById("planStatus").value || "Planned",
            notes: document.getElementById("planNotes").value.trim() || null
        };

        const isEdit = Boolean(planId);
        const url = isEdit ? `/api/crop-plans/${planId}` : "/api/crop-plans";
        const method = isEdit ? "PUT" : "POST";

        const submitBtn = document.getElementById("btnSaveCropPlan");
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = "Saving...";
        }
        isSubmitting = true;

        try {
            const res = await fetch(url, {
                method: method,
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            console.log("[handleFormSubmit] Response for", payload.crop_name, ": status =", res.status, "data =", data);
            if (res.ok && data.status === "success") {
                showToast(isEdit ? t("plan_updated_success", "Crop plan updated successfully!") : t("plan_created_success", "Crop plan created successfully!"), "success");
                closeModal();
                await Promise.all([loadCropPlans(), loadUpcomingPlans(), loadSummary()]);
            } else {
                console.error("Save plan failed with response:", data);
                showToast(data.error || "Failed to save crop plan", "error");
            }
        } catch (err) {
            console.error("Error saving crop plan:", err);
            showToast("Network error while saving crop plan", "error");
        } finally {
            isSubmitting = false;
            console.log("[handleFormSubmit] Finished. isSubmitting reset to false.");
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = t("btn_save_crop_plan", "Save Crop Plan");
            }
        }
    }

    /**
     * Delete Confirmation & Execution
     */
    async function confirmDeletePlan(planId) {
        const confirmed = window.confirm(t("confirm_delete_plan", "Are you sure you want to delete this crop plan?"));
        if (!confirmed) return;

        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch(`/api/crop-plans/${planId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                showToast(t("plan_deleted_success", "Crop plan deleted successfully!"), "success");
                await Promise.all([loadCropPlans(), loadUpcomingPlans(), loadSummary()]);
            } else {
                showToast(data.error || "Failed to delete crop plan", "error");
            }
        } catch (err) {
            console.error("Error deleting crop plan:", err);
            showToast("Network error while deleting crop plan", "error");
        }
    }

    /**
     * Bind Event Listeners
     */
    function bindEvents() {
        // Season filter tabs
        const seasonTabs = document.querySelectorAll(".season-tab-btn");
        seasonTabs.forEach(btn => {
            btn.addEventListener("click", () => {
                seasonTabs.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                filters.season = btn.dataset.season || "all";
                loadCropPlans();
            });
        });

        // Farm Filter
        const filterFarm = document.getElementById("planFilterFarm");
        if (filterFarm) {
            filterFarm.addEventListener("change", (e) => {
                filters.farm_id = e.target.value;
                loadCropPlans();
            });
        }

        // Status Filter
        const filterStatus = document.getElementById("planFilterStatus");
        if (filterStatus) {
            filterStatus.addEventListener("change", (e) => {
                filters.status = e.target.value;
                loadCropPlans();
            });
        }

        // Search Input
        const searchInput = document.getElementById("planSearchInput");
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener("input", (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    filters.search = e.target.value;
                    renderCropPlansUI(cropPlans);
                }, 250);
            });
        }

        // Open Modal Buttons
        const openBtn = document.getElementById("btnOpenNewCropPlan");
        if (openBtn) openBtn.addEventListener("click", openCreateModal);

        const openBtnSection = document.getElementById("btnSectionNewCropPlan");
        if (openBtnSection) openBtnSection.addEventListener("click", openCreateModal);

        // Modal Close Buttons
        const closeBtns = document.querySelectorAll("#cropPlanModal .modal-close-btn");
        closeBtns.forEach(btn => btn.addEventListener("click", closeModal));

        // Form Submit
        const form = document.getElementById("cropPlanForm");
        if (form) form.addEventListener("submit", handleFormSubmit);

        // Language changed event
        window.addEventListener("languageChanged", () => {
            renderSummaryUI(summaryData);
            renderUpcomingDashboardUI(upcomingPlans);
            renderCropPlansUI(cropPlans);
        });
    }

    /**
     * Initialization
     */
    async function init() {
        bindEvents();
        await Promise.all([
            loadFormContext(),
            loadSummary(),
            loadUpcomingPlans(),
            loadCropPlans()
        ]);
    }

    // Public API
    window.CropPlanning = {
        init,
        loadCropPlans,
        loadUpcomingPlans,
        loadSummary,
        openCreateModal,
        openEditModal,
        confirmDeletePlan,
        closeModal,
        handleFormSubmit
    };

    // Auto-init when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
