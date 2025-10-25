from typing import List
import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class LayoutElement:
    """Base class for layout elements"""
    def __init__(self, bbox: List[int], confidence: float = 0.0):
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.element_type = "unknown"
    
    def area(self) -> int:
        """Calculate area of bounding box"""
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


class TextBlock(LayoutElement):
    """Text block element"""
    def __init__(self, bbox: List[int], text: str, confidence: float = 0.0):
        super().__init__(bbox, confidence)
        self.element_type = "text_block"
        self.text = text
        self.lines = []


class TableElement(LayoutElement):
    """Table element with structured data"""
    def __init__(self, bbox: List[int], confidence: float = 0.0):
        super().__init__(bbox, confidence)
        self.element_type = "table"
        self.rows = []
        self.columns = []
        self.cells = []
        self.structured_data = []
    
    def add_cell(self, row: int, col: int, text: str, cell_bbox: List[int], confidence: float = 0.0):
        """Add a cell to the table"""
        self.cells.append({
            'row': row,
            'col': col,
            'text': text.strip(),
            'bbox': cell_bbox,
            'confidence': confidence
        })
    
    def get_structured_data(self) -> List[List[str]]:
        """Get table as 2D array"""
        if not self.cells:
            return []
        
        # Find max row and column
        max_row = max(cell['row'] for cell in self.cells) + 1
        max_col = max(cell['col'] for cell in self.cells) + 1
        
        # Initialize table structure
        table_data = [["" for _ in range(max_col)] for _ in range(max_row)]
        
        # Fill in cell data
        for cell in self.cells:
            table_data[cell['row']][cell['col']] = cell['text']
        
        return table_data


def load_image(image_path: str) -> np.ndarray:
    """Load and preprocess image for analysis"""
    try:
        # Try OpenCV first
        img = cv2.imread(image_path)
        if img is not None:
            return img
    except:
        pass
    
    # Fallback to PIL
    pil_img = Image.open(image_path)
    return np.array(pil_img)