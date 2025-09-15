import asyncio
from app.core.unified_extractor import UnifiedExtractor
from app.core.extraction_models import KIExtractionSchema
from PyPDF2 import PdfReader

async def test_extraction():
    # Read PDF
    pdf_path = "/mnt/d/Common_Resources/irb-ki-summary/test_data/HUM00173014.pdf"
    reader = PdfReader(pdf_path)
    text_chunks = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_chunks.append(text)
    document_text = "\n".join(text_chunks)
    print(f"Document length: {len(document_text)} chars")
    
    # Test extraction
    extractor = UnifiedExtractor()
    result = await extractor.extract(document_text, KIExtractionSchema)
    
    # Print key fields
    print(f"\nExtracted values:")
    print(f"  study_object: {result.study_object}")
    print(f"  study_purpose: {result.study_purpose}")
    print(f"  study_goals: {result.study_goals}")
    print(f"  key_risks: {result.key_risks}")
    print(f"  study_duration: {result.study_duration}")
    print(f"  has_direct_benefits: {result.has_direct_benefits}")
    print(f"  benefit_description: {result.benefit_description}")
    print(f"  has_randomization: {result.has_randomization}")
    print(f"  requires_washout: {result.requires_washout}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
