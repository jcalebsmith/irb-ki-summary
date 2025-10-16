"""
Simplified API for Document Generation
Clean REST API with consistent responses
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import io
import json

from app.pdf import read_pdf
from app.core.document_framework import DocumentGenerationFramework
from app.core.document_models import Document
from app.core.section_parser import parse_ki_sections
from app.config import get_cors_origins
from app.logger import get_logger

logger = get_logger("api")

app = FastAPI(
    title="Document Generation API",
    description="Generate structured documents from PDFs",
    version="2.0.0"
)

# Configure CORS from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize framework once
framework = DocumentGenerationFramework()


class GenerationRequest(BaseModel):
    """Request model for document generation"""
    plugin_id: str
    parameters: Dict[str, Any] = {}


class GenerationResponse(BaseModel):
    """Unified response model for all endpoints"""
    success: bool
    content: Optional[str] = None
    sections: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}


@app.post("/generate/", response_model=GenerationResponse)
async def generate_document(
    file: UploadFile = File(...),
    plugin_id: str = "informed-consent-ki",
    parameters: str = "{}"
):
    """
    Generate document from PDF using specified plugin.
    
    Args:
        file: PDF file to process
        plugin_id: Plugin to use (default: informed-consent-ki)
        parameters: JSON string with additional parameters
    
    Returns:
        GenerationResponse with content and metadata
    """
    try:
        # Parse parameters
        params = json.loads(parameters) if parameters else {}
        
        # Read and process PDF
        contents = await file.read()
        pdf_text = _extract_pdf_text(contents)
        
        # Create document
        document = Document(
            text=pdf_text,
            metadata={"source": file.filename or "upload.pdf"}
        )
        
        # Generate using framework
        result = await framework.generate(
            document_type=plugin_id,
            parameters=params,
            document=document
        )
        
        if result.success:
            # Parse content into sections if structured
            sections = _parse_sections(result.content, plugin_id)
            
            return GenerationResponse(
                success=True,
                content=result.content,
                sections=sections,
                metadata=result.metadata
            )
        else:
            return GenerationResponse(
                success=False,
                error=result.error_message
            )
            
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return GenerationResponse(
            success=False,
            error=str(e)
        )


@app.get("/plugins/")
async def list_plugins():
    """
    List available document generation plugins.
    
    Returns:
        List of plugin IDs and descriptions
    """
    try:
        plugins = framework.list_supported_document_types()
        
        plugin_info = []
        for plugin_id in plugins:
            try:
                info = framework.get_plugin_info(plugin_id)
                plugin_info.append({
                    "id": plugin_id,
                    "name": info.get("name", plugin_id),
                    "description": info.get("description", "")
                })
            except:
                plugin_info.append({
                    "id": plugin_id,
                    "name": plugin_id,
                    "description": ""
                })
        
        return {
            "plugins": plugin_info,
            "count": len(plugin_info)
        }
        
    except Exception as e:
        logger.error(f"Failed to list plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plugins/{plugin_id}/")
async def get_plugin_details(plugin_id: str):
    """
    Get detailed information about a specific plugin.
    
    Args:
        plugin_id: Plugin identifier
        
    Returns:
        Plugin details and usage information
    """
    try:
        info = framework.get_plugin_info(plugin_id)
        
        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Plugin '{plugin_id}' not found"
            )
        
        return {
            "id": plugin_id,
            "info": info,
            "usage": {
                "endpoint": "POST /generate/",
                "parameters": {
                    "file": "PDF file (required)",
                    "plugin_id": plugin_id,
                    "parameters": "{} (optional JSON)"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plugin info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoint for backward compatibility
@app.post("/uploadfile/")
async def legacy_upload(file: UploadFile):
    """Legacy endpoint - redirects to /generate/"""
    return await generate_document(
        file=file,
        plugin_id="informed-consent-ki",
        parameters="{}"
    )


# Helper functions
def _extract_pdf_text(contents: bytes) -> str:
    """Extract text from PDF bytes"""
    file_io = io.BytesIO(contents)
    pdf_pages = read_pdf(file_io)
    return "\n\n".join(pdf_pages.texts)


def _parse_sections(content: str, plugin_id: str) -> Optional[Dict[str, str]]:
    """Parse content into sections if structured"""
    if plugin_id != "informed-consent-ki":
        return None

    parsed_sections = parse_ki_sections(content)
    if not parsed_sections:
        return None

    return {f"section_{section.index}": section.body for section in parsed_sections}
