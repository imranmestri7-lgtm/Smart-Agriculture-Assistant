/**
 * Smart Agriculture Assistant (AgriSmart)
 * Feature Upgrade 8: Centralized Smart Farm Reports Dashboard
 * Client-Side Controller (js/reports.js)
 */

(function () {
    'use strict';

    // State
    const state = {
        currentTab: 'overview',
        datePreset: 'last_30_days',
        startDate: '',
        endDate: '',
        farmId: 'all',
        cropId: 'all',
        farms: [],
        crops: [],
        activeRangeDisplay: 'Last 30 Days'
    };

    // Helper: Auth Token
    function getToken() {
        return localStorage.getItem('token') || localStorage.getItem('authToken') || '';
    }

    // Helper: Headers
    function getHeaders() {
        const token = getToken();
        return {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        };
    }

    // Helper: Translation lookup with fallback
    function t(key, fallback) {
        if (typeof window.i18n !== 'undefined' && typeof window.i18n.t === 'function') {
            const val = window.i18n.t(key);
            if (val && val !== key) return val;
        }
        return fallback || key;
    }

    // Helper: Format Currency (INR)
    function formatINR(amount) {
        const num = Number(amount) || 0;
        return '₹' + num.toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // Helper: Format Date
    function formatDateDisplay(dateStr) {
        if (!dateStr) return '-';
        try {
            const d = new Date(dateStr);
            if (isNaN(d.getTime())) return String(dateStr);
            return d.toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (e) {
            return String(dateStr);
        }
    }

    // Helper: Escape HTML
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Build URL query params for reports API
    function buildQueryParams() {
        const params = new URLSearchParams();
        params.set('range', state.datePreset);
        if (state.datePreset === 'custom') {
            if (state.startDate) params.set('start_date', state.startDate);
            if (state.endDate) params.set('end_date', state.endDate);
        }
        if (state.farmId && state.farmId !== 'all') {
            params.set('farm_id', state.farmId);
        }
        if (state.cropId && state.cropId !== 'all') {
            params.set('crop_id', state.cropId);
        }
        return params.toString();
    }

    // Update active date range label
    function updateDateRangeLabel(rangeObj) {
        const labelEl = document.getElementById('reportsActiveRangeLabel');
        const periodLabelEl = document.getElementById('repFinPeriodLabel');
        if (!labelEl) return;

        let labelText = '';
        if (state.datePreset === 'today') {
            labelText = t('opt_range_today', 'Today');
        } else if (state.datePreset === 'last_7_days') {
            labelText = t('opt_range_last_7_days', 'Last 7 Days');
        } else if (state.datePreset === 'last_30_days') {
            labelText = t('opt_range_last_30_days', 'Last 30 Days');
        } else if (state.datePreset === 'current_month') {
            labelText = t('opt_range_current_month', 'Current Month');
        } else if (state.datePreset === 'previous_month') {
            labelText = t('opt_range_previous_month', 'Previous Month');
        } else if (state.datePreset === 'current_season') {
            labelText = t('opt_range_current_season', 'Current Season');
        } else if (state.datePreset === 'all') {
            labelText = t('opt_range_all', 'All Recorded Time');
        } else if (state.datePreset === 'custom') {
            const s = state.startDate || '';
            const e = state.endDate || '';
            labelText = s && e ? `${s} - ${e}` : t('opt_range_custom', 'Custom Range');
        }

        if (rangeObj && rangeObj.start && rangeObj.end && state.datePreset !== 'all') {
            labelText += ` (${rangeObj.start} to ${rangeObj.end})`;
        }

        state.activeRangeDisplay = labelText;
        labelEl.textContent = labelText;
        if (periodLabelEl) {
            periodLabelEl.textContent = labelText;
        }
    }

    // -------------------------------------------------------------
    // Initial Filter Context Loader
    // -------------------------------------------------------------
    async function loadFilterContext() {
        const token = getToken();
        if (!token) return;

        try {
            const res = await fetch('/api/reports/filters-context', {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            state.farms = data.farms || [];
            state.crops = data.crops || [];

            populateFarmFilter();
            populateCropFilter();
        } catch (err) {
            console.error('[Reports] Error loading filter context:', err);
        }
    }

    function populateFarmFilter() {
        const farmSelect = document.getElementById('reportsFarmFilter');
        if (!farmSelect) return;

        const currentVal = farmSelect.value;
        farmSelect.innerHTML = `<option value="all" data-i18n="opt_all_farms">${t('opt_all_farms', 'All Farms')}</option>`;

        state.farms.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.id;
            opt.textContent = `${f.farm_name} (${f.location || ''})`;
            farmSelect.appendChild(opt);
        });

        if (currentVal && Array.from(farmSelect.options).some(o => o.value === currentVal)) {
            farmSelect.value = currentVal;
        }
    }

    function populateCropFilter() {
        const cropSelect = document.getElementById('reportsCropFilter');
        if (!cropSelect) return;

        const currentVal = cropSelect.value;
        cropSelect.innerHTML = `<option value="all" data-i18n="opt_all_crops">${t('opt_all_crops', 'All Crops')}</option>`;

        // Filter crops by selected farm if specific farm is chosen
        const filteredCrops = (state.farmId && state.farmId !== 'all')
            ? state.crops.filter(c => String(c.farm_id) === String(state.farmId))
            : state.crops;

        filteredCrops.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.crop_name + (c.variety ? ` - ${c.variety}` : '');
            cropSelect.appendChild(opt);
        });

        if (currentVal && Array.from(cropSelect.options).some(o => o.value === currentVal)) {
            cropSelect.value = currentVal;
        } else {
            cropSelect.value = 'all';
            state.cropId = 'all';
        }
    }

    // -------------------------------------------------------------
    // Tab Navigation
    // -------------------------------------------------------------
    function switchTab(tabKey) {
        state.currentTab = tabKey;

        // Update button states
        const tabBtns = document.querySelectorAll('.reports-tab-btn');
        tabBtns.forEach(btn => {
            const isActive = btn.getAttribute('data-tab') === tabKey;
            btn.classList.toggle('active', isActive);
            btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });

        // Update view panes
        const panes = document.querySelectorAll('.report-view-pane');
        panes.forEach(pane => {
            pane.classList.remove('active');
            pane.style.display = 'none';
        });

        const activePaneId = 'viewPane' + tabKey.charAt(0).toUpperCase() + tabKey.slice(1);
        const activePane = document.getElementById(activePaneId);
        if (activePane) {
            activePane.classList.add('active');
            activePane.style.display = 'block';
        }

        // Trigger loader for selected tab
        loadCurrentTab();
    }

    function loadCurrentTab() {
        switch (state.currentTab) {
            case 'overview':
                loadOverviewReport();
                break;
            case 'crops':
                loadCropsReport();
                break;
            case 'disease':
                loadDiseaseReport();
                break;
            case 'irrigation':
                loadIrrigationReport();
                break;
            case 'financial':
                loadFinancialReport();
                break;
            case 'harvest':
                loadHarvestReport();
                break;
            case 'activities':
                loadActivitiesReport();
                break;
            case 'inventory':
                loadInventoryReport();
                break;
            case 'alerts':
                loadAlertsReport();
                break;
            default:
                loadOverviewReport();
                break;
        }
    }

    // -------------------------------------------------------------
    // VIEW 1: FARM OVERVIEW
    // -------------------------------------------------------------
    async function loadOverviewReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/overview?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const o = data.overview || {};
            const farms = o.farms || {};
            const crops = o.crops || {};
            const fin = o.finances || {};
            const tasks = o.tasks || {};
            const water = o.water || {};
            const disease = o.disease || {};
            const inv = o.inventory || {};
            const alerts = o.alerts || {};

            // 1. Top KPI Summary Grid
            const elFarms = document.getElementById('repOverviewFarms');
            const elArea = document.getElementById('repOverviewArea');
            if (elFarms) elFarms.textContent = farms.total_farms || 0;
            if (elArea) elArea.textContent = `${Number(farms.total_area || 0).toFixed(1)} Acres`;

            const elActiveCrops = document.getElementById('repOverviewActiveCrops');
            const elTotalCrops = document.getElementById('repOverviewTotalCrops');
            if (elActiveCrops) elActiveCrops.textContent = crops.active_crops || 0;
            if (elTotalCrops) elTotalCrops.textContent = `${crops.total_crops || 0} Total Registered`;

            const elNetProfit = document.getElementById('repOverviewNetProfit');
            const elMargin = document.getElementById('repOverviewMargin');
            const netVal = Number(fin.net_profit || 0);
            if (elNetProfit) {
                elNetProfit.textContent = formatINR(netVal);
                elNetProfit.style.color = netVal > 0 ? '#16a34a' : (netVal < 0 ? '#dc2626' : '#1e293b');
            }
            if (elMargin) elMargin.textContent = `${Number(fin.profit_margin || 0).toFixed(1)}% Margin`;

            const elCompTasks = document.getElementById('repOverviewCompletedTasks');
            const elPendTasks = document.getElementById('repOverviewPendingTasks');
            if (elCompTasks) elCompTasks.textContent = tasks.completed_tasks || 0;
            if (elPendTasks) elPendTasks.textContent = `${tasks.pending_tasks || 0} Pending / Overdue`;

            // 2. Financial Highlight Card
            const elTotRev = document.getElementById('repOverviewTotalRevenue');
            const elTotExp = document.getElementById('repOverviewTotalExpenses');
            const elBadgeBar = document.getElementById('repProfitBadgeBar');
            const elBadgeText = document.getElementById('repProfitBadgeText');
            if (elTotRev) elTotRev.textContent = formatINR(fin.total_revenue || 0);
            if (elTotExp) elTotExp.textContent = formatINR(fin.total_expenses || 0);

            if (elBadgeBar && elBadgeText) {
                elBadgeBar.classList.remove('profit', 'loss');
                if (netVal > 0) {
                    elBadgeBar.classList.add('profit');
                    elBadgeText.textContent = `Profitable (${formatINR(netVal)} Net Gain)`;
                } else if (netVal < 0) {
                    elBadgeBar.classList.add('loss');
                    elBadgeText.textContent = `Loss Position (${formatINR(Math.abs(netVal))} Net Deficit)`;
                } else {
                    elBadgeText.textContent = `Balanced (${formatINR(0)})`;
                }
            }

            // 3. Resources Highlight Card
            const elInvCount = document.getElementById('repOverviewInventoryItems');
            const elLowStock = document.getElementById('repOverviewLowStock');
            if (elInvCount) elInvCount.textContent = inv.total_items || 0;
            if (elLowStock) elLowStock.textContent = `${inv.low_stock_items || 0} Low Stock`;

            const elWaterApp = document.getElementById('repOverviewWaterApplied');
            const elWaterSav = document.getElementById('repOverviewWaterSaved');
            if (elWaterApp) elWaterApp.textContent = `${Number(water.total_water_applied_mm || 0).toFixed(1)} mm`;
            if (elWaterSav) elWaterSav.textContent = `${Number(water.water_saved_mm || 0).toFixed(1)} mm Saved`;

            const elDisScans = document.getElementById('repOverviewDiseaseScans');
            const elDisConf = document.getElementById('repOverviewScanConfidence');
            if (elDisScans) elDisScans.textContent = disease.total_scans || 0;
            if (elDisConf) elDisConf.textContent = `${Number(disease.avg_confidence || 0).toFixed(1)}% Avg Conf`;

            const elAlertsTot = document.getElementById('repOverviewAlertsTotal');
            const elAlertsUrg = document.getElementById('repOverviewUrgentAlerts');
            if (elAlertsTot) elAlertsTot.textContent = alerts.total_alerts || 0;
            if (elAlertsUrg) elAlertsUrg.textContent = `${alerts.urgent_alerts || 0} Urgent`;

            // 4. Recent Activities Highlight Table
            renderOverviewActivities(data.recent_activities || []);
        } catch (err) {
            console.error('[Reports] Error loading overview report:', err);
        }
    }

    function renderOverviewActivities(activities) {
        const tbody = document.getElementById('repOverviewActivitiesBody');
        const emptyDiv = document.getElementById('repOverviewActivitiesEmpty');
        const table = document.getElementById('repOverviewActivitiesTable');
        if (!tbody) return;

        if (!activities || activities.length === 0) {
            tbody.innerHTML = '';
            if (emptyDiv) emptyDiv.style.display = 'block';
            if (table) table.style.display = 'none';
            return;
        }

        if (emptyDiv) emptyDiv.style.display = 'none';
        if (table) table.style.display = 'table';

        let html = '';
        activities.slice(0, 5).forEach(act => {
            const dateStr = formatDateDisplay(act.scheduled_date || act.completion_date);
            const statusClass = act.status === 'completed' ? 'pill-green' : (act.status === 'in_progress' ? 'pill-amber' : 'pill-blue');
            const cropFarm = [act.crop_name, act.farm_name].filter(Boolean).join(' • ') || '-';

            html += `
                <tr>
                    <td>${escapeHtml(dateStr)}</td>
                    <td><strong>${escapeHtml(act.title)}</strong></td>
                    <td><span class="metric-pill pill-gray">${escapeHtml(act.category || 'General')}</span></td>
                    <td>${escapeHtml(cropFarm)}</td>
                    <td><span class="metric-pill ${statusClass}">${escapeHtml(act.status || 'pending')}</span></td>
                </tr>
            `;
        });
        tbody.innerHTML = html;
    }

    // -------------------------------------------------------------
    // VIEW 2: CROPS MANAGEMENT REPORT
    // -------------------------------------------------------------
    async function loadCropsReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/crops?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const sum = data.summary || {};
            const elTot = document.getElementById('repCropTotal');
            const elAct = document.getElementById('repCropActive');
            const elHarv = document.getElementById('repCropHarvested');
            const elArea = document.getElementById('repCropArea');

            if (elTot) elTot.textContent = sum.total_crops || 0;
            if (elAct) elAct.textContent = sum.active_crops || 0;
            if (elHarv) elHarv.textContent = sum.harvested_crops || 0;
            if (elArea) elArea.textContent = `${Number(sum.total_area || 0).toFixed(1)} Acres`;

            const crops = data.crops || [];
            const tbody = document.getElementById('repCropsBody');
            const emptyDiv = document.getElementById('repCropsEmpty');
            const table = document.getElementById('repCropsTable');

            if (!tbody) return;

            if (crops.length === 0) {
                tbody.innerHTML = '';
                if (emptyDiv) emptyDiv.style.display = 'block';
                if (table) table.style.display = 'none';
                return;
            }

            if (emptyDiv) emptyDiv.style.display = 'none';
            if (table) table.style.display = 'table';

            let html = '';
            crops.forEach(c => {
                const planting = formatDateDisplay(c.planting_date);
                const harvest = formatDateDisplay(c.expected_harvest_date);
                const area = `${Number(c.cultivated_area || 0).toFixed(1)} ${c.area_unit || 'Acres'}`;
                const statusPill = c.growth_status === 'harvested' ? 'pill-blue' : 'pill-green';

                html += `
                    <tr>
                        <td><strong>${escapeHtml(c.crop_name)}</strong></td>
                        <td>${escapeHtml(c.variety || '-')}</td>
                        <td>${escapeHtml(c.farm_name || '-')}</td>
                        <td>${escapeHtml(planting)}</td>
                        <td>${escapeHtml(harvest)}</td>
                        <td>${escapeHtml(area)}</td>
                        <td><span class="metric-pill ${statusPill}">${escapeHtml(c.growth_status || 'growing')}</span></td>
                        <td>${c.days_in_ground !== null && c.days_in_ground !== undefined ? c.days_in_ground + ' days' : '-'}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } catch (err) {
            console.error('[Reports] Error loading crops report:', err);
        }
    }

    // -------------------------------------------------------------
    // VIEW 3: DISEASE DIAGNOSIS REPORT
    // -------------------------------------------------------------
    async function loadDiseaseReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/disease?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const sum = data.summary || {};
            const elTot = document.getElementById('repDiseaseTotalScans');
            const elHlth = document.getElementById('repDiseaseHealthy');
            const elDis = document.getElementById('repDiseaseDiseased');
            const elRate = document.getElementById('repDiseaseHealthRate');

            if (elTot) elTot.textContent = sum.total_scans || 0;
            if (elHlth) elHlth.textContent = sum.healthy_scans || 0;
            if (elDis) elDis.textContent = sum.diseased_scans || 0;
            if (elRate) elRate.textContent = `${Number(sum.healthy_ratio || 0).toFixed(1)}%`;

            const scans = data.scans || [];
            const tbody = document.getElementById('repDiseaseBody');
            const emptyDiv = document.getElementById('repDiseaseEmpty');
            const table = document.getElementById('repDiseaseTable');

            if (!tbody) return;

            if (scans.length === 0) {
                tbody.innerHTML = '';
                if (emptyDiv) emptyDiv.style.display = 'block';
                if (table) table.style.display = 'none';
                return;
            }

            if (emptyDiv) emptyDiv.style.display = 'none';
            if (table) table.style.display = 'table';

            let html = '';
            scans.forEach(s => {
                const date = formatDateDisplay(s.diagnosis_date);
                const isHealthy = s.is_healthy;
                const statusPill = isHealthy ? 'pill-green' : 'pill-red';
                const statusText = isHealthy ? 'Healthy' : 'Action Required';
                const conf = Number(s.confidence || 0).toFixed(1) + '%';

                html += `
                    <tr>
                        <td>${escapeHtml(date)}</td>
                        <td><strong>${escapeHtml(s.crop_name || 'Plant Sample')}</strong></td>
                        <td>${escapeHtml(s.predicted_class || 'Unknown')}</td>
                        <td><strong>${conf}</strong></td>
                        <td><span class="metric-pill ${statusPill}">${statusText}</span></td>
                        <td><small>${escapeHtml(s.notes || '-')}</small></td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } catch (err) {
            console.error('[Reports] Error loading disease report:', err);
        }
    }

    // -------------------------------------------------------------
    // VIEW 4: IRRIGATION & WATER REPORT
    // -------------------------------------------------------------
    async function loadIrrigationReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/irrigation?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const sum = data.summary || {};
            const elTot = document.getElementById('repIrrigTotal');
            const elApp = document.getElementById('repIrrigApplied');
            const elSav = document.getElementById('repIrrigSaved');
            const elMoist = document.getElementById('repIrrigMoisture');

            if (elTot) elTot.textContent = sum.total_irrigation_events || 0;
            if (elApp) elApp.textContent = `${Number(sum.total_water_applied_mm || 0).toFixed(1)} mm`;
            if (elSav) elSav.textContent = `${Number(sum.total_water_saved_mm || 0).toFixed(1)} mm`;
            if (elMoist) elMoist.textContent = `${Number(sum.avg_soil_moisture || 0).toFixed(1)}%`;

            const records = data.records || [];
            const tbody = document.getElementById('repIrrigBody');
            const emptyDiv = document.getElementById('repIrrigEmpty');
            const table = document.getElementById('repIrrigTable');

            if (!tbody) return;

            if (records.length === 0) {
                tbody.innerHTML = '';
                if (emptyDiv) emptyDiv.style.display = 'block';
                if (table) table.style.display = 'none';
                return;
            }

            if (emptyDiv) emptyDiv.style.display = 'none';
            if (table) table.style.display = 'table';

            let html = '';
            records.forEach(r => {
                const date = formatDateDisplay(r.created_at);
                const recStatus = r.recommendation_status || (r.is_irrigation_needed ? 'Needed' : 'Adequate');
                const pillClass = r.is_irrigation_needed ? 'pill-blue' : 'pill-green';

                html += `
                    <tr>
                        <td>${escapeHtml(date)}</td>
                        <td><strong>${escapeHtml(r.crop || '-')}</strong></td>
                        <td>${r.soil_moisture !== null ? Number(r.soil_moisture).toFixed(1) + '%' : '-'}</td>
                        <td>${escapeHtml(r.soil_type || '-')}</td>
                        <td>${escapeHtml(r.growth_stage || '-')}</td>
                        <td>${Number(r.water_quantity_mm || 0).toFixed(1)} mm</td>
                        <td class="text-success font-weight-bold">${Number(r.water_saved_mm || 0).toFixed(1)} mm</td>
                        <td><span class="metric-pill ${pillClass}">${escapeHtml(recStatus)}</span></td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } catch (err) {
            console.error('[Reports] Error loading irrigation report:', err);
        }
    }

    // -------------------------------------------------------------
    // VIEW 5: EXPENSES & PROFIT REPORT
    // -------------------------------------------------------------
    async function loadFinancialReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/financial?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const sum = data.summary || {};
            const elRev = document.getElementById('repFinRevenue');
            const elExp = document.getElementById('repFinExpenses');
            const elNet = document.getElementById('repFinNet');
            const elMar = document.getElementById('repFinMargin');

            const revVal = Number(sum.total_revenue || 0);
            const expVal = Number(sum.total_expenses || 0);
            const netVal = Number(sum.net_profit || 0);
            const marVal = Number(sum.profit_margin || 0);

            if (elRev) elRev.textContent = formatINR(revVal);
            if (elExp) elExp.textContent = formatINR(expVal);
            if (elNet) {
                elNet.textContent = formatINR(netVal);
                elNet.style.color = netVal > 0 ? '#16a34a' : (netVal < 0 ? '#dc2626' : '#1e293b');
            }
            if (elMar) elMar.textContent = `${marVal.toFixed(1)}%`;

            // Breakdown by category
            renderCategoryBreakdown(data.expense_by_category || [], expVal);

            // Crop profitability breakdown
            renderCropProfitability(data.crop_profitability || []);

            // Expenses ledger table
            const expenses = data.expenses || [];
            const tbody = document.getElementById('repExpenseBody');
            const emptyDiv = document.getElementById('repExpenseEmpty');
            const table = document.getElementById('repExpenseTable');

            if (!tbody) return;

            if (expenses.length === 0) {
                tbody.innerHTML = '';
                if (emptyDiv) emptyDiv.style.display = 'block';
                if (table) table.style.display = 'none';
                return;
            }

            if (emptyDiv) emptyDiv.style.display = 'none';
            if (table) table.style.display = 'table';

            let html = '';
            expenses.forEach(e => {
                const date = formatDateDisplay(e.expense_date);
                const cropFarm = [e.crop_name, e.farm_name].filter(Boolean).join(' • ') || '-';

                html += `
                    <tr>
                        <td>${escapeHtml(date)}</td>
                        <td><span class="metric-pill pill-gray">${escapeHtml(e.category || 'General')}</span></td>
                        <td>${escapeHtml(cropFarm)}</td>
                        <td>${escapeHtml(e.description || '-')}</td>
                        <td><strong class="text-danger">${formatINR(e.amount)}</strong></td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } catch (err) {
            console.error('[Reports] Error loading financial report:', err);
        }
    }

    function renderCategoryBreakdown(categories, totalExp) {
        const container = document.getElementById('repExpenseCategoriesList');
        if (!container) return;

        if (!categories || categories.length === 0) {
            container.innerHTML = `<p class="text-muted" style="font-size:13px; text-align:center; padding:12px;">No category expenses in this period.</p>`;
            return;
        }

        let html = '';
        categories.forEach(c => {
            const pct = totalExp > 0 ? Math.min(100, (Number(c.total_amount) / totalExp) * 100).toFixed(1) : 0;
            html += `
                <div class="breakdown-item">
                    <div class="breakdown-label-row">
                        <span>${escapeHtml(c.category)}</span>
                        <span class="breakdown-val">${formatINR(c.total_amount)} (${pct}%)</span>
                    </div>
                    <div class="breakdown-bar-track">
                        <div class="breakdown-bar-fill warning" style="width: ${pct}%"></div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    function renderCropProfitability(crops) {
        const container = document.getElementById('repCropProfitabilityList');
        if (!container) return;

        if (!crops || crops.length === 0) {
            container.innerHTML = `<p class="text-muted" style="font-size:13px; text-align:center; padding:12px;">No crop-linked financial records in this period.</p>`;
            return;
        }

        let html = '';
        crops.forEach(c => {
            const net = Number(c.net_profit || 0);
            const netClass = net >= 0 ? 'text-success' : 'text-danger';
            html += `
                <div class="breakdown-item" style="padding: 6px 0; border-bottom: 1px dashed #e2e8f0;">
                    <div class="breakdown-label-row">
                        <strong>${escapeHtml(c.crop_name)}</strong>
                        <span class="${netClass}">Net: ${formatINR(net)}</span>
                    </div>
                    <div style="font-size:11px; color:#64748b; display:flex; justify-content:space-between; margin-top:2px;">
                        <span>Rev: ${formatINR(c.revenue)}</span>
                        <span>Exp: ${formatINR(c.expenses)}</span>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    }

    // -------------------------------------------------------------
    // VIEW 6: HARVEST & SALES REPORT
    // -------------------------------------------------------------
    async function loadHarvestReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/financial?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const harvests = data.harvests || [];
            const tbody = document.getElementById('repHarvestBody');
            const emptyDiv = document.getElementById('repHarvestEmpty');
            const table = document.getElementById('repHarvestTable');

            if (!tbody) return;

            if (harvests.length === 0) {
                tbody.innerHTML = '';
                if (emptyDiv) emptyDiv.style.display = 'block';
                if (table) table.style.display = 'none';
                return;
            }

            if (emptyDiv) emptyDiv.style.display = 'none';
            if (table) table.style.display = 'table';

            let html = '';
            harvests.forEach(h => {
                const date = formatDateDisplay(h.harvest_date);
                const qty = `${Number(h.quantity || 0).toLocaleString()} ${h.unit || 'kg'}`;
                const unitPrice = h.price_per_unit ? formatINR(h.price_per_unit) : '-';
                const rev = formatINR(h.total_revenue || 0);

                html += `
                    <tr>
                        <td>${escapeHtml(date)}</td>
                        <td><strong>${escapeHtml(h.crop_name || '-')}</strong></td>
                        <td>${escapeHtml(h.farm_name || '-')}</td>
                        <td>${escapeHtml(qty)}</td>
                        <td>${unitPrice}</td>
                        <td class="text-success font-weight-bold">${rev}</td>
                        <td>${escapeHtml(h.buyer_name || '-')}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } catch (err) {
            console.error('[Reports] Error loading harvest report:', err);
        }
    }

    // -------------------------------------------------------------
    // VIEW 7: FARM ACTIVITIES REPORT
    // -------------------------------------------------------------
    async function loadActivitiesReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/activities?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const sum = data.summary || {};
            const elTot = document.getElementById('repActTotal');
            const elComp = document.getElementById('repActCompleted');
            const elPend = document.getElementById('repActPending');
            const elOver = document.getElementById('repActOverdue');

            if (elTot) elTot.textContent = sum.total_activities || 0;
            if (elComp) elComp.textContent = sum.completed || 0;
            if (elPend) elPend.textContent = sum.pending || 0;
            if (elOver) elOver.textContent = sum.overdue || 0;

            const activities = data.activities || [];
            const tbody = document.getElementById('repActivitiesBody');
            const emptyDiv = document.getElementById('repActivitiesEmpty');
            const table = document.getElementById('repActivitiesTable');

            if (!tbody) return;

            if (activities.length === 0) {
                tbody.innerHTML = '';
                if (emptyDiv) emptyDiv.style.display = 'block';
                if (table) table.style.display = 'none';
                return;
            }

            if (emptyDiv) emptyDiv.style.display = 'none';
            if (table) table.style.display = 'table';

            let html = '';
            activities.forEach(a => {
                const date = formatDateDisplay(a.scheduled_date);
                const cropFarm = [a.crop_name, a.farm_name].filter(Boolean).join(' • ') || '-';
                const prioPill = a.priority === 'high' ? 'pill-red' : (a.priority === 'medium' ? 'pill-amber' : 'pill-blue');
                const statusPill = a.status === 'completed' ? 'pill-green' : (a.status === 'in_progress' ? 'pill-amber' : 'pill-gray');

                html += `
                    <tr>
                        <td>${escapeHtml(date)}</td>
                        <td><strong>${escapeHtml(a.title)}</strong></td>
                        <td><span class="metric-pill pill-gray">${escapeHtml(a.category || 'General')}</span></td>
                        <td>${escapeHtml(cropFarm)}</td>
                        <td><span class="metric-pill ${prioPill}">${escapeHtml(a.priority || 'normal')}</span></td>
                        <td><span class="metric-pill ${statusPill}">${escapeHtml(a.status || 'pending')}</span></td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } catch (err) {
            console.error('[Reports] Error loading activities report:', err);
        }
    }

    // -------------------------------------------------------------
    // VIEW 8: INVENTORY & STOCK REPORT
    // -------------------------------------------------------------
    async function loadInventoryReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/inventory?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const sum = data.summary || {};
            const elTot = document.getElementById('repInvTotalItems');
            const elVal = document.getElementById('repInvValuation');
            const elLow = document.getElementById('repInvLowStock');
            const elExp = document.getElementById('repInvExpiring');

            if (elTot) elTot.textContent = sum.total_items || 0;
            if (elVal) elVal.textContent = formatINR(sum.total_valuation || 0);
            if (elLow) elLow.textContent = sum.low_stock_items || 0;
            if (elExp) elExp.textContent = sum.expiring_soon_items || 0;

            // Render items table
            const items = data.items || [];
            const tbody = document.getElementById('repInventoryBody');
            const emptyDiv = document.getElementById('repInventoryEmpty');
            const table = document.getElementById('repInventoryTable');

            if (tbody) {
                if (items.length === 0) {
                    tbody.innerHTML = '';
                    if (emptyDiv) emptyDiv.style.display = 'block';
                    if (table) table.style.display = 'none';
                } else {
                    if (emptyDiv) emptyDiv.style.display = 'none';
                    if (table) table.style.display = 'table';

                    let html = '';
                    items.forEach(it => {
                        const stock = `${Number(it.quantity).toLocaleString()} ${it.unit || ''}`;
                        const unitPrice = formatINR(it.purchase_price || 0);
                        const val = formatINR(it.total_value || 0);
                        const reorder = `${it.min_threshold || 0} ${it.unit || ''}`;

                        let statusPill = 'pill-green';
                        let statusText = 'Normal';
                        if (it.is_low_stock) {
                            statusPill = 'pill-amber';
                            statusText = 'Low Stock';
                        }
                        if (it.is_expired) {
                            statusPill = 'pill-red';
                            statusText = 'Expired';
                        }

                        html += `
                            <tr>
                                <td><strong>${escapeHtml(it.item_name)}</strong></td>
                                <td><span class="metric-pill pill-gray">${escapeHtml(it.category || 'Supplies')}</span></td>
                                <td>${escapeHtml(stock)}</td>
                                <td>${unitPrice}</td>
                                <td><strong>${val}</strong></td>
                                <td>${escapeHtml(reorder)}</td>
                                <td><span class="metric-pill ${statusPill}">${statusText}</span></td>
                            </tr>
                        `;
                    });
                    tbody.innerHTML = html;
                }
            }

            // Render movements table
            const movements = data.movements || [];
            const movBody = document.getElementById('repMovementsBody');
            const movEmpty = document.getElementById('repMovementsEmpty');
            const movTable = document.getElementById('repMovementsTable');

            if (movBody) {
                if (movements.length === 0) {
                    movBody.innerHTML = '';
                    if (movEmpty) movEmpty.style.display = 'block';
                    if (movTable) movTable.style.display = 'none';
                } else {
                    if (movEmpty) movEmpty.style.display = 'none';
                    if (movTable) movTable.style.display = 'table';

                    let html = '';
                    movements.forEach(m => {
                        const date = formatDateDisplay(m.movement_date);
                        const cropFarm = [m.crop_name, m.farm_name].filter(Boolean).join(' • ') || '-';
                        const typePill = m.movement_type === 'in' ? 'pill-green' : (m.movement_type === 'out' ? 'pill-red' : 'pill-blue');
                        const qty = `${Number(m.quantity).toLocaleString()} ${m.unit || ''}`;

                        html += `
                            <tr>
                                <td>${escapeHtml(date)}</td>
                                <td><strong>${escapeHtml(m.item_name || '-')}</strong></td>
                                <td><span class="metric-pill ${typePill}">${escapeHtml(m.movement_type.toUpperCase())}</span></td>
                                <td>${escapeHtml(qty)}</td>
                                <td>${escapeHtml(cropFarm)}</td>
                                <td><small>${escapeHtml(m.reason || m.notes || '-')}</small></td>
                            </tr>
                        `;
                    });
                    movBody.innerHTML = html;
                }
            }
        } catch (err) {
            console.error('[Reports] Error loading inventory report:', err);
        }
    }

    // -------------------------------------------------------------
    // VIEW 9: ALERTS & NOTIFICATIONS REPORT
    // -------------------------------------------------------------
    async function loadAlertsReport() {
        const token = getToken();
        if (!token) return;

        try {
            const qs = buildQueryParams();
            const res = await fetch(`/api/reports/alerts?${qs}`, {
                method: 'GET',
                headers: getHeaders()
            });
            if (!res.ok) return;

            const data = await res.json();
            if (!data.success) return;

            updateDateRangeLabel(data.date_range);

            const sum = data.summary || {};
            const elTot = document.getElementById('repAlertsTotal');
            const elUnread = document.getElementById('repAlertsUnread');
            const elUrg = document.getElementById('repAlertsUrgent');
            const elRead = document.getElementById('repAlertsRead');

            if (elTot) elTot.textContent = sum.total_alerts || 0;
            if (elUnread) elUnread.textContent = sum.unread_alerts || 0;
            if (elUrg) elUrg.textContent = sum.high_severity_alerts || 0;
            if (elRead) elRead.textContent = sum.read_alerts || 0;

            const alerts = data.alerts || [];
            const tbody = document.getElementById('repAlertsTable');
            const emptyDiv = document.getElementById('repAlertsEmpty');
            const table = document.getElementById('repAlertsTable');

            if (!tbody) return;

            if (alerts.length === 0) {
                tbody.innerHTML = '';
                if (emptyDiv) emptyDiv.style.display = 'block';
                if (table) table.style.display = 'none';
                return;
            }

            if (emptyDiv) emptyDiv.style.display = 'none';
            if (table) table.style.display = 'table';

            let html = '';
            alerts.forEach(al => {
                const date = formatDateDisplay(al.created_at);
                const sevPill = al.severity === 'high' ? 'pill-red' : (al.severity === 'medium' ? 'pill-amber' : 'pill-blue');
                const statusPill = al.is_read ? 'pill-green' : 'pill-amber';
                const statusText = al.is_read ? 'Reviewed' : 'Unread';

                html += `
                    <tr>
                        <td>${escapeHtml(date)}</td>
                        <td><span class="metric-pill pill-gray">${escapeHtml(al.category || 'Alert')}</span></td>
                        <td><span class="metric-pill ${sevPill}">${escapeHtml(al.severity || 'info')}</span></td>
                        <td><strong>${escapeHtml(al.title)}</strong></td>
                        <td><small>${escapeHtml(al.message || '')}</small></td>
                        <td><span class="metric-pill ${statusPill}">${statusText}</span></td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        } catch (err) {
            console.error('[Reports] Error loading alerts report:', err);
        }
    }

    // -------------------------------------------------------------
    // Event Setup
    // -------------------------------------------------------------
    function setupEventListeners() {
        // Preset Date Range Dropdown
        const presetSelect = document.getElementById('reportsDateRangePreset');
        const customGroup = document.getElementById('reportsCustomDateGroup');
        if (presetSelect) {
            presetSelect.addEventListener('change', function () {
                state.datePreset = this.value;
                if (this.value === 'custom') {
                    if (customGroup) customGroup.style.display = 'flex';
                } else {
                    if (customGroup) customGroup.style.display = 'none';
                    loadCurrentTab();
                }
            });
        }

        // Apply Custom Dates Button
        const btnApplyCustom = document.getElementById('btnApplyCustomDate');
        if (btnApplyCustom) {
            btnApplyCustom.addEventListener('click', function () {
                const startInp = document.getElementById('reportsStartDate');
                const endInp = document.getElementById('reportsEndDate');
                state.startDate = startInp ? startInp.value : '';
                state.endDate = endInp ? endInp.value : '';

                if (state.startDate && state.endDate && state.startDate > state.endDate) {
                    alert('Start date must be earlier than or equal to End date');
                    return;
                }
                loadCurrentTab();
            });
        }

        // Farm Filter Dropdown
        const farmSelect = document.getElementById('reportsFarmFilter');
        if (farmSelect) {
            farmSelect.addEventListener('change', function () {
                state.farmId = this.value;
                populateCropFilter();
                loadCurrentTab();
            });
        }

        // Crop Filter Dropdown
        const cropSelect = document.getElementById('reportsCropFilter');
        if (cropSelect) {
            cropSelect.addEventListener('change', function () {
                state.cropId = this.value;
                loadCurrentTab();
            });
        }

        // Refresh Button
        const btnRefresh = document.getElementById('btnRefreshReports');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', function () {
                loadCurrentTab();
            });
        }

        // Category Tab Buttons
        const tabBtns = document.querySelectorAll('.reports-tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                const tabKey = this.getAttribute('data-tab');
                if (tabKey) switchTab(tabKey);
            });
        });

        // Multilingual Language Change Listener
        document.addEventListener('languageChanged', function () {
            populateFarmFilter();
            populateCropFilter();
            updateDateRangeLabel();
        });
    }

    // -------------------------------------------------------------
    // Bootstrapper
    // -------------------------------------------------------------
    function init() {
        if (!document.getElementById('reportsSection')) return;
        setupEventListeners();
        loadFilterContext();
        loadOverviewReport();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for debugging
    window.AgriSmartReports = {
        state: state,
        switchTab: switchTab,
        reload: loadCurrentTab,
        loadOverview: loadOverviewReport
    };
})();
