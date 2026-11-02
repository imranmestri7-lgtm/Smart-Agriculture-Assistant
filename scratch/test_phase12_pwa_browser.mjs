import { spawn, execSync } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const ARTIFACTS_DIR = '/Users/imranmestri/.gemini/antigravity/brain/16087c1b-f5ee-4ca1-b144-2c69f54cc795';
const SCREENSHOTS_DIR = path.join(ARTIFACTS_DIR, 'phase12_screenshots');
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

// Generate valid JWT for user 1
const jwtToken = execSync(
  "PYTHONPATH=. backend/venv/bin/python3 -c 'from utils.auth_tokens import create_access_token; print(create_access_token(1))'",
  { encoding: 'utf-8' }
).trim();

const testUser = JSON.stringify({
  id: 1,
  name: 'Ramesh Kumar',
  email: 'ramesh.farmer@example.com',
  mobile: '9876543210',
  preferred_language: 'en'
});

// Start Chrome
const chromeProcess = spawn(
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  [
    '--headless=new',
    '--remote-debugging-port=9230',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--user-data-dir=/tmp/chrome_phase12_inspect',
    'about:blank'
  ],
  { stdio: 'ignore' }
);

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function getPageWsUrl() {
  for (let i = 0; i < 25; i++) {
    try {
      const data = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9230/json/list', (res) => {
          let body = '';
          res.on('data', (c) => (body += c));
          res.on('end', () => resolve(JSON.parse(body)));
        }).on('error', reject);
      });
      const pageTab = data.find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
      if (pageTab) return pageTab.webSocketDebuggerUrl;
    } catch (e) {
      await sleep(300);
    }
  }
  throw new Error('Failed to find open page tab in Chrome.');
}

class DirectCDPClient {
  constructor(ws) {
    this.ws = ws;
    this.id = 1;
    this.callbacks = new Map();
    this.eventListeners = new Map();

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      } else if (msg.method) {
        const listeners = this.eventListeners.get(msg.method) || [];
        for (const fn of listeners) fn(msg.params);
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

  on(event, fn) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event).push(fn);
  }
}

