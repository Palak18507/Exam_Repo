import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import os

RAW_PDF_DIR = "../../data/raw_pdfs/sample"
OUTPUT_TEXT_DIR = "../../data/extracted_text"

os.makedirs(OUTPUT_TEXT_DIR, exist_ok=True)


def extract_text_pymupdf(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text.strip()


def extract_text_ocr(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text += pytesseract.image_to_string(img)
    return text.strip()


def process_pdf(pdf_file):
    pdf_path = os.path.join(RAW_PDF_DIR, pdf_file)
    output_txt = os.path.join(
        OUTPUT_TEXT_DIR, pdf_file.replace(".pdf", ".txt")
    )

    print(f"Processing: {pdf_file}")

    text = extract_text_pymupdf(pdf_path)

    # If text is too small, assume scanned PDF
    if len(text) < 200:
        print("  → Low text detected, switching to OCR")
        text = extract_text_ocr(pdf_path)

    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"  ✓ Saved to {output_txt}")


def main():
    for file in os.listdir(RAW_PDF_DIR):
        if file.lower().endswith(".pdf"):
            process_pdf(file)


if __name__ == "__main__":
    main()