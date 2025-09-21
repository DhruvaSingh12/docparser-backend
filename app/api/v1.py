from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlmodel import Session
import aiofiles
import os
import tempfile
from datetime import datetime
from typing import Dict, Any

from app.db import get_session
from app.models import ParsedDocument, DocumentType, DocumentStatus
from app.services.ocr_service import ocr_process

router = APIRouter()

# File upload configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_FILE_TYPES", "png,jpg,jpeg,pdf").split(",")

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE} bytes"
        )
    
    # Check file extension
    if file.filename:
        extension = file.filename.split(".")[-1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    document_type: DocumentType = DocumentType.OTHER,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Parse uploaded medical document
    
    Args:
        file: Uploaded document file
        document_type: Type of medical document
        session: Database session
    
    Returns:
        Dictionary with parsing results and document ID
    """
    try:
        # Validate file
        validate_file(file)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
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
                result = await ocr_process(temp_path)
                
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
