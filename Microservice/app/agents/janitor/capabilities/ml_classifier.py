"""
ML-Powered File Classification - Advanced content-based categorization.

Uses machine learning for intelligent file classification:
- Content-based document analysis
- Image recognition for better organization  
- Duplicate detection using perceptual hashing
- Learning from user corrections
"""

import os
import hashlib
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime
import asyncio
import json

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.metrics import classification_report
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("ML dependencies not available. Using rule-based classification.")

try:
    from PIL import Image
    import imagehash
    from PIL.ExifTags import TAGS
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    logging.warning("Image processing not available.")

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult
from app.agents.janitor.file_categorizer import FileCategory, categorize_file

logger = logging.getLogger(__name__)


class MLFileClassifier:
    """Machine Learning file classifier with learning capabilities."""
    
    def __init__(self):
        self.model_path = os.path.join(os.path.expanduser("~"), ".janitor_ml")
        self.model_file = os.path.join(self.model_path, "document_classifier.pkl")
        self.vectorizer_file = os.path.join(self.model_path, "vectorizer.pkl")
        self.training_data_file = os.path.join(self.model_path, "training_data.json")
        
        # Initialize ML components
        self.model = None
        self.vectorizer = None
        self.training_data = []
        
        # Create model directory
        os.makedirs(self.model_path, exist_ok=True)
        
        # Load existing model if available
        self._load_model()
    
    def _load_model(self):
        """Load trained model from disk."""
        if not ML_AVAILABLE:
            return False
            
        try:
            if os.path.exists(self.model_file) and os.path.exists(self.vectorizer_file):
                self.model = joblib.load(self.model_file)
                self.vectorizer = joblib.load(self.vectorizer_file)
                logger.info("[MLClassifier] Loaded trained model")
                
            # Load training data
            if os.path.exists(self.training_data_file):
                with open(self.training_data_file, 'r') as f:
                    self.training_data = json.load(f)
                logger.info(f"[MLClassifier] Loaded {len(self.training_data)} training samples")
                
            return True
        except Exception as e:
            logger.warning(f"[MLClassifier] Failed to load model: {e}")
            return False
    
    def _save_model(self):
        """Save trained model to disk."""
        if not ML_AVAILABLE or not self.model or not self.vectorizer:
            return False
            
        try:
            joblib.dump(self.model, self.model_file)
            joblib.dump(self.vectorizer, self.vectorizer_file)
            
            with open(self.training_data_file, 'w') as f:
                json.dump(self.training_data, f, indent=2)
                
            logger.info("[MLClassifier] Saved model and training data")
            return True
        except Exception as e:
            logger.error(f"[MLClassifier] Failed to save model: {e}")
            return False
    
    def _extract_text_features(self, file_path: str) -> Optional[str]:
        """Extract text features from document for ML training."""
        text_content = []
        
        try:
            # Extract filename features
            filename = Path(file_path).name.lower()
            text_content.append(filename)
            
            # Try to read file content for text documents
            ext = Path(file_path).suffix.lower()
            if ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()[:1000]  # First 1000 chars
                        text_content.append(content)
                except:
                    pass
            
            return ' '.join(text_content)
            
        except Exception as e:
            logger.debug(f"[MLClassifier] Failed to extract features from {file_path}: {e}")
            return None
    
    def _train_model(self):
        """Train the ML model with collected data."""
        if not ML_AVAILABLE or len(self.training_data) < 10:
            return False
            
        try:
            # Prepare training data
            texts = [item['features'] for item in self.training_data]
            labels = [item['category'] for item in self.training_data]
            
            # Create and train vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            X = self.vectorizer.fit_transform(texts)
            
            # Train classifier
            self.model = MultinomialNB()
            self.model.fit(X, labels)
            
            logger.info(f"[MLClassifier] Trained model with {len(self.training_data)} samples")
            return True
            
        except Exception as e:
            logger.error(f"[MLClassifier] Training failed: {e}")
            return False
    
    def add_training_sample(self, file_path: str, category: FileCategory):
        """Add a training sample from user feedback."""
        features = self._extract_text_features(file_path)
        if features:
            self.training_data.append({
                'file_path': file_path,
                'features': features,
                'category': category.value,
                'timestamp': datetime.now().isoformat()
            })
            
            # Retrain if we have enough samples
            if len(self.training_data) % 20 == 0:  # Retrain every 20 samples
                self._train_model()
                self._save_model()
    
    def predict_category(self, file_path: str) -> Tuple[FileCategory, float]:
        """Predict file category using ML model."""
        if not ML_AVAILABLE or not self.model or not self.vectorizer:
            # Fallback to rule-based classification
            return categorize_file(file_path), 0.5
        
        try:
            features = self._extract_text_features(file_path)
            if not features:
                return categorize_file(file_path), 0.3
            
            # Transform features and predict
            X = self.vectorizer.transform([features])
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            confidence = max(probabilities)
            
            # Convert prediction back to FileCategory
            try:
                predicted_category = FileCategory(prediction)
                return predicted_category, confidence
            except ValueError:
                return categorize_file(file_path), 0.3
                
        except Exception as e:
            logger.debug(f"[MLClassifier] Prediction failed for {file_path}: {e}")
            return categorize_file(file_path), 0.3


