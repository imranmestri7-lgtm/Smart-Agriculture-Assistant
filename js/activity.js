/**
 * AgriSmart - Smart Farm Activity Calendar & Task Planner (Feature Upgrade 6)
 * Client-Side Controller
 */

(function () {
    "use strict";

    // State
    const today = new Date();
    let currentYear = today.getFullYear();
    let currentMonth = today.getMonth() + 1; // 1 - 12
    let selectedDateStr = formatDateIso(today);
    let activeView = "calendar"; // 'calendar' | 'list'
    let calendarData = null;
    let contextCrops = [];
    let contextFarms = [];

    // Category Icon Map
    const CATEGORY_ICONS = {
        "Land preparation": "🚜",
        "Sowing and planting": "🌱",
        "Irrigation": "💧",
        "Fertilizer application": "🧪",
        "Pesticide application": "🛡️",
        "Weed management": "🌿",
        "Crop inspection": "🔍",
        "Disease monitoring": "🍃",
        "Harvesting": "🌾",
        "Other activities": "📦"
    };

    function getAuthToken() {
        return localStorage.getItem("agriSmartToken") || localStorage.getItem("token");
    }

    function formatDateIso(d) {
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function t(key, fallback = "") {
        if (window.i18n && typeof window.i18n.t === "function") {
            return window.i18n.t(key);
        }
        return fallback || key;
    }

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
     * Load registered crops and farms for selectors
     */
    async function loadContextData() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch("/api/finance/context-crops", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    contextCrops = data.crops || [];
                    contextFarms = data.farms || [];
                    populateDropdowns();
                }
            }
        } catch (e) {
            console.warn("Could not load activity context crops:", e);
        }
    }

    function populateDropdowns() {
        // 1. Crop filter in toolbar
        const filterCrop = document.getElementById("activityFilterCrop");
        if (filterCrop) {
            const currentVal = filterCrop.value;
            let options = `<option value="all">${escapeHtml(t("opt_all_crops", "All Crops"))}</option>`;
            contextCrops.forEach(c => {
                options += `<option value="${c.id}">${escapeHtml(c.crop_name + (c.variety ? " (" + c.variety + ")" : ""))}</option>`;
            });
            filterCrop.innerHTML = options;
            if (currentVal) filterCrop.value = currentVal;
        }

        // 2. Crop selector in activity form
        const formCrop = document.getElementById("activityCropSelect");
        if (formCrop) {
            let options = `<option value="">${escapeHtml(t("opt_general_crop", "-- General / Entire Farm --"))}</option>`;
            contextCrops.forEach(c => {
                options += `<option value="${c.id}">${escapeHtml(c.crop_name + (c.variety ? " (" + c.variety + ")" : ""))}</option>`;
            });
            formCrop.innerHTML = options;
        }

        // 3. Farm selector in activity form
        const formFarm = document.getElementById("activityFarmSelect");
        if (formFarm) {
            let options = `<option value="">${escapeHtml(t("opt_choose_farm", "-- Choose Farm --"))}</option>`;
            contextFarms.forEach(f => {
                options += `<option value="${f.id}">${escapeHtml(f.farm_name + (f.location ? " - " + f.location : ""))}</option>`;
            });
            formFarm.innerHTML = options;
        }
    }

    /**
     * Summary Metrics & KPI Cards
     */
    async function loadActivitySummary() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch("/api/activities/summary", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) return;

            const data = await res.json();
            if (data.status === "success" && data.summary) {
                const s = data.summary;
                const todayEl = document.getElementById("kpiTodayActivities");
                const upcomingEl = document.getElementById("kpiUpcomingActivities");
                const overdueEl = document.getElementById("kpiOverdueActivities");
                const completedEl = document.getElementById("kpiCompletedActivities");

                if (todayEl) todayEl.textContent = s.today_count;
                if (upcomingEl) upcomingEl.textContent = s.upcoming_count;
                if (overdueEl) overdueEl.textContent = s.overdue_count;
                if (completedEl) completedEl.textContent = s.completed_count;

                // Update Dashboard Card Badge
                const cardBadge = document.getElementById("cardActivityBadge");
                if (cardBadge) {
                    const totalPending = s.today_count + s.overdue_count;
                    if (totalPending > 0) {
                        cardBadge.textContent = totalPending;
                        cardBadge.style.display = "inline-block";
                    } else {
                        cardBadge.style.display = "none";
                    }
                }
            }
        } catch (e) {
            console.error("Error loading activity summary:", e);
        }
    }

    /**
     * Crop-Aware Activity Suggestions
     */
    async function loadActivitySuggestions() {
        const token = getAuthToken();
        if (!token) return;

        const container = document.getElementById("activitySuggestionsContainer");
        const countBadge = document.getElementById("suggestionsCountBadge");
        if (!container) return;

        try {
            const res = await fetch("/api/activities/suggestions", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) return;

            const data = await res.json();
            if (data.status === "success" && Array.isArray(data.suggestions)) {
                const suggestions = data.suggestions;
                if (countBadge) countBadge.textContent = suggestions.length;

                if (suggestions.length === 0) {
                    container.innerHTML = `
                        <div style="grid-column: 1 / -1; padding: 12px; color: var(--text-secondary); font-size: 13px;">
                            ${escapeHtml(t("no_suggestions_msg", "No pending crop recommendations right now. All activities are on schedule!"))}
                        </div>
                    `;
                    return;
                }

                let html = "";
                suggestions.forEach(sug => {
                    const icon = CATEGORY_ICONS[sug.category] || "🌱";
                    html += `
                        <div class="suggestion-card">
                            <div>
                                <div class="suggestion-header">
                                    <span class="activity-badge-category">${icon} ${escapeHtml(sug.category)}</span>
                                    <span class="activity-badge-priority ${escapeHtml(sug.priority)}">${escapeHtml(sug.priority)}</span>
                                </div>
                                <h5>${escapeHtml(sug.title)}</h5>
                                <p>${escapeHtml(sug.description)}</p>
                                <div class="suggestion-reason">💡 ${escapeHtml(sug.reason)}</div>
                            </div>
                            <button type="button" class="btn-add-suggestion" data-suggestion='${escapeHtml(JSON.stringify(sug))}'>
                                ➕ ${escapeHtml(t("btn_add_to_calendar", "Add to Calendar"))}
                            </button>
                        </div>
                    `;
                });
                container.innerHTML = html;

                // Attach click listeners to suggestions
                container.querySelectorAll(".btn-add-suggestion").forEach(btn => {
                    btn.addEventListener("click", () => {
                        try {
                            const raw = btn.getAttribute("data-suggestion");
                            const sug = JSON.parse(raw);
                            openActivityModal({
                                title: sug.title,
                                category: sug.category,
                                priority: sug.priority,
                                scheduled_date: sug.suggested_date,
                                crop_id: sug.crop_id,
                                farm_id: sug.farm_id,
                                description: sug.description,
                                notes: `[Recommendation Reason]: ${sug.reason}`
                            });
                        } catch (err) {
                            console.error("Error opening suggestion modal:", err);
                        }
                    });
                });
            }
        } catch (e) {
            console.error("Error loading activity suggestions:", e);
        }
    }

    /**
     * Calendar View Engine
     */
    async function loadCalendar() {
        const token = getAuthToken();
        if (!token) return;

        const category = document.getElementById("activityFilterCategory")?.value || "all";
        const status = document.getElementById("activityFilterStatus")?.value || "all";

        const url = `/api/activities/calendar?year=${currentYear}&month=${currentMonth}&category=${encodeURIComponent(category)}&status=${encodeURIComponent(status)}`;

        try {
            const res = await fetch(url, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) return;

            calendarData = await res.json();
            renderCalendar();
            renderSelectedDayAgenda();
        } catch (e) {
            console.error("Error loading calendar data:", e);
        }
    }

    function renderCalendar() {
        if (!calendarData || !calendarData.days) return;

        const displayEl = document.getElementById("calMonthYearDisplay");
        if (displayEl) {
            // Localized month name
            const monthKeys = [
                "month_jan", "month_feb", "month_mar", "month_apr", "month_may", "month_jun",
                "month_jul", "month_aug", "month_sep", "month_oct", "month_nov", "month_dec"
            ];
            const localizedMonth = t(monthKeys[currentMonth - 1], calendarData.month_name);
            displayEl.textContent = `${localizedMonth} ${currentYear}`;
        }

        const gridEl = document.getElementById("activityCalendarGrid");
        if (!gridEl) return;

        gridEl.innerHTML = "";

        // First day of current month weekday (0=Mon, 6=Sun in python, but calendar header is Sun=0)
        // Let's compute day of week for the 1st
        const firstDayObj = new Date(currentYear, currentMonth - 1, 1);
        const startDayOfWeek = firstDayObj.getDay(); // 0 = Sunday, 1 = Monday ... 6 = Saturday

        // Previous month days to pad
        const prevMonthLastDate = new Date(currentYear, currentMonth - 1, 0).getDate();
        for (let i = startDayOfWeek - 1; i >= 0; i--) {
            const cell = document.createElement("div");
            cell.className = "calendar-day-cell other-month";
            cell.innerHTML = `
                <div class="day-cell-header">
                    <span class="day-number">${prevMonthLastDate - i}</span>
                </div>
            `;
            gridEl.appendChild(cell);
        }

        // Current month days
        calendarData.days.forEach(day => {
            const cell = document.createElement("div");
            cell.className = "calendar-day-cell";
            if (day.is_today) cell.classList.add("is-today");
            if (day.date === selectedDateStr) cell.classList.add("selected");

            const countBadge = day.activity_count > 0 ? `<span class="day-task-count-pill">${day.activity_count}</span>` : "";

            let pillsHtml = "";
            (day.activities || []).slice(0, 3).forEach(act => {
                const icon = CATEGORY_ICONS[act.category] || "•";
                const priorityClass = `priority-${act.priority}`;
                const statusClass = `status-${act.status.replace(/\s+/g, "")}`;
                pillsHtml += `
                    <div class="cal-activity-pill ${priorityClass} ${statusClass}" title="${escapeHtml(act.title)}">
                        <span>${icon}</span> <span>${escapeHtml(act.title)}</span>
                    </div>
                `;
            });
            if (day.activities && day.activities.length > 3) {
                pillsHtml += `<small style="font-size:10px; color:var(--text-secondary); padding-left:4px;">+${day.activities.length - 3} more</small>`;
            }

            cell.innerHTML = `
                <div class="day-cell-header">
                    <span class="day-number">${day.day}</span>
                    ${countBadge}
                </div>
                <div class="day-activities-list">
                    ${pillsHtml}
                </div>
            `;

            // Click event: Select date and render agenda
            cell.addEventListener("click", () => {
                document.querySelectorAll(".calendar-day-cell.selected").forEach(el => el.classList.remove("selected"));
                cell.classList.add("selected");
                selectedDateStr = day.date;
                renderSelectedDayAgenda();
            });

            // Double click: Schedule task on this date
            cell.addEventListener("dblclick", () => {
                openActivityModal({ scheduled_date: day.date });
            });

            gridEl.appendChild(cell);
        });
    }

    function renderSelectedDayAgenda() {
        const agendaTitle = document.getElementById("selectedDayTitle");
        const agendaDateDisplay = document.getElementById("selectedDayDateDisplay");
        const listEl = document.getElementById("selectedDayActivitiesList");
        if (!listEl) return;

        if (agendaDateDisplay) {
            agendaDateDisplay.textContent = selectedDateStr;
        }

        // Find day data in calendarData
        const dayData = (calendarData?.days || []).find(d => d.date === selectedDateStr);
        const activities = dayData?.activities || [];

        if (activities.length === 0) {
            listEl.innerHTML = `
                <div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                    <span style="font-size: 24px; display: block; margin-bottom: 6px;">☕</span>
                    ${escapeHtml(t("no_tasks_for_day", "No activities scheduled for this date."))}<br>
                    <button type="button" class="btn-secondary" style="margin-top:10px; font-size:12px; padding:4px 10px;" id="btnScheduleForSelectedDay">
                        ➕ ${escapeHtml(t("btn_schedule_this_day", "Schedule on this date"))}
                    </button>
                </div>
            `;
            const schedBtn = document.getElementById("btnScheduleForSelectedDay");
            if (schedBtn) {
                schedBtn.addEventListener("click", () => openActivityModal({ scheduled_date: selectedDateStr }));
            }
            return;
        }

        let html = "";
        activities.forEach(act => {
            const icon = CATEGORY_ICONS[act.category] || "🗓️";
            const timeStr = act.scheduled_time ? `⏰ ${act.scheduled_time}` : "";
            const cropStr = act.crop_name ? `🌾 ${escapeHtml(act.crop_name)}` : "";
            const isCompleted = act.status === "Completed";

            html += `
                <div class="agenda-item-card" data-id="${act.id}">
                    <div class="agenda-item-info">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:16px;">${icon}</span>
                            <span class="agenda-item-title" style="${isCompleted ? 'text-decoration: line-through; opacity: 0.7;' : ''}">${escapeHtml(act.title)}</span>
                            <span class="activity-badge-priority ${escapeHtml(act.priority)}">${escapeHtml(act.priority)}</span>
                            <span class="activity-badge-status ${escapeHtml(act.status.replace(/\s+/g, ''))}">${escapeHtml(act.status)}</span>
                        </div>
                        <div class="agenda-item-meta">
                            <span>${escapeHtml(act.category)}</span>
                            ${timeStr ? `<span>•</span> <span>${escapeHtml(timeStr)}</span>` : ""}
                            ${cropStr ? `<span>•</span> <span>${cropStr}</span>` : ""}
                        </div>
                    </div>
                    <div style="display:flex; gap:6px;">
                        ${!isCompleted ? `
                            <button type="button" class="btn-table-action btn-agenda-complete" data-id="${act.id}" title="${escapeHtml(t("btn_mark_completed", "Complete"))}" style="color:#10b981;">✓</button>
                            <button type="button" class="btn-table-action btn-agenda-postpone" data-id="${act.id}" data-title="${escapeHtml(act.title)}" data-date="${act.scheduled_date}" title="${escapeHtml(t("btn_postpone", "Postpone"))}">⏰</button>
                        ` : ""}
                        <button type="button" class="btn-table-action btn-agenda-view" data-id="${act.id}" title="${escapeHtml(t("btn_view_details", "View Details"))}">ℹ️</button>
                    </div>
                </div>
            `;
        });
        listEl.innerHTML = html;

        // Wire quick actions in agenda
        listEl.querySelectorAll(".btn-agenda-complete").forEach(btn => {
            btn.addEventListener("click", async () => {
                const id = btn.getAttribute("data-id");
                await quickUpdateStatus(id, "Completed");
            });
        });

        listEl.querySelectorAll(".btn-agenda-postpone").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                const title = btn.getAttribute("data-title");
                const dateVal = btn.getAttribute("data-date");
                openPostponeModal(id, title, dateVal);
            });
        });

        listEl.querySelectorAll(".btn-agenda-view").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                openActivityDetailsModal(id);
            });
        });
    }

    /**
     * List View Engine
     */
    async function loadListView() {
        const token = getAuthToken();
        if (!token) return;

        const category = document.getElementById("activityFilterCategory")?.value || "all";
        const status = document.getElementById("activityFilterStatus")?.value || "all";
        const cropId = document.getElementById("activityFilterCrop")?.value || "all";
        const priority = document.getElementById("activityFilterPriority")?.value || "all";

        const url = `/api/activities?status=${encodeURIComponent(status)}&category=${encodeURIComponent(category)}&crop_id=${encodeURIComponent(cropId)}&priority=${encodeURIComponent(priority)}&limit=150`;

        const tbody = document.getElementById("activityTableBody");
        const emptyState = document.getElementById("activityEmptyState");
        if (!tbody) return;

        try {
            const res = await fetch(url, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) return;

            const data = await res.json();
            const activities = data.activities || [];

            if (activities.length === 0) {
                tbody.innerHTML = "";
                if (emptyState) emptyState.style.display = "block";
                return;
            }

            if (emptyState) emptyState.style.display = "none";

            let html = "";
            activities.forEach(act => {
                const icon = CATEGORY_ICONS[act.category] || "🗓️";
                const timeStr = act.scheduled_time ? `<br><small style="color:var(--text-secondary);">${act.scheduled_time}</small>` : "";
                const cropStr = act.crop_name ? `🌾 ${escapeHtml(act.crop_name)}` : (act.farm_name ? `🚜 ${escapeHtml(act.farm_name)}` : "—");
                const isCompleted = act.status === "Completed";

                html += `
                    <tr>
                        <td><strong>${act.scheduled_date}</strong>${timeStr}</td>
                        <td>
                            <strong style="${isCompleted ? 'text-decoration: line-through; opacity: 0.7;' : ''}">${escapeHtml(act.title)}</strong>
                            ${act.description ? `<br><small style="color:var(--text-secondary);">${escapeHtml(act.description.substring(0, 50))}${act.description.length > 50 ? '...' : ''}</small>` : ""}
                        </td>
                        <td><span class="activity-badge-category">${icon} ${escapeHtml(act.category)}</span></td>
                        <td>${cropStr}</td>
                        <td><span class="activity-badge-priority ${escapeHtml(act.priority)}">${escapeHtml(act.priority)}</span></td>
                        <td><span class="activity-badge-status ${escapeHtml(act.status.replace(/\s+/g, ''))}">${escapeHtml(act.status)}</span></td>
                        <td style="text-align:right;">
                            <div style="display:inline-flex; gap:4px;">
                                ${!isCompleted ? `
                                    <button type="button" class="btn-table-action btn-list-complete" data-id="${act.id}" title="${escapeHtml(t("btn_mark_completed", "Complete"))}" style="color:#10b981;">✓</button>
                                    <button type="button" class="btn-table-action btn-list-postpone" data-id="${act.id}" data-title="${escapeHtml(act.title)}" data-date="${act.scheduled_date}" title="${escapeHtml(t("btn_postpone", "Postpone"))}">⏰</button>
                                ` : ""}
                                <button type="button" class="btn-table-action btn-list-view" data-id="${act.id}" title="${escapeHtml(t("btn_view_details", "View Details"))}">ℹ️</button>
                                <button type="button" class="btn-table-action delete btn-list-delete" data-id="${act.id}" title="${escapeHtml(t("btn_delete", "Delete"))}">🗑️</button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;

            // Wire action buttons
            tbody.querySelectorAll(".btn-list-complete").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const id = btn.getAttribute("data-id");
                    await quickUpdateStatus(id, "Completed");
                });
            });

            tbody.querySelectorAll(".btn-list-postpone").forEach(btn => {
                btn.addEventListener("click", () => {
                    const id = btn.getAttribute("data-id");
                    const title = btn.getAttribute("data-title");
                    const dateVal = btn.getAttribute("data-date");
                    openPostponeModal(id, title, dateVal);
                });
            });

            tbody.querySelectorAll(".btn-list-view").forEach(btn => {
                btn.addEventListener("click", () => {
                    const id = btn.getAttribute("data-id");
                    openActivityDetailsModal(id);
                });
            });

            tbody.querySelectorAll(".btn-list-delete").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const id = btn.getAttribute("data-id");
                    await deleteActivity(id);
                });
            });

        } catch (e) {
            console.error("Error loading list view:", e);
        }
    }

    /**
     * Modal Operations: Create / Edit Activity
     */
    function openActivityModal(prefill = null) {
        const modal = document.getElementById("activityModal");
        const form = document.getElementById("activityForm");
        const titleEl = document.getElementById("activityModalTitle");
        if (!modal || !form) return;

        form.reset();
        document.getElementById("activityId").value = "";

        const defaultDate = prefill?.scheduled_date || selectedDateStr || formatDateIso(today);
        document.getElementById("activityDateInput").value = defaultDate;
        document.getElementById("activityReminderToggle").checked = true;

        if (prefill) {
            if (prefill.id) {
                // Editing existing activity
                titleEl.textContent = t("modal_edit_activity_title", "Edit Farm Activity");
                document.getElementById("activityId").value = prefill.id;
            } else {
                titleEl.textContent = t("modal_add_activity_title", "Schedule Farm Activity");
            }

            if (prefill.title) document.getElementById("activityTitleInput").value = prefill.title;
            if (prefill.category) document.getElementById("activityCategorySelect").value = prefill.category;
            if (prefill.priority) document.getElementById("activityPrioritySelect").value = prefill.priority;
            if (prefill.status) document.getElementById("activityStatusSelect").value = prefill.status;
            if (prefill.scheduled_time) document.getElementById("activityTimeInput").value = prefill.scheduled_time;
            if (prefill.crop_id) document.getElementById("activityCropSelect").value = prefill.crop_id;
            if (prefill.farm_id) document.getElementById("activityFarmSelect").value = prefill.farm_id;
            if (prefill.description) document.getElementById("activityDescriptionInput").value = prefill.description;
            if (prefill.notes) document.getElementById("activityNotesInput").value = prefill.notes;
            if (prefill.reminder_enabled !== undefined) document.getElementById("activityReminderToggle").checked = !!prefill.reminder_enabled;
        } else {
            titleEl.textContent = t("modal_add_activity_title", "Schedule Farm Activity");
        }

        modal.classList.add("open");
    }

    function closeActivityModal() {
        const modal = document.getElementById("activityModal");
        if (modal) modal.classList.remove("open");
    }

    async function handleActivitySubmit(e) {
        e.preventDefault();
        console.log("handleActivitySubmit triggered");
        const token = getAuthToken();
        if (!token) {
            console.log("handleActivitySubmit: no auth token");
            return;
        }

        const id = document.getElementById("activityId").value;
        const title = document.getElementById("activityTitleInput").value.trim();
        const category = document.getElementById("activityCategorySelect").value;
        const priority = document.getElementById("activityPrioritySelect").value;
        const scheduled_date = document.getElementById("activityDateInput").value;
        const scheduled_time = document.getElementById("activityTimeInput").value || null;
        const crop_id = document.getElementById("activityCropSelect").value || null;
        const farm_id = document.getElementById("activityFarmSelect").value || null;
        const status = document.getElementById("activityStatusSelect").value;
        const reminder_enabled = document.getElementById("activityReminderToggle").checked;
        const description = document.getElementById("activityDescriptionInput").value.trim() || null;
        const notes = document.getElementById("activityNotesInput").value.trim() || null;

        console.log("Form values:", { title, category, priority, scheduled_date, scheduled_time, status });

        if (!title) {
            alert(t("val_err_activity_title", "Please enter an activity title."));
            return;
        }
        if (!category) {
            alert(t("val_err_activity_category", "Please select an activity category."));
            return;
        }
        if (!scheduled_date) {
            alert(t("val_err_scheduled_date", "Please enter a valid scheduled date."));
            return;
        }

        const payload = {
            title,
            category,
            priority,
            scheduled_date,
            scheduled_time,
            crop_id: crop_id ? parseInt(crop_id, 10) : null,
            farm_id: farm_id ? parseInt(farm_id, 10) : null,
            status,
            reminder_enabled,
            description,
            notes
        };

        const url = id ? `/api/activities/${id}` : "/api/activities";
        const method = id ? "PUT" : "POST";

        try {
            const res = await fetch(url, {
                method,
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.status === "success") {
                closeActivityModal();
                selectedDateStr = scheduled_date;
                await refreshAllViews();
            } else {
                alert(data.message || t("err_saving_activity", "Could not save activity."));
            }
        } catch (err) {
            console.error("Save activity error:", err);
            alert(t("err_network", "Network error. Please try again."));
        }
    }

    /**
     * Modal Operations: View Details Modal
     */
    async function openActivityDetailsModal(activityId) {
        const token = getAuthToken();
        if (!token) return;

        const modal = document.getElementById("activityDetailsModal");
        if (!modal) return;

        try {
            const res = await fetch(`/api/activities/${activityId}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!res.ok) return;

            const data = await res.json();
            const act = data.activity;
            if (!act) return;

            const icon = CATEGORY_ICONS[act.category] || "🗓️";
            document.getElementById("detailsModalTitle").textContent = `${icon} ${act.title}`;
            document.getElementById("detailsActivityTitle").textContent = act.title;
            document.getElementById("detailsActivityDescription").textContent = act.description || t("no_description_provided", "No additional description provided.");

            const catBadge = document.getElementById("detailsCategoryBadge");
            if (catBadge) catBadge.textContent = `${icon} ${act.category}`;

            const prioBadge = document.getElementById("detailsPriorityBadge");
            if (prioBadge) {
                prioBadge.className = `activity-badge-priority ${act.priority}`;
                prioBadge.textContent = act.priority;
            }

            const statusBadge = document.getElementById("detailsStatusBadge");
            if (statusBadge) {
                statusBadge.className = `activity-badge-status ${act.status.replace(/\s+/g, '')}`;
                statusBadge.textContent = act.status;
            }

            document.getElementById("detailsScheduledDate").textContent = act.scheduled_date;
            document.getElementById("detailsScheduledTime").textContent = act.scheduled_time || "--:--";
            document.getElementById("detailsCropName").textContent = act.crop_name || t("general_farm_overhead", "General");
            document.getElementById("detailsFarmName").textContent = act.farm_name || "—";

            const notesContainer = document.getElementById("detailsNotesContainer");
            const notesText = document.getElementById("detailsNotesText");
            if (act.notes) {
                notesText.textContent = act.notes;
                notesContainer.style.display = "block";
            } else {
                notesContainer.style.display = "none";
            }

            // Wire action buttons
            const compBtn = document.getElementById("btnQuickComplete");
            if (compBtn) {
                compBtn.onclick = async () => {
                    await quickUpdateStatus(act.id, "Completed");
                    closeActivityDetailsModal();
                };
            }

            const postpBtn = document.getElementById("btnQuickPostpone");
            if (postpBtn) {
                postpBtn.onclick = () => {
                    closeActivityDetailsModal();
                    openPostponeModal(act.id, act.title, act.scheduled_date);
                };
            }

            const editBtn = document.getElementById("btnEditFromDetails");
            if (editBtn) {
                editBtn.onclick = () => {
                    closeActivityDetailsModal();
                    openActivityModal(act);
                };
            }

            const delBtn = document.getElementById("btnDeleteFromDetails");
            if (delBtn) {
                delBtn.onclick = async () => {
                    closeActivityDetailsModal();
                    await deleteActivity(act.id);
                };
            }

            modal.classList.add("open");
        } catch (e) {
            console.error("Error opening activity details:", e);
        }
    }

    function closeActivityDetailsModal() {
        const modal = document.getElementById("activityDetailsModal");
        if (modal) modal.classList.remove("open");
    }

    /**
     * Modal Operations: Postpone / Reschedule
     */
    function openPostponeModal(activityId, title, currentDate) {
        const modal = document.getElementById("postponeModal");
        const form = document.getElementById("postponeForm");
        if (!modal || !form) return;

        form.reset();
        document.getElementById("postponeActivityId").value = activityId;
        document.getElementById("postponeActivityTitle").textContent = title || "";

        // Default tomorrow
        const curD = currentDate ? new Date(currentDate) : new Date();
        const tomorrow = new Date(curD.getTime() + 86400000);
        document.getElementById("postponeDateInput").value = formatDateIso(tomorrow);

        modal.classList.add("open");
    }

    function closePostponeModal() {
        const modal = document.getElementById("postponeModal");
        if (modal) modal.classList.remove("open");
    }

    async function handlePostponeSubmit(e) {
        e.preventDefault();
        const token = getAuthToken();
        if (!token) return;

        const id = document.getElementById("postponeActivityId").value;
        const new_date = document.getElementById("postponeDateInput").value;
        const notes = document.getElementById("postponeNotesInput").value.trim() || null;

        if (!new_date) {
            alert(t("val_err_scheduled_date", "Please enter a valid scheduled date."));
            return;
        }

        try {
            const res = await fetch(`/api/activities/${id}/postpone`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ scheduled_date: new_date, notes })
            });

            if (res.ok) {
                closePostponeModal();
                selectedDateStr = new_date;
                await refreshAllViews();
            } else {
                const data = await res.json();
                alert(data.message || t("err_postpone_activity", "Could not postpone activity."));
            }
        } catch (err) {
            console.error("Postpone activity error:", err);
        }
    }

    /**
     * Quick Status Update & Delete
     */
    async function quickUpdateStatus(activityId, newStatus) {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch(`/api/activities/${activityId}/status`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ status: newStatus })
            });

            if (res.ok) {
                await refreshAllViews();
            }
        } catch (e) {
            console.error("Status update error:", e);
        }
    }

    async function deleteActivity(activityId) {
        const token = getAuthToken();
        if (!token) return;

        const confirmMsg = t("confirm_delete_activity", "Are you sure you want to delete this scheduled activity?");
        if (!window.confirm(confirmMsg)) return;

        try {
            const res = await fetch(`/api/activities/${activityId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.ok) {
                await refreshAllViews();
            }
        } catch (e) {
            console.error("Delete activity error:", e);
        }
    }

    async function refreshAllViews() {
        await Promise.all([
            loadActivitySummary(),
            loadActivitySuggestions(),
            activeView === "calendar" ? loadCalendar() : loadListView()
        ]);
    }

    /**
     * Setup Event Listeners & Initialize
     */
    function init() {
        // Only run if on farmer page with activity section
        const section = document.getElementById("activitySection");
        if (!section) return;

        loadContextData();
        refreshAllViews();

        // 1. Month Navigation
        const prevBtn = document.getElementById("btnPrevMonth");
        if (prevBtn) {
            prevBtn.addEventListener("click", () => {
                currentMonth--;
                if (currentMonth < 1) {
                    currentMonth = 12;
                    currentYear--;
                }
                loadCalendar();
            });
        }

        const nextBtn = document.getElementById("btnNextMonth");
        if (nextBtn) {
            nextBtn.addEventListener("click", () => {
                currentMonth++;
                if (currentMonth > 12) {
                    currentMonth = 1;
                    currentYear++;
                }
                loadCalendar();
            });
        }

        const todayBtn = document.getElementById("btnTodayMonth");
        if (todayBtn) {
            todayBtn.addEventListener("click", () => {
                currentYear = today.getFullYear();
                currentMonth = today.getMonth() + 1;
                selectedDateStr = formatDateIso(today);
                loadCalendar();
            });
        }

        // 2. View Mode Tabs (Calendar vs List)
        const calTab = document.getElementById("tabCalendarViewBtn");
        const listTab = document.getElementById("tabListViewBtn");
        const calContainer = document.getElementById("activityCalendarContainer");
        const listContainer = document.getElementById("activityListContainer");

        if (calTab && listTab && calContainer && listContainer) {
            calTab.addEventListener("click", () => {
                calTab.classList.add("active");
                listTab.classList.remove("active");
                calContainer.style.display = "block";
                listContainer.style.display = "none";
                activeView = "calendar";
                loadCalendar();
            });

            listTab.addEventListener("click", () => {
                listTab.classList.add("active");
                calTab.classList.remove("active");
                calContainer.style.display = "none";
                listContainer.style.display = "block";
                activeView = "list";
                loadListView();
            });
        }

        // 3. Filter dropdown listeners
        ["activityFilterCategory", "activityFilterStatus", "activityFilterCrop", "activityFilterPriority"].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener("change", () => {
                    if (activeView === "calendar") loadCalendar();
                    else loadListView();
                });
            }
        });

        // 4. Header buttons
        const openAddBtn = document.getElementById("btnOpenAddActivityModal");
        if (openAddBtn) {
            openAddBtn.addEventListener("click", () => openActivityModal());
        }

        const refreshBtn = document.getElementById("btnRefreshActivities");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => refreshAllViews());
        }

        // 5. Suggestions toggle
        const toggleHeader = document.getElementById("suggestionsHeaderToggle");
        const toggleBtn = document.getElementById("btnToggleSuggestions");
        const suggContainer = document.getElementById("activitySuggestionsContainer");
        if (toggleHeader && suggContainer) {
            toggleHeader.addEventListener("click", () => {
                suggContainer.classList.toggle("collapsed");
                if (toggleBtn) toggleBtn.classList.toggle("collapsed");
            });
        }

        // 6. Form submissions
        const actForm = document.getElementById("activityForm");
        if (actForm) {
            actForm.addEventListener("submit", handleActivitySubmit);
        }

        const postpForm = document.getElementById("postponeForm");
        if (postpForm) {
            postpForm.addEventListener("submit", handlePostponeSubmit);
        }

        // Quick postpone helper buttons (+1 Day, +3 Days, +1 Week)
        const pDateInp = document.getElementById("postponeDateInput");
        const p1 = document.getElementById("btnPostpone1Day");
        const p3 = document.getElementById("btnPostpone3Days");
        const p7 = document.getElementById("btnPostpone1Week");

        if (pDateInp) {
            const setOffsetDays = (days) => {
                const base = pDateInp.value ? new Date(pDateInp.value) : new Date();
                const target = new Date(base.getTime() + days * 86400000);
                pDateInp.value = formatDateIso(target);
            };
            if (p1) p1.addEventListener("click", () => setOffsetDays(1));
            if (p3) p3.addEventListener("click", () => setOffsetDays(3));
            if (p7) p7.addEventListener("click", () => setOffsetDays(7));
        }

        // 7. Modal Close Buttons
        document.querySelectorAll("#activityModal .modal-close-btn").forEach(btn => {
            btn.addEventListener("click", closeActivityModal);
        });
        document.querySelectorAll("#activityDetailsModal .modal-close-btn").forEach(btn => {
            btn.addEventListener("click", closeActivityDetailsModal);
        });
        document.querySelectorAll("#postponeModal .modal-close-btn").forEach(btn => {
            btn.addEventListener("click", closePostponeModal);
        });

        // Close on backdrop click
        [document.getElementById("activityModal"), document.getElementById("activityDetailsModal"), document.getElementById("postponeModal")].forEach(m => {
            if (m) {
                m.addEventListener("click", (e) => {
                    if (e.target === m) m.classList.remove("open");
                });
            }
        });

        // 8. Trilingual reactivity
        window.addEventListener("languageChanged", () => {
            populateDropdowns();
            renderCalendar();
            renderSelectedDayAgenda();
            if (activeView === "list") loadListView();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
