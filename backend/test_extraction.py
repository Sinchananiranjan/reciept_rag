import os
import sys

# Add the backend path to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ocr_service import OCREngine
from app.services.extraction_service import extraction_service

ocr = OCREngine()

uploads_dir = "uploads"
files = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir) if f.endswith(".png") or f.endswith(".jpeg")]
# Sort by modification time (latest first)
files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

for file in files[:4]:
    print(f"Testing {file}...")
    text, conf, success = ocr.extract_text_from_file(file)
    print("\n--- OCR TEXT ---")
    print(text)
    print("----------------\n")
    
    extracted = extraction_service._extract_with_heuristics(text)
    print(f"Merchant Name: {extracted.get('merchant_name')}")
    print(f"Total: {extracted.get('total')}")
    print(f"Subtotal: {extracted.get('subtotal')}")
    print("Items:")
    for item in extracted.get("items", []):
        print(f"  {item}")
    print("=========================================\n")
