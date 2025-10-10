import os
import numpy as np
from typing import Dict, List, Any, Optional
import warnings

# Suppress PaddleOCR warnings
warnings.filterwarnings("ignore", category=UserWarning, module="paddle")
warnings.filterwarnings("ignore", message=".*ccache.*")

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
    print("PaddleOCR import successful")
except (ImportError, AttributeError) as e:
    PADDLEOCR_AVAILABLE = False
    print(f"PaddleOCR not available: {e}")
except Exception as e:
    PADDLEOCR_AVAILABLE = False
    print(f"PaddleOCR initialization error: {e}")

class TableRecognitionEngine:
    """PaddleOCR-based table recognition and structure extraction"""
    
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.table_ocr = None
        
        if PADDLEOCR_AVAILABLE:
            try:
                # Initialize PaddleOCR with table recognition enabled
                self.table_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=lang,
                    use_gpu=os.getenv("USE_GPU", "false").lower() == "true",
                    show_log=False
                )
                print("PaddleOCR table recognition initialized")
            except Exception as e:
                print(f"Failed to initialize PaddleOCR table recognition: {e}")
                self.table_ocr = None
    
    def is_available(self) -> bool:
        """Check if table recognition is available"""
        return PADDLEOCR_AVAILABLE and self.table_ocr is not None
    
    def extract_table_structure(self, image_path: str) -> Dict[str, Any]:
        """
        Extract table structure and content from image
        
        Returns:
            Dict with table structure, cells, and reconstructed data
        """
        if not self.is_available():
            return {
                "error": "PaddleOCR table recognition not available",
                "table_detected": False,
                "structured_data": []
            }
        
        try:
            # Run PaddleOCR on the image
            result = self.table_ocr.ocr(image_path, cls=True)
            
            if not result or not result[0]:
                return {
                    "error": "No text detected in image",
                    "table_detected": False,
                    "structured_data": []
                }
            
            # Extract text blocks with positions
            text_blocks = []
            for line in result[0]:
                bbox, (text, confidence) = line
                # Calculate center position for sorting
                center_x = (bbox[0][0] + bbox[2][0]) / 2
                center_y = (bbox[0][1] + bbox[2][1]) / 2
                
                text_blocks.append({
                    "text": text.strip(),
                    "confidence": confidence,
                    "bbox": bbox,
                    "center_x": center_x,
                    "center_y": center_y,
                    "left": bbox[0][0],
                    "top": bbox[0][1],
                    "right": bbox[2][0],
                    "bottom": bbox[2][1]
                })
            
            # Detect if this looks like a table
            table_detected = self._detect_table_structure(text_blocks)
            
            if table_detected:
                structured_data = self._reconstruct_table(text_blocks)
            else:
                structured_data = []
            
            return {
                "table_detected": table_detected,
                "structured_data": structured_data,
                "raw_blocks": text_blocks,
                "total_blocks": len(text_blocks)
            }
            
        except Exception as e:
            return {
                "error": f"Table extraction failed: {str(e)}",
                "table_detected": False,
                "structured_data": []
            }
    
    def _detect_table_structure(self, text_blocks: List[Dict]) -> bool:
        """
        Detect if the text blocks form a table structure
        """
        if len(text_blocks) < 8:  # Need at least 8 blocks for a meaningful table
            return False
        
        # Sort blocks by Y position to identify rows
        sorted_by_y = sorted(text_blocks, key=lambda x: x["center_y"])
        
        # Group blocks into potential rows based on Y position
        rows = []
        current_row = [sorted_by_y[0]]
        y_threshold = 15  # Tighter tolerance for same row
        
        for block in sorted_by_y[1:]:
            if abs(block["center_y"] - current_row[-1]["center_y"]) <= y_threshold:
                current_row.append(block)
            else:
                if len(current_row) >= 2:  # Only consider rows with multiple blocks
                    rows.append(current_row)
                current_row = [block]
        
        if len(current_row) >= 2:
            rows.append(current_row)
        
        # Need at least 3 rows for a table
        if len(rows) < 3:
            return False
        
        # Check if rows have similar number of columns
        col_counts = [len(row) for row in rows]
        avg_cols = sum(col_counts) / len(col_counts)
        
        # Most rows should have similar column counts (within 1)
        similar_rows = sum(1 for count in col_counts if abs(count - avg_cols) <= 1)
        
        # At least 80% of rows should have consistent structure AND average columns should be >= 3
        is_consistent = similar_rows >= len(rows) * 0.8
        has_enough_columns = avg_cols >= 3
        
        # Additional check: look for table-like patterns
        # Tables often have consistent spacing between columns
        if is_consistent and has_enough_columns:
            # Check if the first few rows look like headers/data
            first_row_texts = [block["text"] for block in rows[0]]
            
            # Skip if it looks like a form (key-value pairs with colons, slashes)
            form_indicators = sum(1 for text in first_row_texts if ':' in text or '/' in text)
            if form_indicators > len(first_row_texts) * 0.3:  # 30% or more have form indicators
                return False
                
            # Check for repetitive patterns that suggest tabular data
            all_texts = []
            for row in rows[:5]:  # Check first 5 rows
                all_texts.extend([block["text"] for block in row])
            
            # Tables often have repeated short words, numbers, or patterns
            word_counts = {}
            for text in all_texts:
                if len(text) <= 15:  # Short text more likely to be repeated in tables
                    word_counts[text] = word_counts.get(text, 0) + 1
            
            # If we have several repeated short words, it's more likely a table
            repeated_words = sum(1 for count in word_counts.values() if count >= 2)
            
            return repeated_words >= 3
        
        return False
    
    def _reconstruct_table(self, text_blocks: List[Dict]) -> List[List[str]]:
        """
        Reconstruct table structure from text blocks
        """
        # Sort blocks by Y position first, then X position
        sorted_blocks = sorted(text_blocks, key=lambda x: (x["center_y"], x["center_x"]))
        
        # Group into rows based on Y position
        rows = []
        current_row = [sorted_blocks[0]]
        y_threshold = 20  # Pixels tolerance for same row
        
        for block in sorted_blocks[1:]:
            if abs(block["center_y"] - current_row[-1]["center_y"]) <= y_threshold:
                current_row.append(block)
            else:
                # Sort current row by X position
                current_row.sort(key=lambda x: x["center_x"])
                rows.append([block["text"] for block in current_row])
                current_row = [block]
        
        # Don't forget the last row
        if current_row:
            current_row.sort(key=lambda x: x["center_x"])
            rows.append([block["text"] for block in current_row])
        
        # Normalize row lengths (pad shorter rows)
        if rows:
            max_cols = max(len(row) for row in rows)
            for row in rows:
                while len(row) < max_cols:
                    row.append("")
        
        return rows
    
    def format_as_dict(self, structured_data: List[List[str]], has_header: bool = True) -> List[Dict[str, str]]:
        """
        Convert structured table data to list of dictionaries
        """
        if not structured_data:
            return []
        
        if has_header and len(structured_data) > 1:
            headers = structured_data[0]
            data_rows = structured_data[1:]
            
            result = []
            for row in data_rows:
                row_dict = {}
                for i, header in enumerate(headers):
                    value = row[i] if i < len(row) else ""
                    row_dict[header] = value
                result.append(row_dict)
            
            return result
        else:
            # No header, use generic column names
            result = []
            for row in structured_data:
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[f"Column_{i+1}"] = value
                result.append(row_dict)
            
            return result

