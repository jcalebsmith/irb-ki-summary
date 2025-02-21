# IRB Key Information Summary Backend

A FastAPI-based backend service that processes and analyzes Informed Consent documents for human subjects research. The service uses advanced language models and embeddings to generate clear, understandable summaries of complex research consent documents.

## Features

- PDF document processing and analysis
- Hierarchical document parsing using LlamaIndex
- Concurrent processing of document sections
- OpenAI GPT-4o integration for intelligent summarization
- Specialized in bioethics and patient advocacy context
- RESTful API endpoints for document upload and processing

## Prerequisites

- Python 3.x
- OpenAI API key (environment variable: `OPENAI_API_KEY`)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd irb-ki-backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY='your-api-key'
```

## API Endpoints

### Root Endpoint
- `GET /`: Health check endpoint
- Response: `{"Hello": "World3"}`

### File Upload
- `POST /uploadfile/`: Upload and process PDF documents
- Accepts: PDF file upload
- Returns: JSON object containing sectioned summaries of the document

## Technical Architecture

The application uses a multi-layered approach to process documents:

1. **Document Ingestion**: PDF documents are processed using custom PDF reader
2. **Text Processing**: Documents are parsed into hierarchical nodes
3. **Embedding & Indexing**: Text is embedded using OpenAI's text-embedding-3-large model
4. **Query Processing**: Uses LlamaIndex for efficient document querying
5. **Summary Generation**: Employs GPT-4o for generating clear, authoritative summaries

## Development

The project follows these key principles:
- Concurrent processing for improved performance
- Hierarchical document parsing for better context understanding
- Error handling and input validation
- CORS middleware for frontend integration

## Dependencies

Key dependencies include:
- fastapi[standard] >= 0.113.0
- pydantic >= 2.7.0
- python-multipart
- pypdf
- llama_index

## Running the Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The server will start on `http://localhost:8000`
