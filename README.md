# IRB Key Information Summary Backend

A FastAPI-based backend service that processes and analyzes Informed Consent documents for human subjects research. The service uses advanced language models and embeddings via Azure OpenAI Service to generate clear, understandable summaries of complex research consent documents.

## Features

- PDF document processing and analysis
- Hierarchical document parsing using LlamaIndex
- Concurrent processing of document sections
- Azure OpenAI Service integration (e.g., GPT-4o, text-embedding models) for intelligent summarization
- Specialized in bioethics and patient advocacy context
- RESTful API endpoints for document upload and processing

## Prerequisites

- Python 3.x
- Azure OpenAI Service access and credentials (see Environment Variables)
- A `.env` file in the project root to store credentials.

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd irb-ki-backend # Or your project directory name
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
# On Windows: venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root and add your Azure OpenAI credentials:
```dotenv
AZURE_OPENAI_ENDPOINT=<your_azure_openai_endpoint>
AZURE_OPENAI_API_KEY=<your_azure_openai_api_key>
OPENAI_API_VERSION=<your_openai_api_version>
AZURE_OPENAI_DEPLOYMENT_LLM=<your_llm_deployment_name>
AZURE_OPENAI_DEPLOYMENT_EMBED=<your_embedding_deployment_name>
```
Replace the placeholders (`<...>`) with your actual values. The application uses `python-dotenv` to load these variables automatically.

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

1. **Document Ingestion**: PDF documents are processed using a custom PDF reader
2. **Text Processing**: Documents are parsed into hierarchical nodes using LlamaIndex
3. **Embedding & Indexing**: Text is embedded using an Azure OpenAI embedding model (e.g., `text-embedding-3-large`)
4. **Query Processing**: Uses LlamaIndex with Azure OpenAI models for efficient document querying and reranking
5. **Summary Generation**: Employs an Azure OpenAI chat model (e.g., `gpt-4o`) for generating clear, authoritative summaries

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
- llama-index
- llama-index-llms-azure-openai
- llama-index-embeddings-azure-openai
- python-dotenv

See `requirements.txt` for specific versions.

## Running the Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The server will start on `http://localhost:8000` by default.
