from typing import Dict, Any, List, Optional
from .engines import TesseractEngine, PaddleOCREngine

_ocr_service = None

class OCRService:
    def __init__(self):
        self.engines = []
        self.default_engine = None

        # Initialize available engines
        try:
            tesseract = TesseractEngine()
            self.engines.append(tesseract)
            if not self.default_engine:
                self.default_engine = tesseract
        except Exception:
            pass

        try:
            paddle = PaddleOCREngine()
            self.engines.append(paddle)
            self.default_engine = paddle
        except Exception:
            pass

        if not self.engines:
            raise RuntimeError("No OCR engines available. Please install tesseract or paddleocr.")

    def get_available_engines(self) -> List[str]:
        return [engine.name for engine in self.engines]

    def process_with_engine(self, image_path: str, engine_name: Optional[str] = None) -> Dict[str, Any]:
        if engine_name:
            engine = next((e for e in self.engines if e.name == engine_name), None)
            if not engine:
                raise ValueError(f"Engine '{engine_name}' not available")
        else:
            engine = self.default_engine
        
        if not engine:
            raise RuntimeError("No OCR engine available")
        
        return engine.process(image_path)

    def process_with_best_engine(self, image_path: str) -> Dict[str, Any]:
        if len(self.engines) == 1:
            return self.engines[0].process(image_path)
        results = []
        for engine in self.engines:
            try:
                results.append(engine.process(image_path))
            except Exception as e:
                print(f"Engine {engine.name} failed: {e}")
        if not results:
            return {"model": "none", "text": "", "confidence": 0.0, "blocks": [], "error": "All OCR engines failed"}
        best = max(results, key=lambda x: x.get("confidence", 0))
        return best


def get_ocr_service() -> OCRService:
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


async def ocr_process(image_path: str, engine_name: Optional[str] = None) -> Dict[str, Any]:
    service = get_ocr_service()
    if engine_name:
        return service.process_with_engine(image_path, engine_name)
    return service.process_with_best_engine(image_path)
