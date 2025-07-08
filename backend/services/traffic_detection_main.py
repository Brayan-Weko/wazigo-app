#!/usr/bin/env python3
"""
Système de Détection d'Embouteillages YOLO
Intégré avec TrafficAnalyzer, RouteService, RouteOptimizer
import cv2
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import yaml
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Imports YOLO et ML
from ultralytics import YOLO
import torch
from PIL import Image, ImageDraw
from sklearn.metrics import precision_recall_curve, average_precision_score
from sklearn.cluster import DBSCAN

# Imports des services existants (à adapter selon votre structure)
from backend.services.traffic_analyzer import TrafficAnalyzer
from backend.services.route_optimizer import RouteOptimizer


class YOLOTrafficDetector:
    """
    Détecteur YOLO intégré avec votre architecture existante
    """
    
    def __init__(self, dataset_path: str, model_name: str = 'yolov8n.pt'):
        self.dataset_path = Path(dataset_path)
        self.model_name = model_name
        self.model = None
        self.results = {}
        
        # Classes adaptées à votre système d'analyse
        self.classes = {
            0: 'circulation_normale',
            1: 'embouteillage_leger',
            2: 'embouteillage_modere', 
            3: 'embouteillage_severe',
            4: 'accident',
            5: 'construction'
        }
        
        # Seuils compatibles avec TrafficAnalyzer
        self.traffic_thresholds = {
            'free': {'detection_ratio': 0.0, 'jam_confidence': 0.2},
            'light': {'detection_ratio': 0.3, 'jam_confidence': 0.5},
            'moderate': {'detection_ratio': 0.6, 'jam_confidence': 0.7},
            'heavy': {'detection_ratio': 0.8, 'jam_confidence': 0.85},
            'severe': {'detection_ratio': 0.9, 'jam_confidence': 0.95}
        }
        
        self.logger = logging.getLogger(__name__)
        
    def analyze_dataset(self) -> Dict:
        """Analyse approfondie du dataset YOLO"""
        print("🔍 Analyse du dataset YOLO en cours...")
        
        images = list(self.dataset_path.glob("*.jpg"))
        annotations = list(self.dataset_path.glob("*.txt"))
        
        print(f"📁 Images trouvées: {len(images)}")
        print(f"📄 Annotations trouvées: {len(annotations)}")
        
        # Analyse détaillée des annotations
        annotation_stats = []
        for txt_file in annotations:
            if txt_file.stat().st_size > 0:
                with open(txt_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id, x_center, y_center, width, height = map(float, parts[:5])
                            
                            # Confidence score si disponible
                            confidence = float(parts[5]) if len(parts) > 5 else 1.0
                            
                            annotation_stats.append({
                                'file': txt_file.stem,
                                'class_id': int(class_id),
                                'class_name': self.classes.get(int(class_id), 'unknown'),
                                'x_center': x_center,
                                'y_center': y_center,
                                'width': width,
                                'height': height,
                                'area': width * height,
                                'confidence': confidence,
                                'aspect_ratio': width / height if height > 0 else 0
                            })
        
        self.annotation_df = pd.DataFrame(annotation_stats)
        
        # Statistiques avancées
        stats = {
            'total_images': len(images),
            'total_annotations': len(annotation_stats),
            'class_distribution': self.annotation_df['class_id'].value_counts().to_dict(),
            'average_objects_per_image': len(annotation_stats) / len(images) if images else 0,
            'bbox_size_stats': {
                'mean_area': self.annotation_df['area'].mean(),
                'std_area': self.annotation_df['area'].std(),
                'mean_width': self.annotation_df['width'].mean(),
                'mean_height': self.annotation_df['height'].mean()
            },
            'traffic_severity_distribution': self._analyze_traffic_severity()
        }
        
        return stats
    
    def _analyze_traffic_severity(self) -> Dict:
        """Analyser la distribution de la sévérité du trafic"""
        if not hasattr(self, 'annotation_df') or self.annotation_df.empty:
            return {}
        
        # Mapping vers les niveaux de TrafficAnalyzer
        severity_mapping = {
            0: 'free',      # circulation_normale
            1: 'light',     # embouteillage_leger
            2: 'moderate',  # embouteillage_modere
            3: 'heavy',     # embouteillage_severe
            4: 'incident',  # accident
            5: 'incident'   # construction
        }
        
        severity_counts = {}
        for class_id, count in self.annotation_df['class_id'].value_counts().items():
            severity = severity_mapping.get(class_id, 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + count
        
        return severity_counts
    
    def create_enhanced_dataset_yaml(self) -> Path:
        """Créer un fichier de configuration YOLO enrichi"""
        dataset_config = {
            'path': str(self.dataset_path),
            'train': str(self.dataset_path / 'train'),
            'val': str(self.dataset_path / 'val'),
            'test': str(self.dataset_path / 'test'),
            'nc': len(self.classes),
            'names': list(self.classes.values()),
            
            # Configuration avancée
            'roboflow': {
                'workspace': 'traffic-detection',
                'project': 'embouteillage-detection',
                'version': 1
            },
            
            # Augmentation des données
            'augmentation': {
                'hsv_h': 0.015,
                'hsv_s': 0.7,
                'hsv_v': 0.4,
                'degrees': 0.0,
                'translate': 0.1,
                'scale': 0.5,
                'shear': 0.0,
                'perspective': 0.0,
                'flipud': 0.0,
                'fliplr': 0.5,
                'mosaic': 1.0,
                'mixup': 0.0,
                'copy_paste': 0.0
            }
        }
        
        yaml_path = self.dataset_path / 'traffic_dataset.yaml'
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(dataset_config, f, default_flow_style=False, allow_unicode=True)
        
        return yaml_path
    
    def prepare_stratified_split(self, train_ratio=0.7, val_ratio=0.2, test_ratio=0.1):
        """Division stratifiée du dataset basée sur la sévérité du trafic"""
        images = list(self.dataset_path.glob("*.jpg"))
        
        # Regrouper par niveau de sévérité
        severity_groups = {}
        for img_path in images:
            txt_path = img_path.with_suffix('.txt')
            if txt_path.exists():
                severity = self._get_image_severity(txt_path)
                if severity not in severity_groups:
                    severity_groups[severity] = []
                severity_groups[severity].append(img_path)
        
        # Créer les dossiers
        for split in ['train', 'val', 'test']:
            (self.dataset_path / split / 'images').mkdir(parents=True, exist_ok=True)
            (self.dataset_path / split / 'labels').mkdir(parents=True, exist_ok=True)
        
        # Division stratifiée
        splits = {'train': [], 'val': [], 'test': []}
        
        for severity, images_list in severity_groups.items():
            np.random.shuffle(images_list)
            n_total = len(images_list)
            n_train = int(n_total * train_ratio)
            n_val = int(n_total * val_ratio)
            
            splits['train'].extend(images_list[:n_train])
            splits['val'].extend(images_list[n_train:n_train+n_val])
            splits['test'].extend(images_list[n_train+n_val:])
        
        # Copier les fichiers
        for split_name, image_list in splits.items():
            for img_path in image_list:
                # Copier l'image
                dst_img = self.dataset_path / split_name / 'images' / img_path.name
                dst_img.write_bytes(img_path.read_bytes())
                
                # Copier l'annotation
                txt_path = img_path.with_suffix('.txt')
                if txt_path.exists():
                    dst_txt = self.dataset_path / split_name / 'labels' / txt_path.name
                    dst_txt.write_text(txt_path.read_text())
        
        return splits
    
    def _get_image_severity(self, txt_path: Path) -> str:
        """Déterminer la sévérité dominante d'une image"""
        try:
            with open(txt_path, 'r') as f:
                lines = f.readlines()
            
            if not lines:
                return 'free'
            
            # Compter les classes présentes
            class_counts = {}
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(float(parts[0]))
                    class_counts[class_id] = class_counts.get(class_id, 0) + 1
            
            # Déterminer la sévérité basée sur la classe dominante
            if 3 in class_counts or 4 in class_counts or 5 in class_counts:
                return 'severe'
            elif 2 in class_counts:
                return 'moderate'
            elif 1 in class_counts:
                return 'light'
            else:
                return 'free'
                
        except Exception as e:
            self.logger.warning(f"Erreur analyse sévérité {txt_path}: {e}")
            return 'free'
    
    def train_enhanced_model(self, epochs=150, img_size=640, batch_size=16) -> Dict:
        """Entraînement avancé du modèle YOLO"""
        print("🚀 Début de l'entraînement YOLO avancé...")
        
        # Créer la configuration
        yaml_path = self.create_enhanced_dataset_yaml()
        
        # Charger le modèle avec transfer learning
        self.model = YOLO(self.model_name)
        
        # Configuration d'entraînement optimisée
        results = self.model.train(
            data=str(yaml_path),
            epochs=epochs,
            imgsz=img_size,
            batch=batch_size,
            device='cuda' if torch.cuda.is_available() else 'cpu',
            workers=8,
            
            # Optimisations avancées
            optimizer='AdamW',
            lr0=0.01,
            lrf=0.1,
            momentum=0.937,
            weight_decay=0.0005,
            warmup_epochs=3,
            warmup_momentum=0.8,
            warmup_bias_lr=0.1,
            
            # Augmentation des données
            hsv_h=0.015,
            hsv_s=0.7,
            hsv_v=0.4,
            degrees=0.0,
            translate=0.1,
            scale=0.5,
            shear=0.0,
            perspective=0.0,
            flipud=0.0,
            fliplr=0.5,
            mosaic=1.0,
            mixup=0.0,
            copy_paste=0.0,
            
            # Paramètres projet
            project='traffic_detection_yolo',
            name='embouteillage_detector_v2',
            save=True,
            save_period=10,
            cache=True,
            plots=True,
            val=True,
            
            # Early stopping
            patience=50,
            
            # Multi-scale training
            rect=False,
            resume=False,
            amp=True,  # Automatic Mixed Precision
        )
        
        self.results['training'] = results
        return results
    
    def validate_with_traffic_metrics(self) -> Dict:
        """Validation avec métriques adaptées au trafic"""
        print("✅ Validation avec métriques de trafic...")
        
        if self.model is None:
            raise ValueError("Aucun modèle entraîné trouvé!")
        
        # Validation standard YOLO
        results = self.model.val()
        
        # Métriques spécifiques au trafic
        test_images = list((self.dataset_path / 'test' / 'images').glob('*.jpg'))
        traffic_metrics = self._calculate_traffic_specific_metrics(test_images)
        
        validation_results = {
            'yolo_metrics': {
                'map50': float(results.box.map50),
                'map': float(results.box.map),
                'precision': float(results.box.p.mean()),
                'recall': float(results.box.r.mean()),
                'f1_score': float(2 * results.box.p.mean() * results.box.r.mean() / 
                                (results.box.p.mean() + results.box.r.mean()))
            },
            'traffic_metrics': traffic_metrics,
            'class_performance': self._analyze_class_performance(results)
        }
        
        self.results['validation'] = validation_results
        return validation_results
    
    def _calculate_traffic_specific_metrics(self, test_images: List[Path]) -> Dict:
        """Calculer des métriques spécifiques à l'analyse de trafic"""
        severity_predictions = []
        severity_ground_truth = []
        
        for img_path in test_images[:50]:  # Limitation pour la démo
            # Prédiction
            predictions = self.predict_image(img_path, confidence=0.5)
            predicted_severity = self._convert_to_traffic_level(predictions)
            
            # Ground truth
            txt_path = (self.dataset_path / 'test' / 'labels' / 
                       img_path.with_suffix('.txt').name)
            if txt_path.exists():
                actual_severity = self._get_image_severity(txt_path)
                
                severity_predictions.append(predicted_severity)
                severity_ground_truth.append(actual_severity)
        
        # Calculer les métriques de classification de sévérité
        from sklearn.metrics import classification_report, confusion_matrix
        
        if severity_predictions and severity_ground_truth:
            report = classification_report(
                severity_ground_truth, 
                severity_predictions, 
                output_dict=True,
                zero_division=0
            )
            
            cm = confusion_matrix(severity_ground_truth, severity_predictions)
            
            return {
                'severity_classification_report': report,
                'confusion_matrix': cm.tolist(),
                'severity_accuracy': report.get('accuracy', 0),
                'total_samples': len(severity_predictions)
            }
        
        return {'error': 'Pas assez de données pour calculer les métriques'}
    
    def predict_image(self, image_path: Path, confidence: float = 0.5) -> List[Dict]:
        """Prédiction sur une image avec métadonnées enrichies"""
        if self.model is None:
            raise ValueError("Aucun modèle entraîné trouvé!")
        
        # Prédiction YOLO
        results = self.model(str(image_path), conf=confidence)
        
        predictions = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence_score = float(box.conf[0])
                    bbox = box.xyxy[0].tolist()
                    
                    prediction = {
                        'class_id': class_id,
                        'class_name': self.classes.get(class_id, 'unknown'),
                        'confidence': confidence_score,
                        'bbox': bbox,
                        'center': [(bbox[0] + bbox[2])/2, (bbox[1] + bbox[3])/2],
                        'area': (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]),
                        'traffic_impact': self._assess_detection_impact(class_id, confidence_score)
                    }
                    predictions.append(prediction)
        
        return predictions
    
    def _assess_detection_impact(self, class_id: int, confidence: float) -> Dict:
        """Évaluer l'impact d'une détection sur le trafic"""
        impact_scores = {
            0: 0,    # circulation_normale
            1: 3,    # embouteillage_leger  
            2: 6,    # embouteillage_modere
            3: 9,    # embouteillage_severe
            4: 10,   # accident
            5: 7     # construction
        }
        
        base_impact = impact_scores.get(class_id, 0)
        weighted_impact = base_impact * confidence
        
        if weighted_impact <= 2:
            severity = 'low'
        elif weighted_impact <= 5:
            severity = 'medium'
        elif weighted_impact <= 8:
            severity = 'high'
        else:
            severity = 'critical'
        
        return {
            'impact_score': weighted_impact,
            'severity': severity,
            'estimated_delay_seconds': int(weighted_impact * 60),  # 1 point = 1min delay
            'requires_rerouting': weighted_impact > 6
        }
    
    def _convert_to_traffic_level(self, predictions: List[Dict]) -> str:
        """Convertir les prédictions YOLO en niveau de trafic TrafficAnalyzer"""
        if not predictions:
            return 'free'
        
        # Calculer le score global d'impact
        total_impact = sum(pred['traffic_impact']['impact_score'] for pred in predictions)
        max_individual_impact = max(pred['traffic_impact']['impact_score'] for pred in predictions)
        
        # Nombre de détections significatives
        significant_detections = len([p for p in predictions if p['confidence'] > 0.6])
        
        # Classification selon les seuils
        if max_individual_impact >= 9 or total_impact >= 15:
            return 'severe'
        elif max_individual_impact >= 6 or total_impact >= 10:
            return 'heavy' 
        elif max_individual_impact >= 3 or total_impact >= 5:
            return 'moderate'
        elif significant_detections > 0:
            return 'light'
        else:
            return 'free'


