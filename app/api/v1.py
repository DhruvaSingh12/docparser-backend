from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlmodel import Session
import os
import tempfile
from datetime import datetime
from typing import Dict, Any
from enum import Enum

from app.db import get_session
from app.models import ParsedDocument, DocumentType, DocumentStatus
from app.services.ocr_service import ocr_process


class OCREngine(str, Enum):
    """Available OCR engines"""
    AUTO = "auto"
    TESSERACT = "tesseract"
    PADDLEOCR = "paddleocr"

router = APIRouter()

# File upload configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_FILE_TYPES", "png,jpg,jpeg,pdf").split(",")

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check filename exists
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )
    
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE} bytes"
        )
    
    # Check file extension
    extension = file.filename.split(".")[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(DocumentType.OTHER),
    ocr_engine: OCREngine = Form(OCREngine.AUTO),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Parse uploaded medical document
    
    Args:
        file: Uploaded document file (PNG, JPG, JPEG, PDF)
        document_type: Type of medical document
        ocr_engine: OCR engine to use (auto, tesseract, paddleocr)
        session: Database session
    
    Returns:
        Dictionary with parsing results and document ID
    """
    try:
        # Validate file
        validate_file(file)
        
        # Check filename exists
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        
        # Create temporary file
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'tmp'
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            # Read and save file content
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Create database record
            document = ParsedDocument(
                filename=file.filename,
                original_path=temp_path,
                document_type=document_type,
                file_size=len(content),
                status=DocumentStatus.UPLOADED,  
                parsed_json="{}" 
            )
            
            session.add(document)
            session.commit()
            session.refresh(document)
            
            # Update status to processing
            document.status = DocumentStatus.PROCESSING
            session.add(document)
            session.commit()
            
            # Process document with OCR
            try:
                # Determine which engine to use
                engine_name = None if ocr_engine == OCREngine.AUTO else ocr_engine.value
                result = await ocr_process(temp_path, engine_name)
                
                # Update document with results
                document.raw_ocr_text = result.get("text", "")
                document.ocr_confidence = result.get("confidence", 0.0)
                document.ocr_model_used = result.get("model", "unknown")
                document.parsed_json = str(result) if result else "{}"  # Ensure it's never None
                document.status = DocumentStatus.PARSED
                document.processing_timestamp = datetime.utcnow()
                
                session.add(document)
                session.commit()
                
                return {
                    "document_id": document.id,
                    "filename": document.filename,
                    "status": document.status,
                    "processing_timestamp": document.processing_timestamp,
                    "results": result
                }
                
            except Exception as ocr_error:
                # Update document status to failed
                document.status = DocumentStatus.FAILED
                session.add(document)
                session.commit()
                
                raise HTTPException(
                    status_code=500,
                    detail=f"OCR processing failed: {str(ocr_error)}"
                )
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )

@router.get("/document/{document_id}")
async def get_document(
    document_id: int,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Get parsed document by ID"""
    document = session.get(ParsedDocument, document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": document.id,
        "filename": document.filename,
        "document_type": document.document_type,
        "status": document.status,
        "upload_timestamp": document.upload_timestamp,
        "processing_timestamp": document.processing_timestamp,
        "ocr_confidence": document.ocr_confidence,
        "is_cghs_compliant": document.is_cghs_compliant,
        "parsed_data": document.parsed_json
    }

@router.get("/documents")
async def list_documents(
    limit: int = 10,
    offset: int = 0,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """List all parsed documents"""
    documents = session.query(ParsedDocument).offset(offset).limit(limit).all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "status": doc.status,
                "upload_timestamp": doc.upload_timestamp,
                "ocr_confidence": doc.ocr_confidence
            }
            for doc in documents
        ],
        "total": len(documents),
        "limit": limit,
        "offset": offset
    }

@router.get("/engines")
async def get_available_engines() -> Dict[str, Any]:
    """Get available OCR engines and their status"""
    try:
        from app.services.ocr_service import get_ocr_service
        service = get_ocr_service()
        available_engines = service.get_available_engines()
        
        return {
            "available_engines": available_engines,
            "default_engine": service.default_engine.name if service.default_engine else None,
            "engine_options": [
                {"value": "auto", "label": "Auto (Best Available)"},
                {"value": "tesseract", "label": "Tesseract OCR"},
                {"value": "paddleocr", "label": "PaddleOCR"}
            ]
        }
    except Exception as e:
        return {
            "available_engines": [],
            "default_engine": None,
            "error": str(e),
            "engine_options": [
                {"value": "auto", "label": "Auto (Best Available)"},
                {"value": "tesseract", "label": "Tesseract OCR"},
                {"value": "paddleocr", "label": "PaddleOCR"}
            ]
        }
