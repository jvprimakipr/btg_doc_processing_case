import pymupdf
import pytesseract
from langchain_core.tools import tool
from PIL import Image


@tool
def read_pdf_with_pymupdf(path: str) -> str:
    """Extract native text from a PDF using PyMuPDF."""

    document = pymupdf.open(path)
    text = "\n".join(page.get_text() for page in document).strip()

    return text

@tool
def read_pdf_with_tesseract(path: str) -> str:
    """Render PDF pages and extract their text using Tesseract OCR."""

    document = pymupdf.open(path)
    pages = []

    for page in document:
        pixels = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", [pixels.width, pixels.height], pixels.samples)

        try:
            pages.append(pytesseract.image_to_string(image, lang="por+eng"))
        except Exception:
            pages.append(pytesseract.image_to_string(image, lang="eng"))

    return "\n".join(pages).strip()