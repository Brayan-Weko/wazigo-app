// Main JavaScript for Smart Route App

// Global app state
window.SmartRoute = {
    config: window.APP_CONFIG || {},
    user: null,
    initialized: false
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    try {
        // Set user from config
        SmartRoute.user = SmartRoute.config.currentUser;
        
        // Initialize core features
        initializeNavigation();
        initializeAlerts();
        initializeTheme();
        initializeServiceWorker();
        
        // Mark as initialized
        SmartRoute.initialized = true;
        
        console.log('✅ Smart Route app initialized');
    } catch (error) {
        console.error('❌ Failed to initialize app:', error);
        showAlert('Erreur lors de l\'initialisation de l\'application', 'error');
    }
}

/**
 * Initialize navigation features
 */
function initializeNavigation() {
    // Mobile menu toggle
    window.toggleMobileMenu = function() {
        const mobileMenu = document.getElementById('mobile-menu');
        if (mobileMenu) {
            mobileMenu.classList.toggle('hidden');
        }
    };
    
    // Quick search functionality
    const quickSearchInput = document.getElementById('quick-search');
    if (quickSearchInput) {
        let searchTimeout;
        
        quickSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (query.length >= 2) {
                searchTimeout = setTimeout(() => {
                    performQuickSearch(query);
                }, 300);
            }
        });
        
        quickSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = this.value.trim();
                if (query) {
                    window.location.href = `/search?origin=${encodeURIComponent(query)}`;
                }
            }
        });
    }
    
    // Navigation highlighting
    highlightCurrentNavigation();
}

/**
 * Perform quick search
 */
async function performQuickSearch(query) {
    try {
        const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success && data.suggestions.length > 0) {
            // For now, just log the results
            // In a full implementation, you'd show a dropdown
            console.log('Quick search results:', data.suggestions);
        }
    } catch (error) {
        console.error('Quick search error:', error);
    }
}

/**
 * Highlight current navigation item
 */
function highlightCurrentNavigation() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link, .mobile-nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.startsWith(href) && href !== '/') {
            link.classList.add('active');
        } else if (href === '/' && currentPath === '/') {
            link.classList.add('active');
        }
    });
}

/**
 * Initialize alert system
 */
function initializeAlerts() {
    // Create alert container if it doesn't exist
    if (!document.getElementById('alert-container')) {
        const container = document.createElement('div');
        container.id = 'alert-container';
        container.className = 'fixed top-4 right-4 z-40 space-y-2';
        document.body.appendChild(container);
    }
}

/**
 * Show alert message
 */
window.showAlert = function(message, type = 'info', duration = 5000) {
    const container = document.getElementById('alert-container');
    if (!container) return;
    
    const alertId = 'alert-' + Date.now();
    const alertElement = document.createElement('div');
    alertElement.id = alertId;
    alertElement.className = `alert ${type} slide-in-from-right`;
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-triangle',
        warning: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    alertElement.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center">
                <i class="fas ${icons[type] || icons.info} mr-2"></i>
                <span>${message}</span>
            </div>
            <button onclick="removeAlert('${alertId}')" class="ml-4 text-current hover:text-opacity-75 focus:outline-none">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    container.appendChild(alertElement);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            removeAlert(alertId);
        }, duration);
    }
    
    return alertId;
};

/**
 * Remove alert
 */
window.removeAlert = function(alertId) {
    const alert = document.getElementById(alertId);
    if (alert) {
        alert.classList.add('slide-out-to-right');
        setTimeout(() => {
            alert.remove();
        }, 300);
    }
};

/**
 * Initialize theme management
 */
function initializeTheme() {
    // Theme is handled by the base template
    // This function can be extended for manual theme switching
    
    // Store theme preference
    const theme = localStorage.getItem('theme');
    if (theme) {
        document.documentElement.classList.toggle('dark', theme === 'dark');
    }
    
    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            document.documentElement.classList.toggle('dark', e.matches);
        }
    });
}

/**
 * Set theme manually
 */
window.setTheme = function(theme) {
    localStorage.setItem('theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    showAlert(`Thème ${theme === 'dark' ? 'sombre' : 'clair'} activé`, 'success');
};

/**
 * Initialize service worker for offline support
 */
function initializeServiceWorker() {
    if ('serviceWorker' in navigator && window.location.protocol === 'https:') {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('✅ Service Worker registered:', registration);
            })
            .catch(error => {
                console.log('❌ Service Worker registration failed:', error);
            });
    }
}

/**
 * Show loading overlay
 */
window.showLoading = function(message = 'Chargement...') {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.querySelector('p').textContent = message;
        overlay.classList.remove('hidden');
    }
};

/**
 * Hide loading overlay
 */
window.hideLoading = function() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
};

/**
 * API request helper
 */
window.apiRequest = async function(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin'
    };
    
    const config = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(endpoint, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error?.message || 'Erreur de requête');
        }
        
        return data;
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
};

