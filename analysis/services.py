# analysis/services.py
import logging
import tempfile
import json
import os
from collections import defaultdict
import ollama

# Django imports
from django.conf import settings

# Third-party imports
import pandas as pd
from sklearn.ensemble import IsolationForest
import text2emotion as te
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    @staticmethod
    def _get_emoji_data():
        """
        Fonction utilitaire pour obtenir les données emoji 
        de manière compatible avec toutes les versions
        """
        try:
            import emoji
            
            # Essayer la nouvelle API (emoji >= 2.0.0)
            try:
                return set(emoji.EMOJI_DATA.keys())
            except AttributeError:
                pass
            
            # Essayer l'API intermédiaire (emoji >= 1.6.0)
            try:
                return set(emoji.UNICODE_EMOJI['en'].keys())
            except (AttributeError, KeyError):
                pass
            
            # Essayer l'ancienne API (emoji < 1.6.0)
            try:
                return set(emoji.UNICODE_EMOJI.keys())
            except AttributeError:
                pass
                
        except ImportError:
            logger.warning("Bibliothèque emoji non disponible")
        
        return set()
    
    @staticmethod
    def _count_emojis(text):
        """Compte les emojis dans le texte"""
        try:
            import emoji
            
            # Utiliser is_emoji si disponible (plus fiable)
            if hasattr(emoji, 'is_emoji'):
                return sum(1 for char in text if emoji.is_emoji(char))
            
            # Solution de repli avec les données emoji
            emoji_set = SentimentAnalyzer._get_emoji_data()
            return sum(1 for char in text if char in emoji_set)
            
        except Exception as e:
            logger.debug(f"Erreur comptage emojis: {str(e)}")
            return 0

    @staticmethod
    def analyze_sentiment(text_data):
        try:
            # Essayer d'utiliser text2emotion
            try:
                import text2emotion as te
                result = te.get_emotion(text_data)
                
                # Ajouter des métriques supplémentaires
                emoji_count = SentimentAnalyzer._count_emojis(text_data)
                result['emoji_count'] = emoji_count
                
                return result
                
            except Exception as te_error:
                logger.warning(f"text2emotion échoué: {str(te_error)}")
                # Passer à l'implémentation de repli
                pass
            
            # Implémentation manuelle améliorée
            emotions = defaultdict(float)
            
            # Dictionnaires de mots-clés étendus
            emotion_keywords = {
                'happy': ['bon', 'super', 'heureux', 'joie', 'content', 'ravi', 'excellent', 'parfait', 'génial'],
                'angry': ['colère', 'énervé', 'furieux', 'rage', 'irrité', 'fâché', 'mécontent'],
                'sad': ['triste', 'déprimé', 'malheureux', 'chagrin', 'mélancolique', 'désolé'],
                'fear': ['peur', 'inquiet', 'anxieux', 'terreur', 'effroi', 'angoisse', 'stress'],
                'surprise': ['surpris', 'étonné', 'choqué', 'stupéfait', 'incroyable', 'wow']
            }
            
            text = text_data.lower()
            words = text.split()
            
            # Analyser chaque mot
            for word in words:
                for emotion, keywords in emotion_keywords.items():
                    if any(keyword in word for keyword in keywords):
                        emotions[emotion] += 1.0
            
            # Analyser la ponctuation
            if '!' in text_data:
                emotions['surprise'] += 0.5
                emotions['happy'] += 0.3
            if '?' in text_data:
                emotions['surprise'] += 0.2
            if text_data.isupper():
                emotions['angry'] += 0.5
            
            # Compter les emojis
            emoji_count = SentimentAnalyzer._count_emojis(text_data)
            if emoji_count > 0:
                emotions['happy'] += emoji_count * 0.2
            
            # Normalisation
            total = sum(emotions.values()) or 1
            normalized_emotions = {k: round(v/total, 3) for k, v in emotions.items()}
            
            # Ajouter les émotions manquantes avec une valeur de 0
            for emotion in ['happy', 'angry', 'surprise', 'sad', 'fear']:
                if emotion not in normalized_emotions:
                    normalized_emotions[emotion] = 0.0
            
            # Ajouter les métriques
            normalized_emotions['emoji_count'] = emoji_count
            normalized_emotions['word_count'] = len(words)
            
            return normalized_emotions
                
        except Exception as e:
            logger.error(f"Erreur analyse sentiment: {str(e)}")
            return {
                'happy': 0.0,
                'angry': 0.0,
                'surprise': 0.0,
                'sad': 0.0,
                'fear': 0.0,
                'emoji_count': 0,
                'word_count': 0,
                'error': str(e)
            }

