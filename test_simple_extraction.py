#!/usr/bin/env python3
"""
Test script for the simplified chain-of-thought extraction system.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from app.core.simple_extraction import SimpleChainOfThoughtExtractor
from app.core.extraction_models import KIExtractionSchema
from app.core.llm_integration import get_generic_extractor
from app.logger import get_logger

logger = get_logger("test_simple_extraction")


async def test_extraction():
    """Test the simplified extraction with a sample document."""
    
    # Sample informed consent document text
    sample_document = """
    KEY INFORMATION
    
    Purpose of the Study:
    This study is testing a new investigational drug called XYZ-789 to see if it helps 
    reduce symptoms of moderate to severe asthma in adults.
    
    What Will Happen:
    If you join this study, you will be randomly assigned (like flipping a coin) to 
    receive either XYZ-789 or a placebo for 24 weeks. You will need to visit the 
    clinic 8 times over the course of 6 months. We will collect blood samples at 
    each visit for safety monitoring and genetic testing.
    
    Risks:
    The most common risks include injection site reactions, headache, and upper 
    respiratory infections. Some patients may experience allergic reactions.
    
    Benefits:
    You may experience improved breathing and fewer asthma attacks. However, we 
    cannot guarantee you will benefit personally from this study. The information 
    we gather may help future patients with asthma.
    
    Duration:
    Your participation in this study will last approximately 6 months, including 
    the treatment period and follow-up visits.
    
    Alternatives:
    If you choose not to participate, you can continue with your current asthma 
    medications or discuss other treatment options with your doctor.
    """
    
    try:
        # Initialize the extractor
        llm = get_generic_extractor()
        extractor = SimpleChainOfThoughtExtractor(llm=llm)
        
        logger.info("Starting extraction test...")
        
        # Perform extraction
        result = await extractor.extract(
            document_text=sample_document,
            schema_class=KIExtractionSchema
        )
        
        # Print results
        print("\n" + "="*60)
        print("EXTRACTION RESULTS")
        print("="*60)
        
        for field_name, value in result.items():
            print(f"\n{field_name}:")
            print(f"  Value: {value}")
            print(f"  Type: {type(value).__name__}")
        
        # Validate key fields
        print("\n" + "="*60)
        print("VALIDATION")
        print("="*60)
        
        expected_fields = [
            "is_pediatric",
            "study_type", 
            "study_object",
            "has_randomization",
            "study_duration",
            "key_risks",
            "has_direct_benefits",
            "collects_biospecimens"
        ]
        
        missing_fields = [f for f in expected_fields if f not in result]
        if missing_fields:
            print(f"⚠️  Missing fields: {missing_fields}")
        else:
            print("✅ All expected fields present")
        
        # Check specific extractions
        checks = [
            ("study_object should mention XYZ-789", "xyz-789" in str(result.get("study_object", "")).lower()),
            ("has_randomization should be True", result.get("has_randomization") == True),
            ("study_duration should mention 6 months", "6 month" in str(result.get("study_duration", "")).lower()),
            ("collects_biospecimens should be True", result.get("collects_biospecimens") == True),
            ("is_pediatric should be False", result.get("is_pediatric") == False),
            ("study_type should be 'studying'", result.get("study_type") == "studying")
        ]
        
        print("\nField Checks:")
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        # Overall success
        all_passed = all(check[1] for check in checks) and not missing_fields
        
        print("\n" + "="*60)
        if all_passed:
            print("✅ TEST PASSED - All extractions correct!")
        else:
            print("⚠️  TEST COMPLETED - Some issues found")
        print("="*60)
        
        return result
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_with_validation():
    """Test extraction with validation and retry."""
    
    sample_document = """
    This clinical trial studies a new treatment approach for children with acute 
    lymphoblastic leukemia (ALL). Participants will receive standard chemotherapy.
    The study will last up to 60 months including follow-up.
    """
    
    try:
        llm = get_generic_extractor()
        extractor = SimpleChainOfThoughtExtractor(llm=llm)
        
        logger.info("Testing extraction with validation...")
        
        result = await extractor.extract_with_validation(
            document_text=sample_document,
            schema_class=KIExtractionSchema,
            max_retries=2
        )
        
        print("\n" + "="*60)
        print("EXTRACTION WITH VALIDATION")
        print("="*60)
        
        # Check pediatric detection
        print(f"\nis_pediatric: {result.get('is_pediatric')}")
        print(f"  Expected: True (document mentions 'children')")
        print(f"  Result: {'✅ Correct' if result.get('is_pediatric') else '❌ Incorrect'}")
        
        # Check duration extraction
        print(f"\nstudy_duration: {result.get('study_duration')}")
        print(f"  Expected: 'up to 60 months' or similar")
        if "60 month" in str(result.get('study_duration', '')).lower():
            print(f"  Result: ✅ Correct")
        else:
            print(f"  Result: ❌ Incorrect")
        
        return result
        
    except Exception as e:
        logger.error(f"Validation test failed: {e}")
        return None


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TESTING SIMPLIFIED CHAIN-OF-THOUGHT EXTRACTION")
    print("="*60)
    
    # Test 1: Basic extraction
    result1 = await test_extraction()
    
    # Test 2: Extraction with validation
    result2 = await test_with_validation()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    
    return result1 is not None and result2 is not None


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)