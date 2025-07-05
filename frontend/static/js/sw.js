const CACHE_NAME = 'smart-route-v1.0.0';
const STATIC_CACHE_NAME = 'smart-route-static-v1.0.0';
const DYNAMIC_CACHE_NAME = 'smart-route-dynamic-v1.0.0';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/utils.js',
    '/static/js/auth.js',
    '/static/js/maps.js',
    '/static/js/autocomplete.js',
    '/static/images/favicon.ico',
    '/offline',
    'https://cdn.tailwindcss.com/tailwind.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Routes to cache dynamically
const DYNAMIC_ROUTES = [
    '/search',
    '/analytics',
    '/history',
    '/profile',
    '/settings',
    '/about'
];

// API endpoints to cache
const API_CACHE_PATTERNS = [
    /^\/api\/autocomplete/,
    /^\/api\/saved-routes/,
    /^\/api\/history/
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('🔧 Service Worker installing...');
    
    event.waitUntil(
        Promise.all([
            // Cache static assets
            caches.open(STATIC_CACHE_NAME).then(cache => {
                console.log('📦 Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            }),
            // Skip waiting to activate immediately
            self.skipWaiting()
        ])
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('✅ Service Worker activating...');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE_NAME && 
                            cacheName !== DYNAMIC_CACHE_NAME) {
                            console.log('🗑️ Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            // Claim all clients
            self.clients.claim()
        ])
    );
});

// Fetch event - handle requests with caching strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') return;
    
    // Skip cross-origin requests (except specific CDNs)
    if (url.origin !== location.origin && !isTrustedCDN(url.origin)) {
        return;
    }
    
    event.respondWith(handleRequest(request));
});

// Handle different types of requests
async function handleRequest(request) {
    const url = new URL(request.url);
    
    try {
        // Static assets - Cache First
        if (isStaticAsset(url.pathname)) {
            return await cacheFirst(request, STATIC_CACHE_NAME);
        }
        
        // API endpoints - Network First with cache fallback
        if (isAPIEndpoint(url.pathname)) {
            return await networkFirst(request, DYNAMIC_CACHE_NAME);
        }
        
        // HTML pages - Stale While Revalidate
        if (isHTMLPage(url.pathname)) {
            return await staleWhileRevalidate(request, DYNAMIC_CACHE_NAME);
        }
        
        // Default strategy - Network First
        return await networkFirst(request, DYNAMIC_CACHE_NAME);
        
    } catch (error) {
        console.error('❌ Request failed:', error);
        return await handleOfflineFallback(request);
    }
}

// Cache First strategy - good for static assets
async function cacheFirst(request, cacheName) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        throw error;
    }
}

// Network First strategy - good for dynamic content
async function networkFirst(request, cacheName) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        throw error;
    }
}

// Stale While Revalidate strategy - good for HTML pages
async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);
    
    const fetchPromise = fetch(request).then(networkResponse => {
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    }).catch(() => {
        // Network failed, return cached version if available
        return cachedResponse;
    });
    
    // Return cached version immediately if available, otherwise wait for network
    return cachedResponse || fetchPromise;
}