class ImageTrafficAnalyzer:
    """
    Analyseur de trafic basé sur l'analyse d'images
    Compatible avec TrafficAnalyzer existant
    """
    
    def __init__(self, yolo_detector: YOLOTrafficDetector):
        self.detector = yolo_detector
        self.traffic_analyzer = TrafficAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    def analyze_traffic_from_image(self, image_path: Path, 
                                 location: Optional[Dict] = None) -> Dict:
        """Analyser le trafic à partir d'une image"""
        
        try:
            # Détection YOLO
            predictions = self.detector.predict_image(image_path)
            
            # Conversion en format TrafficAnalyzer
            simulated_route_data = self._convert_predictions_to_route_data(
                predictions, location
            )
            
            # Analyse avec TrafficAnalyzer existant
            traffic_analysis = self.traffic_analyzer.analyze_route_traffic(simulated_route_data)
            
            # Enrichissement avec données image
            enhanced_analysis = self._enhance_with_image_data(
                traffic_analysis, predictions, image_path
            )
            
            return enhanced_analysis
            
        except Exception as e:
            self.logger.error(f"Erreur analyse image {image_path}: {str(e)}")
            return self._get_default_image_analysis()
    
    def _convert_predictions_to_route_data(self, predictions: List[Dict], 
                                         location: Optional[Dict]) -> Dict:
        """Convertir les prédictions YOLO en format RouteData"""
        
        # Simuler des données de route basées sur les détections
        traffic_level = self.detector._convert_to_traffic_level(predictions)
        
        # Calculer une durée simulée basée sur le niveau de trafic
        base_duration = 1800  # 30 minutes de base
        typical_duration = base_duration
        
        duration_multipliers = {
            'free': 1.0,
            'light': 1.2,
            'moderate': 1.5,
            'heavy': 2.0,
            'severe': 3.0
        }
        
        current_duration = int(base_duration * duration_multipliers.get(traffic_level, 1.0))
        
        # Format compatible avec TrafficAnalyzer
        route_data = {
            'summary': {
                'duration': current_duration,
                'typicalDuration': typical_duration,
                'length': 15000,  # 15km simulé
                'tollCosts': {},
            },
            'sections': [{
                'summary': {
                    'duration': current_duration,
                    'length': 15000
                },
                'incidents': self._convert_predictions_to_incidents(predictions)
            }]
        }
        
        if location:
            route_data['location'] = location
            
        return route_data
    
    def _convert_predictions_to_incidents(self, predictions: List[Dict]) -> List[Dict]:
        """Convertir les prédictions en incidents pour TrafficAnalyzer"""
        incidents = []
        
        for pred in predictions:
            if pred['class_id'] in [4, 5]:  # Accidents et construction
                incident = {
                    'type': 'accident' if pred['class_id'] == 4 else 'construction',
                    'title': f"{pred['class_name']} détecté",
                    'description': f"Détection automatique avec confiance {pred['confidence']:.2%}",
                    'confidence': pred['confidence']
                }
                incidents.append(incident)
        
        return incidents
    
    def _enhance_with_image_data(self, traffic_analysis: Dict, 
                               predictions: List[Dict], 
                               image_path: Path) -> Dict:
        """Enrichir l'analyse avec les données spécifiques à l'image"""
        
        # Métadonnées image
        image_metadata = {
            'image_path': str(image_path),
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'detection_count': len(predictions),
            'detections_by_class': self._count_detections_by_class(predictions),
            'confidence_stats': self._calculate_confidence_stats(predictions),
            'spatial_analysis': self._analyze_spatial_distribution(predictions)
        }
        
        # Ajouter aux résultats existants
        enhanced_analysis = traffic_analysis.copy()
        enhanced_analysis['image_analysis'] = image_metadata
        enhanced_analysis['prediction_details'] = predictions
        
        return enhanced_analysis
    
    def _count_detections_by_class(self, predictions: List[Dict]) -> Dict:
        """Compter les détections par classe"""
        counts = {}
        for pred in predictions:
            class_name = pred['class_name']
            counts[class_name] = counts.get(class_name, 0) + 1
        return counts
    
    def _calculate_confidence_stats(self, predictions: List[Dict]) -> Dict:
        """Calculer les statistiques de confiance"""
        if not predictions:
            return {'mean': 0, 'min': 0, 'max': 0, 'std': 0}
        
        confidences = [p['confidence'] for p in predictions]
        
        return {
            'mean': np.mean(confidences),
            'min': np.min(confidences),
            'max': np.max(confidences),
            'std': np.std(confidences),
            'high_confidence_count': len([c for c in confidences if c > 0.8])
        }
    
    def _analyze_spatial_distribution(self, predictions: List[Dict]) -> Dict:
        """Analyser la distribution spatiale des détections"""
        if not predictions:
            return {'clustered': False, 'density': 0}
        
        # Extraire les centres des détections
        centers = np.array([p['center'] for p in predictions])
        
        if len(centers) < 2:
            return {'clustered': False, 'density': len(predictions)}
        
        # Clustering DBSCAN pour détecter les regroupements
        clustering = DBSCAN(eps=100, min_samples=2).fit(centers)
        n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
        
        return {
            'clustered': n_clusters > 0,
            'n_clusters': n_clusters,
            'density': len(predictions) / (640 * 640),  # Supposer image 640x640
            'distribution': 'clustered' if n_clusters > 0 else 'scattered'
        }


