from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Protocol


class OCRServiceError(RuntimeError):
    pass


class OCRService(Protocol):
    async def extract_text(self, image: bytes) -> str: ...


class TesseractOCRService:
    async def extract_text(self, image: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise OCRServiceError(
                "OCR dependencies are not installed. Install the project with the 'ocr' extra."
            ) from exc

        def run_ocr() -> str:
            loaded_image = Image.open(BytesIO(image))
            return pytesseract.image_to_string(loaded_image)

        try:
            text = await asyncio.to_thread(run_ocr)
        except Exception as exc:
            raise OCRServiceError("OCR failed for this image.") from exc

        if not text.strip():
            raise OCRServiceError("OCR did not find readable text in this image.")
        return text


def build_ocr_service(provider: str) -> OCRService:
    if provider.lower() in {"", "tesseract"}:
        return TesseractOCRService()
    raise OCRServiceError(f"Unsupported OCR provider: {provider}")
