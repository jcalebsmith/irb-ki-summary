#!/usr/bin/env python3
"""
Test script for Clinical Research Study Protocol Text Generation workflow
Tests the 7-step workflow: template selection, key value entry, value propagation,
sub-template generation, LLM rewording, intent validation, and human review
"""

import sys
import json
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List
import hashlib
import time

# Set up logging for test output
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))
sys.path.append(str(Path(__file__).parent))

# Import configuration and test utilities
from config import TEST_CONFIG, get_test_pdf_path
from tests.test_utils import (
    setup_azure_openai, 
    convert_numpy_types,
    calculate_content_hash,
    display_validation_metrics,
    save_test_results
)

from core.document_framework import DocumentGenerationFramework, EnhancedValidationOrchestrator
from plugins.clinical_protocol_plugin import ClinicalProtocolPlugin
from pdf import read_pdf
from llama_index.core.schema import Document

# Set up Azure OpenAI models
embed_model, llm = setup_azure_openai()


def display_protocol(final_responses: Dict[str, str], validation_results: Dict[str, Any] = None):
    """Display the generated protocol with formatting"""
    logger.info("\n" + "="*80)
    logger.info("CLINICAL RESEARCH STUDY PROTOCOL (7-Step Workflow)")
    logger.info("="*80)
    
    # Display validation results if available
    if validation_results:
        logger.info("\n" + "-"*40)
        logger.info("VALIDATION METRICS:")
        logger.info("-"*40)
        
        if "consistency_metrics" in validation_results:
            metrics = validation_results["consistency_metrics"]
            if "coefficient_of_variation" in metrics:
                cv = metrics["coefficient_of_variation"]
                target_met = "✓" if cv < 15.0 else "✗"
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
        
        # Display workflow step results
        if "workflow_steps" in validation_results:
            logger.info(f"\n" + "-"*40)
            logger.info("7-STEP WORKFLOW STATUS:")
            logger.info("-"*40)
            steps = validation_results["workflow_steps"]
            for step_name, step_status in steps.items():
                status_icon = "✓" if step_status.get("completed", False) else "⚠"
                logger.info(f"{status_icon} {step_name}: {step_status.get('status', 'Not Started')}")
        
        # Display any issues or warnings
        if validation_results.get("issues"):
            logger.warning(f"\n⚠️  Issues Found: {len(validation_results['issues'])}")
            for issue in validation_results["issues"][:3]:  # Show first 3 issues
                logger.warning(f"   - {issue}")
        
        if validation_results.get("warnings"):
            logger.warning(f"\n⚠️  Warnings: {len(validation_results['warnings'])}")
            for warning in validation_results["warnings"][:3]:  # Show first 3 warnings
                logger.warning(f"   - {warning}")
    
    # Display the actual protocol content
    logger.info(f"\n{'-'*40}")
    logger.info("GENERATED PROTOCOL:")
    logger.info(f"{'-'*40}")
    
    # Parse sections if they exist
    if isinstance(final_responses, dict):
        for section_name, content in final_responses.items():
            logger.info(f"\n### {section_name} ###")
            logger.info(content[:500] + "..." if len(content) > 500 else content)
    else:
        logger.info(final_responses[:2000] + "..." if len(final_responses) > 2000 else final_responses)
    
    logger.info("\n" + "="*80)