class TrafficIntegrationService:
    """
    Service d'intégration fusionnant les données YOLO avec RouteService
    """
    
    def __init__(self, yolo_detector: YOLOTrafficDetector):
        self.detector = yolo_detector
        self.image_analyzer = ImageTrafficAnalyzer(yolo_detector)
        self.route_optimizer = RouteOptimizer()
        self.logger = logging.getLogger(__name__)
    
    def analyze_route_with_image_data(self, route_data: Dict, 
                                    image_sources: List[Dict]) -> Dict:
        """
        Analyser un itinéraire en intégrant les données d'images
        
        Args:
            route_data: Données de route depuis RouteService
            image_sources: Liste de {'image_path': Path, 'location': {'lat': float, 'lng': float}}
        """
        
        try:
            # Analyse standard de la route
            base_analysis = route_data
            
            # Analyser chaque source d'image
            image_analyses = []
            for source in image_sources:
                image_analysis = self.image_analyzer.analyze_traffic_from_image(
                    Path(source['image_path']),
                    source.get('location')
                )
                image_analyses.append(image_analysis)
            
            # Fusionner les analyses
            integrated_analysis = self._integrate_analyses(base_analysis, image_analyses)
            
            # Réoptimiser avec les nouvelles données
            optimized_analysis = self._reoptimize_with_image_data(
                integrated_analysis, image_analyses
            )
            
            return optimized_analysis
            
        except Exception as e:
            self.logger.error(f"Erreur intégration: {str(e)}")
            return route_data  # Retourner l'analyse de base en cas d'erreur
    
    def _integrate_analyses(self, route_analysis: Dict, 
                          image_analyses: List[Dict]) -> Dict:
        """Intégrer les analyses d'images avec l'analyse de route"""
        
        integrated = route_analysis.copy()
        
        # Agréger les niveaux de trafic détectés
        detected_levels = []
        total_detections = 0
        high_impact_zones = []
        
        for img_analysis in image_analyses:
            global_analysis = img_analysis.get('global_analysis', {})
            image_analysis = img_analysis.get('image_analysis', {})
            
            if global_analysis.get('traffic_level'):
                detected_levels.append(global_analysis['traffic_level'])
            
            total_detections += image_analysis.get('detection_count', 0)
            
            # Identifier les zones à fort impact
            for pred in img_analysis.get('prediction_details', []):
                if pred.get('traffic_impact', {}).get('severity') in ['high', 'critical']:
                    high_impact_zones.append({
                        'location': img_analysis.get('location'),
                        'impact': pred['traffic_impact'],
                        'detection': pred
                    })
        
        # Modifier l'analyse globale avec les données d'images
        if 'global_analysis' in integrated:
            original_level = integrated['global_analysis'].get('traffic_level', 'unknown')
            
            if detected_levels:
                # Prendre le niveau le plus sévère détecté
                severity_order = ['free', 'light', 'moderate', 'heavy', 'severe']
                most_severe = max(detected_levels, key=lambda x: severity_order.index(x) if x in severity_order else 0)
                
                # Fusionner avec l'analyse originale
                if most_severe in severity_order and original_level in severity_order:
                    final_level = max(most_severe, original_level, key=lambda x: severity_order.index(x))
                    integrated['global_analysis']['traffic_level'] = final_level
                    integrated['global_analysis']['image_enhanced'] = True
        
        # Ajouter les métadonnées d'intégration
        integrated['image_integration'] = {
            'total_images_analyzed': len(image_analyses),
            'total_detections': total_detections,
            'detected_traffic_levels': detected_levels,
            'high_impact_zones': high_impact_zones,
            'integration_timestamp': datetime.utcnow().isoformat()
        }
        
        return integrated


