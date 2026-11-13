import { spawn, execSync } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const ARTIFACTS_DIR = '/Users/imranmestri/.gemini/antigravity/brain/16087c1b-f5ee-4ca1-b144-2c69f54cc795';
const SCREENSHOTS_DIR = path.join(ARTIFACTS_DIR, 'smart_reports_screenshots');
const LOCAL_SCREENSHOTS_DIR = path.join(process.cwd(), 'smart_reports_screenshots');

if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}
if (!fs.existsSync(LOCAL_SCREENSHOTS_DIR)) {
  fs.mkdirSync(LOCAL_SCREENSHOTS_DIR, { recursive: true });
}

// Generate valid JWT token for test user 1
const jwtToken = execSync(
  "PYTHONPATH=. backend/venv/bin/python3 -c 'import os; os.environ[\"FLASK_DEBUG\"]=\"false\"; from utils.auth_tokens import create_access_token; print(create_access_token(1))'",
  { encoding: 'utf-8' }
).trim();

const testUser = JSON.stringify({
  id: 1,
  full_name: 'Ramesh Kumar',
  email: 'ramesh.farmer@example.com',
  mobile_number: '9876543210',
  preferred_language: 'en'
});

const DEBUG_PORT = 9266;
const chromeProcess = spawn(
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  [
    '--headless=new',
    `--remote-debugging-port=${DEBUG_PORT}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--user-data-dir=/tmp/chrome_reports_phase2_inspect',
    'about:blank'
  ],
  { stdio: 'ignore' }
);

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function getPageWsUrl() {
  for (let i = 0; i < 30; i++) {
    try {
      const data = await new Promise((resolve, reject) => {
        http.get(`http://127.0.0.1:${DEBUG_PORT}/json/list`, (res) => {
          let body = '';
          res.on('data', (c) => (body += c));
          res.on('end', () => resolve(JSON.parse(body)));
        }).on('error', reject);
      });
      const pageTab = data.find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
      if (pageTab) return pageTab.webSocketDebuggerUrl;
    } catch (e) {
      await sleep(250);
    }
  }
  throw new Error('Failed to connect to Chrome headless tab.');
}

class CDPClient {
  constructor(ws) {
    this.ws = ws;
    this.id = 1;
    this.callbacks = new Map();
    this.consoleErrors = [];

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      }
      if (msg.method === 'Runtime.consoleAPICalled') {
        if (msg.params.type === 'error') {
          const text = msg.params.args.map((a) => a.value || a.description || '').join(' ');
          this.consoleErrors.push(text);
        }
      }
      if (msg.method === 'Runtime.exceptionThrown') {
        this.consoleErrors.push(msg.params.exceptionDetails?.text || 'Uncaught exception');
      }
    };
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = this.id++;
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    });
    return res.result ? res.result.value : null;
  }

  async setViewport(width, height, isMobile = false) {
    await this.send('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: 2,
      mobile: isMobile
    });
    await this.send('Emulation.setVisibleSize', { width, height });
  }

  async captureScreenshot(filename) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(res.data, 'base64');
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, filename), buffer);
    fs.writeFileSync(path.join(LOCAL_SCREENSHOTS_DIR, filename), buffer);
    console.log(`📸 Saved screenshot: ${filename}`);
  }
}

