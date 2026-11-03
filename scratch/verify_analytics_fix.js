const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const user1Token = execSync("backend/venv/bin/python3 -c \"import sys; sys.path.insert(0, 'backend'); from utils.auth_tokens import create_access_token; print(create_access_token(1))\"").toString().trim();
const emptyToken = execSync("backend/venv/bin/python3 -c \"import sys; sys.path.insert(0, 'backend'); from utils.auth_tokens import create_access_token; print(create_access_token(99999))\"").toString().trim();

console.log('User 1 Token length:', user1Token.length);
console.log('Empty User Token length:', emptyToken.length);

const outDir = '/Users/imranmestri/.gemini/antigravity/brain/16087c1b-f5ee-4ca1-b144-2c69f54cc795/analytics_inspection';
if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
}

async function run() {
    const browser = await puppeteer.launch({
        executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 950 });

    const consoleLogs = [];
    page.on('console', msg => consoleLogs.push({ type: msg.type(), text: msg.text() }));

    // Helper to log in a user
    async function loginAs(token, userObj, lang = 'en') {
        await page.goto('http://127.0.0.1:5000/login.html', { waitUntil: 'domcontentloaded' });
        await page.evaluate((tok, u, l) => {
            localStorage.setItem('agriSmartToken', tok);
            localStorage.setItem('token', tok);
            localStorage.setItem('agriSmartUser', JSON.stringify(u));
            localStorage.setItem('lang', l);
        }, token, userObj, lang);
        await page.goto('http://127.0.0.1:5000/farmer.html', { waitUntil: 'networkidle2' });
        await new Promise(r => setTimeout(r, 1500));
    }

    // -------------------------------------------------------------
    // TEST 1: POPULATED USER (User 1) - English
    // -------------------------------------------------------------
    console.log('\n--- TEST 1: POPULATED USER (English) ---');
    await loginAs(user1Token, { id: 1, name: 'Farmer Imran', email: 'farmer@example.com', role: 'farmer' }, 'en');

    await page.evaluate(() => {
        const el = document.getElementById('cropAnalyticsPanel');
        if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
    });
    await new Promise(r => setTimeout(r, 600));

    const populatedCropState = await page.evaluate(() => {
        const c1 = document.getElementById('cropDistByNameChart');
        const c2 = document.getElementById('cropGrowthStageChart');
        const c3 = document.getElementById('cropsPerFarmChart');
        const c4 = document.getElementById('cropTimelineList');

        return {
            c1_has_bars: !!c1?.querySelector('.bar-row'),
            c1_bars_count: c1?.querySelectorAll('.bar-row').length,
            c2_has_donut: !!c2?.querySelector('.svg-donut-svg'),
            c3_has_bars: !!c3?.querySelector('.bar-row'),
            c3_bars_count: c3?.querySelectorAll('.bar-row').length,
            c4_has_cards: !!c4?.querySelector('.timeline-card'),
            c4_cards_count: c4?.querySelectorAll('.timeline-card').length,
            c1_empty: !!c1?.querySelector('.empty-chart-state'),
            metrics: {
                totalFarms: document.getElementById('metricTotalFarms')?.textContent,
                totalCrops: document.getElementById('metricTotalCrops')?.textContent,
                totalDiagnoses: document.getElementById('metricTotalDiagnoses')?.textContent,
                totalIrrigations: document.getElementById('metricTotalIrrigations')?.textContent
            }
        };
    });

    console.log('Populated User Crop Analytics State:\n', JSON.stringify(populatedCropState, null, 2));
    await page.screenshot({ path: path.join(outDir, '01_populated_crops_en.png') });

    // -------------------------------------------------------------
    // TEST 2: POPULATED USER - Disease & Irrigation Panels
    // -------------------------------------------------------------
    console.log('\n--- TEST 2: POPULATED USER (Disease & Irrigation) ---');
    await page.evaluate(() => {
        const el = document.getElementById('diseaseAnalyticsPanel');
        if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
    });
    await new Promise(r => setTimeout(r, 600));
    await page.screenshot({ path: path.join(outDir, '02_populated_disease_en.png') });

    await page.evaluate(() => {
        const el = document.getElementById('irrigationAnalyticsPanel');
        if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
    });
    await new Promise(r => setTimeout(r, 600));
    await page.screenshot({ path: path.join(outDir, '03_populated_irrigation_en.png') });

    // -------------------------------------------------------------
    // TEST 3: EMPTY USER (No records) - English
    // -------------------------------------------------------------
    console.log('\n--- TEST 3: EMPTY USER (English Empty States) ---');
    await loginAs(emptyToken, { id: 99999, name: 'New Farmer', email: 'new@example.com', role: 'farmer' }, 'en');

    await page.evaluate(() => {
        const el = document.getElementById('cropAnalyticsPanel');
        if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
    });
    await new Promise(r => setTimeout(r, 600));

    const emptyCropStateEn = await page.evaluate(() => {
        const getEmpty = (id) => {
            const el = document.getElementById(id);
            const emptyEl = el ? el.querySelector('.empty-chart-state') : null;
            return {
                found: !!emptyEl,
                icon: emptyEl?.querySelector('.empty-icon')?.textContent?.trim() || '',
                text: emptyEl?.querySelector('p')?.textContent?.trim() || ''
            };
        };
        return {
            cropDist: getEmpty('cropDistByNameChart'),
            growthStages: getEmpty('cropGrowthStageChart'),
            cropsPerFarm: getEmpty('cropsPerFarmChart'),
            timeline: getEmpty('cropTimelineList'),
            diseaseBreakdown: getEmpty('diseaseHealthBreakdownChart'),
            topDiseases: getEmpty('topDiseasesChart'),
            irrigationActivity: getEmpty('irrigationActivityChart'),
            irrigationSummary: getEmpty('cropIrrigationSummaryTable')
        };
    });

    console.log('Empty User (EN) Empty States:\n', JSON.stringify(emptyCropStateEn, null, 2));
    await page.screenshot({ path: path.join(outDir, '04_empty_crops_en.png') });

    // -------------------------------------------------------------
    // TEST 4: EMPTY USER - Marathi Translation Switch
    // -------------------------------------------------------------
    console.log('\n--- TEST 4: EMPTY USER - Switch to Marathi ---');
    await page.evaluate(() => {
        if (window.i18n && typeof window.i18n.setLang === 'function') {
            window.i18n.setLang('mr');
        }
    });
    await new Promise(r => setTimeout(r, 600));

    const emptyCropStateMr = await page.evaluate(() => {
        const getEmpty = (id) => {
            const el = document.getElementById(id);
            const emptyEl = el ? el.querySelector('.empty-chart-state') : null;
            return {
                icon: emptyEl?.querySelector('.empty-icon')?.textContent?.trim() || '',
                text: emptyEl?.querySelector('p')?.textContent?.trim() || ''
            };
        };
        return {
            cropDist: getEmpty('cropDistByNameChart'),
            growthStages: getEmpty('cropGrowthStageChart'),
            cropsPerFarm: getEmpty('cropsPerFarmChart'),
            timeline: getEmpty('cropTimelineList')
        };
    });

    console.log('Empty User (MR) Empty States:\n', JSON.stringify(emptyCropStateMr, null, 2));
    await page.screenshot({ path: path.join(outDir, '05_empty_crops_mr.png') });

    // -------------------------------------------------------------
    // TEST 5: EMPTY USER - Hindi Translation Switch
    // -------------------------------------------------------------
    console.log('\n--- TEST 5: EMPTY USER - Switch to Hindi ---');
    await page.evaluate(() => {
        if (window.i18n && typeof window.i18n.setLang === 'function') {
            window.i18n.setLang('hi');
        }
    });
    await new Promise(r => setTimeout(r, 600));

    const emptyCropStateHi = await page.evaluate(() => {
        const getEmpty = (id) => {
            const el = document.getElementById(id);
            const emptyEl = el ? el.querySelector('.empty-chart-state') : null;
            return {
                icon: emptyEl?.querySelector('.empty-icon')?.textContent?.trim() || '',
                text: emptyEl?.querySelector('p')?.textContent?.trim() || ''
            };
        };
        return {
            cropDist: getEmpty('cropDistByNameChart'),
            growthStages: getEmpty('cropGrowthStageChart'),
            cropsPerFarm: getEmpty('cropsPerFarmChart'),
            timeline: getEmpty('cropTimelineList')
        };
    });

    console.log('Empty User (HI) Empty States:\n', JSON.stringify(emptyCropStateHi, null, 2));
    await page.screenshot({ path: path.join(outDir, '06_empty_crops_hi.png') });

    // -------------------------------------------------------------
    // TEST 6: POPULATED USER - Marathi Translation
    // -------------------------------------------------------------
    console.log('\n--- TEST 6: POPULATED USER (Marathi) ---');
    await loginAs(user1Token, { id: 1, name: 'Farmer Imran', email: 'farmer@example.com', role: 'farmer' }, 'mr');

    await page.evaluate(() => {
        const el = document.getElementById('cropAnalyticsPanel');
        if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
    });
    await new Promise(r => setTimeout(r, 600));
    await page.screenshot({ path: path.join(outDir, '07_populated_crops_mr.png') });

    console.log('\nConsole warnings/errors during test:');
    const errs = consoleLogs.filter(c => c.type === 'error');
    console.log(`Errors count: ${errs.length}`);
    if (errs.length > 0) {
        console.log(errs);
    }

    await browser.close();
    console.log('\nAll tests complete! Screenshots generated in', outDir);
}

run().catch(err => {
    console.error('Test execution error:', err);
    process.exit(1);
});
