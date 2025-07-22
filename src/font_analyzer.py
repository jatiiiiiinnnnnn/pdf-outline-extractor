"""
Font Analyzer - Analyzes font properties to determine text hierarchy
"""

import numpy as np
from typing import List, Dict, Tuple
from collections import defaultdict, Counter

class FontAnalyzer:
    def __init__(self):
        self.font_size_threshold = 2.0  # Minimum difference to consider different levels
    
    def analyze_fonts(self, text_blocks: List[Dict]) -> Dict:
        """Analyze font properties across all text blocks"""
        if not text_blocks:
            return {}
        
        font_stats = self._collect_font_statistics(text_blocks)
        font_hierarchy = self._determine_font_hierarchy(font_stats)
        
        return {
            "statistics": font_stats,
            "hierarchy": font_hierarchy,
            "body_font_size": self._estimate_body_font_size(font_stats)
        }
    
    def _collect_font_statistics(self, text_blocks: List[Dict]) -> Dict:
        """Collect statistics about fonts used in the document"""
        font_sizes = []
        font_families = []
        font_weights = []
        size_frequency = Counter()
        
        for block in text_blocks:
            for span in block["spans"]:
                size = round(span["size"], 1)
                font_sizes.append(size)
                font_families.append(span["font"])
                
                # Determine font weight from flags
                flags = span["flags"]
                weight = self._extract_font_weight(flags)
                font_weights.append(weight)
                
                size_frequency[size] += len(span["text"])
        
        return {
            "sizes": font_sizes,
            "families": font_families,
            "weights": font_weights,
            "size_frequency": dict(size_frequency),
            "unique_sizes": sorted(set(font_sizes), reverse=True),
            "most_common_size": size_frequency.most_common(1)[0][0] if size_frequency else 12
        }
    
    def _extract_font_weight(self, flags: int) -> str:
        """Extract font weight from PyMuPDF flags"""
        # PyMuPDF flag constants
        # 16 = bold, 2 = italic
        if flags & 16:  # Bold
            return "bold"
        elif flags & 2:  # Italic
            return "italic"
        else:
            return "normal"
    
    def _determine_font_hierarchy(self, font_stats: Dict) -> List[Dict]:
        """Determine font hierarchy for heading levels"""
        unique_sizes = font_stats["unique_sizes"]
        body_size = font_stats["most_common_size"]
        
        hierarchy = []
        
        # Create hierarchy based on size relative to body text
        for i, size in enumerate(unique_sizes):
            if size > body_size + 1:  # Significantly larger than body
                level_info = {
                    "size": size,
                    "relative_size": size / body_size,
                    "suggested_level": min(i + 1, 3),  # H1, H2, H3 max
                    "size_difference": size - body_size
                }
                hierarchy.append(level_info)
        
        # Sort by size (largest first)
        hierarchy.sort(key=lambda x: x["size"], reverse=True)
        
        return hierarchy[:3]  # Only keep top 3 levels
    
    def _estimate_body_font_size(self, font_stats: Dict) -> float:
        """Estimate the body text font size"""
        return font_stats["most_common_size"]
    
    def get_text_prominence_score(self, block: Dict, font_info: Dict) -> float:
        """Calculate prominence score for a text block"""
        if not block["spans"]:
            return 0.0
        
        # Calculate average font size for this block
        sizes = [span["size"] for span in block["spans"]]
        avg_size = np.mean(sizes)
        
        # Calculate weight score
        weights = [self._extract_font_weight(span["flags"]) for span in block["spans"]]
        weight_score = sum(2 if w == "bold" else 1.5 if w == "italic" else 1 for w in weights) / len(weights)
        
        # Calculate relative size score
        body_size = font_info.get("body_font_size", 12)
        size_ratio = avg_size / body_size
        
        # Combine scores
        prominence = size_ratio * weight_score
        
        # Bonus for position (earlier in document)
        position_bonus = 1.0 + (0.1 / block["page"])  # Earlier pages get slight bonus
        
        return prominence * position_bonus
    
    def is_different_font_level(self, size1: float, size2: float) -> bool:
        """Check if two font sizes represent different hierarchy levels"""
        return abs(size1 - size2) >= self.font_size_threshold
    
    def classify_font_role(self, block: Dict, font_info: Dict) -> str:
        """Classify the role of text based on font properties"""
        if not block["spans"]:
            return "body"
        
        avg_size = np.mean([span["size"] for span in block["spans"]])
        body_size = font_info.get("body_font_size", 12)
        
        # Check if it's significantly larger than body text
        if avg_size > body_size + 2:
            return "heading"
        elif avg_size > body_size + 1:
            return "subheading"
        elif avg_size < body_size - 1:
            return "caption"
        else:
            return "body"
    
    def get_font_consistency_score(self, blocks: List[Dict]) -> float:
        """Calculate how consistent font usage is across similar text types"""
        if not blocks:
            return 0.0
        
        # Group blocks by similar font properties
        font_groups = defaultdict(list)
        
        for block in blocks:
            if not block["spans"]:
                continue
            
            avg_size = round(np.mean([span["size"] for span in block["spans"]]), 1)
            dominant_weight = Counter([self._extract_font_weight(span["flags"]) for span in block["spans"]]).most_common(1)[0][0]
            
            key = (avg_size, dominant_weight)
            font_groups[key].append(block)
        
        # Calculate consistency based on group sizes
        total_blocks = len(blocks)
        group_sizes = [len(group) for group in font_groups.values()]
        
        # Higher score for fewer, larger groups (more consistent)
        if total_blocks == 0:
            return 0.0
        
        consistency = sum(size * size for size in group_sizes) / (total_blocks * total_blocks)
        return consistency