async def test_clinical_protocol(pdf_path: Path, config: Dict[str, str]) -> Dict[str, Any]:
    """
    Test clinical protocol generation using the 7-step workflow
    
    Args:
        pdf_path: Path to the PDF file (source protocol or regulatory document)
        config: Configuration for protocol generation including:
            - regulatory_section: "device", "drug", or "biologic"
            - therapeutic_area: "cardiovascular", "oncology", "neurology", etc.
            - study_phase: "early", "pivotal", or "post-market"
            - study_design: "randomized", "single-arm", "observational"
    
    Returns:
        Dictionary containing the generated protocol and metrics
    """
    # Initialize the framework with Azure OpenAI models
    framework = DocumentGenerationFramework(
        plugin_dir="app/plugins",
        template_dir="app/templates",
        embed_model=embed_model,
        llm=llm
    )
    
    # Register the clinical protocol plugin
    framework.plugin_manager.register_plugin(
        "clinical-protocol",
        ClinicalProtocolPlugin
    )
    
    # Read PDF and create document
    pdf_data = read_pdf(pdf_path)
    
    # Create a Document object for LlamaIndex
    full_text = "\n".join(pdf_data.texts)
    document = Document(text=full_text, metadata={"source": str(pdf_path)})
    
    # Prepare parameters for generation with 7-step workflow configuration
    parameters = {
        "document_context": full_text,
        "pdf_path": str(pdf_path),
        
        # Required fields for validation
        "study_name": "Test Clinical Study for " + config.get("regulatory_section", "Device"),
        "sponsor_name": "Test Sponsor Corporation",
        "protocol_number": "TEST-001-2024",
        "primary_endpoint": "Primary efficacy endpoint at 12 months",
        "sample_size": "100",
        
        # Step 1: Template Selection parameters
        "regulatory_section": config.get("regulatory_section", "Device"),
        "therapeutic_area": config.get("therapeutic_area", "cardiovascular"),
        "study_phase": config.get("study_phase", "Phase 3"),
        "study_design": config.get("study_design", "Randomized"),
        
        # Additional template variables
        "inclusion_criteria": "Adults aged 18-75 with confirmed diagnosis",
        "exclusion_criteria": "Pregnant women, severe comorbidities",
    }
    
    # Add product-specific field based on regulatory section
    regulatory_section = config.get("regulatory_section", "Device").lower()
    if regulatory_section == "device":
        parameters["device_name"] = "Test Medical Device"
    elif regulatory_section == "drug":
        parameters["drug_name"] = "Test Drug Compound"
    elif regulatory_section == "biologic":
        parameters["biologic_name"] = "Test Biologic Product"
    
    # Continue with remaining parameters
    parameters.update({
        # Step 2: Key Value Entry (will be extracted from document)
        "extract_key_values": True,
        
        # Step 3: Value Propagation
        "propagate_values": True,
        
        # Step 4: Sub-template Generation
        "generate_sub_templates": True,
        
        # Step 5: LLM Rewording
        "enable_llm_rewording": True,
        
        # Step 6: Intent Validation
        "validate_intent": True,
        
        # Step 7: Human Review (simulated)
        "enable_review_mode": False,  # Set to True for interactive review
        
        # Additional workflow parameters
        "preserve_critical_values": True,
        "consistency_check": True,
    })
    
    # Generate protocol using the plugin
    logger.info("Generating clinical protocol using 7-step workflow...")
    logger.info(f"Configuration: {json.dumps(config, indent=2)}")
    
    result = await framework.generate(
        document_type="clinical-protocol",
        parameters=parameters,
        document=document
    )
    
    return {
        "success": result.success,
        "content": result.content,
        "validation_results": result.validation_results,
        "metadata": result.metadata,
        "error_message": result.error_message,
        "workflow_steps": result.metadata.get("workflow_steps", {}) if result.metadata else {}
    }


