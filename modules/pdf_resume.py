"""Bounded text extraction for supported resume PDFs."""
import io
from PyPDF2 import PdfReader


def extract_resume(pdf_bytes):
    if not pdf_bytes or len(pdf_bytes) > 10 * 1024 * 1024:
        raise ValueError("Upload a non-empty PDF smaller than 10MB.")
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("This PDF is password-protected. Upload an unlocked copy.")
        if not 1 <= len(reader.pages) <= 100:
            raise ValueError("Please upload a resume with 1 to 100 pages.")
        result = "\n".join(page.extract_text() or "" for page in reader.pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("This PDF could not be read. Export a fresh text-based PDF and try again.") from exc
    if not result.strip():
        raise ValueError("No text found. Convert scanned/image PDFs to searchable text before uploading.")
    return result