class ForensicAI:
    def __init__(self):
        self.timeout = 30  # 30 secondes timeout
        try:
            self.phi3_config = settings.AI_CONFIG.get('ollama', {})
        except AttributeError:
            logger.warning("Configuration AI_CONFIG non trouvée dans settings")
            self.phi3_config = {'model': 'phi3:mini'}

    def analyze(self, data, data_type):
        """Méthode principale d'analyse des données"""
        try:
            # Debug du contenu des données
            debug_info = self.debug_data_content(data, data_type)
            logger.info(f"Debug info: {debug_info}")
            
            # Vérification des données d'entrée
            if not data:
                return {
                    'error': 'No data provided',
                    'data_type': data_type
                }

            results = {
                'data_type': data_type,
                'item_count': len(data) if isinstance(data, list) else 1
            }

            # Analyse spécifique par type de données
            if data_type == 'sms':
                results.update(self._analyze_text_data(data))
            elif data_type == 'images':
                results.update(self._analyze_image_data(data))
            elif data_type == 'calls':
                results.update(self._analyze_call_data(data))
            else:
                results.update(self._analyze_generic_data(data))

            # Ajout du résumé LLM pour tous les types
            results['llm_summary'] = self._get_llm_summary(data, data_type)

            return results

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse: {str(e)}")
            return {
                'error': str(e),
                'data_type': data_type
            }

    def debug_data_content(self, data, data_type):
        """Méthode pour debugger le contenu avant analyse"""
        logger.info(f"Debug data_type: {data_type}")
        logger.info(f"Type données: {type(data)}")
        
        sample = None
        if isinstance(data, list):
            sample = data[:3]
        elif isinstance(data, dict):
            sample = dict(list(data.items())[:3])
        else:
            sample = str(data)[:100]
            
        logger.info(f"Extrait données: {sample}")
        
        return {
            'data_type': str(data_type),
            'input_type': str(type(data)),
            'sample_data': sample
        }

    def _analyze_text_data(self, text_data):
        """Analyse des données textuelles (SMS, contacts, etc.)"""
        if not isinstance(text_data, list):
            text_data = [text_data]

        return {
            'fraud': self._detect_fraud(text_data, 'sms'),
            'sentiment': self._analyze_sentiment(text_data),
            'anomalies': self._detect_anomalies(text_data)
        }

    def _analyze_image_data(self, image_data):
        """Analyse des métadonnées d'images"""
        return {
            'metadata': {
                'count': len(image_data),
                'sample': [img.get('name') for img in image_data[:3]]
            },
            'anomalies': self._detect_anomalies(image_data)
        }

    def _analyze_call_data(self, call_data):
        """Analyse des logs d'appels"""
        return {
            'stats': {
                'total_calls': len(call_data),
                'duration_avg': sum(c.get('duration', 0) for c in call_data) / len(call_data) if call_data else 0
            },
            'anomalies': self._detect_anomalies(call_data)
        }

    def _analyze_generic_data(self, data):
        """Analyse générique pour les autres types de données"""
        return {
            'data_sample': data[:3] if isinstance(data, list) else data
        }

    def _detect_fraud(self, data, data_type):
        """Détection de fraude basée sur des mots-clés"""
        fraud_keywords = getattr(settings, 'AI_CONFIG', {}).get('fraud_keywords', [
            'urgent', 'félicitations', 'gratuit', 'cliquez', 'argent'
        ])

        frauds = []
        for item in data:
            text = str(item.get('body', item)).lower()
            found_keywords = [kw for kw in fraud_keywords if kw in text]
            
            if found_keywords:
                frauds.append({
                    'text': text[:100] + '...' if len(text) > 100 else text,
                    'keywords': found_keywords,
                    'confidence': min(0.99, len(found_keywords) * 0.3)
                })

        return frauds[:100]  # Limite à 100 résultats

    def _analyze_sentiment(self, text_data):
        """Analyse de sentiment avec text2emotion"""
        try:
            if isinstance(text_data, list):
                text = ' '.join(str(item.get('body', item)) for item in text_data)
            else:
                text = str(text_data)

            return SentimentAnalyzer.analyze_sentiment(text)
        except Exception as e:
            logger.warning(f"Erreur analyse sentiment: {str(e)}")
            return {
                'happy': 0,
                'angry': 0,
                'surprise': 0,
                'sad': 0,
                'fear': 0,
                'error': str(e)
            }

    def _detect_anomalies(self, data):
        """Détection d'anomalies avec Isolation Forest"""
        try:
            df = pd.DataFrame(data if isinstance(data, list) else [data])
            numeric = df.select_dtypes(include=['number'])
            
            if not numeric.empty and len(numeric) > 1:
                clf = IsolationForest(n_estimators=50, random_state=42)
                clf.fit(numeric)
                scores = clf.decision_function(numeric)
                
                return {
                    'anomaly_scores': scores.tolist(),
                    'anomaly_count': sum(1 for score in scores if score < -0.1)
                }
            return {'message': 'Pas assez de données numériques'}
            
        except Exception as e:
            logger.error(f"Erreur détection anomalies: {str(e)}")
            return {'error': str(e)}

    def _get_llm_summary(self, data, data_type):
        """Génère un résumé avec Ollama/LLM"""
        try:
            if not isinstance(data, list):
                data = [data]

            prompt = f"""Analyse forensique des {data_type}:
            Données: {json.dumps(data[:3], ensure_ascii=False)[:1000]}...
            Fais un résumé concis en 3 points maximum en français."""
            
            response = ollama.chat(
                model=self.phi3_config.get('model', 'phi3:mini'),
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1}
            )
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Erreur LLM: {str(e)}")
            return f"Résumé indisponible: {str(e)}"

