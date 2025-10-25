from typing import List, Dict, Any
import logging
from .base import TextBlock, TableElement

logger = logging.getLogger(__name__)

class TextExtractor:
    """Extracts and processes text blocks from OCR data"""
    
    def __init__(self):
        self.min_confidence = 0
    
    def extract_text_blocks(self, ocr_data: Dict, tables: List[TableElement]) -> List[TextBlock]:
        """Extract text blocks that are not part of any table"""
        text_blocks = []
        
        # Get all text elements
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            if not text or int(ocr_data['conf'][i]) <= self.min_confidence:
                continue
            
            bbox = [
                ocr_data['left'][i],
                ocr_data['top'][i],
                ocr_data['left'][i] + ocr_data['width'][i],
                ocr_data['top'][i] + ocr_data['height'][i]
            ]
            
            # Check if this text is inside any table
            is_in_table = False
            for table in tables:
                if self._point_in_bbox(bbox, table.bbox):
                    is_in_table = True
                    break
            
            if not is_in_table:
                confidence = int(ocr_data['conf'][i]) / 100.0
                text_blocks.append(TextBlock(bbox, text, confidence))
        
        return text_blocks
    
    def _point_in_bbox(self, point_bbox: List[int], container_bbox: List[int]) -> bool:
        """Check if a bounding box is inside another bounding box"""
        return (point_bbox[0] >= container_bbox[0] and 
                point_bbox[1] >= container_bbox[1] and
                point_bbox[2] <= container_bbox[2] and 
                point_bbox[3] <= container_bbox[3])
    
    def format_text_block(self, text_block: TextBlock) -> Dict[str, Any]:
        """Convert TextBlock to dictionary format"""
        return {
            "type": "text_block",
            "text": text_block.text,
            "bbox": text_block.bbox,
            "confidence": text_block.confidence
        }
    
    def format_table(self, table: TableElement) -> Dict[str, Any]:
        """Convert TableElement to dictionary format"""
        return {
            "type": "table",
            "bbox": table.bbox,
            "confidence": table.confidence,
            "structured_data": table.get_structured_data(),
            "cells": table.cells,
            "row_count": len(set(cell['row'] for cell in table.cells)) if table.cells else 0,
            "column_count": len(set(cell['col'] for cell in table.cells)) if table.cells else 0
        }