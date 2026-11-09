/**
 * AgriSmart - Progressive Web App Service Worker (Phase 12)
 * Provides offline navigation, asset caching, stale-while-revalidate,
 * safe API response caching for read-only farmer dashboards,
 * and friendly fallback to offline.html.
 */

const CACHE_VERSION = 'v2';
const STATIC_CACHE = `agrismart-static-${CACHE_VERSION}`;
const PAGES_CACHE = `agrismart-pages-${CACHE_VERSION}`;
const DATA_CACHE = `agrismart-data-${CACHE_VERSION}`;

const STATIC_ASSETS = [
    '/index.html',
    '/farmer.html',
    '/disease.html',
    '/crop.html',
    '/weather.html',
    '/irrigation.html',
    '/login.html',
    '/register.html',
    '/offline.html',
    '/manifest.json',
    '/style.css',
    '/css/common.css',
    '/css/farmer.css',
    '/css/disease.css',
    '/css/crop.css',
    '/css/irrigation.css',
    '/css/weather.css',
    '/css/home.css',
    '/js/i18n.js',
    '/js/farmer.js',
    '/js/farm_crop.js',
    '/js/analytics.js',
    '/js/notifications.js',
    '/js/iot_monitoring.js',
    '/js/disease.js',
    '/js/crop.js',
    '/js/irrigation.js',
    '/js/weather.js',
    '/js/login.js',
    '/js/register.js',
    '/js/mobile-nav.js',
    '/js/pwa.js',
    '/images/icons/icon-72x72.png',
    '/images/icons/icon-96x96.png',
    '/images/icons/icon-128x128.png',
    '/images/icons/icon-144x144.png',
    '/images/icons/icon-152x152.png',
    '/images/icons/icon-180x180.png',
    '/images/icons/icon-192x192.png',
    '/images/icons/icon-384x384.png',
    '/images/icons/icon-512x512.png',
    '/images/icons/icon-maskable-192x192.png',
    '/images/icons/icon-maskable-512x512.png',
    '/favicon.ico'
];

// Sensitive or real-time endpoints that MUST NEVER be cached
const NEVER_CACHE_PATTERNS = [
    /\/api\/auth\/login/,
    /\/api\/auth\/register/,
    /\/api\/auth\/otp/,
    /\/api\/auth\/logout/,
    /\/api\/auth\//,
    /\/api\/iot\/ingest/,
    /\/api\/iot\/telemetry\/ingest/,
    /\/api\/disease\/predict/,
    /\/api\/disease\/image\//
];

// Safe read-only API endpoints eligible for network-first offline caching
const SAFE_API_CACHE_PATTERNS = [
    /\/api\/farms$/,
    /\/api\/crops/,
    /\/api\/analytics\/overview/,
    /\/api\/analytics\/filter-options/,
    /\/api\/notifications\/unread-count/,
    /\/api\/iot\/overview/
];

/**
 * 1. Install Event: Pre-cache core static shell
 */
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return Promise.allSettled(
                STATIC_ASSETS.map((asset) => {
                    return cache.add(asset).catch((err) => {
                        console.warn(`[SW] Pre-caching failed for ${asset}:`, err.message);
                    });
                })
            );
        }).then(() => self.skipWaiting())
    );
});

/**
 * 2. Activate Event: Clean up outdated caches
 */
