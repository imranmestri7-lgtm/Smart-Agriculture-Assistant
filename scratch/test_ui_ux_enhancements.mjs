import { spawn, execSync } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const ARTIFACTS_DIR = '/Users/imranmestri/.gemini/antigravity/brain/16087c1b-f5ee-4ca1-b144-2c69f54cc795';
const SCREENSHOTS_DIR = path.join(ARTIFACTS_DIR, 'ui_enhancement_screenshots');
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

// Generate valid JWT for test farmer user 1
const jwtToken = execSync(
  "PYTHONPATH=. backend/venv/bin/python3 -c 'import os; os.environ[\"FLASK_DEBUG\"]=\"false\"; from utils.auth_tokens import create_access_token; print(create_access_token(1))'",
  { encoding: 'utf-8' }
).trim();

const testUser = JSON.stringify({
  id: 1,
  full_name: 'Ramesh Kumar',
  email: 'ramesh.farmer@example.com',
  mobile_number: '9876543210',
  preferred_language: 'English'
});

const DEBUG_PORT = 9245;
const chromeProcess = spawn(
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  [
    '--headless=new',
    `--remote-debugging-port=${DEBUG_PORT}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--user-data-dir=/tmp/chrome_ui_enhance_inspect',
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
      await sleep(300);
    }
  }
  throw new Error('Could not find Chrome page WebSocket URL');
}

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.id = 1;
    this.callbacks = new Map();
    this.consoleErrors = [];
    this.failedRequests = [];
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
    });

    this.ws.onmessage = (event) => {
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
      if (msg.method === 'Network.responseReceived') {
        const status = msg.params.response.status;
        const url = msg.params.response.url;
        if (status >= 400 && !url.includes('manifest') && !url.includes('favicon')) {
          this.failedRequests.push(`${status} ${url}`);
        }
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

  async captureScreenshot(filepath) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(filepath, Buffer.from(res.data, 'base64'));
  }
}

async function runTests() {
  console.log('--- STARTING AGRISMART UI/UX ENHANCEMENT TEST HARNESS ---');
  await sleep(1500);

  const wsUrl = await getPageWsUrl();
  const cdp = new CDPClient(wsUrl);
  await cdp.connect();

  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Network.enable');

  // Ensure test credentials exist on new document load so authenticated pages never redirect
  await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
    source: `
      try {
        localStorage.setItem('token', '${jwtToken}');
        localStorage.setItem('agriSmartToken', '${jwtToken}');
        localStorage.setItem('user', '${testUser.replace(/'/g, "\\'")}');
      } catch (e) {}
    `
  });

  // Establish session on localhost:5000
  await cdp.send('Page.navigate', { url: 'http://localhost:5000/login' });
  await sleep(1000);
  await cdp.evaluate(`
    localStorage.setItem('agriSmartToken', '${jwtToken}');
    localStorage.setItem('token', '${jwtToken}');
    localStorage.setItem('agriSmartUser', '${testUser.replace(/'/g, "\\'")}');
    localStorage.setItem('user', '${testUser.replace(/'/g, "\\'")}');
    localStorage.setItem('lang', 'en');
  `);

  const pages = [
    { name: 'Landing Page', url: 'http://localhost:5000/index.html', auth: false },
    { name: 'Login Page', url: 'http://localhost:5000/login', auth: false },
    { name: 'Register Page', url: 'http://localhost:5000/register', auth: false },
    { name: 'Farmer Dashboard', url: 'http://localhost:5000/farmer', auth: true },
    { name: 'Plant Disease Detection', url: 'http://localhost:5000/disease', auth: true },
    { name: 'Smart Irrigation', url: 'http://localhost:5000/irrigation', auth: true },
    { name: 'Weather Advisory', url: 'http://localhost:5000/weather', auth: true },
    { name: 'Crop Recommendation', url: 'http://localhost:5000/crop', auth: true },
    { name: 'Offline Fallback', url: 'http://localhost:5000/offline.html', auth: false }
  ];

  const viewports = [
    { name: 'desktop_1440', width: 1440, height: 900, isMobile: false },
    { name: 'tablet_768', width: 768, height: 1024, isMobile: true },
    { name: 'mobile_390', width: 390, height: 844, isMobile: true }
  ];

  const results = {
    pagesTested: 0,
    viewportsTested: 0,
    overflowIssues: [],
    animationChecks: [],
    consoleErrors: [],
    languageSwitches: []
  };

  for (const page of pages) {
    console.log(`\nTesting page: ${page.name} (${page.url})`);

    for (const vp of viewports) {
      await cdp.setViewport(vp.width, vp.height, vp.isMobile);

      cdp.consoleErrors = [];
      cdp.failedRequests = [];

      await cdp.send('Page.navigate', { url: page.url });
      await sleep(1000);

      if (page.auth) {
        await cdp.evaluate(`
          localStorage.setItem('token', '${jwtToken}');
          localStorage.setItem('agriSmartToken', '${jwtToken}');
          localStorage.setItem('user', '${testUser.replace(/'/g, "\\'")}');
        `);
      }

      await sleep(600);

      // Check overflow
      const overflow = await cdp.evaluate(`
        ({
          docWidth: document.documentElement.scrollWidth,
          winWidth: window.innerWidth,
          hasOverflow: document.documentElement.scrollWidth > window.innerWidth,
          diff: document.documentElement.scrollWidth - window.innerWidth
        })
      `);

      if (overflow && overflow.hasOverflow) {
        results.overflowIssues.push(`${page.name} @ ${vp.name}: overflow ${overflow.diff}px`);
        console.warn(`  ⚠️ Overflow on ${vp.name}: ${overflow.diff}px`);
      } else {
        console.log(`  ✅ ${vp.name}: 0px horizontal overflow (docWidth=${overflow?.docWidth}px, winWidth=${overflow?.winWidth}px)`);
      }

      // Check animations
      const animCheck = await cdp.evaluate(`
        ({
          hasScrollReveal: typeof window.AgriSmartAnimations !== 'undefined',
          revealedCount: document.querySelectorAll('.visible, .is-revealed').length,
          cardCount: document.querySelectorAll('.card, .feature-card, .dashboard-card, .info-card, .metric-card').length
        })
      `);

      if (vp.name === 'desktop_1440') {
        results.animationChecks.push(`${page.name}: reveal engine active=${animCheck?.hasScrollReveal}, revealedElements=${animCheck?.revealedCount}`);
      }

      // Capture screenshot
      const shotFile = path.join(SCREENSHOTS_DIR, `${page.name.toLowerCase().replace(/ /g, '_')}_${vp.name}.png`);
      await cdp.captureScreenshot(shotFile);

      results.viewportsTested++;
    }

    results.pagesTested++;
  }

  // Test Language Switch on Farmer Dashboard
  console.log('\nTesting Language Switching on Farmer Dashboard:');
  await cdp.setViewport(1440, 900, false);
  await cdp.send('Page.navigate', { url: 'http://localhost:5000/farmer' });
  await sleep(1000);

  // Switch to Marathi
  await cdp.evaluate(`
    const sel = document.getElementById('lang-select');
    if (sel) {
      sel.value = 'mr';
      sel.dispatchEvent(new Event('change'));
    } else if (window.i18n) {
      window.i18n.setLang('mr');
      window.i18n.applyTranslations();
    }
  `);
  await sleep(700);
  const mrText = await cdp.evaluate(`
    document.querySelector('[data-i18n="card_disease_title"]')?.textContent || 
    document.querySelector('[data-i18n="farming_tools_heading"]')?.textContent || ''
  `);
  console.log(`  Marathi Disease Card Title: "${mrText.trim()}"`);
  results.languageSwitches.push(`Marathi: "${mrText.trim()}"`);
  await cdp.captureScreenshot(path.join(SCREENSHOTS_DIR, 'farmer_dashboard_marathi_enhanced.png'));

  // Switch to Hindi
  await cdp.evaluate(`
    const sel = document.getElementById('lang-select');
    if (sel) {
      sel.value = 'hi';
      sel.dispatchEvent(new Event('change'));
    } else if (window.i18n) {
      window.i18n.setLang('hi');
      window.i18n.applyTranslations();
    }
  `);
  await sleep(700);
  const hiText = await cdp.evaluate(`
    document.querySelector('[data-i18n="card_disease_title"]')?.textContent || 
    document.querySelector('[data-i18n="farming_tools_heading"]')?.textContent || ''
  `);
  console.log(`  Hindi Disease Card Title: "${hiText.trim()}"`);
  results.languageSwitches.push(`Hindi: "${hiText.trim()}"`);
  await cdp.captureScreenshot(path.join(SCREENSHOTS_DIR, 'farmer_dashboard_hindi_enhanced.png'));

  // Switch back to English
  await cdp.evaluate(`
    if (window.i18n && typeof window.i18n.setLanguage === 'function') {
      window.i18n.setLanguage('en');
    }
  `);
  await sleep(500);

  console.log('\n--- UI/UX TEST RESULTS SUMMARY ---');
  console.log(`Pages Tested: ${results.pagesTested}`);
  console.log(`Viewport Configurations Tested: ${results.viewportsTested}`);
  console.log(`Overflow Issues Detected: ${results.overflowIssues.length}`);
  if (results.overflowIssues.length > 0) {
    results.overflowIssues.forEach((iss) => console.log(`  - ${iss}`));
  } else {
    console.log('  ✅ ALL PAGES ACHIEVE PERFECT 0PX HORIZONTAL OVERFLOW ACROSS ALL VIEWPORTS (390px, 768px, 1440px)');
  }

  console.log(`\nAnimation Engine Status:`);
  results.animationChecks.forEach((c) => console.log(`  - ${c}`));

  console.log(`\nLanguage Switching Status:`);
  results.languageSwitches.forEach((l) => console.log(`  - ${l}`));

  chromeProcess.kill('SIGTERM');
  console.log('\n--- FINISHED UI/UX HARNESS ---');
}

runTests().catch((err) => {
  console.error('Test harness failed:', err);
  chromeProcess.kill('SIGTERM');
  process.exit(1);
});
