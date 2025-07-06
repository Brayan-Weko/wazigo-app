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
            
            this.addAfricaCountries();
            this.populateCountrySelect();
            console.log('✅ Countries loaded:', this.countries.length);
            
        } catch (error) {
            console.error('❌ Failed to load countries:', error);
            // Fallback avec pays populaires
            this.loadFallbackCountries();
        }
    }

    addAfricaCountries() {
        // Liste étendue de pays africains avec coordonnées précises
        const africanCountries = [
            // Afrique de l'Ouest
            { code: 'cm', name: 'Cameroon', flag: '🇨🇲', lat: 7.3697, lng: 12.3547 },
            { code: 'ng', name: 'Nigeria', flag: '🇳🇬', lat: 9.0820, lng: 8.6753 },
            { code: 'gh', name: 'Ghana', flag: '🇬🇭', lat: 7.9465, lng: -1.0232 },
            { code: 'ci', name: 'Ivory Coast', flag: '🇨🇮', lat: 7.5400, lng: -5.5471 },
            { code: 'sn', name: 'Senegal', flag: '🇸🇳', lat: 14.4974, lng: -14.4524 },
            { code: 'ml', name: 'Mali', flag: '🇲🇱', lat: 17.5707, lng: -3.9962 },
            { code: 'bf', name: 'Burkina Faso', flag: '🇧🇫', lat: 12.2383, lng: -1.5616 },
            { code: 'ne', name: 'Niger', flag: '🇳🇪', lat: 17.6078, lng: 8.0817 },
            { code: 'tg', name: 'Togo', flag: '🇹🇬', lat: 8.6195, lng: 0.8248 },
            { code: 'bj', name: 'Benin', flag: '🇧🇯', lat: 9.3077, lng: 2.3158 },
            
            // Afrique Centrale
            { code: 'ga', name: 'Gabon', flag: '🇬🇦', lat: -0.8037, lng: 11.6094 },
            { code: 'cg', name: 'Congo', flag: '🇨🇬', lat: -0.2280, lng: 15.8277 },
            { code: 'cd', name: 'DR Congo', flag: '🇨🇩', lat: -4.0383, lng: 21.7587 },
            { code: 'cf', name: 'Central African Republic', flag: '🇨🇫', lat: 6.6111, lng: 20.9394 },
            { code: 'td', name: 'Chad', flag: '🇹🇩', lat: 15.4542, lng: 18.7322 },
            { code: 'gq', name: 'Equatorial Guinea', flag: '🇬🇶', lat: 1.6508, lng: 10.2679 },
            
            // Afrique de l'Est
            { code: 'et', name: 'Ethiopia', flag: '🇪🇹', lat: 9.1450, lng: 40.4897 },
            { code: 'ke', name: 'Kenya', flag: '🇰🇪', lat: -0.0236, lng: 37.9062 },
            { code: 'tz', name: 'Tanzania', flag: '🇹🇿', lat: -6.3690, lng: 34.8888 },
            { code: 'ug', name: 'Uganda', flag: '🇺🇬', lat: 1.3733, lng: 32.2903 },
            { code: 'rw', name: 'Rwanda', flag: '🇷🇼', lat: -1.9403, lng: 29.8739 },
            { code: 'bi', name: 'Burundi', flag: '🇧🇮', lat: -3.3731, lng: 29.9189 },
            { code: 'ss', name: 'South Sudan', flag: '🇸🇸', lat: 6.8769, lng: 31.3069 },
            { code: 'dj', name: 'Djibouti', flag: '🇩🇯', lat: 11.8251, lng: 42.5903 },
            { code: 'er', name: 'Eritrea', flag: '🇪🇷', lat: 15.1794, lng: 39.7823 },
            { code: 'so', name: 'Somalia', flag: '🇸🇴', lat: 5.1521, lng: 46.1996 },
            
            // Afrique Australe
            { code: 'za', name: 'South Africa', flag: '🇿🇦', lat: -30.5595, lng: 22.9375 },
            { code: 'na', name: 'Namibia', flag: '🇳🇦', lat: -22.9576, lng: 18.4904 },
            { code: 'bw', name: 'Botswana', flag: '🇧🇼', lat: -22.3285, lng: 24.6849 },
            { code: 'zw', name: 'Zimbabwe', flag: '🇿🇼', lat: -19.0154, lng: 29.1549 },
            { code: 'zm', name: 'Zambia', flag: '🇿🇲', lat: -13.1339, lng: 27.8493 },
            { code: 'mw', name: 'Malawi', flag: '🇲🇼', lat: -13.2543, lng: 34.3015 },
            { code: 'mz', name: 'Mozambique', flag: '🇲🇿', lat: -18.6657, lng: 35.5296 },
            { code: 'mg', name: 'Madagascar', flag: '🇲🇬', lat: -18.7669, lng: 46.8691 },
            
            // Afrique du Nord
            { code: 'eg', name: 'Egypt', flag: '🇪🇬', lat: 26.8206, lng: 30.8025 },
            { code: 'ma', name: 'Morocco', flag: '🇲🇦', lat: 31.7917, lng: -7.0926 },
            { code: 'dz', name: 'Algeria', flag: '🇩🇿', lat: 28.0339, lng: 1.6596 },
            { code: 'tn', name: 'Tunisia', flag: '🇹🇳', lat: 33.8869, lng: 9.5375 },
            { code: 'ly', name: 'Libya', flag: '🇱🇾', lat: 26.3351, lng: 17.2283 },
            { code: 'sd', name: 'Sudan', flag: '🇸🇩', lat: 12.8628, lng: 30.2176 },
            { code: 'mr', name: 'Mauritania', flag: '🇲🇷', lat: 21.0079, lng: -10.9408 }
        ];

        // Fusionner avec les pays existants (en évitant les doublons)
        africanCountries.forEach(africanCountry => {
            if (!this.countries.some(c => c.code === africanCountry.code)) {
                this.countries.push(africanCountry);
            }
        });

        // Trier à nouveau
        this.countries.sort((a, b) => a.name.localeCompare(b.name));
    }

    loadFallbackCountries() {
        this.countries = [
            { code: 'cm', name: 'Cameroon', flag: '🇨🇲', lat: 7.3697, lng: 12.3547 },
            { code: 'et', name: 'Ethiopia', flag: '🇪🇹', lat: 9.1450, lng: 40.4897 },
            { code: 'ng', name: 'Nigeria', flag: '🇳🇬', lat: 9.0820, lng: 8.6753 },
            { code: 'za', name: 'South Africa', flag: '🇿🇦', lat: -30.5595, lng: 22.9375 },
            { code: 'ke', name: 'Kenya', flag: '🇰🇪', lat: -0.0236, lng: 37.9062 },
            { code: 'eg', name: 'Egypt', flag: '🇪🇬', lat: 26.8206, lng: 30.8025 },
            { code: 'ma', name: 'Morocco', flag: '🇲🇦', lat: 31.7917, lng: -7.0926 },
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

                // Créer un mappage des noms de pays alternatifs
                const countryNameMappings = {
                    'cameroon': 'cameroon', // anglais
                    'cameroun': 'cameroon', // français
                    'kamerun': 'cameroon',  // allemand
                    // Ajoutez d'autres mappings au besoin
                };

                // Normaliser le nom du pays détecté
                const normalizedDetectedCountry = locationInfo.country.toLowerCase().trim();
                const mappedCountryName = countryNameMappings[normalizedDetectedCountry] || normalizedDetectedCountry;

                const countryOption = Array.from(countrySelect.options).find(option => {
                    const optionText = option.textContent.toLowerCase();
                    const optionCountry = this.countries.find(c => c.code === option.value);
                    
                    // Vérifier plusieurs possibilités
                    return (
                        optionText.includes(locationInfo.country.toLowerCase()) || // Nom complet
                        option.value === this.getCountryCodeFromName(locationInfo.country) || // Code pays
                        (optionCountry && optionCountry.name.toLowerCase() === locationInfo.country.toLowerCase()) // Nom en anglais
                    );
                });

                if (countryOption) {
                    countrySelect.value = countryOption.value;
                    this.onCountryChange();
                    
                    // Définir automatiquement comme point de départ
                    this.setOriginFromLocation(locationInfo);
                    
                    showAlert(`Position détectée: ${locationInfo.display_name}`, 'success');
                } else {
                    console.warn('Pays non trouvé:', locationInfo.country, 'Options disponibles:', 
                    Array.from(countrySelect.options).map(o => o.textContent));
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

    getCountryCodeFromName(countryName) {
        // Mappage des noms de pays aux codes pays
        const countryMappings = {
            'cameroon': 'cm',
            'cameroun': 'cm',
            'ethiopia': 'et',
            'éthiopie': 'et',
            // Ajoutez d'autres pays au besoin
        };

        return countryMappings[countryName.toLowerCase()];
    }

    getCountryBounds() {
        if (!this.selectedCountry) return null;
        
        // Ces valeurs pourraient être améliorées avec des données plus précises
        // ou en utilisant une API de géolocalisation pour obtenir les vraies frontières
        return {
            north: this.selectedCountry.lat + 5,
            south: this.selectedCountry.lat - 5,
            east: this.selectedCountry.lng + 5,
            west: this.selectedCountry.lng - 5
        };
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