async function run() {
  try {
    const wsUrl = await getPageWsUrl();
    const ws = new WebSocket(wsUrl);
    await new Promise((resolve) => (ws.onopen = resolve));
    const cdp = new DirectCDPClient(ws);

    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('DOM.enable');
    await cdp.send('Network.enable');

    const consoleErrors = [];
    const netFailures = [];

    cdp.on('Runtime.consoleAPICalled', (params) => {
      if (params.type === 'error') {
        const txt = params.args.map((a) => a.value || a.description || JSON.stringify(a)).join(' ');
        if (!txt.includes('favicon')) {
          consoleErrors.push(`[Console Error] ${txt}`);
        }
      }
    });

    cdp.on('Runtime.exceptionThrown', (params) => {
      console.log("FULL EXCEPTION:", params.exceptionDetails.text, params.exceptionDetails.exception?.description || ""); consoleErrors.push(`[JS Exception] ${params.exceptionDetails.text}`);
    });

    cdp.on('Network.responseReceived', (params) => {
      if (params.response.status >= 400 && !params.response.url.includes('favicon') && !params.response.url.includes('uncached-test')) {
        netFailures.push(`[HTTP ${params.response.status}] ${params.response.url}`);
      }
    });

    console.log('1. Setting desktop viewport (1440x900)...');
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false
    });

    // Step 1: Online Visit & Service Worker Registration
    console.log('2. Navigating to farmer.html while online...');
    await cdp.send('Page.navigate', { url: 'http://127.0.0.1:5000/farmer.html' });
    await sleep(1500);

    await cdp.send('Runtime.evaluate', {
      expression: `
        localStorage.setItem('token', '${jwtToken}');
        localStorage.setItem('agriSmartToken', '${jwtToken}');
        localStorage.setItem('user', '${testUser}');
        localStorage.setItem('agriSmartUser', '${testUser}');
        localStorage.setItem('lang', 'en');
      `
    });

    await cdp.send('Page.navigate', { url: 'http://127.0.0.1:5000/farmer.html' });
    await sleep(2000);

    const swCheck = await cdp.send('Runtime.evaluate', {
      expression: `
        (async () => {
          if (!('serviceWorker' in navigator)) return { supported: false };
          const reg = await navigator.serviceWorker.getRegistration();
          return {
            supported: true,
            hasRegistration: !!reg,
            scope: reg ? reg.scope : null,
            active: !!(reg && reg.active)
          };
        })()
      `,
      awaitPromise: true,
      returnByValue: true
    });
    console.log('Service Worker Status:', swCheck.result.value);

    // Capture online desktop screenshot
    let ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'phase12_pwa_online_desktop.png'), Buffer.from(ss.data, 'base64'));

    // Step 2: Show Install Guide Modal
    console.log('3. Triggering PWA Install Guide Modal...');
    await cdp.send('Runtime.evaluate', {
      expression: `
        if (window.AgriSmartPWA && typeof window.AgriSmartPWA.install === 'function') {
          window.AgriSmartPWA.install();
        }
      `
    });
    await sleep(600);
    ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'phase12_pwa_install_modal.png'), Buffer.from(ss.data, 'base64'));

    // Close install modal
    await cdp.send('Runtime.evaluate', {
      expression: `document.getElementById('btnClosePwaGuide')?.click();`
    });
    await sleep(400);

    // Step 3: Emulate Offline Mode
    console.log('4. Emulating network disconnection (Offline)...');
    await cdp.send('Network.emulateNetworkConditions', {
      offline: true,
      latency: 0,
      downloadThroughput: 0,
      uploadThroughput: 0
    });

    // Dispatch offline event
    await cdp.send('Runtime.evaluate', {
      expression: `window.dispatchEvent(new Event('offline'));`
    });
    await sleep(600);

    const offlineEval = await cdp.send('Runtime.evaluate', {
      expression: `
        (() => {
          const banner = document.getElementById('pwaConnectionBanner');
          return {
            isOffline: window.AgriSmartPWA?.isOffline(),
            bannerVisible: banner ? banner.style.display !== 'none' : false,
            bannerClass: banner?.className,
            bannerText: banner?.querySelector('.banner-text')?.textContent.trim()
          };
        })()
      `,
      returnByValue: true
    });
    console.log('Offline State verification:', offlineEval.result.value);

    // Capture offline banner screenshot in English
    ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'phase12_pwa_offline_banner_desktop.png'), Buffer.from(ss.data, 'base64'));

    // Step 4: Switch to Marathi while offline
    console.log('5. Switching to Marathi while offline...');
    await cdp.send('Runtime.evaluate', {
      expression: `
        if (window.i18n && typeof window.i18n.setLang === 'function') {
          window.i18n.setLang('mr');
          window.i18n.applyTranslations();
        }
      `
    });
    await sleep(500);

    ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'phase12_pwa_offline_marathi_desktop.png'), Buffer.from(ss.data, 'base64'));

    // Step 5: Switch to Hindi while offline
    console.log('6. Switching to Hindi while offline...');
    await cdp.send('Runtime.evaluate', {
      expression: `
        if (window.i18n && typeof window.i18n.setLang === 'function') {
          window.i18n.setLang('hi');
          window.i18n.applyTranslations();
        }
      `
    });
    await sleep(500);

    ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'phase12_pwa_offline_hindi_desktop.png'), Buffer.from(ss.data, 'base64'));

    // Step 6: Test Mobile Viewport (390x844) while offline
    console.log('7. Testing mobile viewport (390x844) while offline...');
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: 390,
      height: 844,
      deviceScaleFactor: 2,
      mobile: true
    });
    await sleep(500);

    const overflowEval = await cdp.send('Runtime.evaluate', {
      expression: `
        (() => {
          const docWidth = document.documentElement.clientWidth;
          const scrollWidth = document.documentElement.scrollWidth;
          return {
            docWidth,
            scrollWidth,
            hasOverflow: scrollWidth > docWidth,
            diff: scrollWidth - docWidth
          };
        })()
      `,
      returnByValue: true
    });
    console.log('Mobile horizontal overflow check:', overflowEval.result.value);

    ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'phase12_pwa_mobile_offline.png'), Buffer.from(ss.data, 'base64'));

    // Step 7: Offline Fallback Page (/offline.html)
    console.log('8. Testing offline fallback page (offline.html)...');
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false
    });
    await cdp.send('Page.navigate', { url: 'http://127.0.0.1:5000/offline.html' });
    await sleep(1000);

    ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'phase12_pwa_offline_fallback_page.png'), Buffer.from(ss.data, 'base64'));

    // Step 8: Test Reconnection and Online Recovery
    console.log('9. Emulating network reconnection (Online)...');

    // Reconnect network
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false,
      latency: 0,
      downloadThroughput: 10000000,
      uploadThroughput: 10000000
    });

    await cdp.send('Page.navigate', { url: 'http://127.0.0.1:5000/farmer.html' });
    await sleep(1500);

    // Queue test action
    await cdp.send('Runtime.evaluate', {
      expression: `
        window.AgriSmartPWA.queueAction({
          type: 'add_farm',
          endpoint: '/api/farms',
          method: 'POST',
          payload: { farm_name: 'Offline Test Farm', location: 'Nashik', total_area: 5, area_unit: 'acre' }
        });
      `
    });

    await cdp.send('Runtime.evaluate', {
      expression: `window.dispatchEvent(new Event('online'));`
    });
    await sleep(800);

    ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(SCREENSHOTS_DIR, 'phase12_pwa_reconnected_desktop.png'), Buffer.from(ss.data, 'base64'));

    console.log('\n--- PHASE 12 BROWSER VERIFICATION SUMMARY ---');
    console.log('Console Errors:', consoleErrors.length, consoleErrors);
    console.log('Network Failures:', netFailures.length, netFailures);
    console.log('Screenshots saved to:', SCREENSHOTS_DIR);

    const savedFiles = fs.readdirSync(SCREENSHOTS_DIR);
    console.log(`Total screenshots generated: ${savedFiles.length}`);
    savedFiles.forEach(f => console.log(` - ${f}`));

  } catch (err) {
    console.error('Browser automation test error:', err);
  } finally {
    try {
      chromeProcess.kill('SIGKILL');
    } catch (e) {}
    process.exit(0);
  }
}

run();
