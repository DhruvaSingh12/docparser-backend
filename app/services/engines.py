import os
from typing import Dict, Any
from .preprocess import preprocess_image
from .pdf_utils import convert_pdf_to_images

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except Exception:
    PADDLEOCR_AVAILABLE = False


class OCREngine:
    def __init__(self):
        self.name = "base"
        self.confidence_threshold = 0.5

    def process(self, image_path: str) -> Dict[str, Any]:
        raise NotImplementedError


class TesseractEngine(OCREngine):
    def __init__(self, lang: str = "eng"):
        super().__init__()
        self.name = "tesseract"
        self.lang = lang

        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_path):
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                print(f"Tesseract configured at: {tesseract_path}")
            except Exception:
                pass

    def process(self, image_path: str) -> Dict[str, Any]:
        if not TESSERACT_AVAILABLE:
            return {"model": self.name, "text": "", "confidence": 0.0, "blocks": [], "error": "Tesseract is not available"}

        try:
            if image_path.lower().endswith('.pdf'):
                images = convert_pdf_to_images(image_path)
                all_text = ""
                all_blocks = []
                total_conf = 0
                page_count = 0
                for i, img_path in enumerate(images, 1):
                    result = self.process(img_path)
                    if result.get("text"):
                        all_text += f"[Page {i}]\n{result['text']}\n\n"
                        for b in result.get("blocks", []):
                            b['page'] = i
                            all_blocks.append(b)
                        total_conf += result.get("confidence", 0)
                        page_count += 1
                avg_conf = total_conf / max(page_count, 1)
                return {"model": self.name, "text": all_text.strip(), "confidence": avg_conf, "blocks": all_blocks}
            else:
                image = preprocess_image(image_path)
                data = pytesseract.image_to_data(image, lang=self.lang, output_type=pytesseract.Output.DICT)
                text_blocks = []
                full_text = ""
                total_conf = 0
                valid_blocks = 0
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i]) if data['conf'][i] != -1 else 0
                    if text and conf > 0:
                        text_blocks.append({
                            "text": text,
                            "confidence": conf / 100.0,
                            "bbox": [data['left'][i], data['top'][i], data['left'][i] + data['width'][i], data['top'][i] + data['height'][i]]
                        })
                        full_text += text + " "
                        total_conf += conf
                        valid_blocks += 1
                avg_conf = total_conf / max(valid_blocks, 1) / 100.0
                return {"model": self.name, "text": full_text.strip(), "confidence": avg_conf, "blocks": text_blocks}
        except Exception as e:
            return {"model": self.name, "text": "", "confidence": 0.0, "blocks": [], "error": str(e)}


class PaddleOCREngine(OCREngine):
    def __init__(self, lang: str = "en"):
        super().__init__()
        self.name = "paddleocr"
        self.lang = lang
        if PADDLEOCR_AVAILABLE:
            self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=os.getenv("USE_GPU", "false").lower() == "true")

    def process(self, image_path: str) -> Dict[str, Any]:
        if not PADDLEOCR_AVAILABLE:
            raise RuntimeError("PaddleOCR is not available")
        try:
            result = self.ocr.ocr(image_path, cls=True)
            text_blocks = []
            full_text = ""
            total_conf = 0
            for line in result[0] if result[0] else []:
                bbox, (text, confidence) = line
                text_blocks.append({"text": text, "confidence": confidence, "bbox": [bbox[0][0], bbox[0][1], bbox[2][0], bbox[2][1]]})
                full_text += text + " "
                total_conf += confidence
            avg_conf = total_conf / max(len(text_blocks), 1)
            return {"model": self.name, "text": full_text.strip(), "confidence": avg_conf, "blocks": text_blocks}
        except Exception as e:
            return {"model": self.name, "text": "", "confidence": 0.0, "blocks": [], "error": str(e)}
