#!/usr/bin/env python3
"""
Test script for Key Information Summary generation using new plugin-based architecture
"""

import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
import time

# Set up logging for test output
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add app directory and repo root to path
ROOT_DIR = Path(__file__).parent
APP_DIR = ROOT_DIR / "app"
sys.path.append(str(APP_DIR))
sys.path.append(str(ROOT_DIR))

# Import configuration and test utilities
from config import TEST_CONFIG, get_test_pdf_path
from tests.test_utils import (
    setup_azure_openai,
    calculate_content_hash,
    save_test_results,
)

from core.document_framework import DocumentGenerationFramework, EnhancedValidationOrchestrator
from plugins.informed_consent_plugin import InformedConsentPlugin
from pdf import read_pdf
from llama_index.core.schema import Document

# Set up Azure OpenAI models
embed_model, llm = setup_azure_openai()


def display_summary(final_responses: Dict[str, str], validation_results: Dict[str, Any] = None):
    """Display the generated summary with formatting"""
    logger.info("\n" + "=" * 80)
    logger.info("IRB KEY INFORMATION SUMMARY (Enhanced Plugin Architecture)")
    logger.info("=" * 80)

    # Display validation results if available
    if validation_results:
        logger.info("\n" + "-" * 40)
        logger.info("CONSISTENCY METRICS:")
        logger.info("-" * 40)

        if "consistency_metrics" in validation_results:
            metrics = validation_results["consistency_metrics"]
            if "coefficient_of_variation" in metrics:
                cv = metrics["coefficient_of_variation"]
                target_met = "[OK]" if cv < 15.0 else "[WARN]"
                logger.info(f"Coefficient of Variation: {cv:.2f}% {target_met}")

            if "structural_consistency" in metrics:
                logger.info(f"Structural Consistency: {metrics['structural_consistency']:.2%}")

            if "mean_word_count" in metrics:
                logger.info(f"Average Word Count: {metrics['mean_word_count']:.0f}")

        if "content_analysis" in validation_results:
            analysis = validation_results["content_analysis"]
            if "critical_value_preservation" in analysis:
                preservation = analysis["critical_value_preservation"]
                logger.info(f"Critical Value Preservation: {preservation:.0%}")

            if "word_count" in analysis:
                logger.info(f"Total Word Count: {analysis['word_count']}")

        # Display any issues or warnings
        if validation_results.get("issues"):
            logger.warning(f"\nIssues Found: {len(validation_results['issues'])}")
            for issue in validation_results["issues"][:3]:  # Show first 3 issues
                logger.warning(f"   - {issue}")

        if validation_results.get("warnings"):
            logger.warning(f"\nWarnings: {len(validation_results['warnings'])}")
            for warning in validation_results["warnings"][:3]:  # Show first 3 warnings
                logger.warning(f"   - {warning}")

    # Display the actual summary content
    sections = {}
    for key, value in final_responses.items():
        if key.startswith("section"):
            section_num = key.replace("section", "")
            sections[f"Section {section_num}"] = value
        elif key == "Total Summary":
            sections["Complete Summary"] = value

    for section_name in sorted(sections.keys()):
        logger.info(f"\n{'-' * 40}")
        logger.info(f"{section_name}:")
        logger.info(f"{'-' * 40}")
        logger.info(sections[section_name])

    logger.info("\n" + "=" * 80)


async def test_with_plugin(pdf_path: Path) -> Dict[str, Any]:
    """
    Test summary generation using the new enhanced plugin architecture

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary containing the generated summary and metrics
    """
    # Initialize the framework with Azure OpenAI models
    framework = DocumentGenerationFramework(
        plugin_dir="app/plugins",
        template_dir="app/templates",
        embed_model=embed_model,
        llm=llm,
    )

    # Register the enhanced plugin (pass class, not instance)
    framework.plugin_manager.register_plugin(
        "informed-consent-ki",
        InformedConsentPlugin,
    )

    # Read PDF and create document
    pdf_data = read_pdf(pdf_path)

    # Create a Document object for LlamaIndex
    full_text = "\n".join(pdf_data.texts)
    document = Document(text=full_text, metadata={"source": str(pdf_path)})

    # Prepare parameters for generation
    parameters = {
        "document_context": full_text,
        "pdf_path": str(pdf_path),
        "generate_ki_summary": True,
    }

    # Generate summary using the plugin
    logger.info("Generating summary using enhanced plugin architecture...")
    result = await framework.generate(
        document_type="informed-consent",
        parameters=parameters,
        document=document,
    )

    return {
        "success": result.success,
        "content": result.content,
        "validation_results": result.validation_results,
        "metadata": result.metadata,
        "error_message": result.error_message,
    }


