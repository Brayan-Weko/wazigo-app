class SubscriptionManager {
    constructor() {
        this.plans = [];
        this.currentSubscription = null;
        this.isProcessingPayment = false;
    }

    async loadSubscriptionData() {
        try {
            const response = await fetch('/api/subscription/plans');
            if (response.ok) {
                const data = await response.json();
                this.plans = data.plans;
                this.currentSubscription = data.current_subscription;
            }
        } catch (error) {
            console.error('Failed to load subscription data:', error);
        }
    }

    openUpgradeModal() {
        this.createUpgradeModal();
        document.getElementById('upgrade-modal').classList.remove('hidden');
    }

    createUpgradeModal() {
        const modal = document.getElementById('upgrade-modal');
        if (!modal) return;

        modal.innerHTML = `
            <div class="modal-content max-w-4xl w-full mx-4">
                <div class="bg-gradient-to-br from-primary-600 to-green-800 text-white p-6 rounded-t-xl">
                    <div class="flex items-center justify-between">
                        <div>
                            <h2 class="text-2xl font-bold"><i class="fas fa-crown text-yellow-400"></i> Passez au Premium</h2>
                            <p class="text-purple-100 mt-1">Débloquez toutes les fonctionnalités avancées</p>
                        </div>
                        <button onclick="closeUpgradeModal()" class="text-white/80 hover:text-white">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                </div>

                <div class="p-6">
                    <!-- Feature Comparison -->
                    <div class="mb-8">
                        <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-6 text-center">
                            Comparaison des fonctionnalités
                        </h3>
                        
                        <div class="overflow-x-auto">
                            <table class="w-full text-sm">
                                <thead>
                                    <tr class="border-b border-gray-200 dark:border-gray-700">
                                        <th class="text-left py-3 px-4">Fonctionnalité</th>
                                        <th class="text-center py-3 px-4">
                                            <div class="text-gray-600 dark:text-gray-300">Gratuit</div>
                                        </th>
                                        <th class="text-center py-3 px-4">
                                            <div class="bg-gradient-to-r from-primary-500 to-green-500 text-white px-3 py-1 rounded-full text-xs font-medium">
                                                <i class="fas fa-crown text-yellow-400 mr-1"></i> Premium
                                            </div>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody class="text-gray-700 dark:text-gray-300">
                                    <tr class="border-b border-gray-100 dark:border-gray-800">
                                        <td class="py-3 px-4"><i class="fas fa-map-marked-alt text-blue-500 mr-1"></i> Carte trafic</td>
                                        <td class="text-center py-3 px-4">45km de rayon</td>
                                        <td class="text-center py-3 px-4 text-green-600 dark:text-green-400 font-medium">Illimitée</td>
                                    </tr>
                                    <tr class="border-b border-gray-100 dark:border-gray-800">
                                        <td class="py-3 px-4"><i class="fas fa-globe-americas text-green-500 mr-1"></i> Accès pays</td>
                                        <td class="text-center py-3 px-4">1 pays</td>
                                        <td class="text-center py-3 px-4 text-green-600 dark:text-green-400 font-medium">Monde entier</td>
                                    </tr>
                                    <tr class="border-b border-gray-100 dark:border-gray-800">
                                        <td class="py-3 px-4"><i class="fas fa-search text-purple-500 mr-1"></i> Recherches quotidiennes</td>
                                        <td class="text-center py-3 px-4">50 / jour</td>
                                        <td class="text-center py-3 px-4 text-green-600 dark:text-green-400 font-medium">Illimitées</td>
                                    </tr>
                                    <tr class="border-b border-gray-100 dark:border-gray-800">
                                        <td class="py-3 px-4"><i class="fas fa-ad text-orange-500 mr-1"></i> Publicités</td>
                                        <td class="text-center py-3 px-4">
                                            <i class="fas fa-times text-red-500"></i>
                                        </td>
                                        <td class="text-center py-3 px-4">
                                            <i class="fas fa-check text-green-500"></i> Sans pub
                                        </td>
                                    </tr>
                                    <tr class="border-b border-gray-100 dark:border-gray-800">
                                        <td class="py-3 px-4"><i class="fas fa-bell text-red-500 mr-1"></i> Alertes vocales</td>
                                        <td class="text-center py-3 px-4">Basiques</td>
                                        <td class="text-center py-3 px-4 text-green-600 dark:text-green-400 font-medium">Avancées</td>
                                    </tr>
                                    <tr class="border-b border-gray-100 dark:border-gray-800">
                                        <td class="py-3 px-4"><i class="fas fa-route text-indigo-500 mr-1"></i> Types d'itinéraires</td>
                                        <td class="text-center py-3 px-4">Standard</td>
                                        <td class="text-center py-3 px-4 text-green-600 dark:text-green-400 font-medium">+ Éco, Panoramique</td>
                                    </tr>
                                    <tr class="border-b border-gray-100 dark:border-gray-800">
                                        <td class="py-3 px-4"><i class="fas fa-wifi text-gray-500 mr-1"></i> Mode hors ligne</td>
                                        <td class="text-center py-3 px-4">Basique</td>
                                        <td class="text-center py-3 px-4 text-green-600 dark:text-green-400 font-medium">Avancé</td>
                                    </tr>
                                    <tr>
                                        <td class="py-3 px-4"><i class="fas fa-headset text-teal-500 mr-1"></i> Support prioritaire</td>
                                        <td class="text-center py-3 px-4">
                                            <i class="fas fa-times text-red-500"></i>
                                        </td>
                                        <td class="text-center py-3 px-4">
                                            <i class="fas fa-check text-green-500"></i>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Pricing Plans -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                        <!-- Monthly Plan -->
                        <div class="border-2 border-gray-200 dark:border-gray-700 rounded-xl p-6 hover:border-primary-300 dark:hover:border-primary-600 transition-colors">
                            <div class="text-center">
                                <h4 class="text-lg font-semibold text-gray-900 dark:text-white">Mensuel</h4>
                                <div class="mt-4">
                                    <span class="text-3xl font-bold text-gray-900 dark:text-white">2$</span>
                                    <span class="text-gray-500 dark:text-gray-400">/mois</span>
                                </div>
                                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">≈ 1 200 FCFA</div>
                                <button onclick="selectPlan('monthly')" 
                                        class="w-full mt-6 btn-primary">
                                    Choisir Mensuel
                                </button>
                            </div>
                        </div>

                        <!-- Yearly Plan (Recommended) -->
                        <div class="border-2 border-primary-500 rounded-xl p-6 relative bg-gradient-to-br from-primary-50 to-pink-50 dark:from-primary-900/20 dark:to-pink-900/20">
                            <div class="absolute -top-3 left-1/2 transform -translate-x-1/2">
                                <span class="bg-primary-500 text-white px-3 py-1 rounded-full text-xs font-medium">
                                    <i class="fas fa-fire text-orange-300 mr-1"></i> Recommandé
                                </span>
                            </div>
                            <div class="text-center">
                                <h4 class="text-lg font-semibold text-gray-900 dark:text-white">Annuel</h4>
                                <div class="mt-4">
                                    <span class="text-3xl font-bold text-gray-900 dark:text-white">20$</span>
                                    <span class="text-gray-500 dark:text-gray-400">/an</span>
                                </div>
                                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">≈ 12 000 FCFA</div>
                                <div class="text-sm text-green-600 dark:text-green-400 font-medium mt-1">
                                    Économisez 17% !
                                </div>
                                <button onclick="selectPlan('yearly')" 
                                        class="w-full mt-6 btn-primary bg-gradient-to-r from-primary-600 to-green-600 hover:from-primary-700 hover:to-green-700">
                                    Choisir Annuel
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Payment Simulation -->
                    <div id="payment-section" class="hidden">
                        <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                            <i class="fas fa-credit-card text-purple-500"></i> Simulation de paiement
                        </h3>
                        
                        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                            <div class="flex items-center">
                                <i class="fas fa-info-circle text-blue-600 dark:text-blue-400 mr-2"></i>
                                <span class="text-blue-800 dark:text-blue-200 text-sm">
                                    <strong>Mode démonstration</strong> - Aucun paiement réel ne sera effectué
                                </span>
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <!-- Payment Methods -->
                            <div>
                                <h4 class="font-medium text-gray-900 dark:text-white mb-3">Méthode de paiement</h4>
                                <div class="space-y-3">
                                    <label class="flex items-center p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                                        <input type="radio" name="payment_method" value="card" class="radio" checked>
                                        <div class="ml-3 flex items-center">
                                            <i class="fas fa-credit-card text-blue-600 mr-2"></i>
                                            <span>Carte bancaire</span>
                                        </div>
                                    </label>
                                    <label class="flex items-center p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                                        <input type="radio" name="payment_method" value="paypal" class="radio">
                                        <div class="ml-3 flex items-center">
                                            <i class="fab fa-paypal text-blue-600 mr-2"></i>
                                            <span>PayPal</span>
                                        </div>
                                    </label>
                                    <label class="flex items-center p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                                        <input type="radio" name="payment_method" value="mobile" class="radio">
                                        <div class="ml-3 flex items-center">
                                            <i class="fas fa-mobile-alt text-green-600 mr-2"></i>
                                            <span>Paiement mobile</span>
                                        </div>
                                    </label>
                                </div>
                            </div>

                            <!-- Order Summary -->
                            <div>
                                <h4 class="font-medium text-gray-900 dark:text-white mb-3">Récapitulatif</h4>
                                <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                                    <div id="order-summary">
                                        <!-- Will be populated by selectPlan() -->
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="mt-6 flex space-x-4">
                            <button onclick="hidePaymentSection()" class="btn-secondary flex-1">
                                Retour
                            </button>
                            <button onclick="processPayment()" id="process-payment-btn" class="btn-primary flex-1">
                                <i class="fas fa-lock mr-2"></i>
                                Simuler le paiement
                            </button>
                        </div>
                    </div>

                    <!-- Testimonials -->
                    <div class="mt-8 bg-gray-50 dark:bg-gray-800 rounded-lg p-6">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4 text-center">
                            Ce que disent nos utilisateurs Premium
                        </h3>
                        
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="text-center">
                                <div class="text-yellow-400 mb-2"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i></div>
                                <p class="text-sm text-gray-600 dark:text-gray-300 italic">
                                    "Les itinéraires panoramiques m'ont fait découvrir des endroits magnifiques !"
                                </p>
                                <div class="text-xs text-gray-500 dark:text-gray-400 mt-2">- Marie L.</div>
                            </div>
                            <div class="text-center">
                                <div class="text-yellow-400 mb-2"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i></div>
                                <p class="text-sm text-gray-600 dark:text-gray-300 italic">
                                    "Fini les embouteillages ! Le mode Premium m'a fait économiser des heures."
                                </p>
                                <div class="text-xs text-gray-500 dark:text-gray-400 mt-2">- Pierre K.</div>
                            </div>
                            <div class="text-center">
                                <div class="text-yellow-400 mb-2"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i></div>
                                <p class="text-sm text-gray-600 dark:text-gray-300 italic">
                                    "Interface sans pub, parfait pour me concentrer sur la route."
                                </p>
                                <div class="text-xs text-gray-500 dark:text-gray-400 mt-2">- Sarah M.</div>
                            </div>
                        </div>
                    </div>

                    <!-- Guarantee -->
                    <div class="mt-6 text-center">
                        <div class="inline-flex items-center text-sm text-gray-600 dark:text-gray-300">
                            <i class="fas fa-shield-alt text-green-500 mr-2"></i>
                            Garantie satisfait ou remboursé 30 jours
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    selectPlan(planType) {
        const plans = {
            monthly: { price: 2, period: 'mois', total: 2, savings: 0 },
            yearly: { price: 20, period: 'an', total: 20, savings: 4 }
        };

        const selectedPlan = plans[planType];
        if (!selectedPlan) return;

        // Show payment section
        document.getElementById('payment-section').classList.remove('hidden');

        // Update order summary
        const orderSummary = document.getElementById('order-summary');
        orderSummary.innerHTML = `
            <div class="space-y-2">
                <div class="flex justify-between">
                    <span>Smart Route Premium (${selectedPlan.period})</span>
                    <span>$${selectedPlan.price}</span>
                </div>
                ${selectedPlan.savings > 0 ? `
                <div class="flex justify-between text-green-600 dark:text-green-400">
                    <span>Économies</span>
                    <span>-$${selectedPlan.savings}</span>
                </div>
                ` : ''}
                <div class="border-t border-gray-200 dark:border-gray-700 pt-2 flex justify-between font-semibold">
                    <span>Total</span>
                    <span>$${selectedPlan.total}</span>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                    ≈ ${selectedPlan.total * 600} FCFA
                </div>
            </div>
        `;

        // Store selected plan
        this.selectedPlan = planType;

        // Scroll to payment section
        document.getElementById('payment-section').scrollIntoView({ behavior: 'smooth' });
    }

    hidePaymentSection() {
        document.getElementById('payment-section').classList.add('hidden');
        this.selectedPlan = null;
    }

    async processPayment() {
        if (this.isProcessingPayment) return;

        const paymentMethod = document.querySelector('input[name="payment_method"]:checked')?.value;
        if (!paymentMethod) {
            showAlert('Veuillez sélectionner une méthode de paiement', 'error');
            return;
        }

        this.isProcessingPayment = true;
        const processBtn = document.getElementById('process-payment-btn');
        const originalText = processBtn.innerHTML;
        
        processBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Traitement...';
        processBtn.disabled = true;

        try {
            // Simulation de traitement de paiement
            await new Promise(resolve => setTimeout(resolve, 3000));

            // Simulation d'API call
            const response = await fetch('/api/subscription/simulate-upgrade', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    plan: this.selectedPlan,
                    payment_method: paymentMethod
                })
            });

            if (response.ok) {
                this.showSuccessModal();
            } else {
                throw new Error('Payment simulation failed');
            }

        } catch (error) {
            console.error('Payment error:', error);
            showAlert('Erreur lors de la simulation de paiement', 'error');
        } finally {
            this.isProcessingPayment = false;
            processBtn.innerHTML = originalText;
            processBtn.disabled = false;
        }
    }

    showSuccessModal() {
        closeUpgradeModal();
        
        // Créer modal de succès
        const successModal = document.createElement('div');
        successModal.className = 'modal-overlay';
        successModal.innerHTML = `
            <div class="modal-content max-w-md w-full mx-4">
                <div class="text-center p-8">
                    <div class="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-check text-green-600 dark:text-green-400 text-2xl"></i>
                    </div>
                    <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                        🎉 Félicitations !
                    </h3>
                    <p class="text-gray-600 dark:text-gray-300 mb-6">
                        Votre simulation d'upgrade Premium est réussie ! Dans la vraie application, 
                        vous auriez maintenant accès à toutes les fonctionnalités Premium.
                    </p>
                    <div class="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4 mb-6">
                        <h4 class="font-medium text-purple-900 dark:text-purple-100 mb-2">
                            Nouveautés débloquées :
                        </h4>
                        <ul class="text-sm text-purple-700 dark:text-purple-300 space-y-1">
                            <li>✅ Carte trafic illimitée</li>
                            <li>✅ Accès mondial</li>
                            <li>✅ Interface sans publicité</li>
                            <li>✅ Alertes vocales avancées</li>
                            <li>✅ Itinéraires premium</li>
                        </ul>
                    </div>
                    <button onclick="this.closest('.modal-overlay').remove(); location.reload();" 
                            class="btn-primary w-full">
                        🚀 Découvrir Premium
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(successModal);
    }

    closeUpgradeModal() {
        const modal = document.getElementById('upgrade-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        this.hidePaymentSection();
    }
}

// Instance globale
window.SubscriptionManager = new SubscriptionManager();

// Fonctions globales
window.openUpgradeModal = () => window.SubscriptionManager.openUpgradeModal();
window.closeUpgradeModal = () => window.SubscriptionManager.closeUpgradeModal();
window.selectPlan = (plan) => window.SubscriptionManager.selectPlan(plan);
window.hidePaymentSection = () => window.SubscriptionManager.hidePaymentSection();
window.processPayment = () => window.SubscriptionManager.processPayment();

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    window.SubscriptionManager.loadSubscriptionData();
});