class ImageAnalyzer:
    """Advanced image analysis for better organization."""
    
    @staticmethod
    def get_image_hash(image_path: str) -> Optional[str]:
        """Generate perceptual hash for duplicate detection."""
        if not IMAGE_PROCESSING_AVAILABLE:
            return None
            
        try:
            with Image.open(image_path) as img:
                # Generate multiple hash types for better detection
                phash = str(imagehash.phash(img))
                dhash = str(imagehash.dhash(img))
                ahash = str(imagehash.averagehash(img))
                
                return f"{phash}_{dhash}_{ahash}"
        except Exception as e:
            logger.debug(f"[ImageAnalyzer] Failed to hash {image_path}: {e}")
            return None
    
    @staticmethod
    def extract_metadata(image_path: str) -> Dict:
        """Extract EXIF metadata from images."""
        if not IMAGE_PROCESSING_AVAILABLE:
            return {}
            
        try:
            with Image.open(image_path) as img:
                metadata = {}
                
                # Basic image info
                metadata['format'] = img.format
                metadata['mode'] = img.mode
                metadata['size'] = img.size
                
                # EXIF data
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        metadata[tag] = value
                
                # Extract date for organization
                if 'DateTime' in metadata:
                    try:
                        date_str = metadata['DateTime']
                        metadata['date'] = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                    except:
                        pass
                
                return metadata
                
        except Exception as e:
            logger.debug(f"[ImageAnalyzer] Failed to extract metadata from {image_path}: {e}")
            return {}
    
    @staticmethod
    def is_screenshot(image_path: str) -> bool:
        """Detect if image is a screenshot using ML features."""
        if not IMAGE_PROCESSING_AVAILABLE:
            return False
            
        try:
            with Image.open(image_path) as img:
                # Common screenshot dimensions
                common_sizes = [
                    (1920, 1080), (1366, 768), (1440, 900), (1280, 720),
                    (2560, 1440), (3840, 2160), (1920, 1200), (1680, 1050)
                ]
                
                # Check size
                if img.size in common_sizes:
                    return True
                
                # Check filename patterns
                filename = Path(image_path).name.lower()
                screenshot_patterns = [
                    'screenshot', 'screen shot', 'snip', 'capture',
                    'clip', 'screen recording', 'win_', 'screenshot_'
                ]
                
                return any(pattern in filename for pattern in screenshot_patterns)
                
        except:
            return False


