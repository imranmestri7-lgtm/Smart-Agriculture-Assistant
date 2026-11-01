import { spawn, execSync } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const ARTIFACTS_DIR = '/Users/imranmestri/.gemini/antigravity/brain/16087c1b-f5ee-4ca1-b144-2c69f54cc795';
const SCREENSHOTS_DIR = path.join(ARTIFACTS_DIR, 'phase11_screenshots');
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
    '--remote-debugging-port=9229',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--user-data-dir=/tmp/chrome_phase11_inspect',
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
        http.get('http://127.0.0.1:9229/json/list', (res) => {
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
      consoleErrors.push(`[JS Exception] ${params.exceptionDetails.text}`);
    });

    cdp.on('Network.responseReceived', (params) => {
      if (params.response.status >= 400 && !params.response.url.includes('favicon')) {
        netFailures.push(`[HTTP ${params.response.status}] ${params.response.url}`);
      }
    });

    const pages = [
      { name: 'index', path: 'index.html', auth: false },
      { name: 'login', path: 'login.html', auth: false },
      { name: 'register', path: 'register.html', auth: false },
      { name: 'farmer', path: 'farmer.html', auth: true },
      { name: 'disease', path: 'disease.html', auth: true },
      { name: 'crop', path: 'crop.html', auth: false },
      { name: 'weather', path: 'weather.html', auth: false },
      { name: 'irrigation', path: 'irrigation.html', auth: false }
    ];

    const results = {};

    for (const page of pages) {
      console.log(`\n================ Testing ${page.name} (${page.path}) ================`);
      results[page.name] = {};

      // 1. Desktop English (1440x900)
      await cdp.send('Emulation.setDeviceMetricsOverride', {
        width: 1440,
        height: 900,
        deviceScaleFactor: 1,
        mobile: false
      });

      await cdp.send('Page.navigate', { url: `http://127.0.0.1:5000/${page.path}` });
      await sleep(1200);

      if (page.auth) {
        await cdp.send('Runtime.evaluate', {
          expression: `
            localStorage.setItem('token', '${jwtToken}');
            localStorage.setItem('agriSmartToken', '${jwtToken}');
            localStorage.setItem('user', '${testUser}');
            localStorage.setItem('agriSmartUser', '${testUser}');
          `
        });
      }

      // Switch language function helper
      const switchLang = async (langCode) => {
        return await cdp.send('Runtime.evaluate', {
          expression: `
            (() => {
              if (window.i18n && typeof window.i18n.setLang === 'function') {
                window.i18n.setLang('${langCode}');
                window.i18n.applyTranslations();
                return { success: true, currentLang: window.i18n.currentLang, htmlLang: document.documentElement.lang };
              }
              return { success: false };
            })()
          `,
          returnByValue: true
        });
      };

      // 1. Desktop English
      await switchLang('en');
      await sleep(400);
      let ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
      fs.writeFileSync(path.join(SCREENSHOTS_DIR, `phase11_${page.name}_desktop_en.png`), Buffer.from(ss.data, 'base64'));

      // 2. Desktop Marathi
      const mrRes = await switchLang('mr');
      await sleep(500);
      ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
      fs.writeFileSync(path.join(SCREENSHOTS_DIR, `phase11_${page.name}_desktop_mr.png`), Buffer.from(ss.data, 'base64'));

      // 3. Desktop Hindi
      const hiRes = await switchLang('hi');
      await sleep(500);
      ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
      fs.writeFileSync(path.join(SCREENSHOTS_DIR, `phase11_${page.name}_desktop_hi.png`), Buffer.from(ss.data, 'base64'));

      // 4. Mobile Viewport (390x844)
      await cdp.send('Emulation.setDeviceMetricsOverride', {
        width: 390,
        height: 844,
        deviceScaleFactor: 2,
        mobile: true
      });
      await switchLang('mr'); // capture mobile in Marathi
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

      ss = await cdp.send('Page.captureScreenshot', { format: 'png' });
      fs.writeFileSync(path.join(SCREENSHOTS_DIR, `phase11_${page.name}_mobile_mr.png`), Buffer.from(ss.data, 'base64'));

      results[page.name] = {
        mrSwitched: mrRes.result.value?.success,
        hiSwitched: hiRes.result.value?.success,
        overflow: overflowEval.result.value
      };
      console.log(`Page ${page.name} verified:`, results[page.name]);
    }

    console.log('\n--- PHASE 11 BROWSER VERIFICATION SUMMARY ---');
    console.log('Console Errors:', consoleErrors.length, consoleErrors);
    console.log('Network Failures:', netFailures.length, netFailures);
    console.log('Screenshots saved to:', SCREENSHOTS_DIR);

    // List generated screenshots
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
