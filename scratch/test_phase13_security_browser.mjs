import { spawn, execSync } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const ARTIFACTS_DIR = '/Users/imranmestri/.gemini/antigravity/brain/16087c1b-f5ee-4ca1-b144-2c69f54cc795';
const SCREENSHOTS_DIR = path.join(ARTIFACTS_DIR, 'phase13_screenshots');
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

// Generate valid JWT for user 1
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

const chromeProcess = spawn(
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  [
    '--headless=new',
    '--remote-debugging-port=9240',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--user-data-dir=/tmp/chrome_phase13_inspect',
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
        http.get('http://127.0.0.1:9240/json/list', (res) => {
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
      if (this.onEvent) {
        this.onEvent(msg);
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
    console.log(`[Screenshot Saved] -> ${filepath}`);
  }

  close() {
    if (this.ws) this.ws.close();
  }
}

async function runBrowserSecurityAudit() {
  console.log('=== AGRISMART PHASE 13 BROWSER & SECURITY VERIFICATION ===');
  await sleep(1500);

  const wsUrl = await getPageWsUrl();
  const cdp = new CDPClient(wsUrl);
  await cdp.connect();

  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Network.enable');

  const consoleErrors = [];
  cdp.onEvent = (msg) => {
    try {
      if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
        const text = msg.params.args.map((a) => a.value || a.description || '').join(' ');
        if (!text.includes('favicon') && !text.includes('net::ERR_FAILED')) {
          consoleErrors.push(text);
        }
      }
    } catch (e) {}
  };

  // TEST 1: Clean extensionless navigation to /login (Desktop)
  console.log('\n--- Test 1: Clean URL /login (Desktop 1440x900) ---');
  await cdp.setViewport(1440, 900, false);
  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:5000/login' });
  await sleep(1200);

  const loginTitle = await cdp.evaluate('document.title');
  console.log(`Page Title: ${loginTitle}`);
  await cdp.captureScreenshot(path.join(SCREENSHOTS_DIR, 'phase13_clean_url_login_desktop.png'));

  // TEST 2: Invalid Login Attempt (Displays secure message without leaking server errors)
  console.log('\n--- Test 2: Invalid Login Form Validation ---');
  await cdp.evaluate(`
    document.getElementById('emailOption').click();
    document.getElementById('email').value = 'fake.user@example.com';
    document.getElementById('password').value = 'wrongpassword123';
    document.getElementById('emailLoginBtn').click();
  `);
  await sleep(1000);
  const errorMsg = await cdp.evaluate("document.getElementById('message').textContent");
  console.log(`Displayed Security Message: "${errorMsg}"`);
  await cdp.captureScreenshot(path.join(SCREENSHOTS_DIR, 'phase13_invalid_login_error_desktop.png'));

  // TEST 3: Authenticated Dashboard (Farmer page with JWT)
  console.log('\n--- Test 3: Authenticated Farmer Dashboard (Desktop 1440x900) ---');
  await cdp.evaluate(`
    localStorage.setItem('agriSmartToken', '${jwtToken}');
    localStorage.setItem('agriSmartUser', '${testUser.replace(/'/g, "\\'")}');
    localStorage.setItem('lang', 'en');
  `);
  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:5000/farmer' });
  await sleep(1500);

  const farmerName = await cdp.evaluate("document.getElementById('farmerName') ? document.getElementById('farmerName').textContent : 'N/A'");
  console.log(`Authenticated Farmer Header: ${farmerName}`);
  await cdp.captureScreenshot(path.join(SCREENSHOTS_DIR, 'phase13_farmer_dashboard_desktop.png'));

  // TEST 4: Secure Logout (Clears tokens & calls /api/auth/logout)
  console.log('\n--- Test 4: Secure Session Logout Flow ---');
  await cdp.evaluate(`
    // Trigger logout
    const logoutBtn = document.getElementById('logoutButton');
    if (logoutBtn) {
      // Mock confirm dialog
      window.confirm = () => true;
      logoutBtn.click();
    }
  `);
  await sleep(1200);

  const postLogoutToken = await cdp.evaluate("localStorage.getItem('agriSmartToken')");
  console.log(`Token cleared after logout: ${postLogoutToken === null}`);
  await cdp.captureScreenshot(path.join(SCREENSHOTS_DIR, 'phase13_post_logout_redirect.png'));

  // TEST 5: Mobile Viewport & Horizontal Overflow (Mobile 390x844)
  console.log('\n--- Test 5: Mobile Viewport (iPhone 14 / 390x844) ---');
  await cdp.setViewport(390, 844, true);
  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:5000/login' });
  await sleep(1200);

  const overflow = await cdp.evaluate(`
    Math.max(0, document.documentElement.scrollWidth - window.innerWidth)
  `);
  console.log(`Mobile Horizontal Overflow: ${overflow}px`);
  await cdp.captureScreenshot(path.join(SCREENSHOTS_DIR, 'phase13_mobile_login_390px.png'));

  // TEST 6: Disease Detection Page Security & Form (Desktop)
  console.log('\n--- Test 6: Disease Detection Page (Desktop 1440x900) ---');
  await cdp.setViewport(1440, 900, false);
  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:5000/disease' });
  await sleep(1200);
  await cdp.captureScreenshot(path.join(SCREENSHOTS_DIR, 'phase13_disease_detection_desktop.png'));

  // Summary
  console.log('\n=== BROWSER SECURITY AUDIT SUMMARY ===');
  console.log(`Console Errors: ${consoleErrors.length}`);
  if (consoleErrors.length > 0) {
    console.log(`Errors: ${JSON.stringify(consoleErrors)}`);
  }
  console.log(`Mobile Horizontal Overflow: ${overflow}px (Goal: 0px)`);
  console.log(`Screenshots Captured: 6 in ${SCREENSHOTS_DIR}`);

  cdp.close();
  chromeProcess.kill();
}

runBrowserSecurityAudit().catch((err) => {
  console.error('Browser Security Audit Failed:', err);
  chromeProcess.kill();
  process.exit(1);
});
