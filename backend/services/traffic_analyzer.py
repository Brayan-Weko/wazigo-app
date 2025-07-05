from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics
import logging

class TrafficAnalyzer:
    """Service pour analyser les conditions de trafic en temps réel"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Seuils de classification du trafic
        self.traffic_thresholds = {
            'free': {'jam_factor_max': 2, 'speed_ratio_min': 0.9},
            'light': {'jam_factor_max': 4, 'speed_ratio_min': 0.7},
            'moderate': {'jam_factor_max': 7, 'speed_ratio_min': 0.5},
            'heavy': {'jam_factor_max': 10, 'speed_ratio_min': 0.3},
            'severe': {'jam_factor_max': float('inf'), 'speed_ratio_min': 0}
        }
    
    def analyze_route_traffic(self, route_data: Dict) -> Dict:
        """Analyser les conditions de trafic d'un itinéraire complet"""
        
        try:
            summary = route_data.get('summary', {})
            sections = route_data.get('sections', [])
            
            # Analyse globale de l'itinéraire
            global_analysis = self._analyze_global_traffic(summary)
            
            # Analyse détaillée par section
            sections_analysis = []
            for section in sections:
                section_analysis = self._analyze_section_traffic(section)
                sections_analysis.append(section_analysis)
            
            # Points critiques identifiés
            critical_points = self._identify_critical_points(sections_analysis)
            
            # Prédictions et recommandations
            predictions = self._generate_traffic_predictions(global_analysis, sections_analysis)
            
            return {
                'global_analysis': global_analysis,
                'sections_analysis': sections_analysis,
                'critical_points': critical_points,
                'predictions': predictions,
                'summary': self._generate_traffic_summary(global_analysis, critical_points),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur analyse trafic: {str(e)}")
            return self._get_default_analysis()
    
    def _analyze_global_traffic(self, summary: Dict) -> Dict:
        """Analyser les conditions de trafic globales d'un itinéraire"""
        
        duration = summary.get('duration', 0)
        typical_duration = summary.get('typicalDuration', duration)
        length = summary.get('length', 0)
        
        if typical_duration == 0:
            return self._get_default_global_analysis()
        
        # Calculs de base
        delay_ratio = duration / typical_duration
        average_speed = (length / duration * 3.6) if duration > 0 else 0  # km/h
        typical_speed = (length / typical_duration * 3.6) if typical_duration > 0 else 0
        speed_loss_percentage = ((typical_speed - average_speed) / typical_speed * 100) if typical_speed > 0 else 0
        
        # Classification du niveau de trafic
        traffic_level = self._classify_traffic_level(delay_ratio, speed_loss_percentage)
        
        # Calcul du score de fluidité (0-100)
        fluidity_score = self._calculate_fluidity_score(delay_ratio, speed_loss_percentage)
        
        return {
            'duration_seconds': duration,
            'typical_duration_seconds': typical_duration,
            'delay_seconds': max(0, duration - typical_duration),
            'delay_ratio': delay_ratio,
            'delay_percentage': max(0, (delay_ratio - 1) * 100),
            'average_speed_kmh': round(average_speed, 1),
            'typical_speed_kmh': round(typical_speed, 1),
            'speed_loss_percentage': round(speed_loss_percentage, 1),
            'traffic_level': traffic_level,
            'fluidity_score': fluidity_score,
            'traffic_color': self._get_traffic_color(traffic_level),
            'impact_description': self._get_impact_description(traffic_level, delay_ratio)
        }
    
    def _analyze_section_traffic(self, section: Dict) -> Dict:
        """Analyser les conditions de trafic d'une section d'itinéraire"""
        
        section_summary = section.get('summary', {})
        duration = section_summary.get('duration', 0)
        length = section_summary.get('length', 0)
        
        # Vitesse moyenne de la section
        avg_speed = (length / duration * 3.6) if duration > 0 else 0
        
        # Estimation du type de route basée sur la vitesse et la longueur
        road_type = self._estimate_road_type(avg_speed, length)
        
        # Analyse des incidents sur cette section
        incidents = section.get('incidents', [])
        incident_impact = self._analyze_section_incidents(incidents)
        
        return {
            'length_meters': length,
            'duration_seconds': duration,
            'average_speed_kmh': round(avg_speed, 1),
            'road_type': road_type,
            'incident_impact': incident_impact,
            'traffic_condition': self._assess_section_condition(avg_speed, road_type),
            'congestion_index': self._calculate_congestion_index(avg_speed, road_type)
        }
    
    def _identify_critical_points(self, sections_analysis: List[Dict]) -> List[Dict]:
        """Identifier les points critiques de congestion"""
        
        critical_points = []
        
        for i, section in enumerate(sections_analysis):
            congestion_index = section.get('congestion_index', 0)
            incident_impact = section.get('incident_impact', {})
            
            # Point critique si fort indice de congestion ou incidents majeurs
            if congestion_index >= 7 or incident_impact.get('severity_score', 0) >= 8:
                critical_point = {
                    'section_index': i,
                    'type': 'high_congestion' if congestion_index >= 7 else 'major_incident',
                    'severity': 'high',
                    'congestion_index': congestion_index,
                    'description': self._generate_critical_point_description(section),
                    'estimated_delay': self._estimate_critical_point_delay(section),
                    'alternative_suggestion': self._suggest_alternative_for_critical_point(section)
                }
                critical_points.append(critical_point)
        
        return critical_points
    
    def _generate_traffic_predictions(self, global_analysis: Dict, sections_analysis: List[Dict]) -> Dict:
        """Générer des prédictions de trafic"""
        
        current_level = global_analysis.get('traffic_level', 'moderate')
        current_hour = datetime.now().hour
        
        # Prédictions basées sur les patterns temporels
        predictions = {
            'next_hour': self._predict_next_hour_traffic(current_level, current_hour),
            'rush_hour_impact': self._assess_rush_hour_impact(current_hour),
            'weekend_comparison': self._compare_weekend_traffic(current_hour),
            'improvement_time': self._estimate_improvement_time(global_analysis),
            'alternative_departure_times': self._suggest_alternative_times(global_analysis, current_hour)
        }
        
        return predictions
    
    def get_traffic_status(self, lat: float, lng: float, radius: int = 5000) -> Dict:
        """Récupérer le statut du trafic pour une zone géographique"""
        
        try:
            # Simulation de données de trafic en temps réel
            # En production, utiliser HERE Traffic API
            
            traffic_data = self._simulate_area_traffic(lat, lng, radius)
            
            return {
                'center': {'lat': lat, 'lng': lng},
                'radius': radius,
                'overall_traffic_level': traffic_data['overall_level'],
                'average_speed': traffic_data['average_speed'],
                'congestion_areas': traffic_data['congestion_areas'],
                'incidents_count': traffic_data['incidents_count'],
                'traffic_flow_rating': traffic_data['flow_rating'],
                'recommendations': traffic_data['recommendations'],
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur récupération statut trafic: {str(e)}")
            return self._get_default_traffic_status()
    
    def analyze_historical_patterns(self, route_data: List[Dict], time_period: int = 30) -> Dict:
        """Analyser les patterns historiques de trafic"""
        
        if not route_data:
            return {}
        
        # Analyse par heure de la journée
        hourly_patterns = self._analyze_hourly_patterns(route_data)
        
        # Analyse par jour de la semaine
        daily_patterns = self._analyze_daily_patterns(route_data)
        
        # Tendances générales
        trends = self._analyze_traffic_trends(route_data)
        
        return {
            'hourly_patterns': hourly_patterns,
            'daily_patterns': daily_patterns,
            'trends': trends,
            'peak_hours': self._identify_peak_hours(hourly_patterns),
            'best_travel_times': self._recommend_best_times(hourly_patterns, daily_patterns),
            'analysis_period_days': time_period,
            'data_points': len(route_data)
        }
    
    # Méthodes utilitaires privées
    
    def _classify_traffic_level(self, delay_ratio: float, speed_loss: float) -> str:
        """Classifier le niveau de trafic"""
        
        if delay_ratio <= 1.1 and speed_loss <= 10:
            return 'free'
        elif delay_ratio <= 1.3 and speed_loss <= 25:
            return 'light'
        elif delay_ratio <= 1.6 and speed_loss <= 45:
            return 'moderate'
        elif delay_ratio <= 2.0 and speed_loss <= 65:
            return 'heavy'
        else:
            return 'severe'
    
    def _calculate_fluidity_score(self, delay_ratio: float, speed_loss: float) -> int:
        """Calculer un score de fluidité (0-100)"""
        
        # Score basé sur le délai et la perte de vitesse
        delay_score = max(0, 100 - (delay_ratio - 1) * 100)
        speed_score = max(0, 100 - speed_loss)
        
        # Score final pondéré
        fluidity_score = (delay_score * 0.6 + speed_score * 0.4)
        
        return int(min(100, max(0, fluidity_score)))
    
    def _get_traffic_color(self, traffic_level: str) -> str:
        """Obtenir la couleur associée au niveau de trafic"""
        colors = {
            'free': '#00FF00',      # Vert
            'light': '#ADFF2F',     # Vert clair
            'moderate': '#FFFF00',  # Jaune
            'heavy': '#FFA500',     # Orange
            'severe': '#FF0000'     # Rouge
        }
        return colors.get(traffic_level, '#808080')
    
    def _get_impact_description(self, traffic_level: str, delay_ratio: float) -> str:
        """Générer une description de l'impact du trafic"""
        
        descriptions = {
            'free': 'Circulation fluide, pas de retard',
            'light': 'Circulation légèrement ralentie',
            'moderate': 'Ralentissements modérés à prévoir',
            'heavy': 'Circulation difficile, retards importants',
            'severe': 'Circulation très difficile, retards majeurs'
        }
        
        base_description = descriptions.get(traffic_level, 'Conditions inconnues')
        
        if delay_ratio > 1.1:
            delay_minutes = int((delay_ratio - 1) * 60)  # Estimation approximative
            base_description += f" (+{delay_minutes}min estimées)"
        
        return base_description
    
    def _estimate_road_type(self, avg_speed: float, length: int) -> str:
        """Estimer le type de route basé sur la vitesse et la longueur"""
        
        if avg_speed >= 90:
            return 'highway'
        elif avg_speed >= 60 and length > 5000:
            return 'major_road'
        elif avg_speed >= 40:
            return 'secondary_road'
        elif avg_speed >= 25:
            return 'city_street'
        else:
            return 'residential'
    
    def _analyze_section_incidents(self, incidents: List[Dict]) -> Dict:
        """Analyser l'impact des incidents sur une section"""
        
        if not incidents:
            return {'count': 0, 'severity_score': 0, 'types': []}
        
        severity_scores = []
        incident_types = []
        
        for incident in incidents:
            incident_type = incident.get('type', 'unknown')
            incident_types.append(incident_type)
            
            # Score de sévérité selon le type
            severity_map = {
                'road_closure': 10,
                'accident': 8,
                'construction': 6,
                'traffic_jam': 4,
                'weather': 5,
                'event': 3
            }
            severity_scores.append(severity_map.get(incident_type, 2))
        
        return {
            'count': len(incidents),
            'severity_score': max(severity_scores) if severity_scores else 0,
            'average_severity': statistics.mean(severity_scores) if severity_scores else 0,
            'types': list(set(incident_types))
        }
    
    def _assess_section_condition(self, avg_speed: float, road_type: str) -> str:
        """Évaluer les conditions de circulation d'une section"""
        
        # Vitesses de référence par type de route
        reference_speeds = {
            'highway': 120,
            'major_road': 80,
            'secondary_road': 60,
            'city_street': 40,
            'residential': 30
        }
        
        ref_speed = reference_speeds.get(road_type, 50)
        speed_ratio = avg_speed / ref_speed
        
        if speed_ratio >= 0.8:
            return 'good'
        elif speed_ratio >= 0.6:
            return 'moderate'
        elif speed_ratio >= 0.4:
            return 'poor'
        else:
            return 'very_poor'
    
    def _calculate_congestion_index(self, avg_speed: float, road_type: str) -> int:
        """Calculer un indice de congestion (0-10)"""
        
        reference_speeds = {
            'highway': 120,
            'major_road': 80,
            'secondary_road': 60,
            'city_street': 40,
            'residential': 30
        }
        
        ref_speed = reference_speeds.get(road_type, 50)
        speed_ratio = avg_speed / ref_speed
        
        # Index inversé: plus la vitesse est faible, plus l'index est élevé
        congestion_index = max(0, min(10, 10 - (speed_ratio * 10)))
        
        return int(congestion_index)
    
    def _simulate_area_traffic(self, lat: float, lng: float, radius: int) -> Dict:
        """Simuler les données de trafic d'une zone (à remplacer par vraie API)"""
        
        import random
        
        # Simulation basique pour la démonstration
        current_hour = datetime.now().hour
        
        # Ajuster selon l'heure (heures de pointe)
        if current_hour in [7, 8, 9, 17, 18, 19]:
            base_congestion = random.uniform(0.6, 0.9)
        elif current_hour in [10, 11, 14, 15, 16]:
            base_congestion = random.uniform(0.3, 0.6)
        else:
            base_congestion = random.uniform(0.1, 0.3)
        
        overall_level = self._classify_traffic_level(1 + base_congestion, base_congestion * 100)
        
        return {
            'overall_level': overall_level,
            'average_speed': round(50 * (1 - base_congestion), 1),
            'congestion_areas': random.randint(0, 5),
            'incidents_count': random.randint(0, 3),
            'flow_rating': int((1 - base_congestion) * 10),
            'recommendations': self._generate_area_recommendations(overall_level)
        }
    
    def _generate_area_recommendations(self, traffic_level: str) -> List[str]:
        """Générer des recommandations basées sur le niveau de trafic"""
        
        recommendations = {
            'free': ['Conditions idéales pour voyager'],
            'light': ['Bonne période pour les déplacements'],
            'moderate': ['Prévoir quelques minutes supplémentaires', 'Vérifier les itinéraires alternatifs'],
            'heavy': ['Éviter les axes principaux si possible', 'Reporter le déplacement si non urgent'],
            'severe': ['Privilégier les transports en commun', 'Reporter le déplacement', 'Utiliser des itinéraires alternatifs']
        }
        
        return recommendations.get(traffic_level, ['Vérifier les conditions avant de partir'])
    
    def _get_default_analysis(self) -> Dict:
        """Retourner une analyse par défaut en cas d'erreur"""
        return {
            'global_analysis': self._get_default_global_analysis(),
            'sections_analysis': [],
            'critical_points': [],
            'predictions': {},
            'summary': {'level': 'unknown', 'message': 'Données de trafic non disponibles'},
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_default_global_analysis(self) -> Dict:
        return {
            'traffic_level': 'unknown',
            'fluidity_score': 50,
            'traffic_color': '#808080',
            'impact_description': 'Données de trafic non disponibles'
        }
    
    def _get_default_traffic_status(self) -> Dict:
        return {
            'overall_traffic_level': 'unknown',
            'average_speed': 0,
            'congestion_areas': 0,
            'incidents_count': 0,
            'traffic_flow_rating': 5,
            'recommendations': ['Données de trafic temporairement indisponibles'],
            'last_updated': datetime.utcnow().isoformat()
        }