# Global instance
_table_engine = None

def get_table_engine() -> TableRecognitionEngine:
    """Get global table recognition engine instance"""
    global _table_engine
    if _table_engine is None:
        _table_engine = TableRecognitionEngine()
    return _table_engine

def reconstruct_table_from_tesseract_blocks(text_blocks: List[Dict], confidence_threshold: float = 0.25) -> Dict[str, Any]:
    """
    Fallback table reconstruction using Tesseract block data
    """
    if not text_blocks or len(text_blocks) < 6:
        return {"table_detected": False, "structured_data": []}
    
    # Filter blocks by confidence (lower threshold for medical bills)
    good_blocks = [block for block in text_blocks if block.get("confidence", 0) > confidence_threshold]
    
    if len(good_blocks) < 6:
        return {"table_detected": False, "structured_data": []}
    
    # Sort blocks by Y position first, then X position
    sorted_blocks = sorted(good_blocks, key=lambda x: (x["bbox"][1], x["bbox"][0]))
    
    # Look for table sections by identifying areas with multiple aligned elements
    table_candidates = []
    
    # Group into rows based on Y position with tighter threshold
    rows = []
    current_row = [sorted_blocks[0]]
    y_threshold = 10  # Much tighter threshold to avoid merging separate rows
    
    for block in sorted_blocks[1:]:
        current_y = block["bbox"][1]
        last_y = current_row[-1]["bbox"][1]
        
        if abs(current_y - last_y) <= y_threshold:
            current_row.append(block)
        else:
            # Sort current row by X position and extract text
            current_row.sort(key=lambda x: x["bbox"][0])
            row_texts = [block["text"].strip() for block in current_row if block["text"].strip()]
            
            # Limit row length to prevent massive rows
            if 2 <= len(row_texts) <= 12:  # Reasonable row size
                rows.append(row_texts)
            elif len(row_texts) > 12:
                # Split large rows - take first 6 elements as one row
                rows.append(row_texts[:6])
                print(f"DEBUG: Split large row ({len(row_texts)} cols) into {row_texts[:6]}")
            
            current_row = [block]
    
    # Don't forget the last row
    if current_row and len(current_row) >= 2:
        current_row.sort(key=lambda x: x["bbox"][0])
        row_texts = [block["text"].strip() for block in current_row if block["text"].strip()]
        if 2 <= len(row_texts) <= 12:
            rows.append(row_texts)
        elif len(row_texts) > 12:
            rows.append(row_texts[:6])
            print(f"DEBUG: Split final large row ({len(row_texts)} cols)")
    
    if len(rows) < 3:  # Need at least 3 rows for a meaningful table
        return {"table_detected": False, "structured_data": []}
    
    print(f"DEBUG: Found {len(rows)} raw rows")
    
    # Clean up rows and find the best table section
    cleaned_rows = []
    rejected_rows = []
    
    for i, row in enumerate(rows):
        # Look for rows with consistent patterns (codes, amounts, etc.)
        non_empty = [cell for cell in row if cell.strip()]
        row_info = f"Row {i}: {len(non_empty)} cols: {non_empty[:3]}..."
        
        if non_empty and len(non_empty) <= 12:  # More reasonable column limit
            # Accept most rows that look reasonable
            has_numbers = any(any(c.isdigit() for c in cell) for cell in non_empty)
            has_reasonable_length = 2 <= len(non_empty) <= 8
            
            if has_numbers and has_reasonable_length:
                cleaned_rows.append(non_empty)
                print(f"DEBUG: ACCEPTED {row_info} (has numbers)")
            elif 2 <= len(non_empty) <= 6:  # Accept reasonable multi-column rows
                cleaned_rows.append(non_empty)
                print(f"DEBUG: ACCEPTED {row_info} (reasonable length)")
            else:
                rejected_rows.append((row_info, f"length: {len(non_empty)}, has_numbers: {has_numbers}"))
        else:
            rejected_rows.append((row_info, f"too many cols: {len(non_empty)}"))
    
    print(f"DEBUG: After first pass: {len(cleaned_rows)} cleaned rows")
    
    if len(cleaned_rows) < 3:
        print("DEBUG: Not enough rows, trying fallback...")
        # Fallback: include more rows if we don't have enough
        cleaned_rows = []
        for i, row in enumerate(rows):
            non_empty = [cell for cell in row if cell.strip()]
            if non_empty and 2 <= len(non_empty) <= 10:  # More lenient
                cleaned_rows.append(non_empty)
                print(f"DEBUG: FALLBACK ACCEPTED Row {i}: {len(non_empty)} cols")
    
    print(f"DEBUG: Final cleaned rows: {len(cleaned_rows)}")
    if not cleaned_rows and rejected_rows:
        print("DEBUG: Sample rejected rows:")
        for row_info, reason in rejected_rows[:5]:
            print(f"  REJECTED: {row_info} - {reason}")
    
    # Check column consistency
    if len(cleaned_rows) < 3:
        return {"table_detected": False, "structured_data": [], "reason": f"Only {len(cleaned_rows)} valid rows found"}
    
    col_counts = [len(row) for row in cleaned_rows]
    avg_cols = sum(col_counts) / len(col_counts)
    consistent_rows = sum(1 for count in col_counts if abs(count - avg_cols) <= 2)
    consistency_ratio = consistent_rows / len(cleaned_rows)
    
    # More lenient detection for medical bills
    table_detected = (
        (consistency_ratio >= 0.4 and len(cleaned_rows) >= 3) or  # 40% consistency with 3+ rows
        (consistency_ratio >= 0.3 and len(cleaned_rows) >= 5) or  # 30% consistency with 5+ rows  
        (avg_cols >= 3 and len(cleaned_rows) >= 4)  # 3+ columns with 4+ rows
    )
    
    # Additional check: if we have many rows with numbers/amounts, likely a table
    if not table_detected and len(cleaned_rows) >= 4:
        rows_with_numbers = sum(1 for row in cleaned_rows if any(any(c.isdigit() for c in cell) for cell in row))
        if rows_with_numbers >= len(cleaned_rows) * 0.6:  # 60% of rows have numbers
            table_detected = True
    
    return {
        "table_detected": table_detected,
        "structured_data": cleaned_rows if table_detected else [],
        "method": "tesseract_fallback",
        "debug_info": {
            "total_blocks": len(text_blocks),
            "good_blocks": len(good_blocks),
            "raw_rows": len(rows),
            "cleaned_rows": len(cleaned_rows),
            "avg_cols": avg_cols,
            "consistency_ratio": consistency_ratio,
            "col_counts": col_counts,
            "reason": "Detected" if table_detected else f"Failed: consistency={consistency_ratio:.2f}, rows={len(cleaned_rows)}, avg_cols={avg_cols:.1f}"
        }
    }

