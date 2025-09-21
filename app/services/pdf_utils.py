import os
import tempfile
from typing import List

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except Exception:
    PDF2IMAGE_AVAILABLE = False


def convert_pdf_to_images(pdf_path: str, max_pages: int = 5) -> List[str]:
    """Convert PDF to temporary PNG images. Returns list of file paths."""
    if not PDF2IMAGE_AVAILABLE:
        raise RuntimeError("pdf2image not available")

    poppler_path = os.path.expanduser(
        r"~\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"
    )
    images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=max_pages, poppler_path=poppler_path)

    paths = []
    for i, image in enumerate(images, 1):
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        image.save(tmp.name, 'PNG')
        tmp.close()
        paths.append(tmp.name)

    return paths