class PDFGenerator:
    @staticmethod
    def generate(session, analysis_results=None):
        """Génère un rapport PDF pour une session forensique"""
        try:
            # Créer un fichier temporaire ou dans un dossier spécifique
            filename = f"report_{session.session_id}.pdf"
            
            # Utiliser un dossier temporaire ou le dossier media
            try:
                if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
                    filepath = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                else:
                    filepath = os.path.join(tempfile.gettempdir(), filename)
            except:
                filepath = os.path.join(tempfile.gettempdir(), filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            styles = getSampleStyleSheet()
            
            elements = [
                Paragraph(f"Rapport Forensique - Session {session.session_id}", styles['Title']),
                Spacer(1, 12),
                Paragraph(f"Généré le: {getattr(session, 'created_at', 'N/A')}", styles['Normal']),
                Spacer(1, 12)
            ]
            
            # Récupérer tous les résultats d'analyse de la session
            all_results = {}
            fraud_results = []
            sentiment_data = {}
            anomaly_data = {}
            llm_summaries = []
            
            # Collecter tous les résultats depuis la base de données
            for data_item in session.collected_items.all():
                for result in data_item.results.all():
                    result_json = result.result_json or {}
                    
                    # Organiser par type d'analyse
                    if result.analysis_type == 'fraud' or 'fraud' in result_json:
                        fraud_list = result_json.get('fraud', [])
                        if fraud_list:
                            fraud_results.extend(fraud_list)
                    
                    if result.analysis_type == 'sentiment' or 'sentiment' in result_json:
                        sentiment_data.update(result_json.get('sentiment', {}))
                    
                    if result.analysis_type == 'anomaly' or 'anomalies' in result_json:
                        anomaly_data.update(result_json.get('anomalies', {}))
                    
                    if result.analysis_type == 'llm' or 'llm_summary' in result_json:
                        summary = result_json.get('llm_summary', '')
                        if summary and summary not in llm_summaries:
                            llm_summaries.append(summary)
                    
                    # Collecter tous les résultats pour compatibilité
                    all_results.update(result_json)
            
            # Section Fraude
            if fraud_results:
                elements.extend([
                    Paragraph("🚨 Détection de Fraude", styles['Heading2']),
                    Spacer(1, 6)
                ])
                
                # Créer le tableau des fraudes
                fraud_data = [["Extrait", "Mots-clés détectés", "Niveau de confiance"]]
                
                for fraud in fraud_results[:10]:  # Limiter à 10 pour le PDF
                    if isinstance(fraud, dict):
                        fraud_data.append([
                            fraud.get('text', 'N/A')[:50] + '...' if len(fraud.get('text', '')) > 50 else fraud.get('text', 'N/A'),
                            ', '.join(fraud.get('keywords', [])),
                            f"{fraud.get('confidence', 0):.0%}"
                        ])
                
                if len(fraud_data) > 1:  # Si on a des données en plus de l'en-tête
                    fraud_table = Table(fraud_data, colWidths=[200, 150, 100])
                    fraud_table.setStyle([
                        ('GRID', (0,0), (-1,-1), 1, colors.grey),
                        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('FONTSIZE', (0,0), (-1,-1), 9)
                    ])
                    elements.append(fraud_table)
                    elements.append(Spacer(1, 12))
            
            # Section Analyse Sentiment
            if sentiment_data and not sentiment_data.get('error'):
                elements.extend([
                    Paragraph("😊 Analyse des Sentiments", styles['Heading2']),
                    Spacer(1, 6)
                ])
                
                sentiment_table_data = [["Émotion", "Score"]]
                for emotion, score in sentiment_data.items():
                    if isinstance(score, (int, float)) and emotion not in ['emoji_count', 'word_count']:
                        sentiment_table_data.append([
                            emotion.capitalize(),
                            f"{score:.2%}" if score <= 1 else f"{score:.2f}"
                        ])
                
                if len(sentiment_table_data) > 1:
                    sentiment_table = Table(sentiment_table_data, colWidths=[200, 100])
                    sentiment_table.setStyle([
                        ('GRID', (0,0), (-1,-1), 1, colors.grey),
                        ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
                        ('FONTSIZE', (0,0), (-1,-1), 10)
                    ])
                    elements.append(sentiment_table)
                    elements.append(Spacer(1, 12))
            
            # Section Anomalies
            if anomaly_data and not anomaly_data.get('error'):
                elements.extend([
                    Paragraph("📊 Détection d'Anomalies", styles['Heading2']),
                    Spacer(1, 6)
                ])
                
                if 'anomaly_count' in anomaly_data:
                    elements.append(Paragraph(
                        f"Anomalies détectées: {anomaly_data['anomaly_count']} sur {anomaly_data.get('total_samples', 0)} échantillons",
                        styles['Normal']
                    ))
                elif 'anomaly_scores' in anomaly_data:
                    elements.append(Paragraph(
                        f"Scores d'anomalies calculés: {len(anomaly_data.get('anomaly_scores', []))} points de données",
                        styles['Normal']
                    ))
                else:
                    elements.append(Paragraph(
                        anomaly_data.get('message', 'Analyse d\'anomalies effectuée'),
                        styles['Normal']
                    ))
                
                elements.append(Spacer(1, 12))
            
            # Section Résumé IA
            if llm_summaries:
                elements.extend([
                    Paragraph("🤖 Résumé de l'Intelligence Artificielle", styles['Heading2']),
                    Spacer(1, 6)
                ])
                
                for i, summary in enumerate(llm_summaries[:3]):  # Limiter à 3 résumés
                    if summary and not summary.startswith('Erreur') and not summary.startswith('Résumé indisponible'):
                        if len(llm_summaries) > 1:
                            elements.append(Paragraph(f"Résumé {i+1}:", styles['Heading3']))
                        elements.append(Paragraph(summary, styles['Normal']))
                        elements.append(Spacer(1, 6))
                
                elements.append(Spacer(1, 12))
            
            # Section Statistiques générales
            elements.extend([
                Paragraph("📈 Statistiques Générales", styles['Heading2']),
                Spacer(1, 6)
            ])
            
            stats_data = [
                ["Métrique", "Valeur"],
                ["Nombre d'éléments analysés", str(session.collected_items.count())],
                ["Nombre de résultats de fraude", str(len(fraud_results))],
                ["Types de données analysées", ", ".join(set(session.collected_items.values_list('data_type', flat=True)))],
                ["Résultats critiques", str(session.collected_items.filter(results__is_critical=True).count())],
            ]
            
            stats_table = Table(stats_data, colWidths=[250, 150])
            stats_table.setStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgreen),
                ('FONTSIZE', (0,0), (-1,-1), 10)
            ])
            elements.append(stats_table)
            elements.append(Spacer(1, 12))
            
            # Section Métadonnées
            elements.extend([
                Paragraph("ℹ️ Informations de Session", styles['Heading2']),
                Spacer(1, 6),
                Paragraph(f"ID Session: {session.session_id}", styles['Normal']),
                Paragraph(f"Utilisateur: {getattr(session, 'user', 'N/A')}", styles['Normal']),
                Paragraph(f"Statut d'analyse: {'Complète' if getattr(session, 'is_analyzed', False) else 'Partielle'}", styles['Normal'])
            ])
            
            doc.build(elements)
            logger.info(f"Rapport PDF généré: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Erreur génération PDF: {str(e)}")
            # Créer un rapport d'erreur minimal
            error_filename = f"error_report_{session.session_id}.pdf"
            error_filepath = os.path.join(tempfile.gettempdir(), error_filename)
            
            try:
                doc = SimpleDocTemplate(error_filepath, pagesize=A4)
                styles = getSampleStyleSheet()
                elements = [
                    Paragraph("Erreur de Génération de Rapport", styles['Title']),
                    Spacer(1, 12),
                    Paragraph(f"Une erreur s'est produite: {str(e)}", styles['Normal']),
                    Spacer(1, 12),
                    Paragraph(f"Session ID: {session.session_id}", styles['Normal'])
                ]
                doc.build(elements)
                return error_filepath
            except Exception as final_error:
                logger.error(f"Impossible de créer le rapport d'erreur: {str(final_error)}")
                raise Exception(f"Impossible de générer le rapport PDF: {str(e)}")

# Utilitaire pour tester la compatibilité emoji
def test_emoji_compatibility():
    """Fonction de test pour vérifier la compatibilité emoji"""
    test_text = "Bonjour 😊 Comment allez-vous? 🤔"
    
    print("Test de compatibilité emoji:")
    try:
        analyzer = SentimentAnalyzer()
        emoji_count = analyzer._count_emojis(test_text)
        sentiment = analyzer.analyze_sentiment(test_text)
        
        print(f"✓ Emojis détectés: {emoji_count}")
        print(f"✓ Analyse sentiment: {sentiment}")
        return True
        
    except Exception as e:
        print(f"✗ Erreur: {str(e)}")
        return False

if __name__ == "__main__":
    test_emoji_compatibility()