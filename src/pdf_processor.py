"""
PDF Processor - Fixed for multi-page and optimized for speed
"""

import fitz  # PyMuPDF
import re
import json
from typing import List, Dict, Tuple, Optional
from collections import Counter
import time

class PDFProcessor:
    def __init__(self):
        # Pre-compile essential regex patterns only
        self.heading_patterns = [
            re.compile(r'^\d+\.?\s+[A-Z]'),
            re.compile(r'^\d+(\.\d+)+\.?\s+'),
            re.compile(r'^[A-Z][A-Z\s]{3,}$'),
            re.compile(r'^(Chapter|Section|CHAPTER|SECTION)\s+\d+', re.IGNORECASE),
        ]
        
        self.skip_patterns = [
            re.compile(r'^(page|p\.)\s*\d+', re.IGNORECASE),
            re.compile(r'^\d+\s*$'),
            re.compile(r'@|\.com|\.org'),
            re.compile(r'^(copyright|©)', re.IGNORECASE),
        ]
    
    def extract_outline(self, pdf_path: str) -> Dict:
        """Extract outline from PDF - fixed for multi-page"""
        try:
            start_time = time.time()
            doc = fitz.open(pdf_path)
            
            print(f"Processing {len(doc)} pages...")
            
            # Extract all text blocks from ALL pages
            all_blocks = []
            for page_num in range(len(doc)):
                page_blocks = self._extract_page_blocks(doc[page_num], page_num + 1)
                all_blocks.extend(page_blocks)
                
                # Progress indicator for large docs
                if page_num % 10 == 0 and page_num > 0:
                    print(f"  Processed {page_num} pages...")
            
            print(f"Extracted {len(all_blocks)} text blocks from {len(doc)} pages")
            
            # Extract title and headings
            title = self._extract_title(doc, all_blocks)
            headings = self._extract_headings(all_blocks)
            
            doc.close()
            
            elapsed = time.time() - start_time
            print(f"Total processing time: {elapsed:.2f}s")
            
            return {
                "title": title,
                "outline": headings
            }
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return {"title": "", "outline": []}
    
    def _extract_page_blocks(self, page, page_num: int) -> List[Dict]:
        """Extract text blocks from a single page"""
        blocks = []
        
        try:
            # Get text with basic formatting
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    line_text = ""
                    total_size = 0
                    bold_chars = 0
                    total_chars = 0
                    
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            line_text += text + " "
                            char_count = len(text)
                            total_size += span["size"] * char_count
                            total_chars += char_count
                            
                            if span["flags"] & 16:  # Bold flag
                                bold_chars += char_count
                    
                    line_text = line_text.strip()
                    if line_text and total_chars > 0:
                        avg_size = total_size / total_chars
                        is_bold = bold_chars > (total_chars * 0.5)  # More than 50% bold
                        
                        blocks.append({
                            "text": line_text,
                            "page": page_num,
                            "font_size": round(avg_size, 1),
                            "is_bold": is_bold,
                            "y_pos": line["bbox"][1]
                        })
        
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
        
        return blocks
    
    def _extract_title(self, doc, blocks: List[Dict]) -> str:
        """Extract document title"""
        # Try metadata first
        title = doc.metadata.get("title", "").strip()
        if title and len(title) > 3 and len(title) < 150:
            return title
        
        # Look in first page blocks
        first_page_blocks = [b for b in blocks if b["page"] == 1][:10]
        
        best_candidate = ""
        best_score = 0
        
        for block in first_page_blocks:
            text = block["text"]
            
            # Basic filters
            if len(text) < 5 or len(text) > 200:
                continue
                
            # Skip common non-titles
            if any(pattern.search(text) for pattern in self.skip_patterns):
                continue
            
            # Score based on size and position
            score = block["font_size"]
            if block["is_bold"]:
                score *= 1.3
            if block["page"] == 1:
                score *= 1.2
            
            if score > best_score:
                best_score = score
                best_candidate = text
        
        return best_candidate
    
    def _extract_headings(self, blocks: List[Dict]) -> List[Dict]:
        """Extract headings from all pages"""
        if not blocks:
            return []
        
        # Calculate typical body font size
        font_sizes = [b["font_size"] for b in blocks]
        font_counter = Counter(font_sizes)
        body_size = font_counter.most_common(1)[0][0]
        
        print(f"Detected body font size: {body_size}")
        
        candidates = []
        
        for block in blocks:
            text = block["text"]
            
            # Length filter
            if len(text) < 3 or len(text) > 150:
                continue
            
            # Skip obvious non-headings
            if any(pattern.search(text) for pattern in self.skip_patterns):
                continue
            
            score = 0
            
            # Font size scoring (most important factor)
            if block["font_size"] > body_size + 1:
                score += (block["font_size"] - body_size) * 0.1
            
            # Bold text bonus
            if block["is_bold"]:
                score += 0.3
            
            # Pattern matching
            if any(pattern.match(text) for pattern in self.heading_patterns):
                score += 0.4
            
            # Length bonus for reasonable heading length
            if 5 <= len(text) <= 80:
                score += 0.2
            
            # Capitalization patterns
            if text[0].isupper() and not text.endswith('.'):
                score += 0.1
            
            if score >= 0.4:  # Lowered threshold
                candidates.append({
                    "text": text,
                    "page": block["page"],
                    "score": score,
                    "font_size": block["font_size"]
                })
        
        print(f"Found {len(candidates)} heading candidates")
        
        # Remove duplicates and sort
        seen_texts = set()
        unique_candidates = []
        
        for candidate in candidates:
            text_lower = candidate["text"].lower().strip()
            if text_lower not in seen_texts:
                seen_texts.add(text_lower)
                unique_candidates.append(candidate)
        
        # Sort by score, then by page
        unique_candidates.sort(key=lambda x: (-x["score"], x["page"]))
        
        # Assign levels based on font size groups
        return self._assign_levels(unique_candidates)
    
    def _assign_levels(self, candidates: List[Dict]) -> List[Dict]:
        """Assign H1, H2, H3 levels based on font sizes"""
        if not candidates:
            return []
        
        # Group by font size
        size_groups = {}
        for candidate in candidates:
            size = candidate["font_size"]
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(candidate)
        
        # Sort sizes in descending order
        sorted_sizes = sorted(size_groups.keys(), reverse=True)
        
        # Assign levels
        result = []
        level_names = ["H1", "H2", "H3"]
        
        for i, size in enumerate(sorted_sizes[:3]):  # Only top 3 sizes
            level = level_names[i]
            for candidate in size_groups[size]:
                result.append({
                    "level": level,
                    "text": candidate["text"],
                    "page": candidate["page"]
                })
        
        # Sort final result by page number
        result.sort(key=lambda x: x["page"])
        
        print(f"Final headings: {len(result)}")
        for h in result:
            print(f"  {h['level']}: {h['text'][:50]} (page {h['page']})")
        
        return result