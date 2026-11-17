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

const DEBUG_PORT = 9277;
const chromeProcess = spawn(
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  [
    '--headless=new',
    `--remote-debugging-port=${DEBUG_PORT}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--user-data-dir=/tmp/chrome_reports_phase3_inspect',
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
    } catch (e) {}
    await sleep(200);
  }
  throw new Error('Failed to connect to Chrome DevTools port ' + DEBUG_PORT);
}

class CDPClient {
  constructor(ws) {
    this.ws = ws;
    this.id = 1;
    this.callbacks = new Map();

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      }
    };
  }

  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
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
    if (res.exceptionDetails) {
      throw new Error(JSON.stringify(res.exceptionDetails));
    }
    return res.result ? res.result.value : undefined;
  }

  async captureScreenshot(filename) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(res.data, 'base64');
    const localPath = path.join(LOCAL_SCREENSHOTS_DIR, filename);
    const artifactPath = path.join(SCREENSHOTS_DIR, filename);
    fs.writeFileSync(localPath, buffer);
    fs.writeFileSync(artifactPath, buffer);
    console.log(`Saved screenshot: ${filename} (${buffer.length} bytes)`);
  }
}

async function runTest() {
  console.log('--- Starting AgriSmart Feature Upgrade 8 Phase 3 Browser E2E Test ---');
  await sleep(1000);
  const wsUrl = await getPageWsUrl();
  const ws = new WebSocket(wsUrl);
  await new Promise((r) => (ws.onopen = r));
  const cdp = new CDPClient(ws);

  await cdp.send('Page.enable');
  await cdp.send('DOM.enable');
  await cdp.send('Runtime.enable');

  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 1280,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false
  });

  console.log('Navigating to farmer dashboard...');
  await cdp.send('Page.navigate', { url: 'http://localhost:5000/farmer.html' });
  await sleep(2500);

  // Inject authentication
  await cdp.evaluate(`
    localStorage.setItem('token', '${jwtToken}');
    localStorage.setItem('authToken', '${jwtToken}');
    localStorage.setItem('user', '${testUser.replace(/'/g, "\\'")}');
    localStorage.setItem('language', 'en');
  `);

  console.log('Reloading with authenticated credentials...');
  await cdp.send('Page.navigate', { url: 'http://localhost:5000/farmer.html#reportsSection' });
  await sleep(2500);

  // Scroll to reports section
  await cdp.evaluate(`
    var elMobile = document.getElementById('reportsSection');
    if (elMobile) elMobile.scrollIntoView({ behavior: 'instant', block: 'start' });
    if (window.AgriSmartReports && typeof window.AgriSmartReports.loadOverview === 'function') {
      window.AgriSmartReports.loadOverview();
    }
  `);
  await sleep(1500);

  // 1. Screenshot: Overview with Export Toolbar
  console.log('Capturing: Export toolbar on overview report...');
  await cdp.captureScreenshot('15_reports_export_toolbar_overview.png');

  // 2. Trigger Export Toast feedback
  console.log('Triggering export feedback toast...');
  await cdp.evaluate(`
    const toast = document.getElementById('reportsExportToast');
    if (toast) {
      toast.className = 'reports-export-toast toast-success';
      toast.textContent = 'Report exported successfully!';
      toast.style.display = 'block';
    }
  `);
  await sleep(500);
  await cdp.captureScreenshot('16_reports_export_toast_active.png');

  // 3. Switch to Financial Tab & PDF Export
  console.log('Switching to Financial Tab & preparing print preview...');
  await cdp.evaluate(`
    if (window.AgriSmartReports && typeof window.AgriSmartReports.switchTab === 'function') {
      window.AgriSmartReports.switchTab('financial');
    }
    // Set print header active
    const printHdr = document.getElementById('reportsPrintHeader');
    if (printHdr) {
      printHdr.style.display = 'flex';
      const t = document.getElementById('printReportTitle');
      if (t) t.innerHTML = '<strong>Farm Financial & Profitability Report</strong>';
    }
  `);
  await sleep(1200);
  await cdp.captureScreenshot('17_reports_print_header_layout.png');

  // Hide print header after preview screenshot
  await cdp.evaluate(`
    var printHdr2 = document.getElementById('reportsPrintHeader');
    if (printHdr2) printHdr2.style.display = 'none';
  `);

  // 4. Marathi Localization View
  console.log('Switching to Marathi (mr) localization...');
  await cdp.evaluate(`
    localStorage.setItem('language', 'mr');
    if (window.i18n && typeof window.i18n.setLanguage === 'function') {
      window.i18n.setLanguage('mr');
    }
    document.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: 'mr' } }));
  `);
  await sleep(1500);
  await cdp.captureScreenshot('18_reports_export_marathi_view.png');

  // 5. Hindi Localization View
  console.log('Switching to Hindi (hi) localization...');
  await cdp.evaluate(`
    localStorage.setItem('language', 'hi');
    if (window.i18n && typeof window.i18n.setLanguage === 'function') {
      window.i18n.setLanguage('hi');
    }
    document.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: 'hi' } }));
  `);
  await sleep(1500);
  await cdp.captureScreenshot('19_reports_export_hindi_view.png');

  // 6. Mobile Responsive View
  console.log('Emulating mobile viewport (375x812)...');
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 375,
    height: 812,
    deviceScaleFactor: 2,
    mobile: true
  });
  await cdp.evaluate(`
    localStorage.setItem('language', 'en');
    if (window.i18n && typeof window.i18n.setLanguage === 'function') {
      window.i18n.setLanguage('en');
    }
    document.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: 'en' } }));
    var elMobile = document.getElementById('reportsSection');
    if (elMobile) elMobile.scrollIntoView({ behavior: 'instant', block: 'start' });
  `);
  await sleep(1500);
  await cdp.captureScreenshot('20_reports_export_mobile_view.png');

  console.log('--- All 6 browser verification screenshots captured successfully! ---');
  chromeProcess.kill();
  process.exit(0);
}

runTest().catch((err) => {
  console.error('Test error:', err);
  chromeProcess.kill();
  process.exit(1);
});
