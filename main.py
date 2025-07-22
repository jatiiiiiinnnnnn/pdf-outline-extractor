#!/usr/bin/env python3
"""
PDF Outline Extractor - Main Entry Point
Processes all PDFs in /app/input and generates JSON outlines in /app/output
"""

import os
import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pdf_processor import PDFProcessor

def process_all_pdfs():
    """Process all PDFs in the input directory"""
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in /app/input")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process")
    
    processor = PDFProcessor()
    
    for pdf_path in pdf_files:
        start_time = time.time()
        print(f"Processing: {pdf_path.name}")
        
        try:
            # Extract outline
            result = processor.extract_outline(str(pdf_path))
            
            # Generate output filename
            output_filename = pdf_path.stem + ".json"
            output_path = output_dir / output_filename
            
            # Save result
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            elapsed = time.time() - start_time
            print(f"✓ Completed {pdf_path.name} in {elapsed:.2f}s -> {output_filename}")
            
        except Exception as e:
            print(f"✗ Error processing {pdf_path.name}: {e}")
            # Create empty result for failed files
            empty_result = {"title": "", "outline": []}
            output_filename = pdf_path.stem + ".json"
            output_path = output_dir / output_filename
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(empty_result, f, indent=2)

if __name__ == "__main__":
    process_all_pdfs()