class LocationSearchManager {
    constructor() {
        this.selectedCountry = null;
        this.selectedOrigin = null;
        this.selectedDestination = null;
        this.map = null;
        this.currentMarker = null;
        this.selectingFor = null; // 'origin' ou 'destination'
        this.searchTimeouts = {};
    }

    initialize() {
        this.setupEventListeners();
        this.loadFavoriteRoutes();
        this.loadRecentSearches();
        console.log('✅ Location search manager initialized');
    }

    setupEventListeners() {
        // Écouteurs pour les champs de recherche
        this.setupSearchInput('origin');
        this.setupSearchInput('destination');
        
        // Écouteurs pour les favoris
        this.setupFavoritesDropdown('origin');
        this.setupFavoritesDropdown('destination');
        
        // Écouteurs pour les coordonnées
        this.setupCoordinatesInput('origin');
        this.setupCoordinatesInput('destination');
    }

    setupSearchInput(type) {
        const input = document.getElementById(`${type}-search`);
        const suggestionsContainer = document.getElementById(`${type}-suggestions`);
        
        if (!input || !suggestionsContainer) return;

        input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            // Nettoyer le timeout précédent
            if (this.searchTimeouts[type]) {
                clearTimeout(this.searchTimeouts[type]);
            }
            
            if (query.length < 2) {
                this.hideSuggestions(type);
                return;
            }
            
            // Attendre 300ms avant de rechercher
            this.searchTimeouts[type] = setTimeout(() => {
                this.searchLocations(query, type);
            }, 300);
        });

        // Cacher les suggestions quand on clique ailleurs
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                this.hideSuggestions(type);
            }
        });
    }

    async searchLocations(query, type) {
        this.selectedCountry = window.CountryManager?.getSelectedCountry();

        if (!this.selectedCountry) {
            this.showSuggestionError(type, 'Veuillez d\'abord sélectionner un pays');
            return;
        }

        try {
            const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}&country=${this.selectedCountry.code}&limit=8`);
            const data = await response.json();
            
            if (data.success && data.suggestions) {
                this.displaySuggestions(data.suggestions, type);
            } else {
                this.showSuggestionError(type, 'Aucun résultat trouvé');
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showSuggestionError(type, 'Erreur de recherche');
        }
    }

    displaySuggestions(suggestions, type) {
        const container = document.getElementById(`${type}-suggestions`);
        if (!container) return;

        container.innerHTML = '';
        container.classList.remove('hidden');

        if (suggestions.length === 0) {
            this.showSuggestionError(type, 'Aucun résultat');
            return;
        }

        suggestions.forEach(suggestion => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.innerHTML = `
                <div class="flex items-center">
                    <i class="fas fa-map-marker-alt text-gray-400 mr-3"></i>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900 dark:text-white">${suggestion.title}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${suggestion.label}</div>
                    </div>
                </div>
            `;
            
            item.addEventListener('click', () => {
                this.selectLocation(suggestion, type);
            });
            
            container.appendChild(item);
        });
    }

    showSuggestionError(type, message) {
        const container = document.getElementById(`${type}-suggestions`);
        if (!container) return;

        container.innerHTML = `
            <div class="p-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                <i class="fas fa-exclamation-circle mr-2"></i>
                ${message}
            </div>
        `;
        container.classList.remove('hidden');
    }

    hideSuggestions(type) {
        const container = document.getElementById(`${type}-suggestions`);
        if (container) {
            container.classList.add('hidden');
        }
    }

    selectLocation(location, type) {
        const locationData = {
            address: location.title,
            label: location.label,
            lat: location.position.lat,
            lng: location.position.lng,
            country: this.selectedCountry?.code
        };

        if (type === 'origin') {
            this.selectedOrigin = locationData;
            window.selectedOrigin = locationData;
        } else {
            this.selectedDestination = locationData;
            window.selectedDestination = locationData;
        }

        // Mettre à jour l'input
        const input = document.getElementById(`${type}-search`);
        if (input) {
            input.value = location.title;
        }

        // Cacher les suggestions
        this.hideSuggestions(type);

        // Sauvegarder dans les recherches récentes
        this.saveRecentSearch(locationData);

        console.log(`✅ ${type} selected:`, locationData);
    }

    setupFavoritesDropdown(type) {
        const dropdown = document.getElementById(`${type}-favorites`);
        if (!dropdown) return;

        dropdown.addEventListener('change', (e) => {
            const selectedValue = e.target.value;
            if (!selectedValue) return;

            try {
                const favoriteData = JSON.parse(selectedValue);
                this.selectLocation(favoriteData, type);
            } catch (error) {
                console.error('Error parsing favorite data:', error);
            }
        });
    }

    setupCoordinatesInput(type) {
        const latInput = document.getElementById(`${type}-lat`);
        const lngInput = document.getElementById(`${type}-lng`);
        
        if (!latInput || !lngInput) return;

        const validateCoordinates = () => {
            const lat = parseFloat(latInput.value);
            const lng = parseFloat(lngInput.value);

            if (isNaN(lat) || isNaN(lng)) return false;
            if (lat < -90 || lat > 90) return false;
            if (lng < -180 || lng > 180) return false;

            return { lat, lng };
        };

        [latInput, lngInput].forEach(input => {
            input.addEventListener('blur', () => {
                const coords = validateCoordinates();
                if (coords) {
                    this.reverseGeocode(coords.lat, coords.lng, type);
                }
            });
        });
    }

    async reverseGeocode(lat, lng, type) {
        try {
            const response = await fetch('/maps/reverse-geocode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ lat, lng })
            });

            const data = await response.json();
            
            if (data.success && data.address) {
                const locationData = {
                    address: data.address.title,
                    label: data.address.label,
                    lat: lat,
                    lng: lng,
                    country: this.selectedCountry?.code
                };

                this.selectLocation(locationData, type);
                showAlert(`Coordonnées validées: ${data.address.title}`, 'success');
            } else {
                showAlert('Coordonnées invalides', 'error');
            }
        } catch (error) {
            console.error('Reverse geocoding error:', error);
            showAlert('Erreur de géocodage inverse', 'error');
        }
    }

    openMapSelector(type) {
        this.selectingFor = type;
        this.initializeMap();
        document.getElementById('map-selector-modal').classList.remove('hidden');
    }

    initializeMap() {
        const mapContainer = document.getElementById('interactive-map');
        if (!mapContainer) return;

        // Nettoyer la carte existante
        mapContainer.innerHTML = '';

        // Récupérer le pays sélectionné
        this.selectedCountry = window.CountryManager?.getSelectedCountry();

        // Position par défaut (centre du pays sélectionné ou position de l'utilisateur ou Cameroun)
        let defaultLat = 3.8480;
        let defaultLng = 11.5021;
        let defaultZoom = 8;
        
        if (this.selectedCountry) {
            defaultLat = this.selectedCountry.lat;
            defaultLng = this.selectedCountry.lng;
        }

        // Si on a une position utilisateur et qu'elle est dans le pays sélectionné, l'utiliser
        const userLocation = window.CountryManager?.userLocation;
        if (userLocation && this.selectedCountry) {
            // Vérifier grossièrement si la position est dans le pays
            const bounds = window.CountryManager.getCountryBounds();
            if (bounds && 
                userLocation.lat >= bounds.south && userLocation.lat <= bounds.north &&
                userLocation.lng >= bounds.west && userLocation.lng <= bounds.east) {
                defaultLat = userLocation.lat;
                defaultLng = userLocation.lng;
                defaultZoom = 12;
            }
        }

        // Initialiser Leaflet
        this.map = L.map('interactive-map').setView([defaultLat, defaultLng], defaultZoom);

        // Ajouter les tuiles OpenStreetMap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        // Si un pays est sélectionné, ajouter un rectangle pour le délimiter
        if (this.selectedCountry) {
            const bounds = window.CountryManager.getCountryBounds();
            if (bounds) {
                L.rectangle([
                    [bounds.north, bounds.east],
                    [bounds.south, bounds.west]
                ], {
                    color: "#3388ff",
                    weight: 2,
                    fillOpacity: 0.1
                }).addTo(this.map);
            }
        }

        // Ajouter un marqueur pour la position utilisateur si disponible
        if (userLocation) {
            L.marker([userLocation.lat, userLocation.lng], {
                icon: L.divIcon({
                    className: 'user-location-marker',
                    html: '<i class="fas fa-user text-blue-500 text-xl"></i>',
                    iconSize: [24, 24]
                })
            }).addTo(this.map).bindPopup('Votre position');
        }

        // Gestionnaire de clic sur la carte
        this.map.on('click', (e) => {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;

            // Vérifier que le point est dans le pays sélectionné
            if (this.selectedCountry) {
                const bounds = window.CountryManager.getCountryBounds();
                if (bounds && 
                    (lat < bounds.south || lat > bounds.north ||
                    lng < bounds.west || lng > bounds.east)) {
                    showAlert('Veuillez sélectionner un lieu dans le pays choisi', 'warning');
                    return;
                }
            }

            // Supprimer le marqueur précédent
            if (this.currentMarker) {
                this.map.removeLayer(this.currentMarker);
            }

            // Ajouter un nouveau marqueur
            this.currentMarker = L.marker([lat, lng]).addTo(this.map);

            // Mettre à jour l'info de sélection
            document.getElementById('selected-location-info').textContent = 
                `Position sélectionnée: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;

            // Activer le bouton de confirmation
            document.getElementById('confirm-map-btn').disabled = false;

            // Faire un géocodage inverse pour obtenir l'adresse
            this.reverseGeocodeForMap(lat, lng);
        });

        // Recherche sur la carte
        const mapSearch = document.getElementById('map-search');
        if (mapSearch) {
            mapSearch.addEventListener('input', (e) => {
                const query = e.target.value.trim();
                if (query.length > 2) {
                    this.searchOnMap(query);
                }
            });
        }
    }

    async reverseGeocodeForMap(lat, lng) {
        try {
            const response = await fetch('/maps/reverse-geocode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ lat, lng })
            });

            const data = await response.json();
            
            if (data.success && data.address) {
                document.getElementById('selected-location-info').textContent = 
                    `📍 ${data.address.title}`;
                
                // Stocker les données pour confirmation
                this.mapSelectedLocation = {
                    address: data.address.title,
                    label: data.address.label || data.address.title,
                    lat: parseFloat(lat),
                    lng: parseFloat(lng),
                    country: this.selectedCountry?.code
                };
            } else {
                this.mapSelectedLocation = {
                    address: `Position (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
                    label: `Coordonnées: ${lat.toFixed(6)}, ${lng.toFixed(6)}`,
                    lat: parseFloat(lat),
                    lng: parseFloat(lng),
                    country: this.selectedCountry?.code
                };
            }
        } catch (error) {
            console.error('Map reverse geocoding error:', error);
            this.mapSelectedLocation = {
                address: `Position (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
                label: `Coordonnées: ${lat.toFixed(6)}, ${lng.toFixed(6)}`,
                lat: parseFloat(lat),
                lng: parseFloat(lng),
                country: this.selectedCountry?.code
            };
        }
    }

    async searchOnMap(query) {
        try {
            const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}&country=${this.selectedCountry?.code}&limit=5`);
            const data = await response.json();
            
            if (data.success && data.suggestions && data.suggestions.length > 0) {
                const first = data.suggestions[0];
                this.map.setView([first.position.lat, first.position.lng], 15);
                
                // Ajouter un marqueur
                if (this.currentMarker) {
                    this.map.removeLayer(this.currentMarker);
                }
                this.currentMarker = L.marker([first.position.lat, first.position.lng]).addTo(this.map);
                
                // Mettre à jour l'info
                document.getElementById('selected-location-info').textContent = `📍 ${first.title}`;
                document.getElementById('confirm-map-btn').disabled = false;
                
                this.mapSelectedLocation = {
                    address: first.title,
                    label: first.label || first.title,
                    lat: parseFloat(first.position.lat),
                    lng: parseFloat(first.position.lng),
                    country: this.selectedCountry?.code
                };
            }
        } catch (error) {
            console.error('Map search error:', error);
            showAlert('Erreur lors de la recherche sur la carte', 'error');
        }
    }

    confirmMapSelection() {
        if (!this.mapSelectedLocation || !this.selectingFor) {
            showAlert('Veuillez sélectionner un lieu sur la carte avant de confirmer', 'error');
            return;
        }

        const locationData = {
            title: this.mapSelectedLocation.address,
            label: this.mapSelectedLocation.label || this.mapSelectedLocation.address,
            position: {
                lat: parseFloat(this.mapSelectedLocation.lat),
                lng: parseFloat(this.mapSelectedLocation.lng)
            },
            country: this.selectedCountry?.code
        };

        this.selectLocation(locationData, this.selectingFor);
        this.closeMapSelector();
    }

    closeMapSelector() {
        document.getElementById('map-selector-modal').classList.add('hidden');
        this.selectingFor = null;
        this.mapSelectedLocation = null;
        
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
        
        if (this.currentMarker) {
            this.currentMarker = null;
        }
    }

    validateCoordinates(type) {
        const latInput = document.getElementById(`${type}-lat`);
        const lngInput = document.getElementById(`${type}-lng`);
        
        if (!latInput || !lngInput) return;

        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);

        if (isNaN(lat) || isNaN(lng)) {
            showAlert('Coordonnées invalides', 'error');
            return;
        }

        if (lat < -90 || lat > 90) {
            showAlert('Latitude doit être entre -90 et 90', 'error');
            return;
        }

        if (lng < -180 || lng > 180) {
            showAlert('Longitude doit être entre -180 et 180', 'error');
            return;
        }

        this.reverseGeocode(lat, lng, type);
    }

    async loadFavoriteRoutes() {
        try {
            const response = await fetch('/api/saved-routes');
            if (!response.ok) return;

            const data = await response.json();
            if (data.success && data.routes) {
                this.populateFavoritesDropdowns(data.routes);
                this.displayFavoriteRoutes(data.routes);
            }
        } catch (error) {
            console.warn('Could not load favorite routes:', error);
        }
    }

    populateFavoritesDropdowns(routes) {
        const originDropdown = document.getElementById('origin-favorites');
        const destinationDropdown = document.getElementById('destination-favorites');

        if (!originDropdown || !destinationDropdown) return;

        // Réinitialiser les dropdowns
        [originDropdown, destinationDropdown].forEach(dropdown => {
            dropdown.innerHTML = '<option value="">Choisir un lieu favori...</option>';
        });

        routes.forEach(route => {
            // Option pour l'origine
            const originOption = document.createElement('option');
            originOption.value = JSON.stringify({
                title: route.origin_address,
                label: route.origin_address,
                position: { lat: route.origin_lat, lng: route.origin_lng }
            });
            originOption.textContent = `${route.name} (Départ)`;
            originDropdown.appendChild(originOption);

            // Option pour la destination
            const destOption = document.createElement('option');
            destOption.value = JSON.stringify({
                title: route.destination_address,
                label: route.destination_address,
                position: { lat: route.destination_lat, lng: route.destination_lng }
            });
            destOption.textContent = `${route.name} (Arrivée)`;
            destinationDropdown.appendChild(destOption);
        });
    }

    displayFavoriteRoutes(routes) {
        const container = document.getElementById('favorite-routes');
        if (!container) return;

        if (routes.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-500 dark:text-gray-400">Aucune route favorite</p>';
            return;
        }

        container.innerHTML = routes.slice(0, 5).map(route => `
            <button onclick="window.LocationSearch.useFavoriteRoute(${route.id})" 
                    class="w-full text-left p-2 text-sm bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
                <div class="font-medium text-gray-900 dark:text-white">${route.name}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                    ${route.origin_address} → ${route.destination_address}
                </div>
            </button>
        `).join('');
    }

    async useFavoriteRoute(routeId) {
        try {
            const response = await fetch(`/api/saved-routes/${routeId}`);
            if (!response.ok) return;

            const data = await response.json();
            if (data.success && data.route) {
                const route = data.route;
                
                // Définir l'origine
                this.selectLocation({
                    title: route.origin_address,
                    label: route.origin_address,
                    position: { lat: route.origin_lat, lng: route.origin_lng }
                }, 'origin');

                // Définir la destination
                this.selectLocation({
                    title: route.destination_address,
                    label: route.destination_address,
                    position: { lat: route.destination_lat, lng: route.destination_lng }
                }, 'destination');

                showAlert(`Route "${route.name}" chargée`, 'success');
            }
        } catch (error) {
            console.error('Error loading favorite route:', error);
            showAlert('Erreur lors du chargement de la route', 'error');
        }
    }

    saveRecentSearch(locationData) {
        try {
            const recent = JSON.parse(localStorage.getItem('recentSearches') || '[]');
            
            // Éviter les doublons
            const filtered = recent.filter(item => 
                item.address !== locationData.address || 
                Math.abs(item.lat - locationData.lat) > 0.001
            );
            
            // Ajouter en premier
            filtered.unshift(locationData);
            
            // Limiter à 10 éléments
            const limited = filtered.slice(0, 10);
            
            localStorage.setItem('recentSearches', JSON.stringify(limited));
        } catch (error) {
            console.warn('Could not save recent search:', error);
        }
    }

    loadRecentSearches() {
        try {
            const recent = JSON.parse(localStorage.getItem('recentSearches') || '[]');
            this.displayRecentSearches(recent);
        } catch (error) {
            console.warn('Could not load recent searches:', error);
        }
    }

    displayRecentSearches(searches) {
        const container = document.getElementById('recent-searches');
        if (!container) return;

        if (searches.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-500 dark:text-gray-400">Aucune recherche récente</p>';
            return;
        }

        container.innerHTML = searches.slice(0, 5).map(search => `
            <button onclick="window.LocationSearch.useRecentSearch('${encodeURIComponent(JSON.stringify(search))}')" 
                    class="w-full text-left p-2 text-sm bg-gray-50 dark:bg-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
                <div class="font-medium text-gray-900 dark:text-white">${search.address}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400">${search.label || search.address}</div>
            </button>
        `).join('');
    }

    useRecentSearch(encodedData) {
        try {
            const searchData = JSON.parse(decodeURIComponent(encodedData));
            // Permettre à l'utilisateur de choisir où utiliser cette recherche
            this.showLocationChoiceModal(searchData);
        } catch (error) {
            console.error('Error using recent search:', error);
        }
    }

    showLocationChoiceModal(locationData) {
        const choice = confirm(
            `Utiliser "${locationData.address}" comme :\n\n` +
            `OK = Point de départ\n` +
            `Annuler = Point d'arrivée`
        );
        
        const type = choice ? 'origin' : 'destination';
        this.selectLocation(locationData, type);
    }
}

// Instance globale
window.LocationSearch = new LocationSearchManager();

// Fonctions globales pour les boutons
window.setLocationMethod = (type, method) => {
    // Masquer toutes les méthodes
    document.querySelectorAll(`#${type}-section .location-input-container`).forEach(container => {
        container.classList.add('hidden');
    });
    
    // Afficher la méthode sélectionnée
    document.getElementById(`${type}-${method}-method`).classList.remove('hidden');
    
    // Mettre à jour les boutons
    document.querySelectorAll(`#${type}-section .location-method-btn`).forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`#${type}-section .location-method-btn[data-method="${method}"]`).classList.add('active');
};

window.openMapSelector = (type) => window.LocationSearch.openMapSelector(type);
window.closeMapSelector = () => window.LocationSearch.closeMapSelector();
window.confirmMapSelection = () => window.LocationSearch.confirmMapSelection();
window.validateCoordinates = (type) => window.LocationSearch.validateCoordinates(type);

// Initialisation automatique
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('origin-section')) {
        window.LocationSearch.initialize();
    }
});