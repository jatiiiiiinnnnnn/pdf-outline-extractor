"""
PDF Processor - Main class for extracting document structure
"""

import fitz  # PyMuPDF
import re
import json
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np

from text_analyzer import TextAnalyzer
from font_analyzer import FontAnalyzer
from structure_detector import StructureDetector

class PDFProcessor:
    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.font_analyzer = FontAnalyzer()
        self.structure_detector = StructureDetector()
    
    def extract_outline(self, pdf_path: str) -> Dict:
        """Extract structured outline from PDF"""
        try:
            doc = fitz.open(pdf_path)
            
            # Extract text blocks with formatting info
            text_blocks = self._extract_text_blocks(doc)
            
            # Analyze fonts and detect heading levels
            font_info = self.font_analyzer.analyze_fonts(text_blocks)
            
            # Detect title and headings
            title = self._extract_title(doc, text_blocks, font_info)
            headings = self._extract_headings(text_blocks, font_info)
            
            doc.close()
            
            return {
                "title": title,
                "outline": headings
            }
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return {"title": "", "outline": []}
    
    def _extract_text_blocks(self, doc) -> List[Dict]:
        """Extract text blocks with formatting information"""
        blocks = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get text blocks with formatting
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" not in block:  # Skip image blocks
                    continue
                
                for line in block["lines"]:
                    line_text = ""
                    spans_info = []
                    
                    for span in line["spans"]:
                        span_text = span["text"].strip()
                        if span_text:
                            line_text += span_text + " "
                            spans_info.append({
                                "text": span_text,
                                "font": span["font"],
                                "size": span["size"],
                                "flags": span["flags"],
                                "bbox": span["bbox"]
                            })
                    
                    line_text = line_text.strip()
                    if line_text and spans_info:
                        blocks.append({
                            "text": line_text,
                            "page": page_num + 1,
                            "bbox": line["bbox"],
                            "spans": spans_info
                        })
        
        return blocks
    
    def _extract_title(self, doc, text_blocks: List[Dict], font_info: Dict) -> str:
        """Extract document title"""
        if not text_blocks:
            return ""
        
        # Try to get title from PDF metadata first
        metadata_title = doc.metadata.get("title", "").strip()
        if metadata_title and len(metadata_title) > 3:
            return metadata_title
        
        # Look for title in first few pages
        first_page_blocks = [b for b in text_blocks if b["page"] <= 2]
        
        if not first_page_blocks:
            return ""
        
        # Find the largest font or most prominent text
        title_candidates = []
        
        for block in first_page_blocks[:10]:  # Check first 10 blocks
            text = block["text"]
            
            # Skip very short or very long texts
            if len(text) < 5 or len(text) > 150:
                continue
            
            # Skip common non-title patterns
            if self.text_analyzer.is_likely_non_title(text):
                continue
            
            # Get dominant font size for this block
            font_sizes = [span["size"] for span in block["spans"]]
            avg_font_size = np.mean(font_sizes) if font_sizes else 12
            
            title_candidates.append({
                "text": text,
                "font_size": avg_font_size,
                "page": block["page"],
                "position": block["bbox"][1]  # Y position
            })
        
        if not title_candidates:
            return ""
        
        # Sort by font size (descending) and position (ascending)
        title_candidates.sort(key=lambda x: (-x["font_size"], x["position"]))
        
        # Return the best candidate
        return title_candidates[0]["text"]
    
    def _extract_headings(self, text_blocks: List[Dict], font_info: Dict) -> List[Dict]:
        """Extract headings with hierarchical levels"""
        headings = []
        
        # Analyze text patterns and structure
        heading_candidates = self.structure_detector.detect_headings(text_blocks, font_info)
        
        # Assign hierarchical levels
        level_assignments = self._assign_heading_levels(heading_candidates)
        
        for candidate in heading_candidates:
            level = level_assignments.get(candidate["id"], "H1")
            
            headings.append({
                "level": level,
                "text": candidate["text"],
                "page": candidate["page"]
            })
        
        return headings
    
    def _assign_heading_levels(self, candidates: List[Dict]) -> Dict[str, str]:
        """Assign H1, H2, H3 levels to heading candidates"""
        if not candidates:
            return {}
        
        # Group by font size and style
        font_groups = defaultdict(list)
        
        for candidate in candidates:
            # Create a key based on font size and style
            key = (candidate["font_size"], candidate["font_weight"])
            font_groups[key].append(candidate)
        
        # Sort font groups by size (largest first)
        sorted_groups = sorted(font_groups.keys(), key=lambda x: -x[0])
        
        # Assign levels based on font hierarchy
        level_map = {}
        level_names = ["H1", "H2", "H3"]
        
        for i, group_key in enumerate(sorted_groups[:3]):  # Only H1-H3
            level = level_names[i]
            for candidate in font_groups[group_key]:
                level_map[candidate["id"]] = level
        
        return level_map