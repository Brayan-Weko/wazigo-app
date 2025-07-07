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
    
    def _predict_next_hour_traffic(self, current_level: str, current_hour: int) -> Dict:
        """Prédire le trafic de l'heure suivante"""
        try:
            next_hour = (current_hour + 1) % 24
            
            # Patterns de trafic par heure
            rush_hours = [7, 8, 9, 17, 18, 19]
            moderate_hours = [10, 11, 12, 13, 14, 15, 16, 20]
            
            if next_hour in rush_hours:
                predicted_level = 'heavy' if current_level in ['moderate', 'heavy'] else 'moderate'
            elif next_hour in moderate_hours:
                predicted_level = 'moderate' if current_level == 'heavy' else 'light'
            else:
                predicted_level = 'free'
            
            confidence = 0.7 if current_level == predicted_level else 0.5
            
            return {
                'predicted_level': predicted_level,
                'confidence': confidence,
                'hour': next_hour,
                'trend': 'improving' if predicted_level < current_level else 'worsening' if predicted_level > current_level else 'stable'
            }
        except Exception as e:
            self.logger.error(f"Error predicting next hour traffic: {e}")
            return {
                'predicted_level': current_level,
                'confidence': 0.3,
                'hour': (current_hour + 1) % 24,
                'trend': 'stable'
            }

    def _assess_rush_hour_impact(self, current_hour: int) -> Dict:
        """Évaluer l'impact des heures de pointe"""
        try:
            morning_rush = [7, 8, 9]
            evening_rush = [17, 18, 19]
            
            if current_hour in morning_rush:
                return {
                    'is_rush_hour': True,
                    'type': 'morning',
                    'severity': 'high' if current_hour == 8 else 'moderate',
                    'expected_duration_minutes': 60 - ((current_hour - 7) * 20)
                }
            elif current_hour in evening_rush:
                return {
                    'is_rush_hour': True,
                    'type': 'evening',
                    'severity': 'high' if current_hour == 18 else 'moderate',
                    'expected_duration_minutes': 60 - ((current_hour - 17) * 20)
                }
            else:
                return {
                    'is_rush_hour': False,
                    'type': 'off_peak',
                    'severity': 'low',
                    'expected_duration_minutes': 0
                }
        except Exception as e:
            self.logger.error(f"Error assessing rush hour: {e}")
            return {'is_rush_hour': False, 'type': 'unknown', 'severity': 'low', 'expected_duration_minutes': 0}

    def _compare_weekend_traffic(self, current_hour: int) -> Dict:
        """Comparer avec le trafic de weekend"""
        try:
            import datetime
            is_weekend = datetime.datetime.now().weekday() >= 5
            
            if is_weekend:
                weekend_pattern = 'current'
                comparison = 'Same as current (weekend)'
            else:
                # Simulation des patterns weekend
                if 10 <= current_hour <= 14:
                    weekend_pattern = 'moderate'
                    comparison = 'Lighter on weekends'
                elif current_hour in [7, 8, 17, 18]:
                    weekend_pattern = 'light'
                    comparison = 'Much lighter on weekends'
                else:
                    weekend_pattern = 'free'
                    comparison = 'Similar on weekends'
            
            return {
                'is_weekend': is_weekend,
                'weekend_pattern': weekend_pattern,
                'comparison': comparison
            }
        except Exception as e:
            self.logger.error(f"Error comparing weekend traffic: {e}")
            return {'is_weekend': False, 'weekend_pattern': 'unknown', 'comparison': 'Unable to compare'}

    def _estimate_improvement_time(self, global_analysis: Dict) -> Dict:
        """Estimer le temps d'amélioration du trafic"""
        try:
            traffic_level = global_analysis.get('traffic_level', 'moderate')
            current_hour = datetime.now().hour
            
            if traffic_level in ['free', 'light']:
                return {
                    'improvement_expected': False,
                    'estimated_minutes': 0,
                    'reason': 'Traffic already flowing well'
                }
            
            # Estimation basée sur l'heure et le niveau
            if current_hour in [7, 8, 9]:  # Rush du matin
                improvement_time = (10 - current_hour) * 60
            elif current_hour in [17, 18, 19]:  # Rush du soir
                improvement_time = (21 - current_hour) * 60
            else:
                improvement_time = 30  # Amélioration générale
            
            return {
                'improvement_expected': True,
                'estimated_minutes': max(15, improvement_time),
                'reason': f'Traffic typically improves after current period'
            }
        except Exception as e:
            self.logger.error(f"Error estimating improvement time: {e}")
            return {'improvement_expected': False, 'estimated_minutes': 0, 'reason': 'Unable to estimate'}

    def _suggest_alternative_times(self, global_analysis: Dict, current_hour: int) -> List[Dict]:
        """Suggérer des heures alternatives de départ"""
        try:
            suggestions = []
            traffic_level = global_analysis.get('traffic_level', 'moderate')
            
            if traffic_level in ['heavy', 'severe']:
                # Suggérer des heures moins chargées
                good_hours = [6, 10, 11, 14, 15, 21, 22]
                for hour in good_hours:
                    if hour != current_hour:
                        time_diff = hour - current_hour
                        if time_diff < 0:
                            time_diff += 24
                        
                        if time_diff <= 4:  # Suggestions dans les 4 prochaines heures
                            suggestions.append({
                                'departure_hour': hour,
                                'time_difference_hours': time_diff,
                                'expected_traffic': 'light' if hour in [6, 10, 14, 21] else 'moderate',
                                'recommendation': f"Départ à {hour}h00 pour éviter les embouteillages"
                            })
            
            return suggestions[:3]  # Max 3 suggestions
        except Exception as e:
            self.logger.error(f"Error suggesting alternative times: {e}")
            return []

    def _generate_critical_point_description(self, section: Dict) -> str:
        """Générer une description pour un point critique"""
        try:
            road_type = section.get('road_type', 'unknown')
            congestion_index = section.get('congestion_index', 0)
            incident_impact = section.get('incident_impact', {})
            
            if incident_impact.get('count', 0) > 0:
                return f"Incident majeur détecté sur {road_type}"
            elif congestion_index >= 8:
                return f"Congestion sévère sur {road_type}"
            elif congestion_index >= 6:
                return f"Ralentissements importants sur {road_type}"
            else:
                return f"Point de congestion sur {road_type}"
        except Exception as e:
            return "Point critique détecté"

    def _estimate_critical_point_delay(self, section: Dict) -> int:
        """Estimer le délai causé par un point critique"""
        try:
            congestion_index = section.get('congestion_index', 0)
            incident_count = section.get('incident_impact', {}).get('count', 0)
            
            base_delay = congestion_index * 30  # 30 secondes par point d'index
            incident_delay = incident_count * 120  # 2 minutes par incident
            
            return int(base_delay + incident_delay)
        except Exception as e:
            return 60  # Délai par défaut

    def _suggest_alternative_for_critical_point(self, section: Dict) -> str:
        """Suggérer une alternative pour un point critique"""
        try:
            road_type = section.get('road_type', 'unknown')
            
            suggestions = {
                'highway': "Utiliser les routes secondaires parallèles",
                'major_road': "Emprunter les boulevards alternatifs",
                'city_street': "Éviter le centre-ville si possible",
                'secondary_road': "Chercher un itinéraire de contournement"
            }
            
            return suggestions.get(road_type, "Rechercher un itinéraire alternatif")
        except Exception as e:
            return "Considérer un itinéraire alternatif"

    def _generate_traffic_summary(self, global_analysis: Dict, critical_points: List[Dict]) -> Dict:
        """Générer un résumé du trafic"""
        try:
            traffic_level = global_analysis.get('traffic_level', 'unknown')
            fluidity_score = global_analysis.get('fluidity_score', 50)
            critical_count = len(critical_points)
            
            if traffic_level == 'free':
                message = "🟢 Circulation fluide"
                color = "#00FF00"
            elif traffic_level == 'light':
                message = "🟡 Circulation légèrement ralentie"
                color = "#FFFF00"
            elif traffic_level == 'moderate':
                message = "🟠 Ralentissements modérés"
                color = "#FFA500"
            elif traffic_level == 'heavy':
                message = "🔴 Circulation difficile"
                color = "#FF0000"
            else:
                message = "⚫ Conditions inconnues"
                color = "#808080"
            
            if critical_count > 0:
                message += f" - {critical_count} point(s) critique(s)"
            
            return {
                'level': traffic_level,
                'message': message,
                'color': color,
                'fluidity_score': fluidity_score,
                'critical_points_count': critical_count,
                'recommendation': self._get_summary_recommendation(traffic_level, critical_count)
            }
        except Exception as e:
            return {
                'level': 'unknown',
                'message': 'Conditions de trafic indisponibles',
                'color': '#808080',
                'fluidity_score': 50,
                'critical_points_count': 0,
                'recommendation': 'Vérifier les conditions avant de partir'
            }

    def _get_summary_recommendation(self, traffic_level: str, critical_count: int) -> str:
        """Obtenir une recommandation basée sur le résumé"""
        if traffic_level in ['heavy', 'severe'] or critical_count > 2:
            return "Reporter le déplacement si possible"
        elif traffic_level == 'moderate' or critical_count > 0:
            return "Prévoir du temps supplémentaire"
        else:
            return "Conditions favorables pour voyager"
    
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