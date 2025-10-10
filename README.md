# DocParse Backend - CGHS Medical Document Processing

A comprehensive medical document parsing system designed for CGHS (Central Government Health Scheme) reimbursement processing. This FastAPI-based backend extracts text from medical documents using OCR and processes them for compliance validation.

## Features

- **Multi-format Document Processing**: Supports images (PNG, JPG) and PDF files
- **Advanced OCR Pipeline**: Tesseract-based text extraction with preprocessing
- **PDF Support**: Multi-page PDF processing with automatic image conversion
- **Database Integration**: PostgreSQL with Row Level Security (RLS)
- **Modular Architecture**: Clean separation of OCR engines, preprocessing, and services

## System Requirements

### Prerequisites

- **Python 3.10+**
- **PostgreSQL** (or Neon PostgreSQL cloud database)
- **Tesseract OCR** (Windows binary)
- **Poppler PDF tools** (for PDF processing)

### Windows Setup

1. **Install Tesseract OCR**:
   ```bash
   winget install UB-Mannheim.TesseractOCR
   ```
   This installs Tesseract to: `C:\Program Files\Tesseract-OCR\tesseract.exe`

2. **Install Poppler Tools**:
   ```bash
   winget install oschwartz10612.Poppler
   ```
   This installs Poppler tools for PDF processing.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd docparse/backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   Create a `.env` file in the backend directory:
   ```env
   DATABASE_URL=postgresql://username:password@host:port/database
   DEBUG=false
   LOG_LEVEL=warning
   ```

5. **Initialize database**:
   The database will be automatically initialized when the server starts.

## Running the Application

1. **Start the development server**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Access the application**:
   - API: http://127.0.0.1:8000
   - Interactive docs: http://127.0.0.1:8000/docs
   - Alternative docs: http://127.0.0.1:8000/redoc

## API Endpoints

### Document Processing

- **POST /api/v1/parse**: Upload and process a document
  - Accepts: `multipart/form-data` with file upload
  - Supports: PNG, JPG, PDF files
  - Returns: Extracted text with confidence scores and processing metadata

### Example Usage

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/parse" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@document.pdf"
```

## Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── db.py               # Database configuration and session management
├── models.py           # SQLModel database models
├── api/
│   └── v1.py          # API route definitions
└── services/
    ├── ocr_service.py  # OCR service compatibility wrapper
    ├── engines.py      # OCR engine implementations
    ├── preprocess.py   # Image preprocessing utilities
    ├── pdf_utils.py    # PDF processing utilities
    └── service.py      # Main OCR service orchestrator
```

## OCR Pipeline

The OCR pipeline includes:

1. **Document Type Detection**: Automatically detects PDF vs image files
2. **PDF Processing**: Converts PDF pages to high-resolution images
3. **Image Preprocessing**: 
   - Noise reduction
   - Skew correction
   - Binarization
   - Contrast enhancement
4. **OCR Processing**: Tesseract-based text extraction with confidence scoring
5. **Result Formatting**: Structured JSON output with text blocks and metadata

## Database Schema

- **ParsedDocument**: Stores document metadata and processing results
- **ExtractedEntity**: Stores specific entities extracted from documents
- **ProcessingJob**: Tracks async processing tasks
- **ValidationResult**: Stores validation results and compliance checks

## Configuration

The application supports the following environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `DEBUG`: Enable/disable debug logging (default: false)
- `LOG_LEVEL`: Logging level (default: warning)
- `TESSERACT_PATH`: Custom Tesseract binary path (optional)
- `USE_GPU`: Enable GPU acceleration for OCR (default: false)

## Development

### Adding New OCR Engines

1. Create a new engine class inheriting from `OCREngine` in `engines.py`
2. Implement the `process` method
3. Register the engine in `OCRService.__init__`

### System Dependencies

The application automatically configures paths for:
- Tesseract: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Poppler: Winget installation path under user AppData

## Troubleshooting

### Common Issues

1. **"Tesseract is not installed"**: Ensure Tesseract is installed via winget and accessible
2. **"pdf2image not available"**: Install pdf2image: `pip install pdf2image`
3. **PDF processing fails**: Ensure Poppler tools are installed
4. **Database connection errors**: Check DATABASE_URL in .env file

### Logs

The application provides detailed logging. Set `DEBUG=true` and `LOG_LEVEL=debug` in `.env` for verbose output.