// Offline fallback handling
async function handleOfflineFallback(request) {
    const url = new URL(request.url);
    
    // HTML pages - show offline page
    if (isHTMLPage(url.pathname)) {
        const offlinePage = await caches.match('/offline');
        if (offlinePage) {
            return offlinePage;
        }
        
        // Fallback offline page
        return new Response(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Hors ligne - Smart Route</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .offline { color: #666; }
                    .retry { margin-top: 20px; }
                    button { background: #5D5CDE; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class="offline">
                    <h1>🚫 Connexion perdue</h1>
                    <p>Vous êtes actuellement hors ligne. Certaines fonctionnalités peuvent être limitées.</p>
                    <div class="retry">
                        <button onclick="window.location.reload()">Réessayer</button>
                    </div>
                </div>
            </body>
            </html>
        `, {
            headers: { 'Content-Type': 'text/html' }
        });
    }
    
    // API requests - return error response
    if (isAPIEndpoint(url.pathname)) {
        return new Response(JSON.stringify({
            success: false,
            error: {
                code: 'OFFLINE',
                message: 'Connexion réseau indisponible'
            }
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    // Other requests - let them fail
    throw new Error('Network request failed and no cache available');
}

// Helper functions
function isStaticAsset(pathname) {
    return pathname.startsWith('/static/') || 
           pathname.endsWith('.css') || 
           pathname.endsWith('.js') || 
           pathname.endsWith('.ico') || 
           pathname.endsWith('.png') || 
           pathname.endsWith('.jpg') || 
           pathname.endsWith('.svg');
}

function isAPIEndpoint(pathname) {
    return pathname.startsWith('/api/') || 
           API_CACHE_PATTERNS.some(pattern => pattern.test(pathname));
}

function isHTMLPage(pathname) {
    return !pathname.includes('.') || pathname.endsWith('.html');
}

function isTrustedCDN(origin) {
    const trustedCDNs = [
        'https://cdn.tailwindcss.com',
        'https://cdnjs.cloudflare.com',
        'https://cdn.jsdelivr.net',
        'https://unpkg.com',
        'https://fonts.googleapis.com',
        'https://fonts.gstatic.com',
        'https://js.api.here.com'
    ];
    
    return trustedCDNs.includes(origin);
}

// Background sync for when connection is restored
self.addEventListener('sync', event => {
    console.log('🔄 Background sync triggered:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // Sync any pending data when connection is restored
    console.log('🔄 Performing background sync...');
    
    try {
        // Sync user preferences
        await syncUserPreferences();
        
        // Sync search history
        await syncSearchHistory();
        
        // Notify clients that sync is complete
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_COMPLETE',
                timestamp: Date.now()
            });
        });
        
    } catch (error) {
        console.error('❌ Background sync failed:', error);
    }
}

async function syncUserPreferences() {
    // Check if there are pending preference changes
    const pendingChanges = await getFromIndexedDB('pendingPreferences');
    
    if (pendingChanges && pendingChanges.length > 0) {
        for (const change of pendingChanges) {
            try {
                await fetch('/auth/api/preferences', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(change.data)
                });
                
                // Remove from pending changes
                await removeFromIndexedDB('pendingPreferences', change.id);
            } catch (error) {
                console.warn('Failed to sync preference change:', error);
            }
        }
    }
}

async function syncSearchHistory() {
    // Check if there are pending history items
    const pendingHistory = await getFromIndexedDB('pendingHistory');
    
    if (pendingHistory && pendingHistory.length > 0) {
        for (const item of pendingHistory) {
            try {
                await fetch('/api/history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(item.data)
                });
                
                // Remove from pending history
                await removeFromIndexedDB('pendingHistory', item.id);
            } catch (error) {
                console.warn('Failed to sync history item:', error);
            }
        }
    }
}

// IndexedDB helpers for offline data storage
async function getFromIndexedDB(storeName) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('SmartRouteOffline', 1);
        
        request.onerror = () => reject(request.error);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const getRequest = store.getAll();
            
            getRequest.onsuccess = () => resolve(getRequest.result);
            getRequest.onerror = () => reject(getRequest.error);
        };
        
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains(storeName)) {
                db.createObjectStore(storeName, { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

async function removeFromIndexedDB(storeName, id) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('SmartRouteOffline', 1);
        
        request.onerror = () => reject(request.error);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const deleteRequest = store.delete(id);
            
            deleteRequest.onsuccess = () => resolve();
            deleteRequest.onerror = () => reject(deleteRequest.error);
        };
    });
}

// Push notification handling
self.addEventListener('push', event => {
    console.log('📨 Push notification received');
    
    if (!event.data) return;
    
    try {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/images/icon-192x192.png',
            badge: '/static/images/badge-72x72.png',
            tag: data.tag || 'smart-route-notification',
            data: data.data || {},
            actions: data.actions || [],
            requireInteraction: data.requireInteraction || false
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    } catch (error) {
        console.error('❌ Push notification error:', error);
    }
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    console.log('🔔 Notification clicked');
    
    event.notification.close();
    
    const data = event.notification.data;
    let url = '/';
    
    if (data && data.url) {
        url = data.url;
    }
    
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(clientList => {
            // Try to focus existing window
            for (const client of clientList) {
                if (client.url === url && 'focus' in client) {
                    return client.focus();
                }
            }
            
            // Open new window
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});

// Message handling from main thread
self.addEventListener('message', event => {
    console.log('📩 Message received:', event.data);
    
    const { type, data } = event.data;
    
    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;
            
        case 'CACHE_ROUTES':
            event.waitUntil(cacheRoutes(data.routes));
            break;
            
        case 'CLEAR_CACHE':
            event.waitUntil(clearAllCaches());
            break;
            
        default:
            console.warn('Unknown message type:', type);
    }
});

async function cacheRoutes(routes) {
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    
    for (const route of routes) {
        try {
            const response = new Response(JSON.stringify(route), {
                headers: { 'Content-Type': 'application/json' }
            });
            
            await cache.put(`/api/route/${route.id}`, response);
        } catch (error) {
            console.warn('Failed to cache route:', error);
        }
    }
}

async function clearAllCaches() {
    const cacheNames = await caches.keys();
    
    await Promise.all(
        cacheNames.map(cacheName => caches.delete(cacheName))
    );
    
    console.log('🗑️ All caches cleared');
}

// Periodic background sync
self.addEventListener('periodicsync', event => {
    if (event.tag === 'update-routes') {
        event.waitUntil(updateCachedRoutes());
    }
});

async function updateCachedRoutes() {
    console.log('🔄 Updating cached routes...');
    
    try {
        // Get user's saved routes
        const response = await fetch('/api/saved-routes');
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.success && data.routes) {
                await cacheRoutes(data.routes);
            }
        }
    } catch (error) {
        console.warn('Failed to update cached routes:', error);
    }
}

console.log('🚀 Smart Route Service Worker loaded');