def setup_project_structure(base_path: str) -> Dict[str, Path]:
    """
    Créer la structure de projet complète
    
    Args:
        base_path: Chemin de base du projet
        
    Returns:
        Dict des chemins créés
    """
    
    base = Path(base_path)
    
    # Structure principale
    structure = {
        'root': base,
        'dataset': base / 'dataset',
        'models': base / 'models',
        'results': base / 'results',
        'logs': base / 'logs',
        'config': base / 'config',
        'scripts': base / 'scripts',
        'services': base / 'services'
    }
    
    # Sous-structure dataset
    dataset_structure = {
        'train_images': structure['dataset'] / 'train' / 'images',
        'train_labels': structure['dataset'] / 'train' / 'labels',
        'val_images': structure['dataset'] / 'val' / 'images', 
        'val_labels': structure['dataset'] / 'val' / 'labels',
        'test_images': structure['dataset'] / 'test' / 'images',
        'test_labels': structure['dataset'] / 'test' / 'labels',
        'raw_images': structure['dataset'] / 'raw' / 'images',
        'raw_labels': structure['dataset'] / 'raw' / 'labels'
    }
    
    structure.update(dataset_structure)
    
    # Créer tous les dossiers
    for name, path in structure.items():
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Créé: {name} -> {path}")
    
    # Créer les fichiers de configuration
    create_config_files(structure)
    
    return structure


