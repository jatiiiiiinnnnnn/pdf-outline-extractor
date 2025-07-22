"""
Text Analyzer - Handles text pattern recognition and classification
"""

import re
from typing import List, Dict, Set

class TextAnalyzer:
    def __init__(self):
        # Common non-title patterns
        self.non_title_patterns = [
            r'^(page|p\.)\s*\d+',  # Page numbers
            r'^\d+\s*$',  # Pure numbers
            r'^(abstract|introduction|conclusion|references|bibliography)$',  # Common sections
            r'^(figure|table|chart)\s*\d*',  # Figure/table captions
            r'@|\.com|\.org|\.edu',  # Email/URL fragments
            r'^(copyright|©|\(c\))',  # Copyright notices
            r'^\d{4}$',  # Years
            r'^[a-z\s]{1,3}$',  # Very short lowercase
        ]
        
        # Heading patterns (multilingual support)
        self.heading_patterns = [
            # English
            r'^\d+\.?\s+[A-Z]',  # "1. Introduction" or "1 Introduction"
            r'^[A-Z][A-Z\s]{2,}$',  # ALL CAPS headings
            r'^(Chapter|Section|Part)\s+\d+',  # "Chapter 1"
            
            # Numbered patterns
            r'^\d+(\.\d+)*\.?\s+',  # 1.1, 1.1.1, etc.
            r'^[IVXLC]+\.?\s+[A-Z]',  # Roman numerals
            r'^[A-Z]\.?\s+[A-Z]',  # "A. Introduction"
            
            # Japanese patterns
            r'^第[一二三四五六七八九十\d]+章',  # Chapter markers
            r'^[一二三四五六七八九十]+[、。]',  # Japanese numerals
            r'^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]{1,50}$',  # Japanese text
            
            # Chinese patterns
            r'^第[一二三四五六七八九十\d]+[章节部分]',
            
            # Korean patterns
            r'^제\s*\d+\s*[장절부]',
        ]
        
        # Compile patterns for efficiency
        self.compiled_non_title = [re.compile(p, re.IGNORECASE) for p in self.non_title_patterns]
        self.compiled_heading = [re.compile(p) for p in self.heading_patterns]
    
    def is_likely_non_title(self, text: str) -> bool:
        """Check if text is unlikely to be a title"""
        text_clean = text.strip()
        
        # Check against non-title patterns
        for pattern in self.compiled_non_title:
            if pattern.search(text_clean):
                return True
        
        # Additional heuristics
        if len(text_clean) < 3:
            return True
        
        if text_clean.count('.') > 3:  # Too many periods
            return True
        
        if text_clean.count('\n') > 0:  # Multi-line
            return True
        
        return False
    
    def is_likely_heading(self, text: str) -> bool:
        """Check if text looks like a heading"""
        text_clean = text.strip()
        
        if len(text_clean) < 2 or len(text_clean) > 200:
            return False
        
        # Check heading patterns
        for pattern in self.compiled_heading:
            if pattern.match(text_clean):
                return True
        
        # Additional heading heuristics
        
        # Starts with capital and is relatively short
        if (text_clean[0].isupper() and 
            len(text_clean) <= 100 and 
            not text_clean.endswith('.') and
            text_clean.count('.') <= 1):
            return True
        
        # Check for question format (common in headings)
        if text_clean.endswith('?') and len(text_clean) <= 80:
            return True
        
        return False
    
    def extract_numbering(self, text: str) -> tuple:
        """Extract numbering from heading text"""
        text_clean = text.strip()
        
        # Match various numbering patterns
        patterns = [
            r'^(\d+(?:\.\d+)*)\.?\s+(.+)',  # 1.1.1 format
            r'^([IVXLC]+)\.?\s+(.+)',  # Roman numerals
            r'^([A-Z])\.?\s+(.+)',  # Letter numbering
            r'^(第\d+章)\s*(.+)',  # Japanese chapter
            r'^(Chapter|Section|Part)\s+(\d+)\s*(.+)',  # English chapter/section
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text_clean, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    return match.group(1), match.group(2)
                elif len(match.groups()) == 3:
                    return f"{match.group(1)} {match.group(2)}", match.group(3)
        
        return "", text_clean
    
    def calculate_text_features(self, text: str) -> Dict:
        """Calculate various text features for classification"""
        features = {
            "length": len(text),
            "word_count": len(text.split()),
            "has_numbers": bool(re.search(r'\d', text)),
            "starts_with_number": bool(re.match(r'^\d', text.strip())),
            "starts_with_capital": text.strip()[0].isupper() if text.strip() else False,
            "ends_with_period": text.strip().endswith('.'),
            "has_colon": ':' in text,
            "all_caps_ratio": sum(1 for c in text if c.isupper()) / len(text) if text else 0,
            "punctuation_density": sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text) if text else 0
        }
        
        return features
    
    def detect_language(self, text: str) -> str:
        """Simple language detection"""
        # Japanese characters
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
            return "ja"
        
        # Chinese characters (excluding Japanese kanji)
        if re.search(r'[\u4E00-\u9FFF]', text) and not re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
            return "zh"
        
        # Korean characters
        if re.search(r'[\uAC00-\uD7AF]', text):
            return "ko"
        
        # Default to English
        return "en"