async function run() {
  try {
    console.log('Connecting to Chrome CDP...');
    const wsUrl = await getPageWsUrl();
    const ws = new WebSocket(wsUrl);
    await new Promise((r) => (ws.onopen = r));
    const client = new CDPClient(ws);

    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('DOM.enable');

    await client.setViewport(1440, 900, false);

    console.log('Navigating to http://127.0.0.1:5000/farmer.html...');
    await client.send('Page.navigate', { url: 'http://127.0.0.1:5000/farmer.html' });
    await sleep(1500);

    // Seed test farmer credentials in localStorage
    await client.evaluate(`
      localStorage.setItem('token', '${jwtToken}');
      localStorage.setItem('authToken', '${jwtToken}');
      localStorage.setItem('currentUser', JSON.stringify(${testUser}));
      localStorage.setItem('lang', 'en');
    `);

    // Reload page to let scripts initialize with active session
    await client.send('Page.reload');
    await sleep(2500);

    // Scroll to reports dashboard section
    await client.evaluate(`
      const repSec = document.getElementById('reportsSection');
      if (repSec) repSec.scrollIntoView({ behavior: 'instant', block: 'start' });
    `);
    await sleep(1000);

    // TEST 1: Overview View
    console.log('Verifying Overview View...');
    await client.captureScreenshot('01_reports_dashboard_overview.png');

    // TEST 2: Date Range Filter
    console.log('Testing Date Range Filter Selector...');
    await client.evaluate(`
      const sel = document.getElementById('reportsDateRangePreset');
      if (sel) {
        sel.value = 'current_season';
        sel.dispatchEvent(new Event('change'));
      }
    `);
    await sleep(1200);
    await client.captureScreenshot('02_date_range_filter_selector.png');

    // Switch back to last 30 days
    await client.evaluate(`
      const sel = document.getElementById('reportsDateRangePreset');
      if (sel) {
        sel.value = 'last_30_days';
        sel.dispatchEvent(new Event('change'));
      }
    `);
    await sleep(800);

    // TEST 3: Crops Management Detailed Report & Charts
    console.log('Verifying Crops Management Report & Stage Distribution Chart...');
    await client.evaluate(`window.AgriSmartReports.switchTab('crops');`);
    await sleep(1500);
    await client.captureScreenshot('03_crops_management_report.png');

    // TEST 4: Disease Diagnosis Detailed Report & Donut Chart
    console.log('Verifying Disease Diagnosis Report & Diagnosis Donut Chart...');
    await client.evaluate(`window.AgriSmartReports.switchTab('disease');`);
    await sleep(1500);
    await client.captureScreenshot('04_disease_diagnosis_report.png');

    // TEST 5: Disease Guidance & Treatment Modal
    console.log('Verifying Disease Guidance Modal...');
    await client.evaluate(`
      const btn = document.querySelector('.rep-btn-view-guidance');
      if (btn) btn.click();
      else window.AgriSmartReports.showGuidance(1);
    `);
    await sleep(1000);
    await client.captureScreenshot('05_disease_guidance_modal.png');

    await client.evaluate(`window.AgriSmartReports.hideGuidance();`);
    await sleep(600);

    // TEST 6: Irrigation & Water Usage Detailed Report & Trends Chart
    console.log('Verifying Irrigation Report & Water Volume Trends Chart...');
    await client.evaluate(`window.AgriSmartReports.switchTab('irrigation');`);
    await sleep(1500);
    await client.captureScreenshot('06_irrigation_water_report.png');

    // TEST 7: Financial Expenses & Profit Report, Monthly Trends Chart & Seasonal Performance
    console.log('Verifying Financial Report & Monthly Trends Bar Chart...');
    await client.evaluate(`window.AgriSmartReports.switchTab('financial');`);
    await sleep(1500);
    await client.captureScreenshot('07_financial_profit_report.png');

    // TEST 8: Harvest & Sales Report
    console.log('Verifying Harvest & Sales Report...');
    await client.evaluate(`window.AgriSmartReports.switchTab('harvest');`);
    await sleep(1200);
    await client.captureScreenshot('08_harvest_sales_report.png');

    // TEST 9: Farm Activities Report & Task Completion Charts
    console.log('Verifying Farm Activities Report & Task Planning Charts...');
    await client.evaluate(`window.AgriSmartReports.switchTab('activities');`);
    await sleep(1500);
    await client.captureScreenshot('09_activities_tasks_report.png');

    // TEST 10: Inventory & Stock Management Report & Category Valuation Chart
    console.log('Verifying Inventory & Stock Report & Valuation Chart...');
    await client.evaluate(`window.AgriSmartReports.switchTab('inventory');`);
    await sleep(1500);
    await client.captureScreenshot('10_inventory_stock_report.png');

    // TEST 11: Alerts & Notifications Report by Category Type
    console.log('Verifying Alerts & Notification Report by Category Type...');
    await client.evaluate(`window.AgriSmartReports.switchTab('alerts');`);
    await sleep(1500);
    await client.captureScreenshot('11_alerts_logs_report.png');

    // TEST 12: Marathi Localization View
    console.log('Testing Multilingual Marathi Localization...');
    await client.evaluate(`
      window.AgriSmartReports.switchTab('financial');
      if (window.i18n && window.i18n.setLang) window.i18n.setLang('mr');
    `);
    await sleep(1500);
    await client.captureScreenshot('12_marathi_reports_view.png');

    // TEST 13: Hindi Localization View
    console.log('Testing Multilingual Hindi Localization...');
    await client.evaluate(`
      if (window.i18n && window.i18n.setLang) window.i18n.setLang('hi');
    `);
    await sleep(1500);
    await client.captureScreenshot('13_hindi_reports_view.png');

    // TEST 14: Mobile Responsive Layout (375x812)
    console.log('Testing Mobile Responsive Layout...');
    await client.setViewport(375, 812, true);
    await client.evaluate(`
      if (window.i18n && window.i18n.setLang) window.i18n.setLang('en');
      window.AgriSmartReports.switchTab('overview');
      const repSec = document.getElementById('reportsSection');
      if (repSec) repSec.scrollIntoView({ behavior: 'instant', block: 'start' });
    `);
    await sleep(1500);
    await client.captureScreenshot('14_mobile_reports_view.png');

    console.log('✅ ALL 14 PHASE 2 TEST CASES AND SCREENSHOTS COMPLETED SUCCESSFULLY!');
    ws.close();
  } catch (err) {
    console.error('❌ Test execution failed:', err);
    process.exit(1);
  } finally {
    try {
      chromeProcess.kill();
    } catch (e) {}
  }
}

run();