async def test_consistency(pdf_path: Path, num_runs: int = 3) -> Dict[str, Any]:
    """
    Test consistency by running the generation multiple times

    Args:
        pdf_path: Path to the PDF file
        num_runs: Number of times to run the generation

    Returns:
        Dictionary containing consistency metrics
    """
    logger.info(f"\nTesting consistency with {num_runs} runs...")

    # Initialize orchestrator to track metrics
    orchestrator = EnhancedValidationOrchestrator()

    results = []
    hashes = []
    word_counts = []

    for i in range(num_runs):
        logger.info(f"Run {i+1}/{num_runs}...")

        result = await test_with_plugin(pdf_path)

        if result["success"]:
            content = result["content"]
            results.append(content)

            # Calculate metrics
            content_hash = calculate_content_hash(content)
            hashes.append(content_hash)

            word_count = len(content.split())
            word_counts.append(word_count)

            # Track in orchestrator
            orchestrator._track_consistency_metrics(content, "informed-consent")
        else:
            logger.warning(f"Run {i+1} failed")

    # Get consistency report
    report = orchestrator.get_consistency_report("informed-consent")

    # Calculate additional metrics
    unique_outputs = len(set(hashes))
    consistency_rate = 1.0 - (unique_outputs - 1) / len(hashes) if len(hashes) > 1 else 1.0

    logger.info("\n" + "=" * 80)
    logger.info("CONSISTENCY TEST RESULTS:")
    logger.info("=" * 80)
    logger.info(f"Total Runs: {num_runs}")
    logger.info(f"Successful Runs: {len(results)}")
    logger.info(f"Unique Outputs: {unique_outputs}")
    logger.info(f"Consistency Rate: {consistency_rate:.2%}")

    if "by_document_type" in report and "informed-consent" in report["by_document_type"]:
        metrics = report["by_document_type"]["informed-consent"]

        cv = metrics.get("cv", 0)
        target_met = "PASS" if cv < 15.0 else "FAIL"
        logger.info(f"Coefficient of Variation: {cv:.2f}% ({target_met})")

        logger.info(f"Mean Word Count: {metrics.get('mean_word_count', 0):.0f}")
        logger.info(f"Structural Consistency: {metrics.get('structural_consistency', 0):.2%}")

    logger.info("=" * 80)

    return {
        "num_runs": num_runs,
        "successful_runs": len(results),
        "unique_outputs": unique_outputs,
        "consistency_rate": consistency_rate,
        "report": report,
        "hashes": hashes,
        "word_counts": word_counts,
    }


async def main():
    """Main test function"""
    pdf_path = get_test_pdf_path()

    if not pdf_path.exists():
        logger.error(f"PDF file not found at {pdf_path}")
        sys.exit(1)

    logger.info(f"Processing PDF: {pdf_path}")
    logger.info("Using Enhanced Plugin Architecture with Consistency Improvements")
    logger.info("=" * 80)

    try:
        # Test 1: Single run with full display
        logger.info("\n### TEST 1: Single Generation with Validation ###")
        start_time = time.time()

        result = await test_with_plugin(pdf_path)

        elapsed_time = time.time() - start_time
        logger.info(f"Generation completed in {elapsed_time:.2f} seconds")

        if result["success"]:
            # Parse the content into sections
            content = result["content"]
            sections = {}

            # Parse sections by regex to strip numeric headers from content
            import re
            pattern = re.compile(r"^Section\s+(\d+)\s*\n([\s\S]*?)(?=^Section\s+\d+|\Z)", re.MULTILINE)
            for match in pattern.finditer(content):
                idx = match.group(1)
                body = match.group(2).strip()
                sections[f"section{idx}"] = body

            sections["Total Summary"] = content

            # Display the summary with validation results
            display_summary(sections, result["validation_results"])

            # Save output
            output_file = "ki_summary_enhanced_output.json"
            with open(output_file, 'w') as f:
                json.dump({
                    "sections": sections,
                    "validation_results": result["validation_results"],
                    "metadata": result["metadata"],
                }, f, indent=2)

            logger.info(f"\nSummary saved to: {output_file}")
        else:
            error_msg = result.get('error_message', 'Unknown error')
            logger.error(f"Generation failed: {error_msg}")
            if error_msg != 'Unknown error':
                logger.error(f"Error details: {error_msg}")
            # Add full traceback
            import traceback
            traceback.print_exc()

        # Test 2: Consistency testing
        logger.info("\n### TEST 2: Consistency Testing ###")
        consistency_results = await test_consistency(pdf_path, num_runs=3)

        # Save consistency report
        consistency_file = "ki_summary_consistency_report.json"
        save_test_results(consistency_results, consistency_file)

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY:")
        logger.info("=" * 80)

        if result["success"]:
            logger.info("[OK] Single generation: SUCCESS")
        else:
            logger.error("[FAIL] Single generation: FAILED")

        if consistency_results["consistency_rate"] > 0.8:
            logger.info(f"[OK] Consistency test: PASS ({consistency_results['consistency_rate']:.2%})")
        else:
            logger.error(f"[FAIL] Consistency test: FAIL ({consistency_results['consistency_rate']:.2%})")

        cv_achieved = False
        if "report" in consistency_results:
            report = consistency_results["report"]
            if "by_document_type" in report and "informed-consent" in report["by_document_type"]:
                cv = report["by_document_type"]["informed-consent"].get("cv", 100)
                cv_achieved = cv < 15.0

        if cv_achieved:
            logger.info("[OK] CV Target (<15%): ACHIEVED")
        else:
            logger.warning("[WARN] CV Target (<15%): NOT ACHIEVED")

        print("=" * 80)

    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
