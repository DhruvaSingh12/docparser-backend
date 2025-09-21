import os
import tempfile
from typing import Dict, Any, List
from PIL import Image
import cv2
import numpy as np

# PDF processing
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# OCR engines (will be installed gradually)
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    
    # Configure Tesseract path for Windows
    tesseract_path = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"Tesseract configured at: {tesseract_path}")
    else:
        print("Tesseract not found at expected path, using system PATH")
        
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except (ImportError, AttributeError) as e:
    PADDLEOCR_AVAILABLE = False
    print(f"PaddleOCR not available: {e}")

class OCREngine:
    """Base OCR engine interface"""
    
    def __init__(self):
        self.name = "base"
        self.confidence_threshold = 0.5
    
    def process(self, image_path: str) -> Dict[str, Any]:
        """Process image and return OCR results"""
        raise NotImplementedError

class TesseractEngine(OCREngine):
    """Tesseract OCR engine"""
    
    def __init__(self, lang: str = "eng"):
        super().__init__()
        self.name = "tesseract"
        self.lang = lang
        
        # Configure tesseract path if needed (Windows)
        tesseract_path = os.getenv("TESSERACT_PATH")
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def process(self, image_path: str) -> Dict[str, Any]:
        """Process image with Tesseract"""
        if not TESSERACT_AVAILABLE:
            return {
                "model": self.name,
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "error": "Tesseract is not available"
            }
        
        try:
            # Handle PDF files by converting to images first
            if image_path.lower().endswith('.pdf'):
                return self.process_pdf(image_path)
            else:
                # Process regular image files
                return self.process_image(image_path)
            
        except Exception as e:
            return {
                "model": self.name,
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "error": str(e)
            }
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Process PDF by converting to images"""
        if not PDF2IMAGE_AVAILABLE:
            return {
                "model": self.name,
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "error": "PDF processing requires pdf2image library. Install with: pip install pdf2image"
            }
        
        try:
            # Configure Poppler path for Windows
            poppler_path = None
            winget_poppler_path = os.path.expanduser(
                "~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\\poppler-25.07.0\\Library\\bin"
            )
            
            if os.path.exists(winget_poppler_path):
                poppler_path = winget_poppler_path
                print(f"Using Poppler from: {poppler_path}")
            
            # Convert PDF to images
            if poppler_path:
                images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=5, poppler_path=poppler_path)
            else:
                images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=5)
            
            all_text = ""
            all_blocks = []
            total_confidence = 0
            page_count = 0
            
            for page_num, image in enumerate(images, 1):
                # Save image to temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_path = temp_file.name
                    image.save(temp_path, 'PNG')
                
                try:
                    # Process the page image
                    page_result = self.process_image(temp_path)
                    
                    if page_result.get("text"):
                        all_text += f"[Page {page_num}]\n{page_result['text']}\n\n"
                        
                        # Add page info to blocks
                        for block in page_result.get("blocks", []):
                            block["page"] = page_num
                            all_blocks.append(block)
                        
                        total_confidence += page_result.get("confidence", 0)
                        page_count += 1
                
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            
            avg_confidence = total_confidence / max(page_count, 1)
            
            return {
                "model": self.name,
                "text": all_text.strip(),
                "confidence": avg_confidence,
                "blocks": all_blocks,
                "language": self.lang,
                "pages_processed": page_count
            }
            
        except Exception as e:
            return {
                "model": self.name,
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "error": f"PDF processing failed: {str(e)}"
            }
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process a single image file"""
        try:
            # Load and preprocess image
            image = self.preprocess_image(image_path)
            
            # Extract text with confidence scores
            data = pytesseract.image_to_data(
                image, 
                lang=self.lang, 
                output_type=pytesseract.Output.DICT
            )
            
            # Process results
            text_blocks = []
            full_text = ""
            total_confidence = 0
            valid_blocks = 0
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i]) if data['conf'][i] != -1 else 0
                
                if text and conf > 0:
                    text_blocks.append({
                        "text": text,
                        "confidence": conf / 100.0,
                        "bbox": [
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        ]
                    })
                    full_text += text + " "
                    total_confidence += conf
                    valid_blocks += 1
            
            avg_confidence = total_confidence / max(valid_blocks, 1) / 100.0
            
            return {
                "model": self.name,
                "text": full_text.strip(),
                "confidence": avg_confidence,
                "blocks": text_blocks,
                "language": self.lang
            }
            
        except Exception as e:
            return {
                "model": self.name,
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "error": f"Image processing failed: {str(e)}"
            }
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Try multiple ways to load image with OpenCV
            img = None
            
            # Method 1: Standard cv2.imread
            try:
                img = cv2.imread(image_path)
            except AttributeError:
                pass
            
            # Method 2: If cv2.imread doesn't exist, try with PIL and convert
            if img is None:
                try:
                    from PIL import Image
                    pil_img = Image.open(image_path)
                    # Convert PIL to OpenCV format
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception:
                    pass
            
            # Method 3: Pure PIL approach if OpenCV is problematic
            if img is None:
                from PIL import Image
                pil_img = Image.open(image_path)
                # Convert to grayscale with PIL
                if pil_img.mode != 'L':
                    pil_img = pil_img.convert('L')
                return np.array(pil_img)
            
            # Convert to grayscale
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # Apply basic preprocessing
            try:
                # Denoise
                denoised = cv2.GaussianBlur(gray, (3, 3), 0)
                
                # Binarization
                _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                return binary
            except AttributeError:
                # If OpenCV functions don't work, return the grayscale image
                return gray
                
        except Exception as e:
            # Fallback: load with PIL only
            from PIL import Image
            pil_img = Image.open(image_path)
            if pil_img.mode != 'L':
                pil_img = pil_img.convert('L')
            return np.array(pil_img)