self.addEventListener('activate', (event) => {
    const expectedCaches = [STATIC_CACHE, PAGES_CACHE, DATA_CACHE];
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (!expectedCaches.includes(key)) {
                        console.log(`[SW] Purging obsolete cache: ${key}`);
                        return caches.delete(key);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

/**
 * 3. Fetch Event Routing
 */
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // Only process same-origin HTTP/HTTPS requests
    if (!url.protocol.startsWith('http') || url.origin !== self.location.origin) {
        return;
    }

    // Never intercept non-GET requests (mutations, posts, deletes)
    if (request.method !== 'GET') {
        return;
    }

    // Never cache sensitive endpoints
    if (NEVER_CACHE_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
        return;
    }

    // Strategy A: HTML Page Navigation (Network-First -> Cache -> offline.html)
    if (request.mode === 'navigate' || request.destination === 'document') {
        const isRoot = url.pathname === '/' || url.pathname === '';
        const navRequest = isRoot ? new Request('/index.html', { headers: request.headers, mode: request.mode, credentials: request.credentials }) : request;

        event.respondWith(
            fetch(navRequest)
                .then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const copy = networkResponse.clone();
                        caches.open(PAGES_CACHE).then((cache) => {
                            cache.put(request, copy.clone());
                            if (isRoot) {
                                cache.put('/index.html', copy);
                            }
                        });
                    }
                    return networkResponse;
                })
                .catch(() => {
                    return caches.match(navRequest).then((cachedResponse) => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        if (isRoot) {
                            return caches.match('/index.html');
                        }
                        // Fallback to offline page
                        return caches.match('/offline.html');
                    });
                })
        );
        return;
    }

    // Strategy B: Safe Read-Only APIs (Network-First -> Cache Fallback)
    if (SAFE_API_CACHE_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
        event.respondWith(
            fetch(request)
                .then((networkResponse) => {
                    // Only cache successful JSON responses
                    if (networkResponse && networkResponse.status === 200) {
                        const copy = networkResponse.clone();
                        caches.open(DATA_CACHE).then((cache) => cache.put(request, copy));
                    }
                    return networkResponse;
                })
                .catch(() => {
                    return caches.match(request).then((cachedResponse) => {
                        if (cachedResponse) {
                            // Tag response header to inform client it came from offline cache
                            const headers = new Headers(cachedResponse.headers);
                            headers.set('X-AgriSmart-From-Cache', 'true');
                            return cachedResponse.blob().then((blob) => {
                                return new Response(blob, {
                                    status: cachedResponse.status,
                                    statusText: cachedResponse.statusText,
                                    headers: headers
                                });
                            });
                        }
                        return new Response(JSON.stringify({
                            status: "offline",
                            offline: true,
                            message: "Internet connection unavailable and no cached data exists."
                        }), {
                            status: 503,
                            headers: { "Content-Type": "application/json" }
                        });
                    });
                })
        );
        return;
    }

    // Strategy C: Static Assets (Stale-While-Revalidate)
    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            const fetchPromise = fetch(request)
                .then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const copy = networkResponse.clone();
                        caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
                    }
                    return networkResponse;
                })
                .catch(() => {
                    return cachedResponse || new Response('', { status: 503, statusText: 'Offline' });
                });

            return cachedResponse || fetchPromise;
        })
    );
});

// Handle update skip waiting message
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

/**
 * 4. PWA Push Notifications & Notification Click (Feature Upgrade 4)
 */
self.addEventListener('push', (event) => {
    let payload = {
        title: 'AgriSmart Alert',
        body: 'New agricultural alert for your farm.',
        icon: '/images/icons/icon-192x192.png',
        badge: '/images/icons/icon-72x72.png',
        data: { url: '/farmer.html#notificationSection' },
        tag: 'agrismart-alert'
    };

    if (event.data) {
        try {
            const dataJson = event.data.json();
            payload = Object.assign(payload, dataJson);
        } catch (e) {
            payload.body = event.data.text() || payload.body;
        }
    }

    const options = {
        body: payload.body,
        icon: payload.icon || '/images/icons/icon-192x192.png',
        badge: payload.badge || '/images/icons/icon-72x72.png',
        vibrate: [100, 50, 100],
        data: payload.data || { url: '/farmer.html#notificationSection' },
        tag: payload.tag || 'agrismart-alert',
        renotify: true
    };

    event.waitUntil(
        self.registration.showNotification(payload.title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const targetUrl = (event.notification.data && event.notification.data.url)
        ? event.notification.data.url
        : '/farmer.html#notificationSection';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                if ('focus' in client) {
                    client.navigate(targetUrl);
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});

