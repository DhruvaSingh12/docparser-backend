from typing import Dict, Any, List
import logging
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from .base import load_image
from .table_detector import TableDetector
from .text_extractor import TextExtractor

logger = logging.getLogger(__name__)

class LayoutAnalyzer:
    """Analyzes document layout and extracts structured elements"""
    
    def __init__(self):
        self.table_detector = TableDetector()
        self.text_extractor = TextExtractor()
    
    def analyze_layout(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze document layout and extract structured elements
        
        Returns:
            Dictionary with separate text blocks and tables
        """
        if not TESSERACT_AVAILABLE:
            return {
                "text_blocks": [],
                "tables": [],
                "error": "Tesseract not available"
            }
        
        try:
            # Load and preprocess image
            image = load_image(image_path)
            
            # Get detailed OCR data with layout information
            ocr_data = self._get_detailed_ocr_data(image)
            
            # Detect tables using multiple methods
            tables = self.table_detector.detect_tables(image, ocr_data)
            
            # Extract text blocks (non-table content)
            text_blocks = self.text_extractor.extract_text_blocks(ocr_data, tables)
            
            # Format output
            return {
                "text_blocks": [self.text_extractor.format_text_block(tb) for tb in text_blocks],
                "tables": [self.text_extractor.format_table(table) for table in tables],
                "layout_confidence": self._calculate_layout_confidence(text_blocks, tables)
            }
            
        except Exception as e:
            logger.error(f"Layout analysis failed: {str(e)}")
            return {
                "text_blocks": [],
                "tables": [],
                "error": str(e)
            }
    
    def _get_detailed_ocr_data(self, image: Any) -> Dict:
        """Get detailed OCR data with layout information"""
        # PSM 6 = uniform block of text (good for mixed content)
        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config='--psm 6 -c tessedit_create_hocr=1'
        )
        
        return data
    
    def _calculate_layout_confidence(self, text_blocks: List, tables: List) -> float:
        """Calculate overall confidence in layout detection"""
        if not text_blocks and not tables:
            return 0.0
        
        total_confidence = 0.0
        total_elements = 0
        
        for block in text_blocks:
            total_confidence += block.confidence
            total_elements += 1
        
        for table in tables:
            total_confidence += table.confidence
            total_elements += 1
        
        return total_confidence / total_elements if total_elements > 0 else 0.0