async def test_workflow_consistency(pdf_path: Path, config: Dict[str, str], num_runs: int = 3) -> Dict[str, Any]:
    """
    Test consistency of the 7-step workflow by running it multiple times
    
    Args:
        pdf_path: Path to the PDF file
        config: Configuration for protocol generation
        num_runs: Number of times to run the generation
    
    Returns:
        Dictionary containing consistency metrics
    """
    logger.info(f"\nTesting 7-step workflow consistency with {num_runs} runs...")
    
    # Initialize orchestrator to track metrics
    orchestrator = EnhancedValidationOrchestrator()
    
    results = []
    hashes = []
    word_counts = []
    workflow_completions = []
    
    for i in range(num_runs):
        logger.info(f"Run {i+1}/{num_runs}...")
        
        result = await test_clinical_protocol(pdf_path, config)
        
        if result["success"]:
            content = result["content"]
            results.append(content)
            
            # Calculate metrics
            content_hash = calculate_content_hash(content)
            hashes.append(content_hash)
            
            word_count = len(content.split())
            word_counts.append(word_count)
            
            # Track workflow completion
            workflow_steps = result.get("workflow_steps", {})
            completion_rate = sum(1 for step in workflow_steps.values() if step.get("completed", False)) / 7
            workflow_completions.append(completion_rate)
            
            # Track in orchestrator
            # Consistency metrics are tracked automatically during validation
            orchestrator.consistency_tracker.track(content, "clinical-protocol")
        else:
            logger.warning(f"Run {i+1} failed: {result.get('error_message', 'Unknown error')}")
    
    # Get consistency report
    report = orchestrator.get_consistency_report("clinical-protocol")
    
    # Calculate additional metrics
    unique_outputs = len(set(hashes))
    consistency_rate = 1.0 - (unique_outputs - 1) / len(hashes) if len(hashes) > 1 else 1.0
    avg_workflow_completion = sum(workflow_completions) / len(workflow_completions) if workflow_completions else 0
    
    logger.info("\n" + "="*80)
    logger.info("7-STEP WORKFLOW CONSISTENCY TEST RESULTS:")
    logger.info("="*80)
    logger.info(f"Total Runs: {num_runs}")
    logger.info(f"Successful Runs: {len(results)}")
    logger.info(f"Unique Outputs: {unique_outputs}")
    logger.info(f"Consistency Rate: {consistency_rate:.2%}")
    logger.info(f"Average Workflow Completion: {avg_workflow_completion:.2%}")
    
    if "by_document_type" in report and "clinical-protocol" in report["by_document_type"]:
        metrics = report["by_document_type"]["clinical-protocol"]
        
        cv = metrics.get("cv", 0)
        target_met = "✓ PASS" if cv < 15.0 else "✗ FAIL"
        logger.info(f"Coefficient of Variation: {cv:.2f}% {target_met}")
        
        logger.info(f"Mean Word Count: {metrics.get('mean_word_count', 0):.0f}")
        logger.info(f"Structural Consistency: {metrics.get('structural_consistency', 0):.2%}")
    
    logger.info("="*80)
    
    return {
        "num_runs": num_runs,
        "successful_runs": len(results),
        "unique_outputs": unique_outputs,
        "consistency_rate": consistency_rate,
        "avg_workflow_completion": avg_workflow_completion,
        "report": report,
        "hashes": hashes,
        "word_counts": word_counts,
        "workflow_completions": workflow_completions
    }


async def test_different_configurations(pdf_path: Path) -> None:
    """
    Test the 7-step workflow with different configuration combinations
    
    Args:
        pdf_path: Path to the PDF file
    """
    logger.info("\n" + "="*80)
    logger.info("TESTING DIFFERENT PROTOCOL CONFIGURATIONS")
    logger.info("="*80)
    
    # Define test configurations
    test_configs = [
        {
            "name": "Device IDE - Cardiovascular - Pivotal",
            "config": {
                "regulatory_section": "Device",
                "therapeutic_area": "cardiovascular",
                "study_phase": "Phase 3",
                "study_design": "Randomized"
            }
        },
        {
            "name": "Drug IND - Oncology - Early Phase",
            "config": {
                "regulatory_section": "Drug",
                "therapeutic_area": "oncology",
                "study_phase": "Phase 1",
                "study_design": "Single-arm"
            }
        },
        {
            "name": "Biologic IND - Neurology - Post-Market",
            "config": {
                "regulatory_section": "Biologic",
                "therapeutic_area": "neurology",
                "study_phase": "Phase 4",
                "study_design": "Observational"
            }
        }
    ]
    
    results_summary = []
    
    for test_case in test_configs:
        logger.info(f"\n### Testing: {test_case['name']} ###")
        logger.info("-" * 60)
        
        try:
            result = await test_clinical_protocol(pdf_path, test_case["config"])
            
            if result["success"]:
                word_count = len(result["content"].split())
                workflow_steps = result.get("workflow_steps", {})
                completion_rate = sum(1 for step in workflow_steps.values() if step.get("completed", False)) / 7
                
                results_summary.append({
                    "configuration": test_case["name"],
                    "success": True,
                    "word_count": word_count,
                    "workflow_completion": completion_rate,
                    "validation_passed": result.get("validation_results", {}).get("valid", False)
                })
                
                logger.info(f"✓ Success - Word Count: {word_count}, Workflow Completion: {completion_rate:.0%}")
            else:
                results_summary.append({
                    "configuration": test_case["name"],
                    "success": False,
                    "error": result.get("error_message", "Unknown error")
                })
                logger.error(f"✗ Failed: {result.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            results_summary.append({
                "configuration": test_case["name"],
                "success": False,
                "error": str(e)
            })
            logger.error(f"✗ Exception: {e}")
    
    # Display summary
    logger.info("\n" + "="*80)
    logger.info("CONFIGURATION TEST SUMMARY:")
    logger.info("="*80)
    
    success_count = sum(1 for r in results_summary if r.get("success", False))
    logger.info(f"Successful Configurations: {success_count}/{len(test_configs)}")
    
    for result in results_summary:
        status = "✓" if result.get("success", False) else "✗"
        logger.info(f"{status} {result['configuration']}")
        if result.get("success"):
            logger.info(f"   - Word Count: {result.get('word_count', 'N/A')}")
            logger.info(f"   - Workflow Completion: {result.get('workflow_completion', 0):.0%}")
        else:
            logger.info(f"   - Error: {result.get('error', 'Unknown')}")


