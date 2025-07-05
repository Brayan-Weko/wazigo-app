class MapManager {
    constructor() {
        this.map = null;
        this.mapContainer = null;
        this.isInitialized = false;
        this.markers = [];
        this.routePolylines = [];
        this.trafficLayer = null;
        this.userLocationMarker = null;
        this.currentRoute = null;
        this.mapMode = '2d'; // '2d' or '3d'
        this.mapType = 'normal'; // 'normal', 'satellite', 'terrain'
        
        // HERE Maps API configuration
        this.platform = null;
        this.defaultLayers = null;
        
        // Navigation specific
        this.isNavigationMode = false;
        this.currentInstruction = null;
        this.nextInstruction = null;
        
        this.initializePlatform();
    }

    initializePlatform() {
        if (typeof H === 'undefined') {
            console.error('HERE Maps API not loaded');
            return;
        }

        try {
            this.platform = new H.service.Platform({
                'apikey': window.APP_CONFIG.mapsApiKey || 'demo'
            });
            
            this.defaultLayers = this.platform.createDefaultLayers();
            console.log('✅ HERE Maps platform initialized');
        } catch (error) {
            console.error('❌ Failed to initialize HERE Maps platform:', error);
        }
    }

    async initializeMap(containerId = 'map-container', options = {}) {
        if (!this.platform) {
            throw new Error('HERE Maps platform not initialized');
        }

        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`Map container ${containerId} not found`);
        }

        const defaultOptions = {
            zoom: 10,
            center: { lat: 48.8566, lng: 2.3522 }, // Paris default
            pixelRatio: window.devicePixelRatio || 1
        };

        const mapOptions = { ...defaultOptions, ...options };

        try {
            // Initialize the map
            this.map = new H.Map(
                container,
                this.defaultLayers.vector.normal.map,
                mapOptions
            );

            // Enable map interaction (pan, zoom)
            const behavior = new H.mapevents.Behavior();
            
            // Create default UI (zoom buttons, etc.)
            const ui = H.ui.UI.createDefault(this.map);

            // Store container reference
            this.mapContainer = container;

            // Add event listeners
            this.setupEventListeners();

            this.isInitialized = true;
            console.log('✅ Map initialized successfully');

            // Try to get user location
            await this.requestUserLocation();

            return this.map;
        } catch (error) {
            console.error('❌ Failed to initialize map:', error);
            throw error;
        }
    }

    setupEventListeners() {
        if (!this.map) return;

        // Resize handler
        window.addEventListener('resize', () => {
            if (this.map) {
                this.map.getViewPort().resize();
            }
        });

        // Click handler
        this.map.addEventListener('tap', (evt) => {
            const coord = this.map.screenToGeo(
                evt.currentPointer.viewportX,
                evt.currentPointer.viewportY
            );
            
            this.onMapClick(coord);
        });
    }

    onMapClick(coord) {
        console.log(`Map clicked at: ${coord.lat}, ${coord.lng}`);
        // Emit custom event for other components to listen
        window.dispatchEvent(new CustomEvent('mapClick', {
            detail: { lat: coord.lat, lng: coord.lng }
        }));
    }

    async requestUserLocation() {
        if (!navigator.geolocation) {
            console.warn('Geolocation not supported');
            return null;
        }

        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const userLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    
                    this.setUserLocation(userLocation);
                    this.centerMap(userLocation);
                    resolve(userLocation);
                },
                (error) => {
                    console.warn('Geolocation error:', error);
                    resolve(null);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        });
    }

    setUserLocation(location) {
        if (!this.map) return;

        // Remove existing user location marker
        if (this.userLocationMarker) {
            this.map.removeObject(this.userLocationMarker);
        }

        // Create user location marker
        const icon = new H.map.Icon(this.createUserLocationIcon(), { size: { w: 24, h: 24 } });
        this.userLocationMarker = new H.map.Marker(location, { icon });
        this.map.addObject(this.userLocationMarker);
    }

    createUserLocationIcon() {
        const svg = `
            <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="8" fill="#3B82F6" stroke="#FFFFFF" stroke-width="3"/>
                <circle cx="12" cy="12" r="3" fill="#FFFFFF"/>
            </svg>
        `;
        return `data:image/svg+xml;base64,${btoa(svg)}`;
    }

    centerMap(location, zoom = null) {
        if (!this.map) return;
        
        this.map.setCenter(location);
        if (zoom !== null) {
            this.map.setZoom(zoom);
        }
    }

    // Route display methods
    displayRoutes(routes) {
        if (!this.map || !routes || routes.length === 0) return;

        this.clearRoutes();

        const group = new H.map.Group();
        const bounds = new H.geo.Rect();

        routes.forEach((route, index) => {
            const polyline = this.createRoutePolyline(route, index);
            if (polyline) {
                group.addObject(polyline);
                this.routePolylines.push(polyline);
                
                // Extend bounds
                if (route.coordinates && route.coordinates.length > 0) {
                    route.coordinates.forEach(coord => {
                        bounds.mergePoint(coord);
                    });
                }
            }
        });

        this.map.addObject(group);

        // Fit map to show all routes
        if (!bounds.isEmpty()) {
            this.map.getViewModel().setLookAtData({
                bounds: bounds
            });
        }

        // Add origin and destination markers
        if (routes[0] && routes[0].summary) {
            this.addLocationMarkers(routes[0].summary);
        }
    }

    createRoutePolyline(route, index) {
        if (!route.coordinates || route.coordinates.length === 0) {
            console.warn('Route has no coordinates');
            return null;
        }

        const lineString = new H.geo.LineString();
        route.coordinates.forEach(coord => {
            lineString.pushPoint(coord);
        });

        const colors = [
            '#3B82F6', // Blue - primary route
            '#10B981', // Green - alternative 1
            '#F59E0B', // Yellow - alternative 2
            '#EF4444', // Red - alternative 3
            '#8B5CF6'  // Purple - alternative 4
        ];

        const isSelected = index === 0;
        const strokeWidth = isSelected ? 6 : 4;
        const strokeColor = colors[index % colors.length];

        const polyline = new H.map.Polyline(lineString, {
            style: {
                strokeColor: strokeColor,
                lineWidth: strokeWidth,
                lineCap: 'round',
                lineJoin: 'round'
            },
            data: { routeIndex: index, route: route }
        });

        // Add click handler for route selection
        polyline.addEventListener('tap', (evt) => {
            this.selectRoute(index);
            evt.stopPropagation();
        });

        return polyline;
    }

    addLocationMarkers(summary) {
        if (!summary.origin || !summary.destination) return;

        // Origin marker
        const originIcon = new H.map.Icon(this.createLocationIcon('origin'), { size: { w: 32, h: 40 } });
        const originMarker = new H.map.Marker(summary.origin, { icon: originIcon });
        this.map.addObject(originMarker);
        this.markers.push(originMarker);

        // Destination marker
        const destIcon = new H.map.Icon(this.createLocationIcon('destination'), { size: { w: 32, h: 40 } });
        const destMarker = new H.map.Marker(summary.destination, { icon: destIcon });
        this.map.addObject(destMarker);
        this.markers.push(destMarker);
    }

    createLocationIcon(type) {
        const color = type === 'origin' ? '#10B981' : '#EF4444';
        const letter = type === 'origin' ? 'A' : 'B';
        
        const svg = `
            <svg width="32" height="40" viewBox="0 0 32 40" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 0C7.163 0 0 7.163 0 16c0 16 16 24 16 24s16-8 16-24c0-8.837-7.163-16-16-16z" fill="${color}"/>
                <circle cx="16" cy="16" r="8" fill="#FFFFFF"/>
                <text x="16" y="20" text-anchor="middle" fill="${color}" font-family="Arial, sans-serif" font-size="10" font-weight="bold">${letter}</text>
            </svg>
        `;
        return `data:image/svg+xml;base64,${btoa(svg)}`;
    }

    selectRoute(routeIndex) {
        // Update polyline styles
        this.routePolylines.forEach((polyline, index) => {
            const isSelected = index === routeIndex;
            polyline.setStyle({
                strokeColor: polyline.getStyle().strokeColor,
                lineWidth: isSelected ? 6 : 4
            });
        });

        // Emit route selection event
        window.dispatchEvent(new CustomEvent('routeSelected', {
            detail: { routeIndex }
        }));
    }

    clearRoutes() {
        // Remove existing polylines
        this.routePolylines.forEach(polyline => {
            this.map.removeObject(polyline);
        });
        this.routePolylines = [];

        // Remove existing markers
        this.markers.forEach(marker => {
            this.map.removeObject(marker);
        });
        this.markers = [];
    }

    // Traffic layer methods
    toggleTrafficLayer() {
        if (!this.map) return;

        if (this.trafficLayer) {
            this.map.removeLayer(this.trafficLayer);
            this.trafficLayer = null;
            return false;
        } else {
            this.trafficLayer = this.defaultLayers.vector.normal.traffic;
            this.map.addLayer(this.trafficLayer);
            return true;
        }
    }

    // Map mode methods
    toggleMapMode() {
        if (!this.map) return;

        this.mapMode = this.mapMode === '2d' ? '3d' : '2d';
        
        if (this.mapMode === '3d') {
            this.map.setIncline(45);
            this.map.setHeading(0);
        } else {
            this.map.setIncline(0);
        }

        return this.mapMode;
    }

    setMapType(type) {
        if (!this.map || !this.defaultLayers) return;

        let layer;
        switch (type) {
            case 'satellite':
                layer = this.defaultLayers.raster.satellite.map;
                break;
            case 'terrain':
                layer = this.defaultLayers.raster.terrain.map;
                break;
            default:
                layer = this.defaultLayers.vector.normal.map;
        }

        this.map.setBaseLayer(layer);
        this.mapType = type;
    }

    // Navigation specific methods
    async initializeNavigation() {
        if (!this.isInitialized) {
            await this.initializeMap('navigation-map');
        }

        this.isNavigationMode = true;
        
        // Setup navigation-specific settings
        this.map.getUI().getControl('zoom').setAlignment('top-right');
        
        // Enable continuous location tracking
        this.startLocationTracking();
        
        return this.map;
    }

    startLocationTracking() {
        if (!navigator.geolocation) return;

        const watchId = navigator.geolocation.watchPosition(
            (position) => {
                const location = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                    heading: position.coords.heading,
                    speed: position.coords.speed
                };
                
                this.updateNavigationPosition(location);
            },
            (error) => {
                console.error('Location tracking error:', error);
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 1000
            }
        );

        // Store watch ID for cleanup
        this.locationWatchId = watchId;
    }

    updateNavigationPosition(location) {
        if (!this.map) return;

        // Update user location marker
        this.setUserLocation(location);

        // Center map on user location (with smooth animation)
        this.map.setCenter(location, true);

        // Update heading if available
        if (location.heading !== null) {
            this.map.setHeading(location.heading);
        }

        // Check current instruction
        this.checkCurrentInstruction(location);
    }

    checkCurrentInstruction(location) {
        if (!this.currentRoute || !this.currentRoute.instructions) return;

        // Implementation for checking if user has reached next instruction point
        // This would involve calculating distance to next instruction point
        // and triggering voice guidance when appropriate
        
        const instructions = this.currentRoute.instructions;
        const currentIndex = window.navigationState?.currentInstructionIndex || 0;
        
        if (currentIndex < instructions.length) {
            const instruction = instructions[currentIndex];
            const distance = this.calculateDistance(location, instruction.location);
            
            // If within 50 meters of instruction point, move to next instruction
            if (distance < 50) {
                window.navigationState.currentInstructionIndex++;
                
                // Trigger voice instruction
                if (window.speakInstruction && instruction.text) {
                    window.speakInstruction(instruction.text);
                }
                
                // Update UI
                window.dispatchEvent(new CustomEvent('instructionUpdate', {
                    detail: { instruction, index: currentIndex + 1 }
                }));
            }
        }
    }

    calculateDistance(point1, point2) {
        const R = 6371e3; // Earth's radius in meters
        const φ1 = point1.lat * Math.PI/180;
        const φ2 = point2.lat * Math.PI/180;
        const Δφ = (point2.lat-point1.lat) * Math.PI/180;
        const Δλ = (point2.lng-point1.lng) * Math.PI/180;

        const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                Math.cos(φ1) * Math.cos(φ2) *
                Math.sin(Δλ/2) * Math.sin(Δλ/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

        return R * c; // Distance in meters
    }

    // Fullscreen methods
    async toggleFullscreen() {
        if (!document.fullscreenElement) {
            try {
                await this.mapContainer.requestFullscreen();
                return true;
            } catch (error) {
                console.error('Fullscreen error:', error);
                return false;
            }
        } else {
            try {
                await document.exitFullscreen();
                return false;
            } catch (error) {
                console.error('Exit fullscreen error:', error);
                return true;
            }
        }
    }

    // Cleanup methods
    destroy() {
        if (this.locationWatchId) {
            navigator.geolocation.clearWatch(this.locationWatchId);
        }

        if (this.map) {
            this.map.dispose();
            this.map = null;
        }

        this.isInitialized = false;
        this.isNavigationMode = false;
    }

    // Utility methods
    getMapBounds() {
        if (!this.map) return null;
        return this.map.getViewModel().getLookAtData().bounds;
    }

    async reverseGeocode(lat, lng) {
        if (!this.platform) return null;

        try {
            const geocoder = this.platform.getSearchService();
            
            return new Promise((resolve, reject) => {
                geocoder.reverseGeocode({
                    at: `${lat},${lng}`
                }, (result) => {
                    if (result.items && result.items.length > 0) {
                        resolve(result.items[0]);
                    } else {
                        resolve(null);
                    }
                }, reject);
            });
        } catch (error) {
            console.error('Reverse geocoding error:', error);
            return null;
        }
    }

    async geocode(query) {
        if (!this.platform) return [];

        try {
            const geocoder = this.platform.getSearchService();
            
            return new Promise((resolve, reject) => {
                geocoder.geocode({
                    q: query
                }, (result) => {
                    resolve(result.items || []);
                }, reject);
            });
        } catch (error) {
            console.error('Geocoding error:', error);
            return [];
        }
    }
}

// Create global instance
window.MapManager = new MapManager();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapManager;
}

// Initialize HERE Maps API when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Load HERE Maps API if not already loaded
    if (typeof H === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://js.api.here.com/v3/3.1/mapsjs-core.js';
        script.onload = function() {
            // Load additional HERE Maps modules
            const modules = [
                'https://js.api.here.com/v3/3.1/mapsjs-service.js',
                'https://js.api.here.com/v3/3.1/mapsjs-ui.js',
                'https://js.api.here.com/v3/3.1/mapsjs-mapevents.js'
            ];
            
            let loadedModules = 0;
            modules.forEach(moduleUrl => {
                const moduleScript = document.createElement('script');
                moduleScript.src = moduleUrl;
                moduleScript.onload = function() {
                    loadedModules++;
                    if (loadedModules === modules.length) {
                        window.MapManager.initializePlatform();
                        console.log('✅ HERE Maps API fully loaded');
                    }
                };
                document.head.appendChild(moduleScript);
            });
        };
        document.head.appendChild(script);
    }
});