def create_config_files(structure: Dict[str, Path]):
    """Créer les fichiers de configuration"""
    
    # Configuration principale
    main_config = {
        'project_name': 'traffic_detection_yolo',
        'version': '2.0.0',
        'dataset': {
            'classes': ['circulation_normale', 'embouteillage_leger', 'embouteillage_modere', 
                       'embouteillage_severe', 'accident', 'construction'],
            'img_size': 640,
            'batch_size': 16
        },
        'training': {
            'epochs': 150,
            'patience': 50,
            'optimizer': 'AdamW',
            'lr0': 0.01
        },
        'integration': {
            'enable_route_service': True,
            'enable_traffic_analyzer': True,
            'confidence_threshold': 0.5
        }
    }
    
    config_path = structure['config'] / 'main_config.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(main_config, f, default_flow_style=False)
    
    print(f"✅ Configuration créée: {config_path}")


def index_dataset_files(dataset_path: str, max_files: int = 2000) -> Dict:
    """
    Indexer et organiser un dossier contenant des images et fichiers texte
    
    Args:
        dataset_path: Chemin vers le dossier contenant les images et fichiers txt
        max_files: Nombre maximum de fichiers à traiter
        
    Returns:
        Rapport d'indexation
    """
    
    dataset_dir = Path(dataset_path)
    
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Le dossier {dataset_path} n'existe pas")
    
    print(f"🔍 Indexation du dataset: {dataset_path}")
    
    # Trouver tous les fichiers
    jpg_files = list(dataset_dir.glob("*.jpg"))
    txt_files = list(dataset_dir.glob("*.txt"))
    
    print(f"📁 Fichiers trouvés: {len(jpg_files)} images JPG, {len(txt_files)} fichiers TXT")
    
    # Limiter au nombre maximum
    if len(jpg_files) > max_files:
        jpg_files = jpg_files[:max_files]
        print(f"⚠️ Limitation à {max_files} images")
    
    # Vérifier la correspondance images/annotations
    matched_pairs = []
    unmatched_images = []
    unmatched_texts = []
    
    jpg_stems = {f.stem: f for f in jpg_files}
    txt_stems = {f.stem: f for f in txt_files}
    
    for stem, jpg_path in jpg_stems.items():
        if stem in txt_stems:
            matched_pairs.append((jpg_path, txt_stems[stem]))
        else:
            unmatched_images.append(jpg_path)
    
    for stem, txt_path in txt_stems.items():
        if stem not in jpg_stems:
            unmatched_texts.append(txt_path)
    
    print(f"✅ Paires correspondantes: {len(matched_pairs)}")
    print(f"⚠️ Images sans annotation: {len(unmatched_images)}")
    print(f"⚠️ Annotations sans image: {len(unmatched_texts)}")
    
    # Analyser le contenu des annotations
    annotation_analysis = analyze_annotations(matched_pairs)
    
    # Créer le rapport
    report = {
        'total_images': len(jpg_files),
        'total_annotations': len(txt_files),
        'matched_pairs': len(matched_pairs),
        'unmatched_images': len(unmatched_images),
        'unmatched_annotations': len(unmatched_texts),
        'annotation_analysis': annotation_analysis,
        'dataset_quality_score': calculate_quality_score(matched_pairs, annotation_analysis),
        'indexation_timestamp': datetime.now().isoformat()
    }
    
    # Sauvegarder le rapport
    report_path = dataset_dir / 'indexation_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"📊 Rapport sauvegardé: {report_path}")
    return report


