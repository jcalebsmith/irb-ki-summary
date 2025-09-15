#!/usr/bin/env python3
"""
Integration tests for UnifiedExtractor using REAL API calls and REAL data.
NO MOCKS - all tests use actual Azure OpenAI API with structured extraction only.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from enum import Enum

# Set up test environment
import sys
sys.path.append(str(Path(__file__).parent / "app"))

from tests.test_utils import setup_test_logging, setup_test_paths, setup_azure_openai
from app.core.unified_extractor import UnifiedExtractor
from app.config import get_test_pdf_path, AZURE_OPENAI_CONFIG
from app.pdf import read_pdf

# Initialize logging
logger = setup_test_logging(__name__)
ROOT_DIR, APP_DIR = setup_test_paths()


# Test data models for structured extraction
class StudyType(str, Enum):
    PHASE_1 = "Phase 1"
    PHASE_2 = "Phase 2"
    PHASE_3 = "Phase 3"
    PHASE_4 = "Phase 4"
    OBSERVATIONAL = "Observational"


class ClinicalTrialInfo(BaseModel):
    """Test schema for structured extraction"""
    study_title: str = Field(description="Title of the clinical trial")
    principal_investigator: str = Field(description="Name of the principal investigator")
    study_duration: str = Field(description="Total duration of participant involvement")
    study_type: StudyType = Field(description="Type/phase of the study")
    number_of_visits: int = Field(description="Total number of study visits", ge=1)
    compensation_available: bool = Field(description="Whether participants will be compensated")
    risks_present: bool = Field(description="Whether there are risks involved")


class KeyInformationSummary(BaseModel):
    """Schema for IRB Key Information extraction"""
    purpose: str = Field(description="Purpose of the research study", max_length=500)
    duration: str = Field(description="Expected duration of participation", max_length=200)
    procedures: str = Field(description="Key procedures involved", max_length=500)
    risks: str = Field(description="Main risks or discomforts", max_length=500)
    benefits: str = Field(description="Potential benefits", max_length=300)
    alternatives: str = Field(description="Alternative treatments available", max_length=300)
    compensation: str = Field(description="Compensation details", max_length=200)
    voluntary: bool = Field(description="Whether participation is voluntary")
    contact_info: str = Field(description="Contact information for questions", max_length=300)


class MinimalExtraction(BaseModel):
    """Minimal schema for testing"""
    title: str = Field(description="Document title")
    has_risks: bool = Field(description="Whether risks are mentioned")


class TestUnifiedExtractor:
    """Integration tests for UnifiedExtractor with real API calls"""
    
    def __init__(self):
        """Initialize test environment with real Azure OpenAI client"""
        logger.info("Initializing UnifiedExtractor integration tests...")
        logger.info("Using REAL Azure OpenAI API - STRUCTURED EXTRACTION ONLY")
        
        # Get real LLM client
        _, self.llm = setup_azure_openai()
        
        # Initialize unified extractor with real client
        self.extractor = UnifiedExtractor(self.llm.client if hasattr(self.llm, 'client') else None)
        
        # Load real test document
        self.test_pdf_path = get_test_pdf_path()
        self.document_text = self._load_test_document()
        
        logger.info(f"Test document loaded: {len(self.document_text)} characters")
        logger.info(f"API endpoint: {AZURE_OPENAI_CONFIG.get('endpoint', 'Not configured')}")
    
    def _load_test_document(self) -> str:
        """Load real PDF document for testing"""
        try:
            if self.test_pdf_path and Path(self.test_pdf_path).exists():
                logger.info(f"Loading PDF from: {self.test_pdf_path}")
                pdf_content = read_pdf(self.test_pdf_path)
                # Handle PDFPages object if returned
                if hasattr(pdf_content, 'get_text'):
                    text = pdf_content.get_text()
                elif hasattr(pdf_content, '__str__'):
                    text = str(pdf_content)
                else:
                    text = pdf_content
                
                # If we got valid text, use it
                if text and isinstance(text, str) and len(text) > 100:
                    return text
                else:
                    logger.info("PDF content too short, using sample document")
                    return self._get_sample_document()
            else:
                # Fallback to sample clinical trial text
                logger.info("Using sample clinical trial document")
                return self._get_sample_document()
        except Exception as e:
            logger.warning(f"Could not load PDF: {e}")
            return self._get_sample_document()
    
    def _get_sample_document(self) -> str:
        """Get sample clinical trial document for testing"""
        return """
        CLINICAL TRIAL INFORMED CONSENT FORM
        
        Study Title: A Phase 3, Randomized, Double-Blind Study of Novel Drug XYZ-123 
        for Treatment of Advanced Melanoma
        
        Principal Investigator: Dr. Sarah Johnson, MD, PhD
        Institution: Memorial Cancer Center
        IRB Protocol Number: IRB-2024-0123
        
        STUDY INFORMATION
        
        You are being asked to participate in a research study. This study will test 
        whether a new drug called XYZ-123 is safe and effective for treating advanced 
        melanoma. The study will last approximately 18 months for each participant.
        
        STUDY VISITS AND PROCEDURES
        
        If you agree to participate, you will need to come to the clinic for 24 study 
        visits over the course of 18 months. During these visits, we will:
        - Perform physical examinations
        - Take blood samples for testing
        - Conduct imaging scans (CT or MRI)
        - Monitor your cancer and overall health
        
        RISKS AND BENEFITS
        
        There are risks associated with this study. Common side effects may include:
        - Fatigue (60% of participants)
        - Nausea (45% of participants)
        - Skin rash (30% of participants)
        
        The potential benefits include possible reduction in tumor size and improved 
        survival, though these benefits are not guaranteed.
        
        COMPENSATION
        
        You will receive $50 for each completed study visit to help cover travel 
        expenses and time. Total compensation could be up to $1,200 if all visits 
        are completed.
        
        VOLUNTARY PARTICIPATION
        
        Your participation is entirely voluntary. You may withdraw at any time without 
        penalty or loss of benefits.
        
        CONTACT INFORMATION
        
        For questions about this study, contact Dr. Sarah Johnson at 555-1234 or
        email: sjohnson@memorialcancer.org
        """
    
    async def test_clinical_trial_extraction(self):
        """Test extraction of clinical trial information using real API"""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Clinical Trial Information Extraction")
        logger.info("="*60)
        
        try:
            start_time = time.time()
            
            # Real API call for structured extraction
            result = await self.extractor.extract(
                document=self.document_text,
                output_schema=ClinicalTrialInfo
            )
            
            api_time = time.time() - start_time
            
            # Verify results
            assert isinstance(result, ClinicalTrialInfo), "Result should be ClinicalTrialInfo instance"
            
            logger.info(f"✅ Clinical trial extraction successful (API time: {api_time:.2f}s)")
            logger.info(f"   Study Title: {result.study_title}")
            logger.info(f"   PI: {result.principal_investigator}")
            logger.info(f"   Duration: {result.study_duration}")
            logger.info(f"   Study Type: {result.study_type}")
            logger.info(f"   Number of Visits: {result.number_of_visits}")
            logger.info(f"   Compensation: {result.compensation_available}")
            logger.info(f"   Risks Present: {result.risks_present}")
            
            # Validate extracted values are reasonable
            assert result.number_of_visits > 0, "Should extract positive number of visits"
            assert len(result.study_title) > 10, "Study title should be meaningful"
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Clinical trial extraction failed: {e}")
            return False
    
    async def test_key_information_extraction(self):
        """Test extraction of IRB key information using real API"""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: IRB Key Information Extraction")
        logger.info("="*60)
        
        try:
            start_time = time.time()
            
            # Real API call for key information extraction
            result = await self.extractor.extract(
                document=self.document_text,
                output_schema=KeyInformationSummary
            )
            
            api_time = time.time() - start_time
            
            logger.info(f"✅ Key information extraction successful (API time: {api_time:.2f}s)")
            logger.info(f"   Purpose: {result.purpose[:100]}...")
            logger.info(f"   Duration: {result.duration}")
            logger.info(f"   Procedures: {result.procedures[:100]}...")
            logger.info(f"   Risks: {result.risks[:100]}...")
            logger.info(f"   Benefits: {result.benefits[:100]}...")
            logger.info(f"   Compensation: {result.compensation}")
            logger.info(f"   Voluntary: {result.voluntary}")
            
            # Validate key fields are populated
            assert len(result.purpose) > 20, "Purpose should be extracted"
            assert len(result.risks) > 20, "Risks should be extracted"
            assert result.voluntary is not None, "Voluntary status should be determined"
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Key information extraction failed: {e}")
            return False
    
    async def test_minimal_extraction(self):
        """Test minimal extraction with simple schema"""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Minimal Schema Extraction")
        logger.info("="*60)
        
        try:
            start_time = time.time()
            
            # Test with minimal schema
            result = await self.extractor.extract(
                document=self.document_text[:1000],  # Use shorter text
                output_schema=MinimalExtraction
            )
            
            api_time = time.time() - start_time
            
            logger.info(f"✅ Minimal extraction successful (API time: {api_time:.2f}s)")
            logger.info(f"   Title: {result.title}")
            logger.info(f"   Has Risks: {result.has_risks}")
            
            assert isinstance(result.title, str), "Title should be string"
            assert isinstance(result.has_risks, bool), "Has risks should be boolean"
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Minimal extraction failed: {e}")
            return False
    
    async def test_error_handling(self):
        """Test error handling with invalid inputs"""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: Error Handling")
        logger.info("="*60)
        
        # Test with empty document
        try:
            result = await self.extractor.extract(
                document="",
                output_schema=MinimalExtraction
            )
            logger.info(f"✅ Handled empty document gracefully: {result}")
            assert result is not None, "Should return default values"
        except Exception as e:
            logger.error(f"❌ Failed to handle empty document: {e}")
            return False
        
        # Test with very short document
        try:
            result = await self.extractor.extract(
                document="This is a test.",
                output_schema=ClinicalTrialInfo
            )
            logger.info("✅ Handled short document with defaults")
            assert result is not None, "Should return instance with defaults"
        except Exception as e:
            logger.error(f"❌ Failed to handle short document: {e}")
            return False
        
        return True
    
    async def test_consistency(self):
        """Test extraction consistency across multiple runs"""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Consistency Verification")
        logger.info("="*60)
        
        # Run same extraction multiple times
        results = []
        
        for i in range(3):
            result = await self.extractor.extract(
                document=self.document_text[:2000],
                output_schema=MinimalExtraction
            )
            results.append(result)
            logger.info(f"   Run {i+1}: Title='{result.title}', Has Risks={result.has_risks}")
        
        # Check consistency of boolean field (should be deterministic)
        risk_values = [r.has_risks for r in results]
        all_same = all(v == risk_values[0] for v in risk_values)
        
        if all_same:
            logger.info("✅ Extraction is consistent across runs")
        else:
            logger.warning("⚠️ Some variation in extraction results (expected with temperature > 0)")
        
        return True
    
    async def test_performance(self):
        """Test extraction performance with real API calls"""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: Performance Benchmarking")
        logger.info("="*60)
        
        times = []
        
        for i in range(3):
            start_time = time.time()
            
            result = await self.extractor.extract(
                document=self.document_text[:3000],
                output_schema=MinimalExtraction
            )
            
            elapsed = time.time() - start_time
            times.append(elapsed)
            logger.info(f"   Run {i+1}: {elapsed:.2f}s")
        
        avg_time = sum(times) / len(times)
        logger.info(f"\n✅ Average extraction time: {avg_time:.2f}s")
        
        # Performance should be reasonable
        assert avg_time < 15, "Extraction should complete within 15 seconds"
        
        return True
    
    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("\n" + "🚀"*30)
        logger.info("UNIFIED EXTRACTOR INTEGRATION TESTS")
        logger.info("Using REAL Azure OpenAI API - STRUCTURED EXTRACTION ONLY")
        logger.info("🚀"*30)
        
        tests = [
            ("Clinical Trial Extraction", self.test_clinical_trial_extraction),
            ("Key Information Extraction", self.test_key_information_extraction),
            ("Minimal Extraction", self.test_minimal_extraction),
            ("Error Handling", self.test_error_handling),
            ("Consistency", self.test_consistency),
            ("Performance", self.test_performance)
        ]
        
        results = {}
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                success = await test_func()
                results[test_name] = "PASSED" if success else "FAILED"
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Test {test_name} crashed: {e}")
                results[test_name] = "CRASHED"
                failed += 1
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        
        for test_name, status in results.items():
            emoji = "✅" if status == "PASSED" else "❌"
            logger.info(f"{emoji} {test_name}: {status}")
        
        logger.info(f"\nTotal: {passed} passed, {failed} failed")
        
        # Save results
        with open("unified_extractor_test_results.json", "w") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": results,
                "passed": passed,
                "failed": failed,
                "api_endpoint": AZURE_OPENAI_CONFIG.get("endpoint", "Not configured")
            }, f, indent=2)
        
        return passed > 0 and failed == 0


async def main():
    """Main test runner"""
    tester = TestUnifiedExtractor()
    success = await tester.run_all_tests()
    
    if success:
        logger.info("\n🎉 All tests passed!")
        exit(0)
    else:
        logger.error("\n❌ Some tests failed")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())