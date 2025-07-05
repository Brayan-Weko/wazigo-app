class AutocompleteManager {
    constructor() {
        this.cache = new Map();
        this.debounceTimeout = null;
        this.debounceDelay = 300;
        this.minQueryLength = 2;
        this.maxSuggestions = 8;
        this.recentSearches = this.loadRecentSearches();
        this.favorites = [];
    }

    // Initialize autocomplete for an input element
    setupAutocomplete(inputElement, suggestionsContainer, options = {}) {
        if (!inputElement || !suggestionsContainer) {
            console.error('Input element or suggestions container not found');
            return;
        }

        const config = {
            minLength: this.minQueryLength,
            maxSuggestions: this.maxSuggestions,
            showRecent: true,
            showFavorites: true,
            ...options
        };

        // Store configuration on element
        inputElement._autocompleteConfig = config;
        inputElement._suggestionsContainer = suggestionsContainer;

        // Setup event listeners
        this.setupEventListeners(inputElement, suggestionsContainer, config);
        
        console.log('✅ Autocomplete setup completed for', inputElement.id);
    }

    setupEventListeners(input, container, config) {
        // Input event - trigger search
        input.addEventListener('input', (e) => {
            this.handleInput(input, container, config);
        });

        // Focus event - show recent/favorites
        input.addEventListener('focus', (e) => {
            if (input.value.length === 0 && config.showRecent) {
                this.showRecentSearches(container, input);
            }
        });

        // Blur event - hide suggestions (with delay for clicks)
        input.addEventListener('blur', (e) => {
            setTimeout(() => {
                this.hideSuggestions(container);
            }, 150);
        });

        // Keyboard navigation
        input.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e, container, input);
        });

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !container.contains(e.target)) {
                this.hideSuggestions(container);
            }
        });
    }

    handleInput(input, container, config) {
        const query = input.value.trim();

        // Clear existing timeout
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }

        if (query.length < config.minLength) {
            this.hideSuggestions(container);
            return;
        }

        // Debounce the search
        this.debounceTimeout = setTimeout(() => {
            this.performSearch(query, container, input, config);
        }, this.debounceDelay);
    }

    async performSearch(query, container, input, config) {
        try {
            // Show loading state
            this.showLoading(container);

            // Check cache first
            const cacheKey = `search_${query.toLowerCase()}`;
            if (this.cache.has(cacheKey)) {
                const cachedResults = this.cache.get(cacheKey);
                this.displaySuggestions(cachedResults, container, input);
                return;
            }

            // Perform API search
            const results = await this.searchAddresses(query, config);
            
            // Cache results
            this.cache.set(cacheKey, results);
            
            // Display results
            this.displaySuggestions(results, container, input);

        } catch (error) {
            console.error('Autocomplete search error:', error);
            this.showError(container);
        }
    }

    async searchAddresses(query, config) {
        // Try multiple sources for better results
        const sources = [
            () => this.searchHereAPI(query),
            () => this.searchLocalAPI(query),
            () => this.searchRecentMatches(query)
        ];

        let allResults = [];

        for (const source of sources) {
            try {
                const results = await source();
                allResults = allResults.concat(results);
            } catch (error) {
                console.warn('Search source failed:', error);
            }
        }

        // Remove duplicates and limit results
        const uniqueResults = this.removeDuplicates(allResults);
        return uniqueResults.slice(0, config.maxSuggestions);
    }

    async searchHereAPI(query) {
        if (!window.MapManager || !window.MapManager.platform) {
            return [];
        }

        try {
            return await window.MapManager.geocode(query);
        } catch (error) {
            console.warn('HERE API search failed:', error);
            return [];
        }
    }

    async searchLocalAPI(query) {
        try {
            const response = await fetch('/api/autocomplete?' + new URLSearchParams({
                q: query,
                limit: this.maxSuggestions
            }));

            const data = await response.json();
            return data.success ? data.suggestions : [];
        } catch (error) {
            console.warn('Local API search failed:', error);
            return [];
        }
    }

    searchRecentMatches(query) {
        const queryLower = query.toLowerCase();
        return this.recentSearches.filter(item => 
            item.title.toLowerCase().includes(queryLower) ||
            item.label.toLowerCase().includes(queryLower)
        );
    }

    removeDuplicates(results) {
        const seen = new Set();
        return results.filter(item => {
            const key = `${item.title}_${item.position?.lat}_${item.position?.lng}`;
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        });
    }

    displaySuggestions(suggestions, container, input) {
        container.innerHTML = '';

        if (!suggestions || suggestions.length === 0) {
            this.showNoResults(container);
            return;
        }

        suggestions.forEach((suggestion, index) => {
            const item = this.createSuggestionItem(suggestion, index);
            item.addEventListener('click', () => {
                this.selectSuggestion(suggestion, input, container);
            });
            container.appendChild(item);
        });

        container.classList.remove('hidden');
    }

    createSuggestionItem(suggestion, index) {
        const item = document.createElement('div');
        item.className = 'autocomplete-item px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-600 last:border-b-0';
        item.setAttribute('data-index', index);

        // Determine suggestion type and icon
        const type = this.getSuggestionType(suggestion);
        const icon = this.getSuggestionIcon(type);

        item.innerHTML = `
            <div class="flex items-center">
                <div class="w-8 h-8 flex items-center justify-center mr-3 flex-shrink-0">
                    <i class="${icon} text-gray-400"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="font-medium text-gray-900 dark:text-white truncate">
                        ${this.highlightMatch(suggestion.title, input.value)}
                    </div>
                    <div class="text-sm text-gray-500 dark:text-gray-400 truncate">
                        ${suggestion.label || suggestion.address || ''}
                    </div>
                    ${suggestion.distance ? `
                        <div class="text-xs text-gray-400 mt-1">
                            ${this.formatDistance(suggestion.distance)}
                        </div>
                    ` : ''}
                </div>
                ${this.isFavorite(suggestion) ? `
                    <div class="ml-2">
                        <i class="fas fa-star text-yellow-500"></i>
                    </div>
                ` : ''}
            </div>
        `;

        return item;
    }

    getSuggestionType(suggestion) {
        if (suggestion.categories) {
            if (suggestion.categories.includes('place')) return 'place';
            if (suggestion.categories.includes('building')) return 'building';
            if (suggestion.categories.includes('street')) return 'street';
        }
        
        if (suggestion.type === 'recent') return 'recent';
        if (suggestion.type === 'favorite') return 'favorite';
        
        return 'location';
    }

    getSuggestionIcon(type) {
        const icons = {
            place: 'fas fa-map-marker-alt',
            building: 'fas fa-building',
            street: 'fas fa-road',
            recent: 'fas fa-history',
            favorite: 'fas fa-star',
            location: 'fas fa-map-pin'
        };
        return icons[type] || icons.location;
    }

    highlightMatch(text, query) {
        if (!query) return text;
        
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800 text-inherit">$1</mark>');
    }

    formatDistance(meters) {
        if (meters < 1000) {
            return `${Math.round(meters)}m`;
        } else {
            return `${(meters / 1000).toFixed(1)}km`;
        }
    }

    selectSuggestion(suggestion, input, container) {
        // Set input value
        input.value = suggestion.title;
        
        // Hide suggestions
        this.hideSuggestions(container);
        
        // Add to recent searches
        this.addToRecentSearches(suggestion);
        
        // Trigger custom event
        input.dispatchEvent(new CustomEvent('suggestionSelected', {
            detail: suggestion
        }));

        // Track selection
        this.trackSuggestionSelection(suggestion);
    }

    addToRecentSearches(suggestion) {
        const item = {
            title: suggestion.title,
            label: suggestion.label || suggestion.address,
            position: suggestion.position,
            timestamp: Date.now(),
            type: 'recent'
        };

        // Remove if already exists
        this.recentSearches = this.recentSearches.filter(recent => 
            recent.title !== item.title
        );

        // Add to beginning
        this.recentSearches.unshift(item);

        // Limit to 10 items
        this.recentSearches = this.recentSearches.slice(0, 10);

        // Save to storage
        this.saveRecentSearches();
    }

    showRecentSearches(container, input) {
        if (this.recentSearches.length === 0) {
            this.showNoRecent(container);
            return;
        }

        container.innerHTML = '';

        // Add header
        const header = document.createElement('div');
        header.className = 'px-4 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-50 dark:bg-gray-800';
        header.textContent = 'Recherches récentes';
        container.appendChild(header);

        // Add recent items
        this.recentSearches.slice(0, 5).forEach((item, index) => {
            const suggestionItem = this.createSuggestionItem(item, index);
            suggestionItem.addEventListener('click', () => {
                this.selectSuggestion(item, input, container);
            });
            container.appendChild(suggestionItem);
        });

        // Add clear option
        const clearItem = document.createElement('div');
        clearItem.className = 'px-4 py-3 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer border-t border-gray-200 dark:border-gray-600';
        clearItem.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-trash mr-3"></i>
                Effacer l'historique
            </div>
        `;
        clearItem.addEventListener('click', () => {
            this.clearRecentSearches();
            this.hideSuggestions(container);
        });
        container.appendChild(clearItem);

        container.classList.remove('hidden');
    }

    handleKeyNavigation(e, container, input) {
        const items = container.querySelectorAll('.autocomplete-item');
        if (items.length === 0) return;

        const currentActive = container.querySelector('.autocomplete-item.active');
        let currentIndex = -1;

        if (currentActive) {
            currentIndex = parseInt(currentActive.getAttribute('data-index'));
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                const nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
                this.setActiveItem(items, nextIndex);
                break;

            case 'ArrowUp':
                e.preventDefault();
                const prevIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
                this.setActiveItem(items, prevIndex);
                break;

            case 'Enter':
                e.preventDefault();
                if (currentActive) {
                    currentActive.click();
                }
                break;

            case 'Escape':
                this.hideSuggestions(container);
                input.blur();
                break;
        }
    }

    setActiveItem(items, index) {
        // Remove active class from all items
        items.forEach(item => item.classList.remove('active', 'bg-gray-100', 'dark:bg-gray-700'));
        
        // Add active class to selected item
        if (items[index]) {
            items[index].classList.add('active', 'bg-gray-100', 'dark:bg-gray-700');
            
            // Scroll into view if needed
            items[index].scrollIntoView({ block: 'nearest' });
        }
    }

    showLoading(container) {
        container.innerHTML = `
            <div class="px-4 py-8 text-center">
                <div class="inline-block w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin mb-2"></div>
                <div class="text-sm text-gray-500 dark:text-gray-400">Recherche en cours...</div>
            </div>
        `;
        container.classList.remove('hidden');
    }

    showNoResults(container) {
        container.innerHTML = `
            <div class="px-4 py-8 text-center">
                <i class="fas fa-search text-2xl text-gray-300 dark:text-gray-600 mb-2"></i>
                <div class="text-sm text-gray-500 dark:text-gray-400">Aucun résultat trouvé</div>
            </div>
        `;
        container.classList.remove('hidden');
    }

    showNoRecent(container) {
        container.innerHTML = `
            <div class="px-4 py-8 text-center">
                <i class="fas fa-history text-2xl text-gray-300 dark:text-gray-600 mb-2"></i>
                <div class="text-sm text-gray-500 dark:text-gray-400">Aucune recherche récente</div>
            </div>
        `;
        container.classList.remove('hidden');
    }

    showError(container) {
        container.innerHTML = `
            <div class="px-4 py-8 text-center">
                <i class="fas fa-exclamation-triangle text-2xl text-red-400 mb-2"></i>
                <div class="text-sm text-red-600 dark:text-red-400">Erreur de recherche</div>
            </div>
        `;
        container.classList.remove('hidden');
    }

    hideSuggestions(container) {
        container.classList.add('hidden');
        container.innerHTML = '';
    }

    // Favorites management
    isFavorite(suggestion) {
        return this.favorites.some(fav => 
            fav.title === suggestion.title && 
            fav.position?.lat === suggestion.position?.lat
        );
    }

    toggleFavorite(suggestion) {
        const index = this.favorites.findIndex(fav => 
            fav.title === suggestion.title && 
            fav.position?.lat === suggestion.position?.lat
        );

        if (index >= 0) {
            this.favorites.splice(index, 1);
            return false;
        } else {
            this.favorites.push({
                ...suggestion,
                type: 'favorite',
                timestamp: Date.now()
            });
            return true;
        }
    }

    // Storage methods
    loadRecentSearches() {
        try {
            const stored = localStorage.getItem('autocomplete_recent');
            return stored ? JSON.parse(stored) : [];
        } catch (error) {
            console.warn('Failed to load recent searches:', error);
            return [];
        }
    }

    saveRecentSearches() {
        try {
            localStorage.setItem('autocomplete_recent', JSON.stringify(this.recentSearches));
        } catch (error) {
            console.warn('Failed to save recent searches:', error);
        }
    }

    clearRecentSearches() {
        this.recentSearches = [];
        this.saveRecentSearches();
    }

    // Analytics
    trackSuggestionSelection(suggestion) {
        if (window.trackEvent) {
            window.trackEvent('autocomplete_selection', {
                type: suggestion.type || 'search',
                title: suggestion.title,
                source: suggestion.source || 'api'
            });
        }
    }

    // Public API methods
    updateConfig(inputElement, newConfig) {
        if (inputElement._autocompleteConfig) {
            inputElement._autocompleteConfig = {
                ...inputElement._autocompleteConfig,
                ...newConfig
            };
        }
    }

    clearCache() {
        this.cache.clear();
    }

    destroy(inputElement) {
        if (inputElement._suggestionsContainer) {
            this.hideSuggestions(inputElement._suggestionsContainer);
        }
        
        // Remove event listeners would require storing references
        // For now, just clear the configuration
        delete inputElement._autocompleteConfig;
        delete inputElement._suggestionsContainer;
    }
}

// Create global instance
window.AutocompleteManager = new AutocompleteManager();

// Global setup function for easy use
window.setupAutocomplete = function(inputId, containerId, options = {}) {
    const input = document.getElementById(inputId);
    const container = document.getElementById(containerId);
    
    if (input && container) {
        window.AutocompleteManager.setupAutocomplete(input, container, options);
        return true;
    } else {
        console.error(`Autocomplete setup failed: input (${inputId}) or container (${containerId}) not found`);
        return false;
    }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutocompleteManager;
}