def analyze_annotations(matched_pairs: List[Tuple[Path, Path]]) -> Dict:
    """Analyser le contenu des annotations YOLO"""
    
    print("🔍 Analyse des annotations...")
    
    all_annotations = []
    class_counts = {}
    bbox_sizes = []
    confidence_scores = []
    
    for img_path, txt_path in matched_pairs:
        try:
            with open(txt_path, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(float(parts[0]))
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    confidence = float(parts[5]) if len(parts) > 5 else 1.0
                    
                    all_annotations.append({
                        'file': txt_path.stem,
                        'class_id': class_id,
                        'bbox': [x_center, y_center, width, height],
                        'area': width * height,
                        'confidence': confidence
                    })
                    
                    class_counts[class_id] = class_counts.get(class_id, 0) + 1
                    bbox_sizes.append(width * height)
                    confidence_scores.append(confidence)
                    
        except Exception as e:
            print(f"❌ Erreur lecture {txt_path}: {e}")
    
    analysis = {
        'total_annotations': len(all_annotations),
        'class_distribution': class_counts,
        'bbox_statistics': {
            'mean_area': np.mean(bbox_sizes) if bbox_sizes else 0,
            'std_area': np.std(bbox_sizes) if bbox_sizes else 0,
            'min_area': np.min(bbox_sizes) if bbox_sizes else 0,
            'max_area': np.max(bbox_sizes) if bbox_sizes else 0
        },
        'confidence_statistics': {
            'mean': np.mean(confidence_scores) if confidence_scores else 0,
            'std': np.std(confidence_scores) if confidence_scores else 0,
            'min': np.min(confidence_scores) if confidence_scores else 0,
            'max': np.max(confidence_scores) if confidence_scores else 0
        },
        'annotations_per_image': len(all_annotations) / len(matched_pairs) if matched_pairs else 0
    }
    
    print(f"📊 Analyse terminée: {len(all_annotations)} annotations trouvées")
    return analysis


def calculate_quality_score(matched_pairs: List[Tuple[Path, Path]], 
                          annotation_analysis: Dict) -> float:
    """Calculer un score de qualité du dataset (0-100)"""
    
    score = 0
    
    # Correspondance images/annotations (30 points)
    if len(matched_pairs) > 0:
        score += 30
    
    # Distribution des classes (25 points)
    class_dist = annotation_analysis.get('class_distribution', {})
    if len(class_dist) >= 2:  # Au moins 2 classes
        score += 15
        
        # Bonus si distribution équilibrée
        if len(class_dist) >= 3:
            values = list(class_dist.values())
            max_val = max(values)
            min_val = min(values)
            if max_val / min_val <= 3:  # Ratio acceptable
                score += 10
    
    # Qualité des bounding boxes (25 points)
    bbox_stats = annotation_analysis.get('bbox_statistics', {})
    mean_area = bbox_stats.get('mean_area', 0)
    if 0.001 <= mean_area <= 0.5:  # Taille raisonnable
        score += 15
        
        std_area = bbox_stats.get('std_area', 0)
        if std_area < mean_area:  # Variance acceptable
            score += 10
    
    # Nombre d'annotations (20 points)
    total_annotations = annotation_analysis.get('total_annotations', 0)
    if total_annotations >= 500:
        score += 10
    if total_annotations >= 1000:
        score += 5
    if total_annotations >= 2000:
        score += 5
    
    return min(100, score)


# Exemple d'utilisation principale
def main():
    """Fonction principale d'exécution du système complet"""
    
    print("=" * 60)
    print("🚀 SYSTÈME DE DÉTECTION D'EMBOUTEILLAGES YOLO")
    print("=" * 60)
    
    # 1. Configuration du projet
    project_path = "traffic_detection_project"
    structure = setup_project_structure(project_path)
    
    # 2. Indexation du dataset
    dataset_path = input("obj/")
    try:
        indexation_report = index_dataset_files(dataset_path, max_files=8000)
        print(f"✅ Indexation terminée avec score qualité: {indexation_report['dataset_quality_score']:.1f}/100")
    except Exception as e:
        print(f"❌ Erreur indexation: {e}")
        return
    
    # 3. Initialisation du détecteur
    detector = YOLOTrafficDetector(dataset_path)
    
    # 4. Analyse du dataset
    print("\n📊 Analyse du dataset...")
    dataset_stats = detector.analyze_dataset()
    print(f"📈 Statistiques:")
    print(f"   - Images: {dataset_stats['total_images']}")
    print(f"   - Annotations: {dataset_stats['total_annotations']}")
    print(f"   - Objets par image: {dataset_stats['average_objects_per_image']:.1f}")
    
    # 5. Préparation des données
    print("\n📁 Division stratifiée du dataset...")
    splits = detector.prepare_stratified_split()
    
    # 6. Entraînement du modèle
    print("\n🚀 Entraînement du modèle YOLO...")
    training_results = detector.train_enhanced_model(epochs=100)  # Réduit pour la démo
    
    # 7. Validation
    print("\n✅ Validation avec métriques de trafic...")
    validation_results = detector.validate_with_traffic_metrics()
    
    # 8. Test d'intégration
    print("\n🔗 Test d'intégration avec services existants...")
    integration_service = TrafficIntegrationService(detector)
    
    # 9. Rapport final
    print("\n📋 Génération du rapport final...")
    final_report = {
        'project_info': {
            'name': 'Traffic Detection YOLO',
            'version': '2.0.0',
            'creation_date': datetime.now().isoformat()
        },
        'dataset_info': indexation_report,
        'model_performance': validation_results,
        'integration_status': 'success',
        'recommendations': generate_recommendations(validation_results, indexation_report)
    }
    
    # Sauvegarder le rapport
    report_path = structure['results'] / 'final_report.json'
    with open(report_path, 'w') as f:
        json.dump(final_report, f, indent=2, default=str)
    
    print("=" * 60)
    print("✅ SYSTÈME DÉPLOYÉ AVEC SUCCÈS!")
    print("=" * 60)
    print(f"📊 Performances du modèle:")
    yolo_metrics = validation_results.get('yolo_metrics', {})
    print(f"   - mAP@0.5: {yolo_metrics.get('map50', 0):.3f}")
    print(f"   - mAP@0.5:0.95: {yolo_metrics.get('map', 0):.3f}")
    print(f"   - Précision: {yolo_metrics.get('precision', 0):.3f}")
    print(f"   - Rappel: {yolo_metrics.get('recall', 0):.3f}")
    
    traffic_metrics = validation_results.get('traffic_metrics', {})
    if 'severity_accuracy' in traffic_metrics:
        print(f"   - Précision classification trafic: {traffic_metrics['severity_accuracy']:.3f}")
    
    print(f"📁 Rapport complet: {report_path}")
    print(f"📂 Modèle sauvegardé dans: {structure['models']}")


def generate_recommendations(validation_results: Dict, indexation_report: Dict) -> List[str]:
    """Générer des recommandations d'amélioration"""
    
    recommendations = []
    
    # Recommandations basées sur la performance
    yolo_metrics = validation_results.get('yolo_metrics', {})
    map50 = yolo_metrics.get('map50', 0)
    
    if map50 < 0.5:
        recommendations.append("🔄 Augmenter le nombre d'époques d'entraînement")
        recommendations.append("📈 Ajouter plus de données d'entraînement")
    elif map50 < 0.7:
        recommendations.append("⚡ Optimiser l'augmentation de données")
        recommendations.append("🎯 Ajuster les hyperparamètres")
    
    # Recommandations basées sur la qualité du dataset
    quality_score = indexation_report.get('dataset_quality_score', 0)
    
    if quality_score < 70:
        recommendations.append("📊 Améliorer l'équilibre des classes")
        recommendations.append("🏷️ Vérifier la qualité des annotations")
    
    if indexation_report.get('unmatched_images', 0) > 10:
        recommendations.append("🔗 Créer les annotations manquantes")
    
    # Recommandations d'intégration
    recommendations.append("🌐 Tester l'intégration avec HERE Maps en conditions réelles")
    recommendations.append("⚡ Optimiser les performances pour le déploiement temps réel")
    
    return recommendations


if __name__ == "__main__":
    main()