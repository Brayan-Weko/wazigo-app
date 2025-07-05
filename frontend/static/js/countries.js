class CountryManager {
    constructor() {
        this.countries = [];
        this.selectedCountry = null;
        this.userLocation = null;
    }

    async loadCountries() {
        try {
            // Charger la liste des pays depuis une API gratuite
            const response = await fetch('https://restcountries.com/v3.1/all?fields=name,cca2,flag,latlng');
            const countriesData = await response.json();
            
            this.countries = countriesData
                .map(country => ({
                    code: country.cca2.toLowerCase(),
                    name: country.name.common,
                    flag: country.flag,
                    lat: country.latlng?.[0] || 0,
                    lng: country.latlng?.[1] || 0
                }))
                .sort((a, b) => a.name.localeCompare(b.name));
            
            this.populateCountrySelect();
            console.log('✅ Countries loaded:', this.countries.length);
            
        } catch (error) {
            console.error('❌ Failed to load countries:', error);
            // Fallback avec pays populaires
            this.loadFallbackCountries();
        }
    }

    loadFallbackCountries() {
        this.countries = [
            { code: 'fr', name: 'France', flag: '🇫🇷', lat: 46.2276, lng: 2.2137 },
            { code: 'de', name: 'Germany', flag: '🇩🇪', lat: 51.1657, lng: 10.4515 },
            { code: 'us', name: 'United States', flag: '🇺🇸', lat: 37.0902, lng: -95.7129 },
            { code: 'gb', name: 'United Kingdom', flag: '🇬🇧', lat: 55.3781, lng: -3.4360 },
            { code: 'es', name: 'Spain', flag: '🇪🇸', lat: 40.4637, lng: -3.7492 },
            { code: 'it', name: 'Italy', flag: '🇮🇹', lat: 41.8719, lng: 12.5674 },
            { code: 'ca', name: 'Canada', flag: '🇨🇦', lat: 56.1304, lng: -106.3468 },
            { code: 'au', name: 'Australia', flag: '🇦🇺', lat: -25.2744, lng: 133.7751 },
            { code: 'jp', name: 'Japan', flag: '🇯🇵', lat: 36.2048, lng: 138.2529 },
            { code: 'br', name: 'Brazil', flag: '🇧🇷', lat: -14.2350, lng: -51.9253 },
            { code: 'in', name: 'India', flag: '🇮🇳', lat: 20.5937, lng: 78.9629 },
            { code: 'cn', name: 'China', flag: '🇨🇳', lat: 35.8617, lng: 104.1954 }
        ];
        this.populateCountrySelect();
    }

    populateCountrySelect() {
        const select = document.getElementById('country-select');
        if (!select) return;

        // Vider les options existantes
        select.innerHTML = '<option value="">Choisir un pays...</option>';

        // Ajouter les pays
        this.countries.forEach(country => {
            const option = document.createElement('option');
            option.value = country.code;
            option.textContent = `${country.flag} ${country.name}`;
            option.dataset.lat = country.lat;
            option.dataset.lng = country.lng;
            select.appendChild(option);
        });
    }

    onCountryChange() {
        const select = document.getElementById('country-select');
        const flagElement = document.getElementById('country-flag');
        
        if (select.value) {
            const selectedOption = select.selectedOptions[0];
            const country = this.countries.find(c => c.code === select.value);
            
            if (country) {
                this.selectedCountry = country;
                flagElement.textContent = country.flag;
                
                // Afficher les sections de sélection de lieux
                this.showLocationSections();
                
                // Réinitialiser les autocompletions avec le nouveau pays
                this.resetLocationSelections();
                
                console.log('✅ Country selected:', country);
            }
        } else {
            this.selectedCountry = null;
            flagElement.textContent = '';
            this.hideLocationSections();
        }
    }

    showLocationSections() {
        document.getElementById('origin-section').style.display = 'block';
        document.getElementById('destination-section').style.display = 'block';
        document.getElementById('advanced-options').style.display = 'block';
        document.getElementById('submit-section').style.display = 'block';
    }

    hideLocationSections() {
        document.getElementById('origin-section').style.display = 'none';
        document.getElementById('destination-section').style.display = 'none';
        document.getElementById('advanced-options').style.display = 'none';
        document.getElementById('submit-section').style.display = 'none';
    }

    resetLocationSelections() {
        // Réinitialiser les sélections de lieux
        window.selectedOrigin = null;
        window.selectedDestination = null;
        
        // Vider les champs de recherche
        document.getElementById('origin-search').value = '';
        document.getElementById('destination-search').value = '';
        
        // Masquer les suggestions
        document.getElementById('origin-suggestions').classList.add('hidden');
        document.getElementById('destination-suggestions').classList.add('hidden');
    }

    async detectLocation() {
        if (!navigator.geolocation) {
            showAlert('La géolocalisation n\'est pas supportée par votre navigateur', 'error');
            return;
        }

        const button = document.querySelector('button[onclick="detectLocation()"]');
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Détection...';
        button.disabled = true;

        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                });
            });

            const { latitude, longitude } = position.coords;
            this.userLocation = { lat: latitude, lng: longitude };

            // Géocodage inverse pour obtenir le pays
            const locationInfo = await this.reverseGeocode(latitude, longitude);
            
            if (locationInfo && locationInfo.country) {
                // Sélectionner automatiquement le pays
                const countrySelect = document.getElementById('country-select');
                const countryOption = Array.from(countrySelect.options).find(option => 
                    option.textContent.toLowerCase().includes(locationInfo.country.toLowerCase())
                );

                if (countryOption) {
                    countrySelect.value = countryOption.value;
                    this.onCountryChange();
                    
                    // Définir automatiquement comme point de départ
                    this.setOriginFromLocation(locationInfo);
                    
                    showAlert(`Position détectée: ${locationInfo.display_name}`, 'success');
                } else {
                    showAlert(`Pays détecté (${locationInfo.country}) non trouvé dans la liste`, 'warning');
                }
            }

        } catch (error) {
            console.error('Geolocation error:', error);
            let errorMessage = 'Erreur de géolocalisation';
            
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage = 'Accès à la localisation refusé';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage = 'Position indisponible';
                    break;
                case error.TIMEOUT:
                    errorMessage = 'Délai de géolocalisation dépassé';
                    break;
            }
            
            showAlert(errorMessage, 'error');
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    async reverseGeocode(lat, lng) {
        try {
            // Utiliser Nominatim (OpenStreetMap) pour le géocodage inverse gratuit
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`
            );
            
            if (response.ok) {
                const data = await response.json();
                return {
                    display_name: data.display_name,
                    country: data.address?.country,
                    city: data.address?.city || data.address?.town || data.address?.village,
                    postcode: data.address?.postcode,
                    lat: parseFloat(data.lat),
                    lng: parseFloat(data.lon)
                };
            }
        } catch (error) {
            console.error('Reverse geocoding error:', error);
        }
        return null;
    }

    setOriginFromLocation(locationInfo) {
        window.selectedOrigin = {
            address: locationInfo.display_name,
            lat: locationInfo.lat,
            lng: locationInfo.lng,
            country: this.selectedCountry?.code
        };

        // Mettre à jour l'interface
        document.getElementById('origin-search').value = locationInfo.display_name;
        showAlert('Point de départ défini automatiquement', 'info');
    }

    getSelectedCountry() {
        return this.selectedCountry;
    }

    getCountryBounds() {
        if (!this.selectedCountry) return null;
        
        // Retourner des bounds approximatifs pour le pays sélectionné
        // Ceci pourrait être amélioré avec des données plus précises
        return {
            north: this.selectedCountry.lat + 5,
            south: this.selectedCountry.lat - 5,
            east: this.selectedCountry.lng + 5,
            west: this.selectedCountry.lng - 5
        };
    }
}

// Instance globale
window.CountryManager = new CountryManager();

// Fonctions globales pour l'interface
window.loadCountries = () => window.CountryManager.loadCountries();
window.onCountryChange = () => window.CountryManager.onCountryChange();
window.detectLocation = () => window.CountryManager.detectLocation();

// Initialisation automatique
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('country-select')) {
        window.CountryManager.loadCountries();
    }
});