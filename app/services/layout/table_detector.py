import cv2
import numpy as np
from typing import List, Dict
import logging
from .base import TableElement

logger = logging.getLogger(__name__)

class TableDetector:
    """Detects and extracts tables from document images"""
    
    def __init__(self, min_table_rows: int = 2, min_table_cols: int = 2):
        self.min_table_rows = min_table_rows
        self.min_table_cols = min_table_cols
    
    def detect_tables(self, image: np.ndarray, ocr_data: Dict) -> List[TableElement]:
        """Detect tables using multiple methods"""
        tables = []
        
        # Method 1: Line detection for table borders
        line_tables = self._detect_tables_by_lines(image)
        tables.extend(line_tables)
        
        # Method 2: Text alignment analysis
        alignment_tables = self._detect_tables_by_alignment(ocr_data)
        tables.extend(alignment_tables)
        
        # Remove duplicates and merge overlapping tables
        tables = self._merge_overlapping_tables(tables)
        
        return tables
    
    def _detect_tables_by_lines(self, image: np.ndarray) -> List[TableElement]:
        """Detect tables by finding horizontal and vertical lines"""
        tables = []
        
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Detect horizontal lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
            
            # Detect vertical lines
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
            vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
            
            # Combine lines
            table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0)
            
            # Find contours (potential table regions)
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size (tables should be reasonably large)
                if w > 100 and h > 50:
                    table = TableElement([x, y, x + w, y + h], confidence=0.7)
                    tables.append(table)
        
        except Exception as e:
            logger.warning(f"Line-based table detection failed: {str(e)}")
        
        return tables
    
    def _detect_tables_by_alignment(self, ocr_data: Dict) -> List[TableElement]:
        """Detect tables by analyzing text alignment patterns"""
        tables = []
        
        try:
            # Group text by lines (similar Y coordinates)
            lines = self._group_text_by_lines(ocr_data)
            
            # Look for aligned columns across multiple lines
            potential_tables = self._find_aligned_columns(lines)
            
            for table_region in potential_tables:
                if len(table_region['rows']) >= self.min_table_rows:
                    # Create table element
                    bbox = self._calculate_table_bbox(table_region)
                    table = TableElement(bbox, confidence=0.6)
                    
                    # Extract table structure
                    self._extract_table_structure(table, table_region, ocr_data)
                    tables.append(table)
        
        except Exception as e:
            logger.warning(f"Alignment-based table detection failed: {str(e)}")
        
        return tables
    
    def _group_text_by_lines(self, ocr_data: Dict) -> List[Dict]:
        """Group OCR text elements by lines (similar Y coordinates)"""
        lines = []
        line_threshold = 10  # pixels
        
        # Get valid text elements
        valid_elements = []
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            if text and int(ocr_data['conf'][i]) > 0:
                valid_elements.append({
                    'text': text,
                    'left': ocr_data['left'][i],
                    'top': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                    'conf': int(ocr_data['conf'][i]),
                    'right': ocr_data['left'][i] + ocr_data['width'][i],
                    'bottom': ocr_data['top'][i] + ocr_data['height'][i]
                })
        
        # Sort by top coordinate
        valid_elements.sort(key=lambda x: x['top'])
        
        # Group into lines
        current_line = []
        current_y = None
        
        for element in valid_elements:
            if current_y is None or abs(element['top'] - current_y) <= line_threshold:
                current_line.append(element)
                current_y = element['top'] if current_y is None else current_y
            else:
                if current_line:
                    # Sort line elements by left coordinate
                    current_line.sort(key=lambda x: x['left'])
                    lines.append({
                        'y': current_y,
                        'elements': current_line
                    })
                current_line = [element]
                current_y = element['top']
        
        # Add last line
        if current_line:
            current_line.sort(key=lambda x: x['left'])
            lines.append({
                'y': current_y,
                'elements': current_line
            })
        
        return lines
    
    def _find_aligned_columns(self, lines: List[Dict]) -> List[Dict]:
        """Find sets of lines that have aligned columns (potential tables)"""
        potential_tables = []
        
        if len(lines) < self.min_table_rows:
            return potential_tables
        
        # Look for consecutive lines with similar column structure
        i = 0
        while i < len(lines) - 1:
            table_rows = [lines[i]]
            
            # Check subsequent lines for column alignment
            for j in range(i + 1, len(lines)):
                if self._lines_have_aligned_columns(table_rows[0], lines[j]):
                    table_rows.append(lines[j])
                else:
                    break
            
            # If we found enough aligned rows, it's potentially a table
            if len(table_rows) >= self.min_table_rows:
                potential_tables.append({
                    'rows': table_rows,
                    'start_line': i,
                    'end_line': i + len(table_rows) - 1
                })
                i += len(table_rows)
            else:
                i += 1
        
        return potential_tables
    
    def _lines_have_aligned_columns(self, line1: Dict, line2: Dict, tolerance: int = 20) -> bool:
        """Check if two lines have aligned columns"""
        elements1 = line1['elements']
        elements2 = line2['elements']
        
        # Need at least 2 columns to be considered a table
        if len(elements1) < 2 or len(elements2) < 2:
            return False
        
        # Check if column positions are similar
        aligned_columns = 0
        for elem1 in elements1:
            for elem2 in elements2:
                if abs(elem1['left'] - elem2['left']) <= tolerance:
                    aligned_columns += 1
                    break
        
        # Consider lines aligned if at least half the columns align
        min_elements = min(len(elements1), len(elements2))
        return aligned_columns >= min_elements * 0.5
    
    def _extract_table_structure(self, table: TableElement, table_region: Dict, ocr_data: Dict):
        """Extract structured data from detected table region"""
        rows = table_region['rows']
        
        # Determine column positions based on all elements
        all_elements = []
        for row in rows:
            all_elements.extend(row['elements'])
        
        # Sort unique X positions to determine column boundaries
        x_positions = sorted(set(elem['left'] for elem in all_elements))
        
        # Create column boundaries with some tolerance
        column_boundaries = []
        tolerance = 15
        
        for i, x_pos in enumerate(x_positions):
            if i == 0 or x_pos - x_positions[i-1] > tolerance:
                column_boundaries.append(x_pos)
        
        # Process each row and assign to columns
        for row_idx, row in enumerate(rows):
            for element in row['elements']:
                # Find which column this element belongs to
                col_idx = 0
                for i, boundary in enumerate(column_boundaries):
                    if element['left'] >= boundary - tolerance:
                        col_idx = i
                    else:
                        break
                
                # Add cell to table
                table.add_cell(
                    row=row_idx,
                    col=col_idx,
                    text=element['text'],
                    cell_bbox=[element['left'], element['top'], element['right'], element['bottom']],
                    confidence=element['conf'] / 100.0
                )
    
    def _calculate_table_bbox(self, table_region: Dict) -> List[int]:
        """Calculate bounding box for table region"""
        rows = table_region['rows']
        
        min_x = float('inf')
        min_y = float('inf')
        max_x = 0
        max_y = 0
        
        for row in rows:
            for element in row['elements']:
                min_x = min(min_x, element['left'])
                min_y = min(min_y, element['top'])
                max_x = max(max_x, element['right'])
                max_y = max(max_y, element['bottom'])
        
        return [int(min_x), int(min_y), int(max_x), int(max_y)]
    
    def _merge_overlapping_tables(self, tables: List[TableElement]) -> List[TableElement]:
        """Merge overlapping table detections"""
        if len(tables) <= 1:
            return tables
        
        merged = []
        used = set()
        
        for i, table1 in enumerate(tables):
            if i in used:
                continue
            
            current_table = table1
            used.add(i)
            
            for j, table2 in enumerate(tables[i+1:], i+1):
                if j in used:
                    continue
                
                if self._tables_overlap(current_table, table2):
                    # Merge tables
                    current_table = self._merge_two_tables(current_table, table2)
                    used.add(j)
            
            merged.append(current_table)
        
        return merged
    
    def _tables_overlap(self, table1: TableElement, table2: TableElement, threshold: float = 0.3) -> bool:
        """Check if two tables overlap significantly"""
        bbox1 = table1.bbox
        bbox2 = table2.bbox
        
        # Calculate intersection
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 <= x1 or y2 <= y1:
            return False
        
        intersection_area = (x2 - x1) * (y2 - y1)
        table1_area = table1.area()
        table2_area = table2.area()
        
        overlap_ratio1 = intersection_area / table1_area if table1_area > 0 else 0
        overlap_ratio2 = intersection_area / table2_area if table2_area > 0 else 0
        
        return max(overlap_ratio1, overlap_ratio2) > threshold
    
    def _merge_two_tables(self, table1: TableElement, table2: TableElement) -> TableElement:
        """Merge two overlapping tables"""
        # Calculate merged bounding box
        merged_bbox = [
            min(table1.bbox[0], table2.bbox[0]),
            min(table1.bbox[1], table2.bbox[1]),
            max(table1.bbox[2], table2.bbox[2]),
            max(table1.bbox[3], table2.bbox[3])
        ]
        
        # Create merged table
        merged_table = TableElement(merged_bbox, max(table1.confidence, table2.confidence))
        
        # Combine cells (this is simplified - in practice, you'd need more sophisticated merging)
        merged_table.cells = table1.cells + table2.cells
        
        return merged_table