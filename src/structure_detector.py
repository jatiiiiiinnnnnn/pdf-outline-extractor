"""
Structure Detector - Detects document structure and identifies headings
"""

import re
import numpy as np
from typing import List, Dict, Tuple, Set
from collections import defaultdict

from text_analyzer import TextAnalyzer

class StructureDetector:
    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.min_heading_score = 0.3
        self.max_headings_per_page = 10
    
    def detect_headings(self, text_blocks: List[Dict], font_info: Dict) -> List[Dict]:
        """Detect headings in the document"""
        candidates = []
        
        for i, block in enumerate(text_blocks):
            score = self._calculate_heading_score(block, font_info, text_blocks, i)
            
            if score >= self.min_heading_score:
                candidate = {
                    "id": f"heading_{i}",
                    "text": block["text"],
                    "page": block["page"],
                    "score": score,
                    "font_size": np.mean([span["size"] for span in block["spans"]]),
                    "font_weight": self._get_dominant_weight(block),
                    "position": block["bbox"][1],  # Y position
                    "block_index": i
                }
                candidates.append(candidate)
        
        # Filter and rank candidates
        filtered_candidates = self._filter_candidates(candidates)
        return self._rank_candidates(filtered_candidates)
    
    def _calculate_heading_score(self, block: Dict, font_info: Dict, all_blocks: List[Dict], block_index: int) -> float:
        """Calculate likelihood that a text block is a heading"""
        text = block["text"]
        score = 0.0
        
        # Text pattern analysis
        if self.text_analyzer.is_likely_heading(text):
            score += 0.4
        
        if self.text_analyzer.is_likely_non_title(text):
            score -= 0.5
        
        # Font size analysis
        if block["spans"]:
            avg_size = np.mean([span["size"] for span in block["spans"]])
            body_size = font_info.get("body_font_size", 12)
            
            size_ratio = avg_size / body_size
            if size_ratio > 1.2:
                score += min(0.3, (size_ratio - 1.0) * 0.3)
        
        # Font weight analysis
        bold_spans = sum(1 for span in block["spans"] if span["flags"] & 16)
        if bold_spans > 0:
            bold_ratio = bold_spans / len(block["spans"])
            score += bold_ratio * 0.2
        
        # Length analysis
        text_length = len(text)
        if 5 <= text_length <= 100:
            score += 0.2
        elif text_length <= 5:
            score -= 0.2
        elif text_length > 200:
            score -= 0.3
        
        # Position analysis
        # Headings often appear at the start of lines/sections
        if self._is_start_of_section(block, all_blocks, block_index):
            score += 0.2
        
        # Numbering analysis
        numbering, clean_text = self.text_analyzer.extract_numbering(text)
        if numbering:
            score += 0.3
        
        # Isolation analysis (headings often stand alone)
        if self._is_isolated_text(block, all_blocks, block_index):
            score += 0.15
        
        # Language-specific patterns
        lang = self.text_analyzer.detect_language(text)
        if lang in ["ja", "zh", "ko"]:
            score += self._analyze_cjk_patterns(text)
        
        return max(0.0, min(1.0, score))
    
    def _get_dominant_weight(self, block: Dict) -> str:
        """Get the dominant font weight for a block"""
        if not block["spans"]:
            return "normal"
        
        weights = []
        for span in block["spans"]:
            flags = span["flags"]
            if flags & 16:  # Bold
                weights.append("bold")
            elif flags & 2:  # Italic
                weights.append("italic")
            else:
                weights.append("normal")
        
        # Return most common weight
        from collections import Counter
        return Counter(weights).most_common(1)[0][0]
    
    def _is_start_of_section(self, block: Dict, all_blocks: List[Dict], block_index: int) -> bool:
        """Check if block appears to start a new section"""
        # Check if there's whitespace before this block
        if block_index > 0:
            prev_block = all_blocks[block_index - 1]
            
            # Same page but significant vertical gap
            if (block["page"] == prev_block["page"] and 
                block["bbox"][1] - prev_block["bbox"][3] > 20):  # 20pt gap
                return True
        
        # First block on a page (excluding page 1)
        if block["page"] > 1:
            page_blocks = [b for b in all_blocks if b["page"] == block["page"]]
            if page_blocks and page_blocks[0] == block:
                return True
        
        return False
    
    def _is_isolated_text(self, block: Dict, all_blocks: List[Dict], block_index: int) -> bool:
        """Check if text block stands alone (typical for headings)"""
        text_length = len(block["text"])
        
        # Very short text is often isolated
        if text_length <= 50:
            return True
        
        # Check if next block has different formatting
        if block_index < len(all_blocks) - 1:
            next_block = all_blocks[block_index + 1]
            
            # Different font size suggests this block is isolated
            if block["spans"] and next_block["spans"]:
                current_size = np.mean([span["size"] for span in block["spans"]])
                next_size = np.mean([span["size"] for span in next_block["spans"]])
                
                if abs(current_size - next_size) > 2:
                    return True
        
        return False
    
    def _analyze_cjk_patterns(self, text: str) -> float:
        """Analyze CJK (Chinese, Japanese, Korean) specific heading patterns"""
        score_bonus = 0.0
        
        # Japanese patterns
        if re.search(r'第[一二三四五六七八九十\d]+章', text):
            score_bonus += 0.3
        elif re.search(r'[一二三四五六七八九十]+[、。]', text):
            score_bonus += 0.2
        
        # Chinese patterns
        elif re.search(r'第[一二三四五六七八九十\d]+[章节部分]', text):
            score_bonus += 0.3
        
        # Korean patterns
        elif re.search(r'제\s*\d+\s*[장절부]', text):
            score_bonus += 0.3
        
        # General CJK heading characteristics
        if len(text) <= 30 and re.search(r'[\u4E00-\u9FFF]', text):
            score_bonus += 0.1
        
        return score_bonus
    
    def _filter_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Filter heading candidates to remove duplicates and false positives"""
        if not candidates:
            return []
        
        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        filtered = []
        used_texts = set()
        page_counts = defaultdict(int)
        
        for candidate in candidates:
            text = candidate["text"].strip().lower()
            page = candidate["page"]
            
            # Skip duplicates
            if text in used_texts:
                continue
            
            # Limit headings per page
            if page_counts[page] >= self.max_headings_per_page:
                continue
            
            # Skip very low scores
            if candidate["score"] < self.min_heading_score:
                continue
            
            filtered.append(candidate)
            used_texts.add(text)
            page_counts[page] += 1
        
        return filtered
    
    def _rank_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Rank and finalize heading candidates"""
        if not candidates:
            return []
        
        # Sort by page first, then by position on page
        candidates.sort(key=lambda x: (x["page"], x["position"]))
        
        # Additional ranking factors
        for candidate in candidates:
            # Boost score for early document headings
            if candidate["page"] <= 3:
                candidate["score"] *= 1.1
            
            # Boost score for numbered headings
            numbering, _ = self.text_analyzer.extract_numbering(candidate["text"])
            if numbering:
                candidate["score"] *= 1.2
        
        return candidates
    
    def detect_table_of_contents(self, text_blocks: List[Dict]) -> List[Dict]:
        """Detect table of contents and extract structure"""
        toc_candidates = []
        
        for i, block in enumerate(text_blocks):
            text = block["text"]
            
            # Look for TOC patterns
            if self._is_toc_entry(text):
                toc_candidates.append({
                    "text": text,
                    "page": block["page"],
                    "level": self._estimate_toc_level(text)
                })
        
        return toc_candidates
    
    def _is_toc_entry(self, text: str) -> bool:
        """Check if text looks like a table of contents entry"""
        # Common TOC patterns
        patterns = [
            r'.*\.{3,}.*\d+',  # "Title....123"
            r'.*\s+\d+',  # "Title 123"
            r'^\d+(\.\d+)*\s+.*\d+',  # "1.1 Title 123"
        ]
        
        for pattern in patterns:
            if re.match(pattern, text.strip()):
                return True
        
        return False
    
    def _estimate_toc_level(self, text: str) -> int:
        """Estimate hierarchical level from TOC entry"""
        # Count leading dots or indentation
        stripped = text.lstrip()
        indent_level = len(text) - len(stripped)
        
        # Check for numbering depth
        numbering_match = re.match(r'^(\d+(?:\.\d+)*)', stripped)
        if numbering_match:
            depth = numbering_match.group(1).count('.') + 1
            return min(depth, 3)
        
        # Estimate from indentation
        if indent_level > 10:
            return 3
        elif indent_level > 5:
            return 2
        else:
            return 1
    
    def validate_structure(self, headings: List[Dict]) -> List[Dict]:
        """Validate and clean up detected structure"""
        if not headings:
            return []
        
        validated = []
        
        for heading in headings:
            # Clean up text
            cleaned_text = re.sub(r'\s+', ' ', heading["text"]).strip()
            
            # Skip empty or very short headings
            if len(cleaned_text) < 2:
                continue
            
            # Skip headings that are too long
            if len(cleaned_text) > 200:
                continue
            
            heading["text"] = cleaned_text
            validated.append(heading)
        
        return validated