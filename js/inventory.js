/**
 * AgriSmart - Smart Farm Inventory & Stock Management (Feature Upgrade 7)
 * Client-Side Controller
 */

(function () {
    "use strict";

    // Module State
    let inventoryItems = [];
    let inventorySummary = null;
    let contextFarms = [];
    let contextCrops = [];
    let isSubmitting = false;

    // Filters
    const filters = {
        category: "all",
        status: "all",
        farm_id: "all",
        search: ""
    };

    // Category Icons Map
    const CATEGORY_ICONS = {
        "Seeds": "🌾",
        "Fertilizers": "🧪",
        "Pesticides": "🛡️",
        "Herbicides": "🌿",
        "Farming equipment": "🚜",
        "Irrigation supplies": "💧",
        "Tools and machinery": "⚙️",
        "Other agricultural supplies": "📦"
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
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatCurrency(val) {
        const num = parseFloat(val) || 0;
        return "₹" + num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function formatDate(val) {
        if (!val) return "—";
        try {
            const d = new Date(val);
            if (isNaN(d.getTime())) return String(val).substring(0, 10);
            return d.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
        } catch (e) {
            return String(val).substring(0, 10);
        }
    }

    function getStatusBadgeClass(status) {
        switch (status) {
            case "In Stock": return "stock-status-in-stock";
            case "Low Stock": return "stock-status-low-stock";
            case "Out of Stock": return "stock-status-out-of-stock";
            case "Expiring Soon": return "stock-status-expiring";
            case "Expired": return "stock-status-expired";
            default: return "stock-status-in-stock";
        }
    }

    function getMovementTypeBadgeClass(type) {
        switch (type) {
            case "Usage / Consumption": return "mov-type-usage";
            case "Purchase / Addition": return "mov-type-purchase";
            case "Adjustment": return "mov-type-adjustment";
            case "Damaged or Expired": return "mov-type-damaged";
            case "Transfer": return "mov-type-transfer";
            default: return "mov-type-adjustment";
        }
    }

    // =========================================================================
    // INITIALIZATION & DATA LOADING
    // =========================================================================

    async function initInventory() {
        const token = getAuthToken();
        if (!token) return;

        // Set default dates in modals to today
        const todayStr = new Date().toISOString().substring(0, 10);
        const purchaseDateInput = document.getElementById("invPurchaseDate");
        const movDateInput = document.getElementById("movDate");
        if (purchaseDateInput && !purchaseDateInput.value) purchaseDateInput.value = todayStr;
        if (movDateInput && !movDateInput.value) movDateInput.value = todayStr;

        setupEventListeners();
        await loadContextData();
        await refreshInventoryData();
    }

    async function loadContextData() {
        const token = getAuthToken();
        if (!token) return;

        try {
            // Load Farms
            const farmRes = await fetch("/api/farms", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (farmRes.ok) {
                const farmData = await farmRes.json();
                contextFarms = farmData.farms || farmData.data || [];
                populateFarmDropdowns();
            }

            // Load Crops
            const cropRes = await fetch("/api/crops", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (cropRes.ok) {
                const cropData = await cropRes.json();
                contextCrops = cropData.crops || cropData.data || [];
                populateCropDropdowns();
            }
        } catch (e) {
            console.warn("Could not load farms/crops context:", e);
        }
    }

    function populateFarmDropdowns() {
        const filterSelect = document.getElementById("inventoryFarmFilter");
        const modalSelect = document.getElementById("invFarmId");
        const movFarmSelect = document.getElementById("movFarmSelect");

        if (filterSelect) {
            const currentVal = filterSelect.value;
            filterSelect.innerHTML = `<option value="all">${t("opt_all_farms", "All Farms")}</option>` +
                contextFarms.map(f => `<option value="${f.id}">${escapeHtml(f.farm_name)} (${escapeHtml(f.location || "General")})</option>`).join("");
            filterSelect.value = currentVal;
        }

        if (modalSelect) {
            modalSelect.innerHTML = `<option value="">${t("opt_general_inventory", "General / All Farms")}</option>` +
                contextFarms.map(f => `<option value="${f.id}">${escapeHtml(f.farm_name)}</option>`).join("");
        }

        if (movFarmSelect) {
            movFarmSelect.innerHTML = `<option value="">${t("opt_no_farm", "-- No specific farm --")}</option>` +
                contextFarms.map(f => `<option value="${f.id}">${escapeHtml(f.farm_name)}</option>`).join("");
        }
    }

    function populateCropDropdowns() {
        const movCropSelect = document.getElementById("movCropSelect");
        if (movCropSelect) {
            movCropSelect.innerHTML = `<option value="">${t("opt_no_crop", "-- No specific crop --")}</option>` +
                contextCrops.map(c => `<option value="${c.id}">${escapeHtml(c.crop_name)} (${escapeHtml(c.variety || c.growth_stage || "General")})</option>`).join("");
        }
    }

    function populateItemDropdownForMovements() {
        const select = document.getElementById("movInventorySelect");
        if (!select) return;

        const currentVal = select.value;
        let html = `<option value="">${t("opt_choose_item", "-- Select item --")}</option>`;
        inventoryItems.forEach(item => {
            const icon = CATEGORY_ICONS[item.category] || "📦";
            html += `<option value="${item.id}" data-unit="${escapeHtml(item.unit)}" data-qty="${item.quantity}">${icon} ${escapeHtml(item.item_name)} (${item.quantity} ${escapeHtml(item.unit)} available)</option>`;
        });
        select.innerHTML = html;
        if (currentVal) select.value = currentVal;
    }

    async function refreshInventoryData() {
        const token = getAuthToken();
        if (!token) return;

        try {
            await Promise.all([
                fetchSummary(token),
                fetchInventoryList(token)
            ]);
        } catch (e) {
            console.error("Error refreshing inventory data:", e);
        }
    }

    // =========================================================================
    // API FETCHERS
    // =========================================================================

    async function fetchSummary(token) {
        try {
            const res = await fetch("/api/inventory/summary", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                inventorySummary = data.summary || data.data || {};
                renderSummaryKPIs(inventorySummary);
                renderRecentMovements(inventorySummary.recent_movements || []);
            }
        } catch (e) {
            console.error("Error fetching inventory summary:", e);
        }
    }

    async function fetchInventoryList(token) {
        try {
            const queryParams = new URLSearchParams();
            if (filters.category !== "all") queryParams.set("category", filters.category);
            if (filters.status !== "all") queryParams.set("status", filters.status);
            if (filters.farm_id !== "all") queryParams.set("farm_id", filters.farm_id);
            if (filters.search) queryParams.set("search", filters.search);

            const res = await fetch(`/api/inventory?${queryParams.toString()}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.ok) {
                const data = await res.json();
                inventoryItems = data.items || data.data || [];
                renderInventoryTable(inventoryItems);
                populateItemDropdownForMovements();
            }
        } catch (e) {
            console.error("Error fetching inventory items:", e);
        }
    }

    // =========================================================================
    // RENDERING
    // =========================================================================

    function renderSummaryKPIs(summary) {
        const totalItemsEl = document.getElementById("kpiTotalInventoryItems");
        const lowStockEl = document.getElementById("kpiLowStockCount");
        const expiringEl = document.getElementById("kpiExpiringCount");
        const valuationEl = document.getElementById("kpiStockValuation");
        const cardBadgeEl = document.getElementById("cardInventoryBadge");
        const alertsBarEl = document.getElementById("inventoryAlertsBar");
        const alertsMsgEl = document.getElementById("inventoryAlertsMessage");

        if (totalItemsEl) totalItemsEl.textContent = summary.total_items || 0;
        if (lowStockEl) lowStockEl.textContent = summary.low_stock_count || 0;

        const expiringOrExpired = (summary.expiring_soon_count || summary.expiring_count || 0) + (summary.expired_count || 0);
        if (expiringEl) expiringEl.textContent = expiringOrExpired;

        if (valuationEl) valuationEl.textContent = formatCurrency(summary.total_valuation || 0);

        // Dashboard Card Badge
        const attentionCount = (summary.low_stock_count || 0) + (summary.out_of_stock_count || 0) + expiringOrExpired;
        if (cardBadgeEl) {
            if (attentionCount > 0) {
                cardBadgeEl.style.display = "inline-block";
                cardBadgeEl.textContent = `${attentionCount} Alerts`;
            } else {
                cardBadgeEl.style.display = "none";
            }
        }

        // Reorder & Critical Alerts Banner
        if (alertsBarEl && alertsMsgEl) {
            const outCount = summary.out_of_stock_count || 0;
            const lowCount = summary.low_stock_count || 0;
            const expCount = summary.expired_count || 0;
            const nearExpCount = summary.expiring_soon_count || summary.expiring_count || 0;

            if (outCount > 0 || lowCount > 0 || expCount > 0 || nearExpCount > 0) {
                alertsBarEl.style.display = "flex";
                const parts = [];
                if (outCount > 0) parts.push(`${outCount} item(s) out of stock`);
                if (lowCount > 0) parts.push(`${lowCount} item(s) running low`);
                if (expCount > 0) parts.push(`${expCount} item(s) expired`);
                if (nearExpCount > 0) parts.push(`${nearExpCount} item(s) expiring within 30 days`);
                alertsMsgEl.textContent = parts.join(", ") + ". Review stock levels and reorder as needed.";
            } else {
                alertsBarEl.style.display = "none";
            }
        }
    }

    function renderInventoryTable(items) {
        const tbody = document.getElementById("inventoryTableBody");
        const emptyState = document.getElementById("inventoryEmptyState");
        const table = document.getElementById("inventoryTable");

        if (!tbody) return;

        if (!items || items.length === 0) {
            tbody.innerHTML = "";
            if (emptyState) emptyState.style.display = "block";
            if (table) table.style.display = "none";
            return;
        }

        if (emptyState) emptyState.style.display = "none";
        if (table) table.style.display = "table";

        let html = "";
        items.forEach(item => {
            const icon = CATEGORY_ICONS[item.category] || "📦";
            const badgeClass = getStatusBadgeClass(item.status);
            const statusLocalized = t(`status_${item.status.toLowerCase().replace(/ /g, "_")}`, item.status);
            const unitPrice = formatCurrency(item.purchase_price);
            const totalVal = formatCurrency(item.total_value);
            const farmName = item.farm_name ? `${escapeHtml(item.farm_name)}` : t("opt_general_inventory", "General Farm");
            const storageLoc = item.storage_location ? `<br><small style="color:var(--text-secondary);">${escapeHtml(item.storage_location)}</small>` : "";

            // Calculate progress relative to min threshold
            const qty = parseFloat(item.quantity) || 0;
            const threshold = parseFloat(item.min_threshold) || 1;
            const pct = Math.min(Math.round((qty / Math.max(threshold * 2, 1)) * 100), 100);
            let fillClass = "normal";
            if (qty <= 0) fillClass = "out";
            else if (qty <= threshold) fillClass = "low";

            html += `
                <tr data-id="${item.id}">
                    <td>
                        <strong>${icon} ${escapeHtml(item.item_name)}</strong>
                        ${item.supplier_name ? `<br><small style="color:var(--text-secondary); font-size:11px;">${t("lbl_supplier", "Supplier")}: ${escapeHtml(item.supplier_name)}</small>` : ""}
                    </td>
                    <td>
                        <span style="font-size:12px; color:var(--text-secondary);">${escapeHtml(item.category)}</span>
                    </td>
                    <td>
                        <strong>${qty.toFixed(2)} ${escapeHtml(item.unit)}</strong>
                        <div class="stock-bar-wrap" title="${pct}% of optimal buffer">
                            <div class="stock-bar-fill ${fillClass}" style="width: ${pct}%;"></div>
                        </div>
                    </td>
                    <td>
                        <span>${unitPrice} / ${escapeHtml(item.unit)}</span>
                        <br><strong style="color:#059669; font-size:12px;">${totalVal}</strong>
                    </td>
                    <td>
                        <span style="font-size:12px; color:var(--text-secondary);">${threshold.toFixed(2)} ${escapeHtml(item.unit)}</span>
                    </td>
                    <td>
                        <span style="font-size:12px;">${formatDate(item.expiry_date)}</span>
                    </td>
                    <td>
                        <span>${farmName}</span>
                        ${storageLoc}
                    </td>
                    <td>
                        <span class="stock-status-badge ${badgeClass}">${statusLocalized}</span>
                    </td>
                    <td style="text-align:right; white-space:nowrap;">
                        <button type="button" class="btn-sm btn-secondary btn-action-mov" data-id="${item.id}" title="${t("btn_log_movement", "Log Movement")}">⇄</button>
                        <button type="button" class="btn-sm btn-secondary btn-action-hist" data-id="${item.id}" title="${t("btn_view_history", "Audit Trail")}">📋</button>
                        <button type="button" class="btn-sm btn-secondary btn-action-edit" data-id="${item.id}" title="${t("btn_edit", "Edit")}">✏️</button>
                        <button type="button" class="btn-sm btn-danger btn-action-del" data-id="${item.id}" title="${t("btn_delete", "Delete")}">🗑️</button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
        attachTableActionListeners();
    }

    function renderRecentMovements(movements) {
        const tbody = document.getElementById("recentMovementsTableBody");
        const emptyState = document.getElementById("recentMovementsEmptyState");
        const table = document.getElementById("recentMovementsTable");

        if (!tbody) return;

        if (!movements || movements.length === 0) {
            tbody.innerHTML = "";
            if (emptyState) emptyState.style.display = "block";
            if (table) table.style.display = "none";
            return;
        }

        if (emptyState) emptyState.style.display = "none";
        if (table) table.style.display = "table";

        let html = "";
        movements.forEach(m => {
            const badgeClass = getMovementTypeBadgeClass(m.movement_type);
            const dateStr = formatDate(m.movement_date) + (m.movement_time ? ` ${m.movement_time}` : "");
            const cropOrFarm = m.crop_name ? `🌾 ${escapeHtml(m.crop_name)}` : (m.farm_name ? `🏡 ${escapeHtml(m.farm_name)}` : "—");
            const reason = m.reason ? escapeHtml(m.reason) : "—";

            html += `
                <tr>
                    <td style="font-size:12px; white-space:nowrap;">${dateStr}</td>
                    <td><strong>${escapeHtml(m.item_name)}</strong></td>
                    <td><span class="mov-type-badge ${badgeClass}">${escapeHtml(m.movement_type)}</span></td>
                    <td><strong>${m.quantity} ${escapeHtml(m.unit)}</strong></td>
                    <td style="font-size:12px;">${cropOrFarm}</td>
                    <td style="font-size:12px; color:var(--text-secondary);">${reason}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    // =========================================================================
    // EVENT LISTENERS & MODAL HANDLERS
    // =========================================================================

    function setupEventListeners() {
        // Add Item Modal Button
        const btnOpenAdd = document.getElementById("btnOpenInventoryModal");
        if (btnOpenAdd) {
            btnOpenAdd.addEventListener("click", () => openInventoryModal());
        }

        // Record Movement Button
        const btnOpenMov = document.getElementById("btnOpenMovementModal");
        if (btnOpenMov) {
            btnOpenMov.addEventListener("click", () => openStockMovementModal());
        }

        // Refresh Button
        const btnRefresh = document.getElementById("btnRefreshInventory");
        if (btnRefresh) {
            btnRefresh.addEventListener("click", async () => {
                btnRefresh.classList.add("rotating");
                await refreshInventoryData();
                setTimeout(() => btnRefresh.classList.remove("rotating"), 500);
            });
        }

        // Critical Attention Filter Button in Alerts Banner
        const btnFilterCritical = document.getElementById("btnFilterCriticalStock");
        if (btnFilterCritical) {
            btnFilterCritical.addEventListener("click", () => {
                const statusSelect = document.getElementById("inventoryStatusFilter");
                if (statusSelect) {
                    statusSelect.value = "low_stock";
                    filters.status = "low_stock";
                    fetchInventoryList(getAuthToken());
                }
            });
        }

        // Filters Toolbar
        const catFilter = document.getElementById("inventoryCategoryFilter");
        if (catFilter) {
            catFilter.addEventListener("change", (e) => {
                filters.category = e.target.value;
                fetchInventoryList(getAuthToken());
            });
        }

        const statusFilter = document.getElementById("inventoryStatusFilter");
        if (statusFilter) {
            statusFilter.addEventListener("change", (e) => {
                filters.status = e.target.value;
                fetchInventoryList(getAuthToken());
            });
        }

        const farmFilter = document.getElementById("inventoryFarmFilter");
        if (farmFilter) {
            farmFilter.addEventListener("change", (e) => {
                filters.farm_id = e.target.value;
                fetchInventoryList(getAuthToken());
            });
        }

        const searchInput = document.getElementById("inventorySearchInput");
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener("input", (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    filters.search = e.target.value.trim();
                    fetchInventoryList(getAuthToken());
                }, 300);
            });
        }

        // Forms Submit Handlers
        const invForm = document.getElementById("inventoryForm");
        if (invForm) {
            invForm.addEventListener("submit", handleInventoryFormSubmit);
        }

        const movForm = document.getElementById("stockMovementForm");
        if (movForm) {
            movForm.addEventListener("submit", handleMovementFormSubmit);
        }

        // Movement Modal Dynamic Adjustments
        const movItemSelect = document.getElementById("movInventorySelect");
        if (movItemSelect) {
            movItemSelect.addEventListener("change", updateMovementModalItemInfo);
        }

        const movTypeSelect = document.getElementById("movType");
        if (movTypeSelect) {
            movTypeSelect.addEventListener("change", updateMovementModalTypeInfo);
        }

        // Modal Close Buttons
        document.querySelectorAll(".modal-close-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                closeAllInventoryModals();
            });
        });

        // Close on Backdrop Click
        ["inventoryModal", "stockMovementModal", "itemHistoryModal"].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener("click", (e) => {
                    if (e.target === el) closeAllInventoryModals();
                });
            }
        });

        // Language change event listener
        document.addEventListener("languageChanged", () => {
            populateFarmDropdowns();
            populateCropDropdowns();
            renderSummaryKPIs(inventorySummary || {});
            renderInventoryTable(inventoryItems);
        });
    }

    function attachTableActionListeners() {
        // Log Movement
        document.querySelectorAll(".btn-action-mov").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                openStockMovementModal(id);
            });
        });

        // Audit History
        document.querySelectorAll(".btn-action-hist").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                openItemHistoryModal(id);
            });
        });

        // Edit
        document.querySelectorAll(".btn-action-edit").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                openInventoryModal(id);
            });
        });

        // Delete
        document.querySelectorAll(".btn-action-del").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = btn.getAttribute("data-id");
                confirmDeleteInventoryItem(id);
            });
        });
    }

    // =========================================================================
    // MODAL OPEN / CLOSE LOGIC
    // =========================================================================

    function openInventoryModal(editItemId = null) {
        const modal = document.getElementById("inventoryModal");
        const form = document.getElementById("inventoryForm");
        const titleEl = document.getElementById("inventoryModalTitle");
        const idInput = document.getElementById("inventoryId");

        if (!modal || !form) return;
        form.reset();

        const todayStr = new Date().toISOString().substring(0, 10);
        document.getElementById("invPurchaseDate").value = todayStr;
        document.getElementById("invQuantity").removeAttribute("disabled");

        if (editItemId) {
            const item = inventoryItems.find(i => String(i.id) === String(editItemId));
            if (!item) return;

            idInput.value = item.id;
            if (titleEl) titleEl.textContent = t("modal_edit_inventory_title", "Edit Inventory Item");
            document.getElementById("invItemName").value = item.item_name || "";
            document.getElementById("invCategory").value = item.category || "Fertilizers";
            document.getElementById("invQuantity").value = item.quantity;
            document.getElementById("invUnit").value = item.unit || "kg";
            document.getElementById("invPurchasePrice").value = item.purchase_price;
            document.getElementById("invPurchaseDate").value = item.purchase_date ? String(item.purchase_date).substring(0, 10) : todayStr;
            document.getElementById("invMinThreshold").value = item.min_threshold;
            document.getElementById("invExpiryDate").value = item.expiry_date ? String(item.expiry_date).substring(0, 10) : "";
            document.getElementById("invFarmId").value = item.farm_id || "";
            document.getElementById("invStorageLocation").value = item.storage_location || "";
            document.getElementById("invSupplierName").value = item.supplier_name || "";
            document.getElementById("invNotes").value = item.notes || "";
        } else {
            idInput.value = "";
            if (titleEl) titleEl.textContent = t("modal_add_inventory_title", "Add Inventory Item");
            document.getElementById("invMinThreshold").value = "5.00";
        }

        modal.classList.add("active");
        modal.style.display = "flex";
    }

    function openStockMovementModal(preselectedItemId = null) {
        const modal = document.getElementById("stockMovementModal");
        const form = document.getElementById("stockMovementForm");
        if (!modal || !form) return;

        form.reset();
        const todayStr = new Date().toISOString().substring(0, 10);
        document.getElementById("movDate").value = todayStr;

        populateItemDropdownForMovements();

        if (preselectedItemId) {
            const select = document.getElementById("movInventorySelect");
            if (select) {
                select.value = preselectedItemId;
                updateMovementModalItemInfo();
            }
        } else {
            updateMovementModalItemInfo();
        }

        updateMovementModalTypeInfo();

        modal.classList.add("active");
        modal.style.display = "flex";
    }

    function updateMovementModalItemInfo() {
        const select = document.getElementById("movInventorySelect");
        const infoEl = document.getElementById("movCurrentStockInfo");
        const unitBadge = document.getElementById("movUnitBadge");

        if (!select || !select.value) {
            if (infoEl) infoEl.textContent = "";
            if (unitBadge) unitBadge.textContent = "units";
            return;
        }

        const opt = select.options[select.selectedIndex];
        const unit = opt.getAttribute("data-unit") || "units";
        const qty = parseFloat(opt.getAttribute("data-qty")) || 0;

        if (infoEl) {
            infoEl.textContent = `${t("lbl_current_stock", "Current available stock")}: ${qty.toFixed(2)} ${unit}`;
        }
        if (unitBadge) {
            unitBadge.textContent = unit;
        }
    }

    function updateMovementModalTypeInfo() {
        const typeSelect = document.getElementById("movType");
        const adjustBox = document.getElementById("movAdjustModeBox");
        const reasonInput = document.getElementById("movReason");

        if (!typeSelect) return;
        const type = typeSelect.value;

        // Show/hide adjustment mode radio
        if (adjustBox) {
            adjustBox.style.display = (type === "Adjustment") ? "block" : "none";
        }

        // Set contextual placeholder
        if (reasonInput) {
            if (type === "Usage / Consumption") {
                reasonInput.placeholder = t("ph_mov_usage", "e.g. Foliar spray plot A, Sowing 2 acres");
            } else if (type === "Purchase / Addition") {
                reasonInput.placeholder = t("ph_mov_purchase", "e.g. Received seasonal vendor consignment");
            } else if (type === "Damaged or Expired") {
                reasonInput.placeholder = t("ph_mov_damaged", "e.g. Bag torn during rain, shelf expiration");
            } else if (type === "Adjustment") {
                reasonInput.placeholder = t("ph_mov_adjustment", "e.g. Physical inventory count correction");
            } else if (type === "Transfer") {
                reasonInput.placeholder = t("ph_mov_transfer", "e.g. Transferred to South Agro field storage");
            }
        }
    }

    async function openItemHistoryModal(itemId) {
        const modal = document.getElementById("itemHistoryModal");
        const titleEl = document.getElementById("itemHistoryModalTitle");
        const subEl = document.getElementById("itemHistorySubtitle");
        const pillsEl = document.getElementById("itemHistoryOverviewPills");
        const tbody = document.getElementById("itemMovementsTableBody");
        const emptyEl = document.getElementById("itemMovementsEmpty");
        const table = document.getElementById("itemMovementsTable");

        if (!modal) return;

        const item = inventoryItems.find(i => String(i.id) === String(itemId));
        if (item) {
            if (titleEl) titleEl.textContent = `${item.item_name} — ${t("title_audit_history", "Movement History")}`;
            if (subEl) subEl.textContent = `${item.category} • ${item.farm_name || "General Farm"} • Location: ${item.storage_location || "N/A"}`;
            if (pillsEl) {
                pillsEl.innerHTML = `
                    <div style="background:#f1f5f9; padding:6px 12px; border-radius:6px; font-size:12px;"><strong>Stock:</strong> ${item.quantity} ${escapeHtml(item.unit)}</div>
                    <div style="background:#f1f5f9; padding:6px 12px; border-radius:6px; font-size:12px;"><strong>Reorder Threshold:</strong> ${item.min_threshold} ${escapeHtml(item.unit)}</div>
                    <div style="background:#f1f5f9; padding:6px 12px; border-radius:6px; font-size:12px;"><strong>Total Value:</strong> ${formatCurrency(item.total_value)}</div>
                    <div style="background:#f1f5f9; padding:6px 12px; border-radius:6px; font-size:12px;"><strong>Status:</strong> ${item.status}</div>
                `;
            }
        }

        modal.classList.add("active");
        modal.style.display = "flex";

        // Fetch movements
        const token = getAuthToken();
        try {
            const res = await fetch(`/api/inventory/${itemId}/movements`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                const movements = data.movements || data.data || [];

                if (movements.length === 0) {
                    if (tbody) tbody.innerHTML = "";
                    if (emptyEl) emptyEl.style.display = "block";
                    if (table) table.style.display = "none";
                } else {
                    if (emptyEl) emptyEl.style.display = "none";
                    if (table) table.style.display = "table";

                    let html = "";
                    movements.forEach(m => {
                        const badgeClass = getMovementTypeBadgeClass(m.movement_type);
                        const dateStr = formatDate(m.movement_date) + (m.movement_time ? ` ${m.movement_time}` : "");
                        const cropOrFarm = m.crop_name ? `🌾 ${escapeHtml(m.crop_name)}` : (m.farm_name ? `🏡 ${escapeHtml(m.farm_name)}` : "—");

                        html += `
                            <tr>
                                <td style="font-size:12px; white-space:nowrap;">${dateStr}</td>
                                <td><span class="mov-type-badge ${badgeClass}">${escapeHtml(m.movement_type)}</span></td>
                                <td><strong>${m.quantity} ${escapeHtml(m.unit)}</strong></td>
                                <td style="font-size:12px;">${cropOrFarm}</td>
                                <td style="font-size:12px; color:var(--text-secondary);">${escapeHtml(m.reason || "—")}</td>
                            </tr>
                        `;
                    });
                    if (tbody) tbody.innerHTML = html;
                }
            }
        } catch (e) {
            console.error("Error loading item movements:", e);
        }
    }

    function closeAllInventoryModals() {
        ["inventoryModal", "stockMovementModal", "itemHistoryModal"].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.classList.remove("active");
                el.style.display = "none";
            }
        });
    }

    // =========================================================================
    // FORM SUBMISSIONS & ACTIONS
    // =========================================================================

    async function handleInventoryFormSubmit(e) {
        e.preventDefault();
        if (isSubmitting) return;

        const token = getAuthToken();
        if (!token) return;

        const id = document.getElementById("inventoryId").value;
        const isEdit = Boolean(id);

        const payload = {
            item_name: document.getElementById("invItemName").value.trim(),
            category: document.getElementById("invCategory").value,
            quantity: parseFloat(document.getElementById("invQuantity").value) || 0,
            unit: document.getElementById("invUnit").value,
            purchase_price: parseFloat(document.getElementById("invPurchasePrice").value) || 0,
            purchase_date: document.getElementById("invPurchaseDate").value,
            min_threshold: parseFloat(document.getElementById("invMinThreshold").value) || 5.0,
            expiry_date: document.getElementById("invExpiryDate").value || null,
            farm_id: document.getElementById("invFarmId").value || null,
            storage_location: document.getElementById("invStorageLocation").value.trim() || null,
            supplier_name: document.getElementById("invSupplierName").value.trim() || null,
            notes: document.getElementById("invNotes").value.trim() || null
        };

        if (!payload.item_name) {
            alert(t("alert_item_name_required", "Item name is required."));
            return;
        }

        const saveBtn = document.getElementById("btnSaveInventory");
        try {
            isSubmitting = true;
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = t("btn_saving", "Saving...");
            }

            const url = isEdit ? `/api/inventory/${id}` : "/api/inventory";
            const method = isEdit ? "PUT" : "POST";

            const res = await fetch(url, {
                method: method,
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok) {
                closeAllInventoryModals();
                await refreshInventoryData();
            } else {
                alert(data.message || t("alert_save_failed", "Failed to save inventory item."));
            }
        } catch (err) {
            console.error("Save inventory error:", err);
            alert(t("alert_network_error", "Network error. Please try again."));
        } finally {
            isSubmitting = false;
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = t("btn_save_item", "Save Inventory Item");
            }
        }
    }

    async function handleMovementFormSubmit(e) {
        e.preventDefault();
        if (isSubmitting) return;

        const token = getAuthToken();
        if (!token) return;

        const select = document.getElementById("movInventorySelect");
        const itemId = select ? select.value : null;
        if (!itemId) {
            alert(t("alert_choose_item_required", "Please select an inventory item."));
            return;
        }

        const opt = select.options[select.selectedIndex];
        const currentStock = parseFloat(opt.getAttribute("data-qty")) || 0;
        const unit = opt.getAttribute("data-unit") || "units";

        const movType = document.getElementById("movType").value;
        const quantity = parseFloat(document.getElementById("movQuantity").value) || 0;

        if (quantity <= 0) {
            alert(t("alert_positive_qty_required", "Quantity must be greater than 0."));
            return;
        }

        // Live check negative stock protection on client
        if ((movType === "Usage / Consumption" || movType === "Damaged or Expired" || movType === "Transfer") && quantity > currentStock) {
            alert(`${t("alert_insufficient_stock", "Insufficient stock available")}: ${currentStock.toFixed(2)} ${unit}. You attempted: ${quantity.toFixed(2)} ${unit}.`);
            return;
        }

        // Adjust mode
        let adjustMode = "absolute";
        const adjustModeRadio = document.querySelector('input[name="movAdjustMode"]:checked');
        if (adjustModeRadio) adjustMode = adjustModeRadio.value;

        const payload = {
            movement_type: movType,
            quantity: quantity,
            movement_date: document.getElementById("movDate").value,
            crop_id: document.getElementById("movCropSelect") ? document.getElementById("movCropSelect").value || null : null,
            farm_id: document.getElementById("movFarmSelect") ? document.getElementById("movFarmSelect").value || null : null,
            adjust_mode: adjustMode,
            reason: document.getElementById("movReason").value.trim(),
            notes: document.getElementById("movNotes").value.trim() || null
        };

        const saveBtn = document.getElementById("btnSaveMovement");
        try {
            isSubmitting = true;
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.textContent = t("btn_saving", "Recording...");
            }

            const res = await fetch(`/api/inventory/${itemId}/movement`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok) {
                closeAllInventoryModals();
                await refreshInventoryData();
            } else {
                alert(data.message || t("alert_movement_failed", "Failed to record stock movement."));
            }
        } catch (err) {
            console.error("Record movement error:", err);
            alert(t("alert_network_error", "Network error. Please try again."));
        } finally {
            isSubmitting = false;
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = t("btn_record_movement_submit", "Record Movement");
            }
        }
    }

    async function confirmDeleteInventoryItem(itemId) {
        const item = inventoryItems.find(i => String(i.id) === String(itemId));
        const name = item ? item.item_name : "this item";

        if (!confirm(`${t("confirm_delete_item", "Are you sure you want to delete")} "${name}"? ${t("confirm_delete_item_warning", "All stock history and audit logs for this item will be removed.")}`)) {
            return;
        }

        const token = getAuthToken();
        try {
            const res = await fetch(`/api/inventory/${itemId}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                await refreshInventoryData();
            } else {
                const data = await res.json();
                alert(data.message || t("alert_delete_failed", "Failed to delete item."));
            }
        } catch (e) {
            console.error("Delete inventory error:", e);
        }
    }

    // Expose for external access if needed
    window.agriSmartInventory = {
        init: initInventory,
        refresh: refreshInventoryData,
        openModal: openInventoryModal,
        openMovement: openStockMovementModal
    };

    // Auto-init on DOMContentLoaded
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initInventory);
    } else {
        initInventory();
    }
})();