async def main():
    """Main test function"""
    pdf_path = get_test_pdf_path()
    
    if not pdf_path.exists():
        logger.error(f"PDF file not found at {pdf_path}")
        sys.exit(1)
    
    logger.info(f"Processing PDF: {pdf_path}")
    logger.info(f"Using Clinical Protocol Plugin with 7-Step Workflow")
    logger.info("="*80)
    
    try:
        # Test 1: Single run with device IDE configuration
        logger.info("\n### TEST 1: Single Protocol Generation (Device IDE) ###")
        start_time = time.time()
        
        config = {
            "regulatory_section": "Device",
            "therapeutic_area": "cardiovascular",
            "study_phase": "Phase 3",
            "study_design": "Randomized"
        }
        
        result = await test_clinical_protocol(pdf_path, config)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Generation completed in {elapsed_time:.2f} seconds")
        
        if result["success"]:
            # Display the protocol with validation results
            display_protocol(result["content"], result["validation_results"])
            
            # Save output
            output_file = "clinical_protocol_output.json"
            with open(output_file, 'w') as f:
                json.dump({
                    "content": result["content"],
                    "validation_results": result["validation_results"],
                    "metadata": result["metadata"],
                    "workflow_steps": result.get("workflow_steps", {})
                }, f, indent=2)
            
            logger.info(f"\nProtocol saved to: {output_file}")
        else:
            error_msg = result.get('error_message', 'Unknown error')
            logger.error(f"Generation failed: {error_msg}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Consistency testing
        logger.info("\n### TEST 2: 7-Step Workflow Consistency Testing ###")
        consistency_results = await test_workflow_consistency(pdf_path, config, num_runs=3)
        
        # Save consistency report
        consistency_file = "clinical_protocol_consistency_report.json"
        save_test_results(consistency_results, consistency_file)
        
        # Test 3: Different configurations
        logger.info("\n### TEST 3: Testing Different Protocol Configurations ###")
        await test_different_configurations(pdf_path)
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY:")
        logger.info("="*80)
        
        if result["success"]:
            logger.info("✓ Single generation: SUCCESS")
        else:
            logger.error("✗ Single generation: FAILED")
        
        if consistency_results["consistency_rate"] > 0.8:
            logger.info(f"✓ Consistency test: PASS ({consistency_results['consistency_rate']:.2%})")
        else:
            logger.error(f"✗ Consistency test: FAIL ({consistency_results['consistency_rate']:.2%})")
        
        avg_workflow = consistency_results.get("avg_workflow_completion", 0)
        if avg_workflow > 0.85:
            logger.info(f"✓ Workflow completion: PASS ({avg_workflow:.0%})")
        else:
            logger.warning(f"✗ Workflow completion: NEEDS IMPROVEMENT ({avg_workflow:.0%})")
        
        cv_achieved = False
        if "report" in consistency_results:
            report = consistency_results["report"]
            if "by_document_type" in report and "clinical-protocol" in report["by_document_type"]:
                cv = report["by_document_type"]["clinical-protocol"].get("cv", 100)
                cv_achieved = cv < 15.0
        
        if cv_achieved:
            logger.info(f"✓ CV Target (<15%): ACHIEVED")
        else:
            logger.warning(f"✗ CV Target (<15%): NOT ACHIEVED")
        
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())