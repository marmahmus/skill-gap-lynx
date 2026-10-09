"""Read text from PDF or modern Word resumes without executing content."""
import io
import zipfile
from xml.etree import ElementTree

from modules.pdf_resume import extract_resume

_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def read_resume(data, filename):
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError("Upload a non-empty resume smaller than 10MB.")
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension == "pdf":
        return extract_resume(data)
    if extension != "docx":
        raise ValueError("Use PDF or Word (.docx). Save older .doc files as .docx first.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            parts = ["word/document.xml"] + sorted(
                name for name in names
                if name.startswith(("word/header", "word/footer")) and name.endswith(".xml")
            )
            if sum(archive.getinfo(name).file_size for name in parts) > 20 * 1024 * 1024:
                raise ValueError("Word document is too large to extract safely.")
            paragraphs = []
            for name in parts:
                root = ElementTree.fromstring(archive.read(name))
                for paragraph in root.findall(".//w:p", _NS):
                    fragments = []
                    for node in paragraph.iter():
                        tag = node.tag.rsplit("}", 1)[-1]
                        if tag == "t":
                            fragments.append(node.text or "")
                        elif tag in ("tab", "br", "cr"):
                            fragments.append(" ")
                    paragraphs.append("".join(fragments))
            result = "\n".join(paragraphs).strip()
    except ValueError:
        raise
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, RuntimeError, OSError) as exc:
        raise ValueError("This Word file could not be read. Save an unlocked .docx copy in Word and upload again.") from exc
    if not result:
        raise ValueError("No text found in the Word document. Upload a resume containing selectable text.")
    return result