class MLFileClassifierCapability(BaseCapability):
    """ML-Powered File Classification capability."""
    
    name = "ml_classifier"
    description = "Advanced ML-powered file classification and organization"
    
    def __init__(self):
        self.classifier = MLFileClassifier()
        self.image_analyzer = ImageAnalyzer()
        self._file_hashes = {}  # Cache for duplicate detection
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """Analyze file using ML classification."""
        try:
            # Get ML prediction
            predicted_category, confidence = self.classifier.predict_category(file_path)
            
            # Get rule-based category for comparison
            rule_category = categorize_file(file_path)
            
            # Use ML prediction if confidence is high
            final_category = predicted_category if confidence > 0.7 else rule_category
            
            # Check for duplicates
            is_duplicate = await self._check_duplicate(file_path)
            
            # Extract image metadata if applicable
            metadata = {}
            if final_category in [FileCategory.IMAGES, FileCategory.SCREENSHOTS]:
                metadata = self.image_analyzer.extract_metadata(file_path)
                if metadata.get('date'):
                    metadata['date_folder'] = metadata['date'].strftime('%Y/%m')
            
            # Determine action
            action_required = True
            action_type = "move"
            suggestion = f"Classify as {final_category.value}"
            
            if is_duplicate:
                action_type = "delete"
                suggestion = "Duplicate file - safe to delete"
            elif final_category == FileCategory.TRASH:
                action_type = "delete"
                suggestion = "Temporary file - safe to delete"
            
            return CapabilityResult(
                capability=self.name,
                action_required=action_required,
                action_type=action_type,
                confidence=confidence,
                suggestion=suggestion,
                requires_permission=action_type == "delete",
                metadata={
                    'predicted_category': final_category.value,
                    'rule_category': rule_category.value,
                    'confidence': confidence,
                    'is_duplicate': is_duplicate,
                    'metadata': metadata
                }
            )
            
        except Exception as e:
            logger.error(f"[MLClassifier] Analysis failed: {e}")
            return CapabilityResult(
                capability=self.name,
                action_required=False,
                suggestion=f"Analysis failed: {str(e)}"
            )
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Execute the classification action."""
        try:
            from app.agents.janitor.janitor_tools import safe_move, safe_delete
            
            metadata = result.metadata
            predicted_category = metadata.get('predicted_category')
            
            if result.action_type == "delete":
                # Safe delete
                delete_result = await safe_delete(file_path, to_recycle=True)
                return delete_result.success
            
            elif result.action_type == "move":
                # Get appropriate destination
                from app.agents.janitor.file_categorizer import get_destination_path
                
                try:
                    category = FileCategory(predicted_category)
                except ValueError:
                    return False
                
                # Use date-based folder for images if metadata available
                user_home = os.path.expanduser("~")
                if category == FileCategory.IMAGES and metadata.get('metadata', {}).get('date_folder'):
                    dest_path = os.path.join(user_home, "Pictures", metadata['metadata']['date_folder'])
                else:
                    dest_path = get_destination_path(category, user_home, file_path)
                
                if not dest_path:
                    return False
                
                dest_file = os.path.join(dest_path, os.path.basename(file_path))
                
                # Move file
                move_result = await safe_move(file_path, dest_file)
                
                # Add to training data if ML was used
                if metadata.get('confidence', 0) > 0.7:
                    self.classifier.add_training_sample(file_path, category)
                
                return move_result.success
            
            return False
            
        except Exception as e:
            logger.error(f"[MLClassifier] Execution failed: {e}")
            return False
    
    async def _check_duplicate(self, file_path: str) -> bool:
        """Check if file is a duplicate using perceptual hashing."""
        try:
            # For images, use perceptual hashing
            ext = Path(file_path).suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                file_hash = self.image_analyzer.get_image_hash(file_path)
                if file_hash:
                    if file_hash in self._file_hashes:
                        return True
                    self._file_hashes[file_hash] = file_path
                    return False
            
            # For other files, use content hashing
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                if file_hash in self._file_hashes:
                    return True
                self._file_hashes[file_hash] = file_path
            
            return False
            
        except Exception as e:
            logger.debug(f"[MLClassifier] Duplicate check failed: {e}")
            return False