/**
 * Format duration for display
 */
window.formatDuration = function(seconds) {
    if (seconds < 60) {
        return `${seconds}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        return `${minutes}min`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return minutes > 0 ? `${hours}h${minutes.toString().padStart(2, '0')}` : `${hours}h`;
    }
};

/**
 * Format distance for display
 */
window.formatDistance = function(meters) {
    if (meters < 1000) {
        return `${meters}m`;
    } else {
        const km = meters / 1000;
        return km < 10 ? `${km.toFixed(1)}km` : `${Math.round(km)}km`;
    }
};

/**
 * Format score for display
 */
window.formatScore = function(score, showDecimals = true) {
    const rounded = showDecimals ? score.toFixed(1) : Math.round(score);
    return `${rounded}/10`;
};

/**
 * Get score class for styling
 */
window.getScoreClass = function(score) {
    if (score >= 8.5) return 'score-excellent';
    if (score >= 7.0) return 'score-good';
    if (score >= 5.0) return 'score-average';
    if (score >= 3.0) return 'score-poor';
    return 'score-bad';
};

/**
 * Get traffic level class
 */
window.getTrafficClass = function(level) {
    const classes = {
        'free': 'traffic-free',
        'light': 'traffic-light',
        'moderate': 'traffic-moderate',
        'heavy': 'traffic-heavy',
        'severe': 'traffic-severe'
    };
    return classes[level] || 'traffic-moderate';
};

/**
 * Copy text to clipboard
 */
window.copyToClipboard = async function(text) {
    try {
        await navigator.clipboard.writeText(text);
        showAlert('Copié dans le presse-papier', 'success', 2000);
    } catch (error) {
        console.error('Failed to copy:', error);
        showAlert('Erreur lors de la copie', 'error');
    }
};

/**
 * Share functionality
 */
window.shareRoute = async function(routeData) {
    const shareData = {
        title: 'Itinéraire Smart Route',
        text: `De ${routeData.origin} à ${routeData.destination}`,
        url: window.location.href
    };
    
    try {
        if (navigator.share) {
            await navigator.share(shareData);
        } else {
            // Fallback to copying URL
            await copyToClipboard(shareData.url);
        }
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Share failed:', error);
            showAlert('Erreur lors du partage', 'error');
        }
    }
};

/**
 * Download route data
 */
window.downloadRoute = function(routeData, format = 'json') {
    let content, mimeType, filename;
    
    switch (format) {
        case 'json':
            content = JSON.stringify(routeData, null, 2);
            mimeType = 'application/json';
            filename = 'route.json';
            break;
        case 'gpx':
            content = convertToGPX(routeData);
            mimeType = 'application/gpx+xml';
            filename = 'route.gpx';
            break;
        default:
            showAlert('Format non supporté', 'error');
            return;
    }
    
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showAlert('Téléchargement commencé', 'success');
};

/**
 * Convert route data to GPX format (basic implementation)
 */
function convertToGPX(routeData) {
    const date = new Date().toISOString();
    
    let gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Smart Route" xmlns="http://www.topografix.com/GPX/1/1">
    <metadata>
        <name>Smart Route - ${routeData.origin || 'Route'}</name>
        <desc>Itinéraire optimisé</desc>
        <time>${date}</time>
    </metadata>
    <trk>
        <name>Route</name>
        <trkseg>`;
    
    // Add route points (this would need actual route coordinates)
    if (routeData.coordinates) {
        routeData.coordinates.forEach(coord => {
            gpx += `
            <trkpt lat="${coord.lat}" lon="${coord.lng}">
                <time>${date}</time>
            </trkpt>`;
        });
    }
    
    gpx += `
        </trkseg>
    </trk>
</gpx>`;
    
    return gpx;
}

/**
 * Handle offline/online status
 */
window.addEventListener('online', function() {
    showAlert('Connexion rétablie', 'success', 3000);
});

window.addEventListener('offline', function() {
    showAlert('Connexion perdue - Mode hors ligne', 'warning', 5000);
});

/**
 * Handle errors globally
 */
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    if (SmartRoute.config.debug) {
        showAlert(`Erreur: ${event.error.message}`, 'error');
    }
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    if (SmartRoute.config.debug) {
        showAlert(`Erreur: ${event.reason}`, 'error');
    }
});

/**
 * Initialize analytics (if enabled)
 */
function initializeAnalytics() {
    // This would integrate with Google Analytics, Mixpanel, etc.
    console.log('Analytics initialized');
}

/**
 * Track user interaction
 */
window.trackEvent = function(eventName, eventData = {}) {
    if (SmartRoute.config.debug) {
        console.log('Track event:', eventName, eventData);
    }
    
    // This would send to analytics service
    // analytics.track(eventName, eventData);
};

// Export for use in other scripts
window.SmartRoute = SmartRoute;