def extract_table_from_image(image_path: str, as_dict: bool = True, has_header: bool = True, tesseract_blocks: List[Dict] = None) -> Dict[str, Any]:
    """
    High-level function to extract table from image
    
    Args:
        image_path: Path to image file
        as_dict: Return structured data as list of dictionaries
        has_header: Whether the first row is a header
        tesseract_blocks: Pre-computed Tesseract blocks (fallback method)
    
    Returns:
        Dictionary with table extraction results
    """
    # Try PaddleOCR first
    if PADDLEOCR_AVAILABLE:
        engine = get_table_engine()
        result = engine.extract_table_structure(image_path)
        
        if result.get("table_detected") and result.get("structured_data"):
            if as_dict:
                result["formatted_data"] = engine.format_as_dict(
                    result["structured_data"], 
                    has_header=has_header
                )
            return result
    
    # Fallback to Tesseract block reconstruction
    if tesseract_blocks:
        result = reconstruct_table_from_tesseract_blocks(tesseract_blocks)
        
        if result.get("table_detected") and as_dict:
            structured_data = result.get("structured_data", [])
            if structured_data:
                if has_header and len(structured_data) > 1:
                    headers = structured_data[0]
                    data_rows = structured_data[1:]
                    
                    formatted_data = []
                    for row in data_rows:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            value = row[i] if i < len(row) else ""
                            row_dict[header] = value
                        formatted_data.append(row_dict)
                    
                    result["formatted_data"] = formatted_data
        
        return result
    
    return {"table_detected": False, "structured_data": [], "error": "No extraction method available"}