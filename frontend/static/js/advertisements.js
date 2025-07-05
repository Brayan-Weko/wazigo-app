class AdvertisementManager {
    constructor() {
        this.currentAds = [];
        this.displayedAds = new Set();
        this.rotationInterval = null;
        this.rotationDelay = 30000; // 30 secondes
    }

    async initializeAdvertisements() {
        try {
            // Charger les publicités depuis l'API
            await this.loadAdvertisements();
            
            // Initialiser l'affichage
            this.setupAdContainers();
            this.displayRandomAd();
            
            // Démarrer la rotation automatique
            this.startAdRotation();
            
            console.log('✅ Advertisement system initialized');
        } catch (error) {
            console.error('❌ Failed to initialize advertisements:', error);
        }
    }

    async loadAdvertisements() {
        try {
            const response = await fetch('/api/advertisements', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.currentAds = data.ads || [];
            } else {
                // Fallback avec publicités par défaut
                this.loadDefaultAds();
            }
        } catch (error) {
            console.warn('Failed to load ads from API, using defaults');
            this.loadDefaultAds();
        }
    }

    loadDefaultAds() {
        this.currentAds = [
            {
                id: 1,
                title: '🏨 Hôtel Central - Réservez maintenant !',
                description: 'Profitez de 20% de réduction sur votre prochain séjour dans notre hôtel 4 étoiles.',
                image_url: 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&h=200&fit=crop',
                click_url: '#demo-hotel',
                ad_type: 'banner',
                cta: 'Réserver maintenant'
            },
            {
                id: 2,
                title: '🚗 Location AutoPlus - Prix imbattables',
                description: 'Voitures neuves et entretenues disponibles 24h/24. Livraison gratuite.',
                image_url: 'https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=400&h=200&fit=crop',
                click_url: '#demo-rental',
                ad_type: 'sidebar',
                cta: 'Voir les offres'
            },
            {
                id: 3,
                title: '🍕 Restaurant Le Bon Goût',
                description: 'Cuisine locale authentique préparée avec amour. Livraison gratuite sous 30min.',
                image_url: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&h=200&fit=crop',
                click_url: '#demo-restaurant',
                ad_type: 'banner',
                cta: 'Commander'
            },
            {
                id: 4,
                title: '⛽ Station Essence Eco+',
                description: 'Carburant écologique de qualité. Programme de points fidélité avantageux.',
                image_url: 'https://images.unsplash.com/photo-1545262107-70ec4f821c9d?w=400&h=200&fit=crop',
                click_url: '#demo-gas',
                ad_type: 'sidebar',
                cta: 'Localiser'
            },
            {
                id: 5,
                title: '🛠️ Garage AutoExpert',
                description: 'Réparation et entretien auto par des experts. Devis gratuit en ligne.',
                image_url: 'https://images.unsplash.com/photo-1486754735734-325b5831c3ad?w=400&h=200&fit=crop',
                click_url: '#demo-garage',
                ad_type: 'banner',
                cta: 'Devis gratuit'
            },
            {
                id: 6,
                title: '🏪 SuperMarché Fresh',
                description: 'Produits frais et locaux. Drive et livraison à domicile disponibles.',
                image_url: 'https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=400&h=200&fit=crop',
                click_url: '#demo-supermarket',
                ad_type: 'sidebar',
                cta: 'Faire ses courses'
            }
        ];
    }

    setupAdContainers() {
        const adSpace = document.getElementById('advertisement-space');
        if (!adSpace) return;

        adSpace.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
                <div class="p-2 bg-gray-100 dark:bg-gray-700 text-center">
                    <span class="text-xs text-gray-500 dark:text-gray-400">📢 Publicité</span>
                </div>
                <div id="ad-content" class="p-4">
                    <!-- Ad content will be inserted here -->
                </div>
                <div class="px-4 pb-2">
                    <div class="flex justify-between items-center">
                        <button onclick="window.AdManager.reportAd()" 
                                class="text-xs text-gray-400 hover:text-gray-600 transition-colors">
                            Signaler
                        </button>
                        <button onclick="openUpgradeModal()" 
                                class="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                            Supprimer les pubs
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    displayRandomAd() {
        if (this.currentAds.length === 0) return;

        // Sélectionner une pub non affichée récemment
        let availableAds = this.currentAds.filter(ad => !this.displayedAds.has(ad.id));
        
        // Si toutes les pubs ont été affichées, réinitialiser
        if (availableAds.length === 0) {
            this.displayedAds.clear();
            availableAds = this.currentAds;
        }

        const randomAd = availableAds[Math.floor(Math.random() * availableAds.length)];
        this.displayAd(randomAd);
        this.displayedAds.add(randomAd.id);
    }

    displayAd(ad) {
        const adContent = document.getElementById('ad-content');
        if (!adContent) return;

        // Effet de transition
        adContent.style.opacity = '0';
        
        setTimeout(() => {
            adContent.innerHTML = this.generateAdHTML(ad);
            adContent.style.opacity = '1';
            
            // Enregistrer l'impression
            this.trackImpression(ad.id);
        }, 300);
    }

    generateAdHTML(ad) {
        return `
            <div class="ad-item cursor-pointer" onclick="window.AdManager.handleAdClick(${ad.id}, '${ad.click_url}')">
                <div class="relative">
                    <img src="${ad.image_url}" 
                         alt="${ad.title}"
                         class="w-full h-32 object-cover rounded-lg"
                         onerror="this.src='https://images.unsplash.com/photo-1557804506-669a67965ba0?w=400&h=200&fit=crop'">
                    <div class="absolute top-2 right-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
                        Pub
                    </div>
                </div>
                <div class="mt-3">
                    <h4 class="font-semibold text-gray-900 dark:text-white text-sm line-clamp-2">
                        ${ad.title}
                    </h4>
                    <p class="text-gray-600 dark:text-gray-300 text-xs mt-1 line-clamp-2">
                        ${ad.description}
                    </p>
                    <div class="mt-3 flex justify-between items-center">
                        <span class="text-blue-600 dark:text-blue-400 text-sm font-medium">
                            ${ad.cta || 'En savoir plus'}
                        </span>
                        <i class="fas fa-external-link-alt text-gray-400 text-xs"></i>
                    </div>
                </div>
            </div>
        `;
    }

    handleAdClick(adId, url) {
        // Enregistrer le clic
        this.trackClick(adId);
        
        // Simuler l'ouverture du lien (en demo)
        if (url.startsWith('#demo')) {
            this.showDemoModal(url);
        } else {
            window.open(url, '_blank', 'noopener,noreferrer');
        }
    }

    showDemoModal(demoType) {
        const modals = {
            '#demo-hotel': {
                title: '🏨 Hôtel Central',
                content: 'Merci de votre intérêt ! Dans la vraie application, ceci redirigerait vers le site de l\'hôtel.'
            },
            '#demo-rental': {
                title: '🚗 Location AutoPlus',
                content: 'Merci de votre intérêt ! Dans la vraie application, ceci redirigerait vers le site de location.'
            },
            '#demo-restaurant': {
                title: '🍕 Restaurant Le Bon Goût',
                content: 'Merci de votre intérêt ! Dans la vraie application, ceci redirigerait vers le menu en ligne.'
            },
            '#demo-gas': {
                title: '⛽ Station Essence Eco+',
                content: 'Merci de votre intérêt ! Dans la vraie application, ceci redirigerait vers le localisateur de stations.'
            },
            '#demo-garage': {
                title: '🛠️ Garage AutoExpert',
                content: 'Merci de votre intérêt ! Dans la vraie application, ceci redirigerait vers le formulaire de devis.'
            },
            '#demo-supermarket': {
                title: '🏪 SuperMarché Fresh',
                content: 'Merci de votre intérêt ! Dans la vraie application, ceci redirigerait vers le site de courses en ligne.'
            }
        };

        const modal = modals[demoType];
        if (modal) {
            showAlert(`${modal.title}\n\n${modal.content}`, 'info');
        }
    }

    startAdRotation() {
        if (this.rotationInterval) {
            clearInterval(this.rotationInterval);
        }

        this.rotationInterval = setInterval(() => {
            this.displayRandomAd();
        }, this.rotationDelay);
    }

    stopAdRotation() {
        if (this.rotationInterval) {
            clearInterval(this.rotationInterval);
            this.rotationInterval = null;
        }
    }

    async trackImpression(adId) {
        try {
            await fetch('/api/advertisements/impression', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ad_id: adId })
            });
        } catch (error) {
            console.warn('Failed to track impression:', error);
        }
    }

    async trackClick(adId) {
        try {
            await fetch('/api/advertisements/click', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ad_id: adId })
            });
        } catch (error) {
            console.warn('Failed to track click:', error);
        }
    }

    reportAd() {
        const reasons = [
            'Contenu inapproprié',
            'Publicité trompeuse',
            'Contenu répétitif',
            'Ne m\'intéresse pas',
            'Autre'
        ];

        const reason = prompt(`Pourquoi signaler cette publicité ?\n\n${reasons.map((r, i) => `${i+1}. ${r}`).join('\n')}\n\nEntrez le numéro (1-${reasons.length}):`);
        
        if (reason && reason >= 1 && reason <= reasons.length) {
            showAlert(`Merci pour votre signalement. Nous examinerons cette publicité.`, 'info');
            
            // En vraie application, envoyer le signalement au serveur
            console.log('Ad reported:', reasons[reason - 1]);
        }
    }

    destroy() {
        this.stopAdRotation();
        this.currentAds = [];
        this.displayedAds.clear();
    }
}

// Instance globale
window.AdManager = new AdvertisementManager();

// Fonction d'initialisation
window.initializeAdvertisements = () => {
    window.AdManager.initializeAdvertisements();
};

// Auto-initialisation pour les utilisateurs gratuits
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si l'utilisateur doit voir des publicités
    const shouldShowAds = document.querySelector('[data-show-ads="true"]') || 
                         document.getElementById('advertisement-space');
    
    if (shouldShowAds) {
        window.AdManager.initializeAdvertisements();
    }
});

// CSS pour les publicités
const adStyles = document.createElement('style');
adStyles.textContent = `
.ad-item {
    transition: all 0.3s ease;
}

.ad-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

#ad-content {
    transition: opacity 0.3s ease;
}

.dark .ad-item:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
`;
document.head.appendChild(adStyles);