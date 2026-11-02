/**
 * AgriSmart - Phase 12: Progressive Web App & Offline Client Controller
 * Manages service worker lifecycle, PWA installation prompts, connection
 * monitoring, multilingual offline banners, and safe offline action queuing.
 */

(function () {
    "use strict";

    let deferredInstallPrompt = null;
    let isOffline = !navigator.onLine;

    function t(key, fallback) {
        if (window.i18n && typeof window.i18n.t === "function") {
            const val = window.i18n.t(key);
            if (val && val !== key) return val;
        }
        return fallback || key;
    }

    function getAuthToken() {
        return localStorage.getItem("token") || localStorage.getItem("agriSmartToken");
    }

    function getCurrentUserId() {
        try {
            const uStr = localStorage.getItem("user") || localStorage.getItem("agriSmartUser");
            if (uStr) {
                const u = JSON.parse(uStr);
                return u.id || "guest";
            }
        } catch (e) {}
        return "guest";
    }

    // =========================================================================
    // 1. SERVICE WORKER REGISTRATION
    // =========================================================================

    function registerServiceWorker() {
        if (!("serviceWorker" in navigator)) {
            console.log("[PWA] Service Workers not supported in this browser.");
            return;
        }

        window.addEventListener("load", () => {
            navigator.serviceWorker.register("/sw.js", { scope: "/" })
                .then((reg) => {
                    console.log("[PWA] Service Worker registered with scope:", reg.scope);

                    // Check for updates
                    reg.addEventListener("updatefound", () => {
                        const newWorker = reg.installing;
                        if (!newWorker) return;
                        newWorker.addEventListener("statechange", () => {
                            if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
                                showUpdateAvailableBanner(newWorker);
                            }
                        });
                    });
                })
                .catch((err) => {
                    console.warn("[PWA] Service Worker registration failed:", err);
                });
        });
    }

    function showUpdateAvailableBanner(worker) {
        let updateBanner = document.getElementById("pwaUpdateBanner");
        if (!updateBanner) {
            updateBanner = document.createElement("div");
            updateBanner.id = "pwaUpdateBanner";
            updateBanner.className = "pwa-update-banner";
            updateBanner.innerHTML = `
                <span>🔄 ${t("pwa_update_available", "A new version of AgriSmart is available.")}</span>
                <button type="button" id="btnPwaRefresh">${t("pwa_btn_refresh", "Update Now")}</button>
            `;
            document.body.prepend(updateBanner);

            document.getElementById("btnPwaRefresh")?.addEventListener("click", () => {
                worker.postMessage({ type: "SKIP_WAITING" });
                window.location.reload();
            });
        }
    }

    // =========================================================================
    // 2. PWA INSTALLATION PROMPT & GUIDE
    // =========================================================================

    function initInstallPrompt() {
        window.addEventListener("beforeinstallprompt", (e) => {
            // Prevent Chrome 67 and earlier from automatically showing the prompt
            e.preventDefault();
            deferredInstallPrompt = e;
            showInstallUI(true);
        });

        window.addEventListener("appinstalled", () => {
            deferredInstallPrompt = null;
            showInstallUI(false);
            console.log("[PWA] AgriSmart was installed successfully.");
        });

        // Bind install button clicks
        document.querySelectorAll(".btn-pwa-install").forEach(btn => {
            btn.addEventListener("click", handleInstallClick);
        });
    }

    function showInstallUI(visible) {
        const installBtns = document.querySelectorAll(".btn-pwa-install");
        installBtns.forEach(btn => {
            btn.style.display = visible ? "inline-flex" : "none";
        });
    }

    async function handleInstallClick(e) {
        if (e && typeof e.preventDefault === "function") e.preventDefault();

        if (deferredInstallPrompt) {
            try {
                await deferredInstallPrompt.prompt();
                const choice = await deferredInstallPrompt.userChoice;
                if (choice && choice.outcome === "accepted") {
                    console.log("[PWA] User accepted the install prompt");
                }
                deferredInstallPrompt = null;
                showInstallUI(false);
                return;
            } catch (err) {
                console.log("[PWA] Prompt fallback to guide modal:", err.message);
            }
        }
        showInstallGuideModal();
    }

    function showInstallGuideModal() {
        let modal = document.getElementById("pwaInstallModal");
        if (!modal) {
            modal = document.createElement("div");
            modal.id = "pwaInstallModal";
            modal.className = "modal-overlay";
            modal.style.display = "flex";
            modal.innerHTML = `
                <div class="modal-content" style="max-width: 480px; text-align: left;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                        <h3 style="margin:0; color:#15803d; font-size:20px;">
                            📲 ${t("pwa_install_guide_title", "How to Install AgriSmart")}
                        </h3>
                        <button type="button" class="modal-close-btn" style="background:none; border:none; font-size:22px; cursor:pointer;">&times;</button>
                    </div>
                    <p style="color:#475569; font-size:14px; line-height:1.6; margin-bottom:16px;">
                        ${t("pwa_install_desc", "Install AgriSmart on your device for fast access, home screen launching, and offline support.")}
                    </p>
                    <div style="background:#f8fafc; border-radius:12px; padding:14px; margin-bottom:14px; border-left:4px solid #16a34a;">
                        <strong style="display:block; color:#1e293b; font-size:13px; margin-bottom:4px;">🍎 Apple iOS (Safari)</strong>
                        <span style="color:#64748b; font-size:13px; line-height:1.5;">
                            ${t("pwa_install_guide_ios", "Tap the Share button at the bottom of Safari, then scroll down and select 'Add to Home Screen'.")}
                        </span>
                    </div>
                    <div style="background:#f8fafc; border-radius:12px; padding:14px; margin-bottom:20px; border-left:4px solid #0284c7;">
                        <strong style="display:block; color:#1e293b; font-size:13px; margin-bottom:4px;">💻 Android / Chrome / Edge</strong>
                        <span style="color:#64748b; font-size:13px; line-height:1.5;">
                            ${t("pwa_install_guide_desktop", "Click the install icon in the address bar (top right) or open browser settings and tap 'Install AgriSmart'.")}
                        </span>
                    </div>
                    <button type="button" class="btn-secondary" id="btnClosePwaGuide" style="width:100%; padding:10px; border-radius:10px; background:#e2e8f0; border:none; font-weight:700; cursor:pointer;">
                        ${t("btn_close", "Close")}
                    </button>
                </div>
            `;
            document.body.appendChild(modal);

            modal.querySelector(".modal-close-btn")?.addEventListener("click", () => modal.remove());
            modal.querySelector("#btnClosePwaGuide")?.addEventListener("click", () => modal.remove());
            modal.addEventListener("click", (evt) => {
                if (evt.target === modal) modal.remove();
            });
        }
    }

    // =========================================================================
    // 3. CONNECTION MONITORING & OFFLINE INDICATOR BANNER
    // =========================================================================

    function createBannerElement() {
        let banner = document.getElementById("pwaConnectionBanner");
        if (!banner) {
            banner = document.createElement("div");
            banner.id = "pwaConnectionBanner";
            banner.className = "pwa-connection-banner";
            banner.style.display = "none";
            document.body.prepend(banner);
        }
        return banner;
    }

    function updateConnectionStatus() {
        const banner = createBannerElement();
        isOffline = !navigator.onLine;

        if (isOffline) {
            banner.className = "pwa-connection-banner offline";
            banner.innerHTML = `
                <div class="banner-inner">
                    <span class="banner-icon">⚠️</span>
                    <span class="banner-text">${t("pwa_offline_banner", "You are currently offline. Showing cached information.")}</span>
                    <a href="/offline.html" class="banner-link">${t("offline_learn_more", "Learn what works offline →")}</a>
                </div>
            `;
            banner.style.display = "block";
            document.body.classList.add("is-offline-mode");
        } else {
            // Was offline, now back online
            if (banner.classList.contains("offline")) {
                banner.className = "pwa-connection-banner online";
                banner.innerHTML = `
                    <div class="banner-inner">
                        <span class="banner-icon">✓</span>
                        <span class="banner-text">${t("pwa_online_banner", "Connection restored. You are back online.")}</span>
                    </div>
                `;
                banner.style.display = "block";
                document.body.classList.remove("is-offline-mode");

                // Process pending offline actions
                syncOfflineQueue();

                // Hide after 4 seconds
                setTimeout(() => {
                    if (banner && !isOffline) {
                        banner.style.display = "none";
                    }
                }, 4000);
            } else {
                banner.style.display = "none";
                document.body.classList.remove("is-offline-mode");
            }
        }
    }

    function initConnectionMonitoring() {
        window.addEventListener("online", updateConnectionStatus);
        window.addEventListener("offline", updateConnectionStatus);
        window.addEventListener("languageChanged", updateConnectionStatus);

        // Initial state check
        if (!navigator.onLine) {
            updateConnectionStatus();
        }
    }

    // =========================================================================
    // 4. OFFLINE ACTION QUEUE (Safe Farm / Crop registrations)
    // =========================================================================

    function getQueueKey() {
        return `agriSmart_offline_queue_${getCurrentUserId()}`;
    }

    function getOfflineQueue() {
        try {
            const raw = localStorage.getItem(getQueueKey());
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    function saveOfflineQueue(queue) {
        try {
            localStorage.setItem(getQueueKey(), JSON.stringify(queue));
            updateQueueBadge();
        } catch (e) {}
    }

    function queueOfflineAction(action) {
        // action format: { id: Date.now(), userId: number, type: 'add_crop' | 'add_farm', endpoint: string, method: string, payload: object, createdAt: string }
        const currentUserId = getCurrentUserId();
        const q = getOfflineQueue();
        q.push({
            ...action,
            userId: currentUserId,
            id: Date.now().toString(),
            createdAt: new Date().toISOString()
        });
        saveOfflineQueue(q);
        console.log("[PWA] Action queued for offline sync:", action.type);
    }

    async function clearPrivateCache() {
        try {
            if ("caches" in window) {
                await caches.delete("agrismart-data-v1");
                console.log("[PWA] Purged private user cache (agrismart-data-v1).");
            }
        } catch (e) {
            console.warn("[PWA] Failed to clear private cache:", e);
        }
    }

    function checkUserSessionChange() {
        const currentId = getCurrentUserId();
        const lastId = localStorage.getItem("agriSmart_last_user_id");
        if (lastId && String(lastId) !== String(currentId)) {
            // User account switched on this client: clear cached private API data
            clearPrivateCache();
        }
        if (currentId) {
            localStorage.setItem("agriSmart_last_user_id", String(currentId));
        } else {
            localStorage.removeItem("agriSmart_last_user_id");
        }
    }

    async function syncOfflineQueue() {
        const token = getAuthToken();
        const currentUserId = getCurrentUserId();
        if (!token) return;

        const q = getOfflineQueue();
        if (q.length === 0) return;

        console.log(`[PWA] Syncing ${q.length} queued offline actions for user ${currentUserId}...`);
        const remaining = [];

        for (const item of q) {
            // Security check: Never submit another user's action with the current token
            if (item.userId && item.userId !== currentUserId) {
                console.warn(`[PWA] Skipping queued action ${item.id} belonging to user ${item.userId} while logged in as ${currentUserId}.`);
                remaining.push(item);
                continue;
            }

            try {
                const res = await fetch(item.endpoint, {
                    method: item.method || "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify(item.payload)
                });

                if (!res.ok && res.status >= 500) {
                    // Server error, keep in queue for next retry
                    remaining.push(item);
                } else {
                    console.log(`[PWA] Synced action ${item.id} (${item.type}) successfully.`);
                }
            } catch (err) {
                // Still unreachable
                remaining.push(item);
            }
        }

        saveOfflineQueue(remaining);

        if (remaining.length === 0 && q.length > 0) {
            // Trigger refresh of relevant data tables if open
            if (window.agriSmartFarmCrop && typeof window.agriSmartFarmCrop.loadFarms === "function") {
                window.agriSmartFarmCrop.loadFarms();
                window.agriSmartFarmCrop.loadCrops();
            }
        }
    }

    function updateQueueBadge() {
        const q = getOfflineQueue();
        const badge = document.getElementById("offlineQueueBadge");
        if (badge) {
            if (q.length > 0) {
                badge.textContent = `${q.length} ${t("pwa_offline_queue_badge", "Offline Actions Pending")}`;
                badge.style.display = "inline-flex";
            } else {
                badge.style.display = "none";
            }
        }
    }

    function clearFarmerOfflineQueue() {
        localStorage.removeItem(getQueueKey());
        updateQueueBadge();
    }

    // =========================================================================
    // 5. INITIALIZATION & GLOBAL EXPORT
    // =========================================================================

    function init() {
        registerServiceWorker();
        initInstallPrompt();
        initConnectionMonitoring();
        checkUserSessionChange();
        updateQueueBadge();
    }

    window.AgriSmartPWA = {
        install: handleInstallClick,
        isOffline: () => isOffline,
        queueAction: queueOfflineAction,
        syncQueue: syncOfflineQueue,
        clearQueue: clearFarmerOfflineQueue,
        getQueue: getOfflineQueue,
        clearPrivateCache: clearPrivateCache
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
