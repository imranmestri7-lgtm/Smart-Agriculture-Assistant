/**
 * js/finance.js
 * Smart Agriculture Assistant - Feature Upgrade 5: Smart Farm Expense & Profit Management Controller
 */

(function () {
    "use strict";

    let contextData = { crops: [], farms: [], categories: [] };
    let summaryData = null;
    let cachedExpenses = [];
    let cachedHarvests = [];
    let activeTab = "expenses"; // "expenses" | "harvests"

    const CATEGORY_COLORS = {
        "Seeds": "#10b981",
        "Fertilizers": "#3b82f6",
        "Pesticides": "#f59e0b",
        "Labour": "#8b5cf6",
        "Irrigation and electricity": "#06b6d4",
        "Machinery and equipment": "#ec4899",
        "Transportation": "#f97316",
        "Other expenses": "#64748b"
    };

    function getAuthToken() {
        return localStorage.getItem("agriSmartToken") || localStorage.getItem("token") || "";
    }

    function t(key, fallback) {
        if (window.i18n && typeof window.i18n.t === "function") {
            const val = window.i18n.t(key);
            if (val && val !== key) return val;
        }
        return fallback || key;
    }

    function formatCurrency(val) {
        const num = parseFloat(val) || 0.0;
        return "₹" + num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
     * Load registered crops and farms for dropdown selectors
     */
    async function loadContextCrops() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch("/api/finance/context-crops", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    contextData = data;
                    populateDropdowns();
                }
            }
        } catch (e) {
            console.warn("Could not load financial context crops:", e);
        }
    }

    function populateDropdowns() {
        // Populate filter crop dropdown
        const filterCrop = document.getElementById("financeFilterCrop");
        if (filterCrop) {
            const currentVal = filterCrop.value;
            let options = `<option value="all">${escapeHtml(t("opt_all_crops", "All Crops"))}</option>`;
            contextData.crops.forEach(c => {
                options += `<option value="${c.id}">${escapeHtml(c.crop_name + (c.variety ? " (" + c.variety + ")" : ""))}</option>`;
            });
            filterCrop.innerHTML = options;
            if (currentVal) filterCrop.value = currentVal;
        }

        // Populate filter category dropdown
        const filterCat = document.getElementById("financeFilterCategory");
        if (filterCat) {
            const currentVal = filterCat.value;
            let options = `<option value="all">${escapeHtml(t("opt_all_categories", "All Categories"))}</option>`;
            (contextData.categories || []).forEach(cat => {
                options += `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`;
            });
            filterCat.innerHTML = options;
            if (currentVal) filterCat.value = currentVal;
        }

        // Populate Expense Modal Selects
        const expCropSelect = document.getElementById("expenseCropSelect");
        if (expCropSelect) {
            let options = `<option value="">${escapeHtml(t("opt_general_overhead", "-- General Farm Overhead --"))}</option>`;
            contextData.crops.forEach(c => {
                options += `<option value="${c.id}">${escapeHtml(c.crop_name + (c.variety ? " (" + c.variety + ")" : ""))}</option>`;
            });
            expCropSelect.innerHTML = options;
        }

        const expFarmSelect = document.getElementById("expenseFarmSelect");
        if (expFarmSelect) {
            let options = `<option value="">${escapeHtml(t("opt_choose_farm", "-- Choose Farm --"))}</option>`;
            contextData.farms.forEach(f => {
                options += `<option value="${f.id}">${escapeHtml(f.farm_name + (f.location ? " - " + f.location : ""))}</option>`;
            });
            expFarmSelect.innerHTML = options;
        }

        // Populate Harvest Modal Selects
        const harvCropSelect = document.getElementById("harvestCropSelect");
        if (harvCropSelect) {
            let options = `<option value="">${escapeHtml(t("opt_choose_crop", "-- Choose Registered Crop --"))}</option>`;
            contextData.crops.forEach(c => {
                options += `<option value="${c.id}" data-cropname="${escapeHtml(c.crop_name)}">${escapeHtml(c.crop_name + (c.variety ? " (" + c.variety + ")" : ""))}</option>`;
            });
            options += `<option value="custom">${escapeHtml(t("opt_other_custom_crop", "+ Other / Enter Crop Name"))}</option>`;
            harvCropSelect.innerHTML = options;
        }

        const harvFarmSelect = document.getElementById("harvestFarmSelect");
        if (harvFarmSelect) {
            let options = `<option value="">${escapeHtml(t("opt_choose_farm", "-- Choose Farm --"))}</option>`;
            contextData.farms.forEach(f => {
                options += `<option value="${f.id}">${escapeHtml(f.farm_name + (f.location ? " - " + f.location : ""))}</option>`;
            });
            harvFarmSelect.innerHTML = options;
        }
    }

    /**
     * Load financial summary metrics, category breakdown, crop profitability, trends
     */
    async function loadFinancialSummary() {
        const token = getAuthToken();
        if (!token) return;

        try {
            const res = await fetch("/api/finance/summary", {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    summaryData = data;
                    renderSummary(data);
                }
            }
        } catch (e) {
            console.error("Failed to load financial summary:", e);
        }
    }

    function renderSummary(data) {
        const s = data.summary || {};

        // 1. KPI Cards
        const totalExpEl = document.getElementById("kpiTotalExpenses");
        const totalRevEl = document.getElementById("kpiTotalRevenue");
        const netProfitEl = document.getElementById("kpiNetProfit");
        const profitMarginEl = document.getElementById("kpiProfitMargin");
        const expCountEl = document.getElementById("kpiExpenseCount");
        const harvCountEl = document.getElementById("kpiHarvestCount");
        const profitBadgeEl = document.getElementById("kpiProfitBadge");
        const profitCardEl = document.getElementById("kpiNetProfitCard");
        const dashboardProfitBadge = document.getElementById("cardProfitBadge");

        if (totalExpEl) totalExpEl.textContent = formatCurrency(s.total_expenses);
        if (totalRevEl) totalRevEl.textContent = formatCurrency(s.total_revenue);
        if (netProfitEl) netProfitEl.textContent = formatCurrency(s.net_profit);
        if (profitMarginEl) profitMarginEl.textContent = (s.profit_margin || 0.0).toFixed(1) + "%";

        if (expCountEl) {
            expCountEl.textContent = `${s.count_expenses || 0} ` + t("recorded_entries_label", "recorded entries");
        }
        if (harvCountEl) {
            harvCountEl.textContent = (s.total_harvested_quantity > 0)
                ? `${s.total_harvested_quantity} ` + t("units_sold_label", "units harvested & sold")
                : t("from_actual_sales_label", "From actual sales");
        }

        // Net Profit / Loss Styling & Badge
        if (profitBadgeEl && profitCardEl) {
            if (s.empty_state) {
                profitBadgeEl.textContent = t("status_no_data", "No Data");
                profitBadgeEl.style.background = "#e2e8f0";
                profitBadgeEl.style.color = "#475569";
                profitCardEl.style.borderLeftColor = "#94a3b8";
            } else if (s.is_profitable) {
                profitBadgeEl.textContent = t("profitable_badge", "Profitable");
                profitBadgeEl.style.background = "#dcfce7";
                profitBadgeEl.style.color = "#166534";
                profitCardEl.style.borderLeftColor = "#10b981";
            } else {
                profitBadgeEl.textContent = t("deficit_badge", "Deficit / Loss");
                profitBadgeEl.style.background = "#fee2e2";
                profitBadgeEl.style.color = "#991b1b";
                profitCardEl.style.borderLeftColor = "#ef4444";
            }
        }

        // Dashboard card badge
        if (dashboardProfitBadge) {
            if (!s.empty_state) {
                dashboardProfitBadge.textContent = (s.net_profit >= 0 ? "+" : "") + formatCurrency(s.net_profit);
                dashboardProfitBadge.style.background = s.net_profit >= 0 ? "#10b981" : "#ef4444";
                dashboardProfitBadge.style.display = "inline-block";
            } else {
                dashboardProfitBadge.style.display = "none";
            }
        }

        // 2. Category Breakdown
        renderCategoryBreakdown(data.category_breakdown || []);

        // 3. Crop-wise Profitability
        renderCropProfitability(data.crop_profitability || []);

        // 4. Monthly Trends
        renderMonthlyTrends(data.monthly_trends || []);

        // 5. Seasonal Summary
        renderSeasonalSummary(data.seasonal_summary || []);
    }

    function renderCategoryBreakdown(categories) {
        const container = document.getElementById("categoryBreakdownContainer");
        if (!container) return;

        if (!categories || categories.length === 0) {
            container.innerHTML = `
                <div class="finance-empty-state">
                    <span class="empty-icon">📊</span>
                    <p>${escapeHtml(t("empty_category_breakdown", "No expenses recorded yet. Breakdown will display as you add costs."))}</p>
                </div>
            `;
            return;
        }

        let html = '<div class="cat-breakdown-list">';
        categories.forEach(c => {
            const color = CATEGORY_COLORS[c.category] || "#64748b";
            html += `
                <div class="cat-breakdown-item">
                    <div class="cat-info-row">
                        <span class="cat-name-badge">${escapeHtml(c.category)}</span>
                        <span class="cat-amount-badge">${formatCurrency(c.total_amount)} (${c.percentage}%)</span>
                    </div>
                    <div class="cat-progress-track">
                        <div class="cat-progress-fill" style="width: ${Math.min(c.percentage, 100)}%; background: ${color};"></div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    function renderCropProfitability(crops) {
        const container = document.getElementById("cropProfitabilityContainer");
        if (!container) return;

        if (!crops || crops.length === 0) {
            container.innerHTML = `
                <div class="finance-empty-state">
                    <span class="empty-icon">🌾</span>
                    <p>${escapeHtml(t("empty_crop_profitability", "No crop-specific financial records found."))}</p>
                </div>
            `;
            return;
        }

        let html = '<div class="crop-profit-list">';
        crops.forEach(c => {
            const isProf = c.is_profitable;
            const sign = c.net_profit >= 0 ? "+" : "";
            const profClass = isProf ? "positive" : "negative";

            html += `
                <div class="crop-profit-item">
                    <div>
                        <div class="crop-profit-name">${escapeHtml(c.crop_name)}</div>
                        <div class="crop-profit-sub">
                            ${t("lbl_expenses", "Expenses")}: ${formatCurrency(c.total_expenses)} | ${t("lbl_revenue", "Revenue")}: ${formatCurrency(c.total_revenue)}
                        </div>
                    </div>
                    <div class="crop-profit-val">
                        <div class="profit-val-amount ${profClass}">${sign}${formatCurrency(c.net_profit)}</div>
                        <span class="profit-val-margin ${profClass}">${(c.profit_margin || 0.0).toFixed(1)}%</span>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    function renderMonthlyTrends(trends) {
        const container = document.getElementById("monthlyTrendsContainer");
        if (!container) return;

        if (!trends || trends.length === 0) {
            container.innerHTML = `
                <div class="finance-empty-state">
                    <span class="empty-icon">📅</span>
                    <p>${escapeHtml(t("empty_monthly_trends", "Monthly financial history will show once records are added."))}</p>
                </div>
            `;
            return;
        }

        // SVG Bar visualization
        let maxVal = 1000;
        trends.forEach(m => {
            if (m.expenses > maxVal) maxVal = m.expenses;
            if (m.revenue > maxVal) maxVal = m.revenue;
        });

        const svgHeight = 140;
        const barWidth = 14;
        const groupWidth = 46;
        const totalSvgWidth = Math.max(trends.length * groupWidth, 280);

        let svgHtml = `<svg class="monthly-bar-svg" viewBox="0 0 ${totalSvgWidth} ${svgHeight}">`;
        svgHtml += `<line x1="0" y1="110" x2="${totalSvgWidth}" y2="110" stroke="#cbd5e1" stroke-dasharray="2" />`;

        trends.forEach((m, idx) => {
            const x = idx * groupWidth + 10;
            const expH = Math.max(Math.round((m.expenses / maxVal) * 90), 2);
            const revH = Math.max(Math.round((m.revenue / maxVal) * 90), 2);
            const expY = 110 - expH;
            const revY = 110 - revH;

            // Expense bar (red/rose)
            svgHtml += `<rect x="${x}" y="${expY}" width="${barWidth}" height="${expH}" rx="3" fill="#f87171" title="${escapeHtml(m.month)} Exp: ${formatCurrency(m.expenses)}" />`;
            // Revenue bar (green)
            svgHtml += `<rect x="${x + barWidth + 3}" y="${revY}" width="${barWidth}" height="${revH}" rx="3" fill="#34d399" title="${escapeHtml(m.month)} Rev: ${formatCurrency(m.revenue)}" />`;
            // Month label
            svgHtml += `<text x="${x + 14}" y="128" font-size="10" fill="#64748b" text-anchor="middle">${escapeHtml(m.month.slice(5))}</text>`;
        });

        svgHtml += `</svg>`;

        // Chart Legend
        svgHtml += `
            <div style="display:flex; justify-content:center; gap:16px; margin-top:8px; font-size:12px; color:var(--text-secondary);">
                <span style="display:inline-flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; background:#f87171; border-radius:2px; display:inline-block;"></span> ${escapeHtml(t("lbl_expenses", "Expenses"))}</span>
                <span style="display:inline-flex; align-items:center; gap:4px;"><span style="width:10px; height:10px; background:#34d399; border-radius:2px; display:inline-block;"></span> ${escapeHtml(t("lbl_revenue", "Revenue"))}</span>
            </div>
        `;

        container.innerHTML = svgHtml;
    }

    function renderSeasonalSummary(seasons) {
        const container = document.getElementById("seasonalSummaryContainer");
        if (!container) return;

        if (!seasons || seasons.length === 0) {
            container.innerHTML = `
                <div class="finance-empty-state">
                    <span class="empty-icon">🌦️</span>
                    <p>${escapeHtml(t("empty_seasonal_summary", "No seasonal records logged yet."))}</p>
                </div>
            `;
            return;
        }

        let html = '<div class="season-card-row">';
        seasons.forEach(s => {
            const isProf = s.is_profitable;
            const sign = s.net_profit >= 0 ? "+" : "";
            const profColor = isProf ? "#16a34a" : "#dc2626";

            html += `
                <div class="season-mini-card">
                    <h5>${escapeHtml(s.season)}</h5>
                    <div class="season-stat">
                        <span>${escapeHtml(t("lbl_expenses", "Costs"))}:</span>
                        <strong>${formatCurrency(s.expenses)}</strong>
                    </div>
                    <div class="season-stat">
                        <span>${escapeHtml(t("lbl_revenue", "Sales"))}:</span>
                        <strong>${formatCurrency(s.revenue)}</strong>
                    </div>
                    <div class="season-stat" style="margin-top:6px; border-top:1px dashed #e2e8f0; padding-top:4px;">
                        <span>${escapeHtml(t("lbl_profit", "Profit"))}:</span>
                        <strong style="color:${profColor};">${sign}${formatCurrency(s.net_profit)}</strong>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    /**
     * Load expenses table records
     */
    async function loadExpensesList() {
        const token = getAuthToken();
        if (!token) return;

        const cropFilter = document.getElementById("financeFilterCrop")?.value || "all";
        const catFilter = document.getElementById("financeFilterCategory")?.value || "all";

        const params = new URLSearchParams();
        if (cropFilter && cropFilter !== "all") params.append("crop_id", cropFilter);
        if (catFilter && catFilter !== "all") params.append("category", catFilter);
        params.append("limit", "100");

        try {
            const res = await fetch(`/api/finance/expenses?${params.toString()}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    cachedExpenses = data.expenses || [];
                    renderExpensesTable(cachedExpenses);
                }
            }
        } catch (e) {
            console.error("Failed to load expenses list:", e);
        }
    }

    function renderExpensesTable(expenses) {
        const tbody = document.getElementById("expensesTableBody");
        const emptyState = document.getElementById("expensesEmptyState");
        const table = document.getElementById("expensesTable");
        if (!tbody) return;

        if (!expenses || expenses.length === 0) {
            tbody.innerHTML = "";
            if (table) table.style.display = "none";
            if (emptyState) emptyState.style.display = "block";
            return;
        }

        if (table) table.style.display = "table";
        if (emptyState) emptyState.style.display = "none";

        let html = "";
        expenses.forEach(e => {
            const cropDisplay = e.crop_name
                ? `${escapeHtml(e.crop_name)}${e.farm_name ? " (" + escapeHtml(e.farm_name) + ")" : ""}`
                : `<span style="color:#94a3b8;">${escapeHtml(t("opt_general_overhead", "General Overhead"))}</span>`;

            const qtyDisplay = (e.quantity !== null && e.quantity !== undefined)
                ? `${e.quantity} ${escapeHtml(e.unit || "")}`
                : "-";

            html += `
                <tr id="expenseRow-${e.id}">
                    <td><strong>${escapeHtml(e.expense_date)}</strong></td>
                    <td><span class="badge-finance-cat">${escapeHtml(e.category)}</span></td>
                    <td>${cropDisplay}</td>
                    <td>${escapeHtml(e.description || "-")}</td>
                    <td>${qtyDisplay}</td>
                    <td><strong style="color:#dc2626;">${formatCurrency(e.amount)}</strong></td>
                    <td style="text-align:right; white-space:nowrap;">
                        <button type="button" class="btn-table-action btn-edit-expense" data-id="${e.id}" title="${escapeHtml(t("btn_edit", "Edit"))}">✏️</button>
                        <button type="button" class="btn-table-action delete btn-delete-expense" data-id="${e.id}" title="${escapeHtml(t("btn_delete", "Delete"))}">🗑️</button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
        bindExpenseTableActions();
    }

    function bindExpenseTableActions() {
        document.querySelectorAll(".btn-edit-expense").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = parseInt(btn.getAttribute("data-id"), 10);
                const expense = cachedExpenses.find(e => e.id === id);
                if (expense) openExpenseModal(expense);
            });
        });

        document.querySelectorAll(".btn-delete-expense").forEach(btn => {
            btn.addEventListener("click", async () => {
                const id = parseInt(btn.getAttribute("data-id"), 10);
                await deleteExpense(id);
            });
        });
    }

    /**
     * Load harvests table records
     */
    async function loadHarvestsList() {
        const token = getAuthToken();
        if (!token) return;

        const cropFilter = document.getElementById("financeFilterCrop")?.value || "all";
        const params = new URLSearchParams();
        if (cropFilter && cropFilter !== "all") params.append("crop_id", cropFilter);
        params.append("limit", "100");

        try {
            const res = await fetch(`/api/finance/harvests?${params.toString()}`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success") {
                    cachedHarvests = data.harvests || [];
                    renderHarvestsTable(cachedHarvests);
                }
            }
        } catch (e) {
            console.error("Failed to load harvests list:", e);
        }
    }

    function renderHarvestsTable(harvests) {
        const tbody = document.getElementById("harvestsTableBody");
        const emptyState = document.getElementById("harvestsEmptyState");
        const table = document.getElementById("harvestsTable");
        if (!tbody) return;

        if (!harvests || harvests.length === 0) {
            tbody.innerHTML = "";
            if (table) table.style.display = "none";
            if (emptyState) emptyState.style.display = "block";
            return;
        }

        if (table) table.style.display = "table";
        if (emptyState) emptyState.style.display = "none";

        let html = "";
        harvests.forEach(h => {
            html += `
                <tr id="harvestRow-${h.id}">
                    <td><strong>${escapeHtml(h.harvest_date)}</strong></td>
                    <td><strong>${escapeHtml(h.crop_name)}</strong> ${h.farm_name ? "<small style='color:#64748b;'>(" + escapeHtml(h.farm_name) + ")</small>" : ""}</td>
                    <td>${h.quantity} ${escapeHtml(h.unit)}</td>
                    <td>${formatCurrency(h.price_per_unit)} / ${escapeHtml(h.unit)}</td>
                    <td><strong style="color:#059669;">${formatCurrency(h.total_revenue)}</strong></td>
                    <td>${escapeHtml(h.buyer_name || "-")}</td>
                    <td style="text-align:right; white-space:nowrap;">
                        <button type="button" class="btn-table-action btn-edit-harvest" data-id="${h.id}" title="${escapeHtml(t("btn_edit", "Edit"))}">✏️</button>
                        <button type="button" class="btn-table-action delete btn-delete-harvest" data-id="${h.id}" title="${escapeHtml(t("btn_delete", "Delete"))}">🗑️</button>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
        bindHarvestTableActions();
    }

    function bindHarvestTableActions() {
        document.querySelectorAll(".btn-edit-harvest").forEach(btn => {
            btn.addEventListener("click", () => {
                const id = parseInt(btn.getAttribute("data-id"), 10);
                const harvest = cachedHarvests.find(h => h.id === id);
                if (harvest) openHarvestModal(harvest);
            });
        });

        document.querySelectorAll(".btn-delete-harvest").forEach(btn => {
            btn.addEventListener("click", async () => {
                const id = parseInt(btn.getAttribute("data-id"), 10);
                await deleteHarvest(id);
            });
        });
    }

    /**
     * Modal Management: Expenses
     */
    function openExpenseModal(expense = null) {
        const modal = document.getElementById("expenseModal");
        const title = document.getElementById("expenseModalTitle");
        const form = document.getElementById("expenseForm");
        if (!modal || !form) return;

        form.reset();

        const todayStr = new Date().toISOString().split("T")[0];
        document.getElementById("expenseDateInput").value = todayStr;

        if (expense) {
            title.textContent = t("modal_edit_expense_title", "Edit Farm Expense");
            document.getElementById("expenseId").value = expense.id;
            document.getElementById("expenseCategorySelect").value = expense.category || "";
            document.getElementById("expenseAmountInput").value = expense.amount || "";
            document.getElementById("expenseDateInput").value = expense.expense_date || todayStr;
            document.getElementById("expenseCropSelect").value = expense.crop_id || "";
            document.getElementById("expenseFarmSelect").value = expense.farm_id || "";
            document.getElementById("expenseQuantityInput").value = expense.quantity !== null ? expense.quantity : "";
            document.getElementById("expenseUnitInput").value = expense.unit || "";
            document.getElementById("expenseDescriptionInput").value = expense.description || "";
            document.getElementById("expenseNotesInput").value = expense.notes || "";
        } else {
            title.textContent = t("modal_add_expense_title", "Record Farm Expense");
            document.getElementById("expenseId").value = "";
        }

        modal.classList.add("open");
    }

    function closeExpenseModal() {
        const modal = document.getElementById("expenseModal");
        if (modal) modal.classList.remove("open");
    }

    async function handleExpenseSubmit(e) {
        e.preventDefault();
        const token = getAuthToken();
        if (!token) return;

        const id = document.getElementById("expenseId").value;
        const category = document.getElementById("expenseCategorySelect").value;
        const amount = parseFloat(document.getElementById("expenseAmountInput").value);
        const expense_date = document.getElementById("expenseDateInput").value;
        const crop_id = document.getElementById("expenseCropSelect").value || null;
        const farm_id = document.getElementById("expenseFarmSelect").value || null;
        const rawQty = document.getElementById("expenseQuantityInput").value;
        const quantity = rawQty !== "" ? parseFloat(rawQty) : null;
        const unit = document.getElementById("expenseUnitInput").value.trim() || null;
        const description = document.getElementById("expenseDescriptionInput").value.trim() || null;
        const notes = document.getElementById("expenseNotesInput").value.trim() || null;

        if (!category) {
            alert(t("val_err_category", "Please select an expense category."));
            return;
        }
        if (isNaN(amount) || amount <= 0) {
            alert(t("val_err_amount", "Please enter a valid expense amount greater than 0."));
            return;
        }

        const payload = {
            category,
            amount,
            expense_date,
            crop_id: crop_id ? parseInt(crop_id, 10) : null,
            farm_id: farm_id ? parseInt(farm_id, 10) : null,
            quantity,
            unit,
            description,
            notes
        };

        const url = id ? `/api/finance/expenses/${id}` : "/api/finance/expenses";
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
                closeExpenseModal();
                loadFinancialSummary();
                loadExpensesList();
            } else {
                alert(data.message || t("err_saving_expense", "Could not save expense record."));
            }
        } catch (err) {
            console.error("Save expense error:", err);
            alert(t("err_network", "Network error. Please try again."));
        }
    }

    async function deleteExpense(id) {
        const token = getAuthToken();
        if (!token || !id) return;

        const confirmMsg = t("confirm_delete_expense", "Are you sure you want to delete this expense record?");
        if (!window.confirm(confirmMsg)) return;

        try {
            const res = await fetch(`/api/finance/expenses/${id}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.ok) {
                loadFinancialSummary();
                loadExpensesList();
            }
        } catch (e) {
            console.error("Failed to delete expense:", e);
        }
    }

    /**
     * Modal Management: Harvests
     */
    function openHarvestModal(harvest = null) {
        const modal = document.getElementById("harvestModal");
        const title = document.getElementById("harvestModalTitle");
        const form = document.getElementById("harvestForm");
        const customCropInput = document.getElementById("harvestCropNameInput");
        if (!modal || !form) return;

        form.reset();
        if (customCropInput) customCropInput.style.display = "none";

        const todayStr = new Date().toISOString().split("T")[0];
        document.getElementById("harvestDateInput").value = todayStr;

        if (harvest) {
            title.textContent = t("modal_edit_harvest_title", "Edit Harvest & Sales Record");
            document.getElementById("harvestId").value = harvest.id;
            document.getElementById("harvestCropSelect").value = harvest.crop_id || (harvest.crop_name ? "custom" : "");
            if (!harvest.crop_id && harvest.crop_name && customCropInput) {
                customCropInput.style.display = "block";
                customCropInput.value = harvest.crop_name;
            }
            document.getElementById("harvestFarmSelect").value = harvest.farm_id || "";
            document.getElementById("harvestDateInput").value = harvest.harvest_date || todayStr;
            document.getElementById("harvestQuantityInput").value = harvest.quantity || "";
            document.getElementById("harvestUnitInput").value = harvest.unit || "quintals";
            document.getElementById("harvestPricePerUnitInput").value = harvest.price_per_unit || "";
            document.getElementById("harvestTotalRevenueInput").value = harvest.total_revenue || "";
            document.getElementById("harvestBuyerNameInput").value = harvest.buyer_name || "";
            document.getElementById("harvestNotesInput").value = harvest.notes || "";
        } else {
            title.textContent = t("modal_add_harvest_title", "Record Harvest & Sales");
            document.getElementById("harvestId").value = "";
        }

        modal.classList.add("open");
    }

    function closeHarvestModal() {
        const modal = document.getElementById("harvestModal");
        if (modal) modal.classList.remove("open");
    }

    function recalculateHarvestRevenue() {
        const qty = parseFloat(document.getElementById("harvestQuantityInput").value) || 0.0;
        const price = parseFloat(document.getElementById("harvestPricePerUnitInput").value) || 0.0;
        const revInput = document.getElementById("harvestTotalRevenueInput");
        if (revInput && qty >= 0 && price >= 0) {
            revInput.value = (qty * price).toFixed(2);
        }
    }

    async function handleHarvestSubmit(e) {
        e.preventDefault();
        const token = getAuthToken();
        if (!token) return;

        const id = document.getElementById("harvestId").value;
        const cropSelect = document.getElementById("harvestCropSelect");
        const crop_id = cropSelect.value && cropSelect.value !== "custom" ? parseInt(cropSelect.value, 10) : null;
        let crop_name = "";
        if (crop_id) {
            const selectedOpt = cropSelect.options[cropSelect.selectedIndex];
            crop_name = selectedOpt ? selectedOpt.getAttribute("data-cropname") || selectedOpt.text : "";
        } else {
            crop_name = document.getElementById("harvestCropNameInput").value.trim();
        }

        const farm_id = document.getElementById("harvestFarmSelect").value || null;
        const harvest_date = document.getElementById("harvestDateInput").value;
        const quantity = parseFloat(document.getElementById("harvestQuantityInput").value);
        const unit = document.getElementById("harvestUnitInput").value.trim();
        const price_per_unit = parseFloat(document.getElementById("harvestPricePerUnitInput").value);
        const total_revenue = parseFloat(document.getElementById("harvestTotalRevenueInput").value);
        const buyer_name = document.getElementById("harvestBuyerNameInput").value.trim() || null;
        const notes = document.getElementById("harvestNotesInput").value.trim() || null;

        if (!crop_name) {
            alert(t("val_err_crop_name", "Please select or enter the crop name."));
            return;
        }
        if (isNaN(quantity) || quantity <= 0) {
            alert(t("val_err_quantity", "Please enter a harvest quantity greater than 0."));
            return;
        }
        if (isNaN(price_per_unit) || price_per_unit < 0) {
            alert(t("val_err_price", "Please enter a valid price per unit."));
            return;
        }

        const payload = {
            crop_name,
            crop_id,
            farm_id: farm_id ? parseInt(farm_id, 10) : null,
            harvest_date,
            quantity,
            unit,
            price_per_unit,
            total_revenue: isNaN(total_revenue) ? quantity * price_per_unit : total_revenue,
            buyer_name,
            notes
        };

        const url = id ? `/api/finance/harvests/${id}` : "/api/finance/harvests";
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
                closeHarvestModal();
                loadFinancialSummary();
                loadHarvestsList();
            } else {
                alert(data.message || t("err_saving_harvest", "Could not save harvest record."));
            }
        } catch (err) {
            console.error("Save harvest error:", err);
            alert(t("err_network", "Network error. Please try again."));
        }
    }

    async function deleteHarvest(id) {
        const token = getAuthToken();
        if (!token || !id) return;

        const confirmMsg = t("confirm_delete_harvest", "Are you sure you want to delete this harvest and sales record?");
        if (!window.confirm(confirmMsg)) return;

        try {
            const res = await fetch(`/api/finance/harvests/${id}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.ok) {
                loadFinancialSummary();
                loadHarvestsList();
            }
        } catch (e) {
            console.error("Failed to delete harvest:", e);
        }
    }

    /**
     * Tab Switcher (Expenses vs Harvests)
     */
    function setupTabs() {
        const tabExpBtn = document.getElementById("tabExpensesBtn");
        const tabHarvBtn = document.getElementById("tabHarvestsBtn");
        const expPane = document.getElementById("expensesTabPane");
        const harvPane = document.getElementById("harvestsTabPane");

        if (tabExpBtn && tabHarvBtn) {
            tabExpBtn.addEventListener("click", () => {
                activeTab = "expenses";
                tabExpBtn.classList.add("active");
                tabHarvBtn.classList.remove("active");
                if (expPane) expPane.style.display = "block";
                if (harvPane) harvPane.style.display = "none";
                loadExpensesList();
            });

            tabHarvBtn.addEventListener("click", () => {
                activeTab = "harvests";
                tabHarvBtn.classList.add("active");
                tabExpBtn.classList.remove("active");
                if (harvPane) harvPane.style.display = "block";
                if (expPane) expPane.style.display = "none";
                loadHarvestsList();
            });
        }
    }

    /**
     * Setup Event Listeners
     */
    function initFinanceListeners() {
        // Refresh button
        const refreshBtn = document.getElementById("btnRefreshFinance");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", () => {
                loadContextCrops();
                loadFinancialSummary();
                if (activeTab === "expenses") loadExpensesList();
                else loadHarvestsList();
            });
        }

        // Open Modal buttons
        const openExpBtn = document.getElementById("btnOpenAddExpenseModal");
        if (openExpBtn) {
            openExpBtn.addEventListener("click", () => openExpenseModal());
        }

        const openHarvBtn = document.getElementById("btnOpenAddHarvestModal");
        if (openHarvBtn) {
            openHarvBtn.addEventListener("click", () => openHarvestModal());
        }

        // Modal Form Submits
        const expForm = document.getElementById("expenseForm");
        if (expForm) expForm.addEventListener("submit", handleExpenseSubmit);

        const harvForm = document.getElementById("harvestForm");
        if (harvForm) harvForm.addEventListener("submit", handleHarvestSubmit);

        // Auto revenue calculation on quantity/price changes
        const qtyInp = document.getElementById("harvestQuantityInput");
        const priceInp = document.getElementById("harvestPricePerUnitInput");
        if (qtyInp) qtyInp.addEventListener("input", recalculateHarvestRevenue);
        if (priceInp) priceInp.addEventListener("input", recalculateHarvestRevenue);

        // Custom crop toggle in harvest modal
        const harvCropSel = document.getElementById("harvestCropSelect");
        if (harvCropSel) {
            harvCropSel.addEventListener("change", (e) => {
                const customInp = document.getElementById("harvestCropNameInput");
                if (customInp) {
                    if (e.target.value === "custom") {
                        customInp.style.display = "block";
                        customInp.required = true;
                    } else {
                        customInp.style.display = "none";
                        customInp.required = false;
                    }
                }
            });
        }

        // Inline filters
        const filterCrop = document.getElementById("financeFilterCrop");
        const filterCat = document.getElementById("financeFilterCategory");
        if (filterCrop) {
            filterCrop.addEventListener("change", () => {
                if (activeTab === "expenses") loadExpensesList();
                else loadHarvestsList();
            });
        }
        if (filterCat) {
            filterCat.addEventListener("change", () => {
                if (activeTab === "expenses") loadExpensesList();
            });
        }

        // Modal close buttons
        document.querySelectorAll("#expenseModal .modal-close-btn").forEach(btn => {
            btn.addEventListener("click", closeExpenseModal);
        });
        document.querySelectorAll("#harvestModal .modal-close-btn").forEach(btn => {
            btn.addEventListener("click", closeHarvestModal);
        });

        // Close on backdrop click
        const expModal = document.getElementById("expenseModal");
        if (expModal) {
            expModal.addEventListener("click", (e) => {
                if (e.target === expModal) closeExpenseModal();
            });
        }
        const harvModal = document.getElementById("harvestModal");
        if (harvModal) {
            harvModal.addEventListener("click", (e) => {
                if (e.target === harvModal) closeHarvestModal();
            });
        }

        // Tab switcher
        setupTabs();

        // Listen for language changes
        window.addEventListener("languageChanged", () => {
            populateDropdowns();
            if (summaryData) renderSummary(summaryData);
            if (activeTab === "expenses") renderExpensesTable(cachedExpenses);
            else renderHarvestsTable(cachedHarvests);
        });
    }

    /**
     * Initialization entrypoint
     */
    function init() {
        initFinanceListeners();
        loadContextCrops();
        loadFinancialSummary();
        loadExpensesList();
    }

    // Expose globally
    window.agriSmartFinance = {
        loadSummary: loadFinancialSummary,
        loadExpenses: loadExpensesList,
        loadHarvests: loadHarvestsList,
        openExpenseModal,
        openHarvestModal
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();
