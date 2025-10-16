import io
import logging
import re
from typing import Union, Optional, Dict, Any, List

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pdf import read_pdf
from .core.document_framework import DocumentGenerationFramework
from .core.exceptions import DocumentFrameworkError, PDFProcessingError
from .core.document_models import Document
from .core.section_parser import parse_ki_sections


def convert_section(text):
    match = re.fullmatch(r'section(\d+)', text, re.IGNORECASE)
    if match:
        number = match.group(1)
        return f"Section {number}"
    else:
        raise ValueError("Input string does not match the pattern 'section[0-9]+'")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restricted to specific origins for security
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World3"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

class DocumentGenerationRequest(BaseModel):
    """Request model for document generation with explicit plugin selection."""
    plugin_id: str  # Required - no default, user must specify
    template_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = {}


class DocumentGenerationResponse(BaseModel):
    """Unified response model for all document generation endpoints"""
    sections: List[str]  # List of section names
    texts: List[str]     # List of section texts (parallel to sections)
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Initialize framework for new endpoints
framework = DocumentGenerationFramework()


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    """Unified endpoint using new framework for informed consent KI summary"""
    contents = await file.read()
    file_io = io.BytesIO(contents)
    pdf_pages = read_pdf(file_io)
    
    # Convert to Document
    full_text = "\n\n".join(pdf_pages.texts)
    document = Document(
        text=full_text,
        metadata={
            "page_labels": pdf_pages.labels,
            "source": file.filename or "uploaded_file.pdf"
        }
    )
    
    # Generate using framework with informed-consent-ki type
    result = await framework.generate(
        document_type="informed-consent-ki",
        parameters={},
        document=document
    )
    
    if result.success:
        parsed_sections = parse_ki_sections(result.content)
        if parsed_sections:
            sections = [section.title for section in parsed_sections]
            texts = [section.body for section in parsed_sections]
            summary_text = "\n\n".join(texts)
            sections.append("Total Summary")
            texts.append(summary_text)
        else:
            sections = ["Total Summary"]
            texts = [result.content.strip()]
        return {"sections": sections, "texts": texts}
    else:
        # Return error in expected format
        return {
            "sections": ["Error"],
            "texts": [f"Failed to generate summary: {result.error_message}"]
        }


@app.post("/generate/")
async def generate_document(
    file: UploadFile = File(...),
    plugin_id: str = Form(...),  # Required - user must explicitly specify
    template_id: Optional[str] = Form(None),
    parameters: Optional[str] = Form("{}")
):
    """
    Unified endpoint for document generation with explicit plugin selection.
    
    Args:
        file: The PDF file to process
        plugin_id: ID of the plugin to use (required - e.g., "informed-consent-ki", "clinical-protocol")
        template_id: Optional specific template ID within the plugin
        parameters: JSON string with additional parameters
    
    Returns:
        Standardized response with sections and texts lists
    """
    try:
        # Parse parameters
        import json
        params = json.loads(parameters) if parameters else {}
        
        # Read PDF
        contents = await file.read()
        file_io = io.BytesIO(contents)
        pdf_pages = read_pdf(file_io)
        
        # Convert to Document
        full_text = "\n\n".join(pdf_pages.texts)
        document = Document(
            text=full_text,
            metadata={
                "page_labels": pdf_pages.labels,
                "source": file.filename
            }
        )
        
        # Add template_id to parameters if provided
        if template_id:
            params["template_id"] = template_id
        
        # Generate using framework with explicit plugin
        result = await framework.generate(
            document_type=plugin_id,  # Using plugin_id as document_type
            parameters=params,
            document=document
        )
        
        if result.success:
            if plugin_id == "informed-consent-ki":
                parsed_sections = parse_ki_sections(result.content)
                if parsed_sections:
                    sections = [section.title for section in parsed_sections]
                    texts = [section.body for section in parsed_sections]
                    summary_text = "\n\n".join(texts)
                    sections.append("Total Summary")
                    texts.append(summary_text)
                else:
                    sections = ["Total Summary"]
                    texts = [result.content.strip()]
            else:
                sections: List[str] = []
                texts: List[str] = []
                if "\n## " in result.content:
                    # Parse markdown sections
                    content_sections = result.content.split("\n## ")
                    for section in content_sections:
                        if section.strip():
                            lines = section.split("\n", 1)
                            if len(lines) > 0:
                                section_title = lines[0].strip()
                                section_content = lines[1].strip() if len(lines) > 1 else ""
                                sections.append(section_title)
                                texts.append(section_content)
                else:
                    # Return as single section
                    sections.append(plugin_id.replace("-", " ").title())
                    texts.append(result.content)

            return {
                "sections": sections,
                "texts": texts,
                "metadata": result.metadata
            }
        else:
            return {
                "sections": ["Error"],
                "texts": [f"Failed to generate document: {result.error_message}"],
                "error": result.error_message
            }
            
    except DocumentFrameworkError as e:
        # Framework-specific errors with detailed context
        return {
            "sections": ["Error"],
            "texts": [e.message],
            "error": e.message,
            "details": e.details
        }
    except Exception as e:
        # Unexpected errors
        return {
            "sections": ["Error"],
            "texts": [f"An unexpected error occurred: {str(e)}"],
            "error": str(e)
        }


@app.get("/plugins/")
async def list_plugins():
    """List all available plugins for document processing.
    
    Returns a list of plugins with their IDs, names, and descriptions.
    Users must specify one of these plugin IDs when calling /generate/.
    """
    plugin_ids = framework.list_supported_document_types()
    return {
        "plugins": [
            {
                "plugin_id": plugin_id,
                "info": framework.get_plugin_info(plugin_id)
            }
            for plugin_id in plugin_ids
        ],
        "total": len(plugin_ids)
    }


@app.get("/plugins/{plugin_id}/")
async def get_plugin_info(plugin_id: str):
    """Get detailed information about a specific plugin.
    
    Args:
        plugin_id: The ID of the plugin (e.g., "informed-consent-ki")
    
    Returns:
        Detailed plugin information including supported templates,
        validation rules, and capabilities.
    """
    info = framework.get_plugin_info(plugin_id)
    if not info:
        raise HTTPException(
            status_code=404, 
            detail=f"Plugin '{plugin_id}' not found. Use GET /plugins/ to see available plugins."
        )
    return {
        "plugin_id": plugin_id,
        "details": info,
        "usage": {
            "endpoint": "/generate/",
            "required_fields": {
                "file": "PDF file to process",
                "plugin_id": plugin_id,
                "template_id": "Optional template within plugin",
                "parameters": "Optional JSON parameters"
            }
        }
    }

