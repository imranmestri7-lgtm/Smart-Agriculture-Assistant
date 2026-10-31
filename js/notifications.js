/**
 * js/notifications.js
 * Smart Agriculture Assistant - Phase 8 Smart Notifications & Alerts Controller
 */

(function () {
    "use strict";

    let currentCategory = "all";
    let isUnreadFilter = false;
    let cachedNotifications = [];

    function getAuthToken() {
        return localStorage.getItem("token") || localStorage.getItem("agriSmartToken");
    }

    function t(key, fallback) {
        if (window.i18n && typeof window.i18n.t === "function") {
            const val = window.i18n.t(key);
            if (val && val !== key) return val;
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

    function getCategoryIcon(cat) {
        switch (cat) {
            case "crop": return "🌾";
            case "irrigation": return "💧";
            case "weather": return "🌦️";
            case "disease": return "🍃";
            default: return "🔔";
        }
    }

    function updateBadges(unreadCount) {
        const count = parseInt(unreadCount, 10) || 0;
        const navBadge = document.getElementById("navNotificationBadge");
        const cardBadge = document.getElementById("cardNotificationBadge");

        if (navBadge) {
            if (count > 0) {
                navBadge.textContent = count > 99 ? "99+" : count;
                navBadge.style.display = "inline-flex";
            } else {
                navBadge.style.display = "none";
            }
        }

        if (cardBadge) {
            if (count > 0) {
                cardBadge.textContent = count > 99 ? "99+" : `${count} new`;
                cardBadge.style.display = "inline-flex";
            } else {
                cardBadge.style.display = "none";
            }
        }
    }

    /**
     * Fetch unread count quickly
     */
    async function loadUnreadCount() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const resp = await fetch("/api/notifications/unread-count", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (resp.ok) {
                const data = await resp.json();
                updateBadges(data.unread_count);
            }
        } catch (e) {
            console.warn("Could not fetch unread count:", e);
        }
    }

    /**
     * Fetch notifications from API
     */
    async function loadNotifications() {
        const token = getAuthToken();
        if (!token) return;

        const listContainer = document.getElementById("notificationsList");
        if (!listContainer) return;

        const queryParams = new URLSearchParams();
        if (isUnreadFilter) {
            queryParams.append("unread_only", "true");
        } else if (currentCategory && currentCategory !== "all") {
            queryParams.append("category", currentCategory);
        }

        const url = `/api/notifications${queryParams.toString() ? "?" + queryParams.toString() : ""}`;

        try {
            const resp = await fetch(url, {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (resp.status === 401) return;

            const data = await resp.json();
            if (data.status === "success") {
                cachedNotifications = data.notifications || [];
                updateBadges(data.unread_count);
                renderNotifications(cachedNotifications);
            }
        } catch (err) {
            console.error("Failed to load notifications:", err);
        }
    }

    /**
     * Render notification cards
     */
    function renderNotifications(notifications) {
        const listContainer = document.getElementById("notificationsList");
        if (!listContainer) return;

        if (!notifications || notifications.length === 0) {
            const emptyMsg = isUnreadFilter
                ? t("no_unread_notifications_msg", "You have no unread notifications.")
                : t("no_notifications_msg", "No alerts at this time. All farming activities are up to date!");

            listContainer.innerHTML = `
                <div class="notif-empty-state">
                    <span class="empty-icon">🔔</span>
                    <p>${escapeHtml(emptyMsg)}</p>
                </div>
            `;
            return;
        }

        let html = "";
        notifications.forEach(n => {
            const severityClass = `severity-${n.severity || "info"}`;
            const unreadClass = n.is_read ? "" : "unread";
            const icon = getCategoryIcon(n.category);
            const markReadTitle = t("mark_as_read", "Mark as Read");
            const deleteTitle = t("delete_notification", "Delete");

            let actionLinkHtml = "";
            if (n.link) {
                let linkLabel = "View Details →";
                if (n.category === "crop") linkLabel = "Manage Crops →";
                else if (n.category === "irrigation") linkLabel = "View Irrigation →";
                else if (n.category === "weather") linkLabel = "Check Weather →";
                else if (n.category === "disease") linkLabel = "Check Diagnosis →";

                actionLinkHtml = `<a href="${escapeHtml(n.link)}" class="notif-link-btn">${linkLabel}</a>`;
            }

            const readBtnHtml = !n.is_read
                ? `<button type="button" class="btn-notif-circle btn-read-notif" data-id="${n.id}" title="${markReadTitle}">✓</button>`
                : "";

            html += `
                <div class="notif-card ${severityClass} ${unreadClass}" id="notifCard-${n.id}">
                    <div class="notif-icon-col">
                        ${icon}
                    </div>
                    <div class="notif-content-col">
                        <div class="notif-title-row">
                            <span class="notif-badge-cat">${escapeHtml(n.category)}</span>
                            <strong class="notif-title">${escapeHtml(n.title)}</strong>
                        </div>
                        <p class="notif-message">${escapeHtml(n.message)}</p>
                        <div class="notif-meta-row">
                            <span>⏱️ ${escapeHtml(n.created_at)}</span>
                            ${actionLinkHtml}
                        </div>
                    </div>
                    <div class="notif-actions-col">
                        ${readBtnHtml}
                        <button type="button" class="btn-notif-circle btn-delete-notif" data-id="${n.id}" title="${deleteTitle}">🗑️</button>
                    </div>
                </div>
            `;
        });

        listContainer.innerHTML = html;
        bindCardActions();
    }

    /**
     * Bind individual card action buttons
     */
    function bindCardActions() {
        // Mark as Read
        document.querySelectorAll(".btn-read-notif").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                const notifId = e.currentTarget.getAttribute("data-id");
                await markSingleRead(notifId);
            });
        });

        // Delete
        document.querySelectorAll(".btn-delete-notif").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                const notifId = e.currentTarget.getAttribute("data-id");
                await deleteSingleNotification(notifId);
            });
        });
    }

    /**
     * Mark single notification as read
     */
    async function markSingleRead(id) {
        const token = getAuthToken();
        if (!token || !id) return;

        try {
            const resp = await fetch(`/api/notifications/${id}/read`, {
                method: "PATCH",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (resp.ok) {
                const data = await resp.json();
                updateBadges(data.unread_count);

                const card = document.getElementById(`notifCard-${id}`);
                if (card) {
                    card.classList.remove("unread");
                    const readBtn = card.querySelector(".btn-read-notif");
                    if (readBtn) readBtn.remove();
                }

                // If in unread filter, remove card
                if (isUnreadFilter && card) {
                    card.remove();
                    const listContainer = document.getElementById("notificationsList");
                    if (listContainer && listContainer.children.length === 0) {
                        renderNotifications([]);
                    }
                }
            }
        } catch (err) {
            console.error("Failed to mark notification read:", err);
        }
    }

    /**
     * Mark all notifications as read
     */
    async function markAllRead() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const resp = await fetch("/api/notifications/read-all", {
                method: "PATCH",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (resp.ok) {
                const data = await resp.json();
                updateBadges(data.unread_count);
                loadNotifications();
            }
        } catch (err) {
            console.error("Failed to mark all read:", err);
        }
    }

    /**
     * Delete individual notification
     */
    async function deleteSingleNotification(id) {
        const token = getAuthToken();
        if (!token || !id) return;

        try {
            const resp = await fetch(`/api/notifications/${id}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (resp.ok) {
                const data = await resp.json();
                updateBadges(data.unread_count);

                const card = document.getElementById(`notifCard-${id}`);
                if (card) card.remove();

                const listContainer = document.getElementById("notificationsList");
                if (listContainer && listContainer.children.length === 0) {
                    renderNotifications([]);
                }
            }
        } catch (err) {
            console.error("Failed to delete notification:", err);
        }
    }

    /**
     * Clear all notifications with confirmation
     */
    async function clearAllNotifications() {
        const token = getAuthToken();
        if (!token) return;

        const confirmMsg = t("confirm_clear_notifications", "Are you sure you want to clear all your notifications?");
        if (!window.confirm(confirmMsg)) return;

        try {
            const resp = await fetch("/api/notifications/clear", {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (resp.ok) {
                const data = await resp.json();
                updateBadges(0);
                renderNotifications([]);
            }
        } catch (err) {
            console.error("Failed to clear notifications:", err);
        }
    }

    /**
     * Notification Preferences
     */
    async function openPreferencesModal() {
        const token = getAuthToken();
        if (!token) return;

        const modal = document.getElementById("notificationPrefsModal");
        if (!modal) return;

        try {
            const resp = await fetch("/api/notifications/preferences", {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (resp.ok) {
                const data = await resp.json();
                const p = data.preferences || {};

                const cropCheck = document.getElementById("prefCropReminders");
                const irrigCheck = document.getElementById("prefIrrigationAlerts");
                const weathCheck = document.getElementById("prefWeatherAlerts");
                const disCheck = document.getElementById("prefDiseaseReminders");

                if (cropCheck) cropCheck.checked = !!p.crop_reminders;
                if (irrigCheck) irrigCheck.checked = !!p.irrigation_alerts;
                if (weathCheck) weathCheck.checked = !!p.weather_alerts;
                if (disCheck) disCheck.checked = !!p.disease_reminders;
            }

            modal.style.display = "flex";
        } catch (err) {
            console.error("Failed to load preferences:", err);
        }
    }

    async function savePreferences(e) {
        e.preventDefault();
        const token = getAuthToken();
        if (!token) return;

        const payload = {
            crop_reminders: document.getElementById("prefCropReminders")?.checked ?? true,
            irrigation_alerts: document.getElementById("prefIrrigationAlerts")?.checked ?? true,
            weather_alerts: document.getElementById("prefWeatherAlerts")?.checked ?? true,
            disease_reminders: document.getElementById("prefDiseaseReminders")?.checked ?? true
        };

        try {
            const resp = await fetch("/api/notifications/preferences", {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                json: true,
                body: JSON.stringify(payload)
            });

            if (resp.ok) {
                const modal = document.getElementById("notificationPrefsModal");
                if (modal) modal.style.display = "none";
                loadNotifications();
            }
        } catch (err) {
            console.error("Failed to save preferences:", err);
        }
    }

    /**
     * Initialize Event Listeners
     */
    function initNotifications() {
        // Tab Filtering
        document.querySelectorAll(".notif-tab").forEach(tab => {
            tab.addEventListener("click", (e) => {
                document.querySelectorAll(".notif-tab").forEach(t => t.classList.remove("active"));
                e.currentTarget.classList.add("active");

                const cat = e.currentTarget.getAttribute("data-category");
                const unread = e.currentTarget.getAttribute("data-unread");

                if (unread === "true") {
                    isUnreadFilter = true;
                    currentCategory = "all";
                } else {
                    isUnreadFilter = false;
                    currentCategory = cat || "all";
                }

                loadNotifications();
            });
        });

        // Mark All Read
        const markAllBtn = document.getElementById("markAllReadBtn");
        if (markAllBtn) {
            markAllBtn.addEventListener("click", markAllRead);
        }

        // Clear All
        const clearAllBtn = document.getElementById("clearAllNotificationsBtn");
        if (clearAllBtn) {
            clearAllBtn.addEventListener("click", clearAllNotifications);
        }

        // Refresh
        const refreshBtn = document.getElementById("refreshNotificationsBtn");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", async () => {
                const token = getAuthToken();
                if (token) {
                    try {
                        await fetch("/api/notifications/generate", {
                            method: "POST",
                            headers: { "Authorization": `Bearer ${token}` }
                        });
                    } catch (e) {
                        // ignore
                    }
                }
                loadNotifications();
            });
        }

        // Preferences Modal
        const openPrefsBtn = document.getElementById("openNotificationPrefsBtn");
        if (openPrefsBtn) {
            openPrefsBtn.addEventListener("click", openPreferencesModal);
        }

        const prefsForm = document.getElementById("notificationPrefsForm");
        if (prefsForm) {
            prefsForm.addEventListener("submit", savePreferences);
        }

        // Close modal buttons
        const prefsModal = document.getElementById("notificationPrefsModal");
        if (prefsModal) {
            prefsModal.querySelectorAll(".modal-close-btn").forEach(btn => {
                btn.addEventListener("click", () => {
                    prefsModal.style.display = "none";
                });
            });

            prefsModal.addEventListener("click", (e) => {
                if (e.target === prefsModal) {
                    prefsModal.style.display = "none";
                }
            });
        }

        // Listen for language changes
        window.addEventListener("languageChanged", () => {
            renderNotifications(cachedNotifications);
        });

        // Initial Load
        loadUnreadCount();
        loadNotifications();
    }

    // Expose globally
    window.agriSmartNotifications = {
        loadNotifications,
        loadUnreadCount,
        markAllRead,
        clearAllNotifications
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initNotifications);
    } else {
        initNotifications();
    }

})();