class PaddleOCREngine(OCREngine):
    """PaddleOCR engine"""
    
    def __init__(self, lang: str = "en"):
        super().__init__()
        self.name = "paddleocr"
        self.lang = lang
        
        if PADDLEOCR_AVAILABLE:
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                use_gpu=os.getenv("USE_GPU", "false").lower() == "true"
            )
    
    def process(self, image_path: str) -> Dict[str, Any]:
        """Process image with PaddleOCR"""
        if not PADDLEOCR_AVAILABLE:
            raise RuntimeError("PaddleOCR is not available")
        
        try:
            result = self.ocr.ocr(image_path, cls=True)
            
            text_blocks = []
            full_text = ""
            total_confidence = 0
            
            for line in result[0] if result[0] else []:
                bbox, (text, confidence) = line
                
                text_blocks.append({
                    "text": text,
                    "confidence": confidence,
                    "bbox": [bbox[0][0], bbox[0][1], bbox[2][0], bbox[2][1]]
                })
                full_text += text + " "
                total_confidence += confidence
            
            avg_confidence = total_confidence / max(len(text_blocks), 1)
            
            return {
                "model": self.name,
                "text": full_text.strip(),
                "confidence": avg_confidence,
                "blocks": text_blocks,
                "language": self.lang
            }
            
        except Exception as e:
            return {
                "model": self.name,
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "error": str(e)
            }

class OCRService:
    """Main OCR service that manages multiple engines"""
    
    def __init__(self):
        self.engines = []
        self.default_engine = None
        
        # Initialize available engines
        if TESSERACT_AVAILABLE:
            tesseract = TesseractEngine()
            self.engines.append(tesseract)
            if not self.default_engine:
                self.default_engine = tesseract
        
        if PADDLEOCR_AVAILABLE:
            paddle = PaddleOCREngine()
            self.engines.append(paddle)
            self.default_engine = paddle  # Prefer PaddleOCR if available
        
        if not self.engines:
            raise RuntimeError("No OCR engines available. Please install tesseract or paddleocr.")
    
    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engines"""
        return [engine.name for engine in self.engines]
    
    def process_with_engine(self, image_path: str, engine_name: str = None) -> Dict[str, Any]:
        """Process image with specific engine"""
        if engine_name:
            engine = next((e for e in self.engines if e.name == engine_name), None)
            if not engine:
                raise ValueError(f"Engine '{engine_name}' not available")
        else:
            engine = self.default_engine
        
        return engine.process(image_path)
    
    def process_with_best_engine(self, image_path: str) -> Dict[str, Any]:
        """Process with multiple engines and return best result"""
        if len(self.engines) == 1:
            return self.engines[0].process(image_path)
        
        results = []
        for engine in self.engines:
            try:
                result = engine.process(image_path)
                results.append(result)
            except Exception as e:
                print(f"Engine {engine.name} failed: {e}")
        
        if not results:
            return {
                "model": "none",
                "text": "",
                "confidence": 0.0,
                "blocks": [],
                "error": "All OCR engines failed"
            }
        
        # Return result with highest confidence
        best_result = max(results, key=lambda x: x.get("confidence", 0))
        return best_result

# Global OCR service instance
_ocr_service = None

def get_ocr_service() -> OCRService:
    """Get global OCR service instance"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service

async def ocr_process(image_path: str, engine_name: str = None) -> Dict[str, Any]:
    """
    Main OCR processing function
    
    Args:
        image_path: Path to image file
        engine_name: Specific OCR engine to use (optional)
    
    Returns:
        OCR processing results
    """
    service = get_ocr_service()
    
    if engine_name:
        return service.process_with_engine(image_path, engine_name)
    else:
        return service.process_with_best_engine(image_path)