from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum

class DocumentStatus(str, Enum):
    """Document processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSED = "parsed"
    VALIDATED = "validated"
    FAILED = "failed"

class DocumentType(str, Enum):
    """Types of medical documents"""
    PRESCRIPTION = "prescription"
    MEDICAL_BILL = "medical_bill"
    DIAGNOSTIC_REPORT = "diagnostic_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    INSURANCE_CLAIM = "insurance_claim"
    OTHER = "other"

class ParsedDocument(SQLModel, table=True):
    """Main document table"""
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    original_path: str
    document_type: DocumentType = DocumentType.OTHER
    file_size: int
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_timestamp: Optional[datetime] = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    
    # OCR Results
    raw_ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_model_used: Optional[str] = None
    
    # Structured Data
    parsed_json: Optional[str] = None  # JSON string of extracted structured data
    
    # CGHS Specific
    is_cghs_compliant: Optional[bool] = None
    cghs_validation_notes: Optional[str] = None
    
    # Relationships
    entities: List["ExtractedEntity"] = Relationship(back_populates="document")
    processing_jobs: List["ProcessingJob"] = Relationship(back_populates="document")

class ExtractedEntity(SQLModel, table=True):
    """Extracted entities from documents"""
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="parseddocument.id")
    
    entity_type: str  # drug_name, doctor_name, price, date, etc.
    entity_value: str
    confidence_score: float
    
    # Bounding box coordinates (for layout)
    bbox_x1: Optional[float] = None
    bbox_y1: Optional[float] = None
    bbox_x2: Optional[float] = None
    bbox_y2: Optional[float] = None
    
    # Validation
    is_validated: bool = False
    corrected_value: Optional[str] = None
    validation_notes: Optional[str] = None
    
    # Relationships
    document: ParsedDocument = Relationship(back_populates="entities")

class ProcessingJob(SQLModel, table=True):
    """Track processing jobs for async operations"""
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="parseddocument.id")
    
    job_type: str  # ocr, nlp, validation
    status: DocumentStatus
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    error_message: Optional[str] = None
    result_data: Optional[str] = None  # JSON string
    
    # Relationships
    document: ParsedDocument = Relationship(back_populates="processing_jobs")

class MedicineDatabase(SQLModel, table=True):
    """Reference medicine database for validation"""
    id: Optional[int] = Field(default=None, primary_key=True)
    
    medicine_name: str = Field(index=True)
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    dosage_form: Optional[str] = None  # tablet, syrup, injection
    strength: Optional[str] = None  # 500mg, 10ml
    
    mrp: Optional[float] = None
    manufacturer: Optional[str] = None
    
    # Search optimization
    search_keywords: Optional[str] = None  # Space-separated keywords for fuzzy search
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class ValidationResult(SQLModel, table=True):
    """Store validation results"""
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="parseddocument.id")
    
    validation_type: str  # medicine_validation, price_validation, cghs_compliance
    is_valid: bool
    confidence_score: float
    
    validation_details: str  # JSON string with detailed results
    suggestions: Optional[str] = None  # Suggested corrections
    
    validated_at: datetime = Field(default_factory=datetime.utcnow)
