import math
from typing import List, Dict, Optional
from datetime import datetime
from flask import current_app
import logging

class RouteOptimizer:
    """Service pour optimiser et scorer les itinéraires"""
    
    def __init__(self):
        self.config = current_app.config.get('ROUTE_OPTIMIZATION', {})
        self.logger = logging.getLogger(__name__)
        
        # Poids des critères d'optimisation
        self.weights = {
            'traffic': self.config.get('traffic_weight', 0.4),
            'distance': self.config.get('distance_weight', 0.3),
            'time': self.config.get('time_weight', 0.3),
            'incident_penalty': self.config.get('incident_penalty', 0.2)
        }
    
    def optimize_routes(self, routes: List[Dict], search_params: Dict) -> List[Dict]:
        """Optimiser et classer les itinéraires par score"""
        
        if not routes:
            return []
        
        optimized_routes = []
        
        for route in routes:
            # Calculer le score d'optimisation
            optimization_score = self._calculate_optimization_score(route, search_params)
            
            # Enrichir les données de l'itinéraire
            enriched_route = self._enrich_route_data(route, optimization_score)
            
            optimized_routes.append(enriched_route)
        
        # Trier par score d'optimisation (décroissant)
        optimized_routes.sort(key=lambda r: r['optimization_score'], reverse=True)
        
        # Ajouter les rangs
        for i, route in enumerate(optimized_routes):
            route['rank'] = i + 1
            route['recommendation'] = self._get_recommendation(route, i, len(optimized_routes))
        
        return optimized_routes
    
    def _calculate_optimization_score(self, route: Dict, search_params: Dict) -> float:
        """Calculer le score d'optimisation d'un itinéraire (0-10)"""
        
        summary = route.get('summary', {})
        
        # Scores individuels (0-10)
        traffic_score = self._calculate_traffic_score(route)
        time_score = self._calculate_time_score(summary)
        distance_score = self._calculate_distance_score(summary)
        incident_score = self._calculate_incident_score(route)
        road_quality_score = self._calculate_road_quality_score(route)
        
        # Score pondéré
        weighted_score = (
            traffic_score * self.weights['traffic'] +
            time_score * self.weights['time'] +
            distance_score * self.weights['distance'] +
            road_quality_score * 0.1
        )
        
        # Appliquer les pénalités d'incidents
        final_score = weighted_score - (incident_score * self.weights['incident_penalty'])
        
        # Bonus/malus selon les préférences utilisateur
        preference_modifier = self._calculate_preference_modifier(route, search_params)
        final_score += preference_modifier
        
        # Normaliser entre 0 et 10
        return max(0, min(10, final_score))
    
    def _calculate_traffic_score(self, route: Dict) -> float:
        """Calculer le score de trafic (10 = fluide, 0 = très congestionné)"""
        
        summary = route.get('summary', {})
        
        # Utiliser la durée typique vs durée actuelle
        duration = summary.get('duration', 0)  # Durée actuelle en secondes
        typical_duration = summary.get('typicalDuration', duration)  # Durée typique
        
        if typical_duration == 0:
            return 8.0  # Score par défaut si pas de données
        
        # Ratio de ralentissement
        slowdown_ratio = duration / typical_duration
        
        # Convertir en score (1.0 = pas de ralentissement = score 10)
        if slowdown_ratio <= 1.0:
            return 10.0
        elif slowdown_ratio <= 1.2:
            return 8.5
        elif slowdown_ratio <= 1.5:
            return 7.0
        elif slowdown_ratio <= 2.0:
            return 5.0
        elif slowdown_ratio <= 3.0:
            return 3.0
        else:
            return 1.0
    
    def _calculate_time_score(self, summary: Dict) -> float:
        """Calculer le score de temps (favorise les trajets courts)"""
        
        duration_hours = summary.get('duration', 0) / 3600
        
        # Score basé sur la durée
        if duration_hours <= 0.25:  # 15 minutes
            return 10.0
        elif duration_hours <= 0.5:  # 30 minutes
            return 9.0
        elif duration_hours <= 1.0:  # 1 heure
            return 8.0
        elif duration_hours <= 2.0:  # 2 heures
            return 6.0
        elif duration_hours <= 4.0:  # 4 heures
            return 4.0
        else:
            return 2.0
    
    def _calculate_distance_score(self, summary: Dict) -> float:
        """Calculer le score de distance (favorise les trajets courts)"""
        
        distance_km = summary.get('length', 0) / 1000
        
        # Score basé sur la distance
        if distance_km <= 5:
            return 10.0
        elif distance_km <= 15:
            return 9.0
        elif distance_km <= 50:
            return 8.0
        elif distance_km <= 100:
            return 6.0
        elif distance_km <= 200:
            return 4.0
        else:
            return 2.0
    
    def _calculate_incident_score(self, route: Dict) -> float:
        """Calculer le score d'incidents (0 = pas d'incidents, 10 = beaucoup d'incidents graves)"""
        
        notices = route.get('notices', [])
        incidents_penalty = 0
        
        for notice in notices:
            notice_code = notice.get('code', '')
            
            # Pénalités selon le type d'incident
            if 'roadClosure' in notice_code:
                incidents_penalty += 5.0
            elif 'accident' in notice_code:
                incidents_penalty += 3.0
            elif 'construction' in notice_code:
                incidents_penalty += 2.0
            elif 'traffic' in notice_code:
                incidents_penalty += 1.0
        
        return min(10, incidents_penalty)
    
    def _calculate_road_quality_score(self, route: Dict) -> float:
        """Calculer le score de qualité des routes"""
        
        # Analyser les sections de l'itinéraire
        sections = route.get('sections', [])
        if not sections:
            return 7.0  # Score par défaut
        
        highway_ratio = 0
        city_ratio = 0
        
        total_length = 0
        for section in sections:
            section_length = section.get('summary', {}).get('length', 0)
            total_length += section_length
            
            # Analyser le type de route
            transport = section.get('transport', {})
            mode = transport.get('mode', 'car')
            
            # Approximation: les sections longues sont probablement des autoroutes
            if section_length > 10000:  # Plus de 10km
                highway_ratio += section_length
            else:
                city_ratio += section_length
        
        if total_length > 0:
            highway_ratio /= total_length
            city_ratio /= total_length
        
        # Score basé sur le ratio autoroute/ville
        # Les autoroutes sont généralement plus fluides
        score = 5.0 + (highway_ratio * 3.0) + (city_ratio * 2.0)
        return min(10, max(0, score))
    
    def _calculate_preference_modifier(self, route: Dict, search_params: Dict) -> float:
        """Calculer le modificateur basé sur les préférences utilisateur"""
        
        modifier = 0.0
        summary = route.get('summary', {})
        
        # Préférence pour le type de route
        route_type = search_params.get('route_type', 'fastest')
        duration = summary.get('duration', 0)
        distance = summary.get('length', 0)
        
        if route_type == 'shortest' and distance > 0:
            # Bonus pour les routes courtes
            modifier += 0.5
        elif route_type == 'fastest' and duration > 0:
            # Bonus pour les routes rapides
            modifier += 0.5
        elif route_type == 'balanced':
            # Score équilibré
            modifier += 0.3
        
        # Pénalités pour les évitements
        toll_cost = summary.get('tollCosts', {})
        if search_params.get('avoid_tolls') and toll_cost:
            modifier += 1.0  # Bonus pour éviter les péages
        
        return modifier
    
    def _enrich_route_data(self, route: Dict, optimization_score: float) -> Dict:
        """Enrichir les données d'un itinéraire avec des métadonnées utiles"""
        
        summary = route.get('summary', {})
        
        enriched_route = {
            'original_data': route,
            'optimization_score': round(optimization_score, 2),
            'summary': {
                'duration': summary.get('duration', 0),
                'length': summary.get('length', 0),
                'typical_duration': summary.get('typicalDuration', summary.get('duration', 0)),
                'origin': route.get('origin_coords', {}),
                'destination': route.get('destination_coords', {}),
                'toll_costs': summary.get('tollCosts', {}),
                'formatted_duration': self._format_duration(summary.get('duration', 0)),
                'formatted_length': self._format_distance(summary.get('length', 0)),
                'delay_info': self._calculate_delay_info(summary)
            },
            'traffic_analysis': self._analyze_route_traffic(route),
            'incidents': self._extract_incidents(route),
            'road_types': self._analyze_road_types(route),
            'environmental_impact': self._calculate_environmental_impact(summary),
            'cost_estimate': self._calculate_cost_estimate(summary)
        }
        
        return enriched_route
    
    def _format_duration(self, seconds: int) -> str:
        """Formater une durée en format lisible"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}min"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h{minutes:02d}"
            else:
                return f"{hours}h"
    
    def _format_distance(self, meters: int) -> str:
        """Formater une distance en format lisible"""
        if meters < 1000:
            return f"{meters}m"
        else:
            km = meters / 1000
            if km < 10:
                return f"{km:.1f}km"
            else:
                return f"{km:.0f}km"
    
    def _calculate_delay_info(self, summary: Dict) -> Dict:
        """Calculer les informations de retard"""
        
        duration = summary.get('duration', 0)
        typical_duration = summary.get('typicalDuration', duration)
        
        delay_seconds = duration - typical_duration
        delay_percentage = (delay_seconds / typical_duration * 100) if typical_duration > 0 else 0
        
        if delay_seconds <= 0:
            status = 'on_time'
            message = 'Trafic fluide'
        elif delay_percentage <= 15:
            status = 'slight_delay'
            message = 'Léger ralentissement'
        elif delay_percentage <= 40:
            status = 'moderate_delay'
            message = 'Ralentissement modéré'
        else:
            status = 'heavy_delay'
            message = 'Fort ralentissement'
        
        return {
            'delay_seconds': max(0, delay_seconds),
            'delay_percentage': max(0, delay_percentage),
            'status': status,
            'message': message,
            'formatted_delay': self._format_duration(max(0, delay_seconds))
        }
    
    def _analyze_route_traffic(self, route: Dict) -> Dict:
        """Analyser les conditions de trafic d'un itinéraire"""
        
        summary = route.get('summary', {})
        duration = summary.get('duration', 0)
        typical_duration = summary.get('typicalDuration', duration)
        
        traffic_ratio = duration / typical_duration if typical_duration > 0 else 1.0
        
        if traffic_ratio <= 1.1:
            level = 'free'
            color = '#00FF00'  # Vert
        elif traffic_ratio <= 1.3:
            level = 'light'
            color = '#FFFF00'  # Jaune
        elif traffic_ratio <= 1.7:
            level = 'moderate'
            color = '#FFA500'  # Orange
        else:
            level = 'heavy'
            color = '#FF0000'  # Rouge
        
        return {
            'level': level,
            'ratio': traffic_ratio,
            'color': color,
            'description': self._get_traffic_description(level)
        }
    
    def _extract_incidents(self, route: Dict) -> List[Dict]:
        """Extraire et classifier les incidents d'un itinéraire"""
        
        notices = route.get('notices', [])
        incidents = []
        
        for notice in notices:
            incident_type = self._classify_notice(notice.get('code', ''))
            
            incident = {
                'type': incident_type,
                'title': notice.get('title', ''),
                'description': notice.get('description', ''),
                'severity': self._get_incident_severity(incident_type),
                'icon': self._get_incident_icon(incident_type)
            }
            incidents.append(incident)
        
        return incidents
    
    def _analyze_road_types(self, route: Dict) -> Dict:
        """Analyser la répartition des types de routes"""
        
        sections = route.get('sections', [])
        road_analysis = {
            'highway_percentage': 0,
            'city_percentage': 0,
            'country_percentage': 0,
            'total_sections': len(sections)
        }
        
        if not sections:
            return road_analysis
        
        total_length = sum(s.get('summary', {}).get('length', 0) for s in sections)
        
        if total_length > 0:
            highway_length = 0
            city_length = 0
            
            for section in sections:
                section_length = section.get('summary', {}).get('length', 0)
                
                # Classification approximative basée sur la longueur des sections
                if section_length > 15000:  # Plus de 15km = probablement autoroute
                    highway_length += section_length
                else:
                    city_length += section_length
            
            road_analysis['highway_percentage'] = round((highway_length / total_length) * 100, 1)
            road_analysis['city_percentage'] = round((city_length / total_length) * 100, 1)
            road_analysis['country_percentage'] = round(100 - road_analysis['highway_percentage'] - road_analysis['city_percentage'], 1)
        
        return road_analysis
    
    def _calculate_environmental_impact(self, summary: Dict) -> Dict:
        """Calculer l'impact environnemental estimé"""
        
        distance_km = summary.get('length', 0) / 1000
        
        # Estimation de consommation pour une voiture moyenne (7L/100km)
        fuel_consumption = distance_km * 0.07  # Litres
        co2_emission = fuel_consumption * 2.31  # kg CO2 (2.31 kg CO2 par litre d'essence)
        
        return {
            'distance_km': round(distance_km, 1),
            'estimated_fuel_consumption': round(fuel_consumption, 2),
            'estimated_co2_emission': round(co2_emission, 2),
            'environmental_score': self._calculate_environmental_score(distance_km)
        }
    
    def _calculate_cost_estimate(self, summary: Dict) -> Dict:
        """Calculer l'estimation des coûts du trajet"""
        
        distance_km = summary.get('length', 0) / 1000
        toll_costs = summary.get('tollCosts', {})
        
        # Coût du carburant (prix moyen 1.50€/L, consommation 7L/100km)
        fuel_cost = distance_km * 0.07 * 1.50
        
        # Coût des péages
        toll_cost = 0
        if toll_costs:
            for currency, amount in toll_costs.items():
                toll_cost += amount  # Supposer EUR
        
        total_cost = fuel_cost + toll_cost
        
        return {
            'fuel_cost': round(fuel_cost, 2),
            'toll_cost': round(toll_cost, 2),
            'total_cost': round(total_cost, 2),
            'currency': 'XAF'
        }
    
    def _get_recommendation(self, route: Dict, rank: int, total_routes: int) -> Dict:
        """Générer une recommandation pour l'itinéraire"""
        
        score = route['optimization_score']
        
        if rank == 0:  # Meilleur itinéraire
            if score >= 8.5:
                recommendation = {
                    'type': 'highly_recommended',
                    'title': '🌟 Fortement recommandé',
                    'message': 'Itinéraire optimal avec excellent trafic',
                    'color': '#00C851'
                }
            elif score >= 7.0:
                recommendation = {
                    'type': 'recommended',
                    'title': '✅ Recommandé',
                    'message': 'Bon itinéraire avec trafic favorable',
                    'color': '#2BBBAD'
                }
            else:
                recommendation = {
                    'type': 'best_available',
                    'title': '🚗 Meilleur disponible',
                    'message': 'Meilleur itinéraire dans les conditions actuelles',
                    'color': '#FF6F00'
                }
        elif score >= 7.0:
            recommendation = {
                'type': 'alternative',
                'title': '🔄 Alternative viable',
                'message': 'Bonne alternative au meilleur itinéraire',
                'color': '#1976D2'
            }
        else:
            recommendation = {
                'type': 'avoid',
                'title': '⚠️ À éviter',
                'message': 'Conditions de trafic défavorables',
                'color': '#D32F2F'
            }
        
        return recommendation
    
    # Méthodes utilitaires
    
    def _get_traffic_description(self, level: str) -> str:
        descriptions = {
            'free': 'Circulation fluide',
            'light': 'Circulation légèrement ralentie',
            'moderate': 'Circulation modérément ralentie',
            'heavy': 'Circulation fortement ralentie'
        }
        return descriptions.get(level, 'Conditions inconnues')
    
    def _classify_notice(self, notice_code: str) -> str:
        if 'closure' in notice_code.lower():
            return 'road_closure'
        elif 'accident' in notice_code.lower():
            return 'accident'
        elif 'construction' in notice_code.lower():
            return 'construction'
        elif 'traffic' in notice_code.lower():
            return 'traffic_jam'
        else:
            return 'general'
    
    def _get_incident_severity(self, incident_type: str) -> str:
        severity_map = {
            'road_closure': 'high',
            'accident': 'high',
            'construction': 'medium',
            'traffic_jam': 'medium',
            'general': 'low'
        }
        return severity_map.get(incident_type, 'low')
    
    def _get_incident_icon(self, incident_type: str) -> str:
        icon_map = {
            'road_closure': '🚧',
            'accident': '🚨',
            'construction': '👷',
            'traffic_jam': '🚗',
            'general': 'ℹ️'
        }
        return icon_map.get(incident_type, 'ℹ️')
    
    def _calculate_environmental_score(self, distance_km: float) -> int:
        if distance_km <= 5:
            return 9
        elif distance_km <= 15:
            return 7
        elif distance_km <= 50:
            return 5
        else:
            return 3