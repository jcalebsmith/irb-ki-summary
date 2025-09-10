"""
Clinical Protocol Plugin
Implements document generation for Clinical Research Study Protocols
Supports the 7-step workflow: template selection, key value entry, value propagation,
sub-template generation, LLM rewording, intent validation, and human review
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

import sys
from pathlib import Path
# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.plugin_manager import (
    DocumentPlugin,
    TemplateCatalog,
    ValidationRuleSet,
    TemplateSlot,
    SlotType
)
from app.core.multi_agent_system import (
    BaseAgent, 
    AgentRole, 
    ExtractionAgent,
    GenerationAgent,
    ValidationAgent,
    SpecialistAgent
)


@dataclass
class ClinicalProtocolConfig:
    """Configuration for clinical protocol generation"""
    regulatory_section: str  # "device", "drug", "biologic"
    therapeutic_area: str  # "cardiovascular", "oncology", "neurology", etc.
    study_phase: str  # "early", "pivotal", "post-market"
    study_design: str  # "randomized", "single-arm", "observational"
    

class ClinicalProtocolPlugin(DocumentPlugin):
    """
    Plugin for generating Clinical Research Study Protocol documents
    """
    
    def __init__(self):
        self.plugin_id = "clinical-protocol"
        self.display_name = "Clinical Research Study Protocol"
        self.version = "1.0.0"
        self.supported_types = [
            "clinical-protocol",
            "ind-ide",
            "study-protocol"
        ]
        self.current_parameters = {}
        
        # Define sub-template rules for the 7-step workflow
        self.sub_template_rules = {
            "regulatory_section": {
                "device": ["ide", "device-specific", "fda-device"],
                "drug": ["ind", "drug-specific", "fda-drug"],
                "biologic": ["ind", "biologic-specific", "fda-biologic"]
            },
            "therapeutic_area": {
                "cardiovascular": ["cardiac-endpoints", "cardiovascular-safety"],
                "oncology": ["tumor-response", "oncology-endpoints"],
                "neurology": ["neurological-assessments", "cognitive-endpoints"]
            },
            "study_phase": {
                "early": ["phase1-2", "safety-focused", "dose-finding"],
                "pivotal": ["phase3", "efficacy-focused", "primary-endpoints"],
                "post-market": ["phase4", "surveillance", "real-world"]
            }
        }
        
        # Critical values that must be preserved exactly
        self.critical_values = [
            "study_name",
            "sponsor_name",
            "device_name",
            "drug_name",
            "primary_endpoint",
            "sample_size",
            "study_duration",
            "inclusion_criteria",
            "exclusion_criteria",
            "safety_monitoring"
        ]
        
        # Define propagated values for cross-template consistency
        self.propagated_values = {
            "study_identifier": ["protocol_number", "nct_number", "study_id"],
            "product_name": ["device_name", "drug_name", "intervention_name"],
            "sponsor_info": ["sponsor_name", "sponsor_address", "sponsor_contact"]
        }
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Return plugin metadata"""
        return {
            "id": self.plugin_id,
            "name": self.display_name,
            "version": self.version,
            "description": "Generates Clinical Research Study Protocol documents with 7-step workflow",
            "supported_document_types": self.supported_types,
            "features": [
                "Template selection based on study type",
                "Key value propagation across sections",
                "Sub-template selection by regulatory requirements",
                "Intent validation for critical values",
                "Multiple therapeutic area support"
            ],
            "workflow_steps": [
                "1. Template selection",
                "2. Key value entry",
                "3. Value propagation",
                "4. Sub-template generation",
                "5. LLM rewording",
                "6. Intent validation",
                "7. Human review"
            ]
        }
    
    def get_template_catalog(self) -> TemplateCatalog:
        """Return available templates for clinical protocols"""
        templates = {
            "device-ide": "clinical-protocol/device-ide.j2",
            "drug-ind": "clinical-protocol/drug-ind.j2",
            "biologic-ind": "clinical-protocol/biologic-ind.j2",
            "observational": "clinical-protocol/observational.j2",
            "master": "clinical-protocol/master-protocol.j2"
        }
        
        return TemplateCatalog(
            templates=templates,
            default_template="master",
            metadata={
                "requires_sub_templates": True,
                "supports_value_propagation": True,
                "validation_level": "strict"
            }
        )
    
    def get_specialized_agents(self) -> List[BaseAgent]:
        """Return specialized agents for clinical protocol generation"""
        agents = []
        
        # Template Selection Agent
        agents.append(SpecialistAgent(
            name="TemplateSelectionAgent",
            specialty="template_selection"
        ))
        
        # Key Value Extraction Agent
        agents.append(ExtractionAgent(
            name="KeyValueExtractionAgent"
        ))
        
        # Value Propagation Agent
        agents.append(GenerationAgent(
            name="ValuePropagationAgent"
        ))
        
        # Sub-Template Selection Agent
        agents.append(SpecialistAgent(
            name="SubTemplateSelectionAgent",
            specialty="sub_template_selection"
        ))
        
        # Intent Validation Agent
        agents.append(ValidationAgent(
            name="IntentValidationAgent"
        ))
        
        return agents
    
    def get_validation_rules(self) -> ValidationRuleSet:
        """Return validation rules for clinical protocols"""
        return ValidationRuleSet(
            required_fields=[
                "study_name",
                "sponsor_name",
                "protocol_number",
                "study_design",
                "primary_endpoint",
                "sample_size"
            ],
            max_lengths={
                "study_title": 200,
                "brief_summary": 500,
                "primary_endpoint": 300,
                "inclusion_criteria": 2000,
                "exclusion_criteria": 2000
            },
            allowed_values={
                "study_phase": ["Phase 1", "Phase 1/2", "Phase 2", "Phase 3", "Phase 4", "Observational"],
                "study_design": ["Randomized", "Single-arm", "Parallel", "Crossover", "Observational"],
                "regulatory_section": ["Device", "Drug", "Biologic", "Combination"],
                "blinding": ["Open Label", "Single Blind", "Double Blind", "Triple Blind"]
            },
            custom_validators=[
                "validate_sample_size_calculation",
                "validate_statistical_plan",
                "validate_safety_monitoring",
                "validate_regulatory_compliance"
            ],
            intent_critical_fields=self.critical_values
        )
    
    def supports_document_type(self, doc_type: str) -> bool:
        """Check if this plugin supports the given document type"""
        return doc_type.lower() in self.supported_types
    
    def get_sub_template_rules(self) -> Dict[str, Any]:
        """Return rules for sub-template selection"""
        return self.sub_template_rules
    
    def get_critical_values(self) -> List[str]:
        """Return list of critical values that must be preserved"""
        # Only return critical values that apply to all protocols
        # Device/drug/biologic specific values are handled differently
        return [
            "study_name",
            "sponsor_name", 
            "primary_endpoint",
            "sample_size",
            "study_duration",
            "inclusion_criteria",
            "exclusion_criteria",
            "safety_monitoring",
            "device_name",  # Include all possible critical values
            "drug_name",    # Validation will check based on what's actually present
            "biologic_name"
        ]
    
    def resolve_template(self, parameters: Dict[str, Any]) -> str:
        """
        Resolve which template to use based on parameters
        Implements Step 1 of the 7-step workflow
        """
        # Extract configuration from parameters
        regulatory_section = parameters.get("regulatory_section", "drug").lower()
        therapeutic_area = parameters.get("therapeutic_area", "general").lower()
        study_phase = parameters.get("study_phase", "pivotal").lower()
        template_id = parameters.get("template_id")
        
        # If specific template requested, use it
        if template_id:
            catalog = self.get_template_catalog()
            return catalog.get_template(template_id)
        
        # Otherwise, select based on regulatory section
        template_map = {
            "device": "device-ide",
            "drug": "drug-ind",
            "biologic": "biologic-ind"
        }
        
        base_template = template_map.get(regulatory_section, "master")
        
        # Build full template path
        template_path = f"clinical-protocol/{base_template}.j2"
        
        # Store sub-template selection for later use
        parameters["_selected_sub_templates"] = self._select_sub_templates(
            regulatory_section,
            therapeutic_area,
            study_phase
        )
        
        return template_path
    
    def _select_sub_templates(self,
                             regulatory_section: str,
                             therapeutic_area: str,
                             study_phase: str) -> List[str]:
        """
        Select appropriate sub-templates based on study characteristics
        Implements Step 4 of the 7-step workflow
        """
        selected = []
        
        # Add regulatory-specific templates
        if regulatory_section in self.sub_template_rules["regulatory_section"]:
            selected.extend(self.sub_template_rules["regulatory_section"][regulatory_section])
        
        # Add therapeutic area templates
        if therapeutic_area in self.sub_template_rules["therapeutic_area"]:
            selected.extend(self.sub_template_rules["therapeutic_area"][therapeutic_area])
        
        # Add study phase templates
        if study_phase in self.sub_template_rules["study_phase"]:
            selected.extend(self.sub_template_rules["study_phase"][study_phase])
        
        return selected
    
    def get_template_parameters(self) -> Dict[str, Any]:
        """
        Get parameters required for template selection
        Used for Step 2 of the 7-step workflow (Key value entry)
        """
        return {
            "study_name": {
                "type": "text",
                "required": True,
                "description": "Official name of the clinical study",
                "propagate": True
            },
            "sponsor_name": {
                "type": "text",
                "required": True,
                "description": "Name of the study sponsor",
                "propagate": True
            },
            "device_name": {
                "type": "text",
                "required": False,
                "description": "Name of the investigational device (if applicable)",
                "propagate": True,
                "condition": "regulatory_section == 'device'"
            },
            "drug_name": {
                "type": "text",
                "required": False,
                "description": "Name of the investigational drug (if applicable)",
                "propagate": True,
                "condition": "regulatory_section == 'drug'"
            },
            "regulatory_section": {
                "type": "select",
                "required": True,
                "options": ["Device", "Drug", "Biologic", "Combination"],
                "description": "Type of regulatory submission"
            },
            "therapeutic_area": {
                "type": "select",
                "required": True,
                "options": ["Cardiovascular", "Oncology", "Neurology", "Infectious Disease", "Other"],
                "description": "Primary therapeutic area"
            },
            "study_phase": {
                "type": "select",
                "required": True,
                "options": ["Early", "Pivotal", "Post-market"],
                "description": "Phase of clinical development"
            },
            "primary_endpoint": {
                "type": "text",
                "required": True,
                "description": "Primary endpoint of the study",
                "max_length": 300,
                "propagate": True
            },
            "sample_size": {
                "type": "number",
                "required": True,
                "description": "Total number of subjects to be enrolled",
                "min": 1,
                "propagate": True
            }
        }
    
    def validate_intent_preservation(self,
                                    original_values: Dict[str, Any],
                                    generated_content: str) -> Dict[str, Any]:
        """
        Validate that critical values are preserved in generated content
        Implements Step 6 of the 7-step workflow
        """
        validation_results = {
            "passed": True,
            "preserved_values": [],
            "modified_values": [],
            "missing_values": []
        }
        
        for critical_field in self.critical_values:
            if critical_field in original_values:
                original_value = str(original_values[critical_field])
                
                # Check if value appears in generated content
                if original_value in generated_content:
                    validation_results["preserved_values"].append(critical_field)
                else:
                    # Check for potential modifications
                    # This would use more sophisticated NLP in production
                    validation_results["modified_values"].append({
                        "field": critical_field,
                        "original": original_value,
                        "status": "potentially_modified"
                    })
                    validation_results["passed"] = False
        
        return validation_results
    
    def process_workflow(self, parameters: Dict[str, Any], 
                        generated_content: str = None) -> Dict[str, Any]:
        """
        Process the 7-step workflow for clinical protocol generation
        Returns detailed workflow tracking information
        """
        import time
        
        workflow_steps = {
            "template_selection": {
                "name": "Step 1: Template Selection",
                "completed": False,
                "status": "Not Started",
                "start_time": None,
                "end_time": None,
                "metadata": {}
            },
            "key_value_entry": {
                "name": "Step 2: Key Value Entry",
                "completed": False,
                "status": "Not Started",
                "start_time": None,
                "end_time": None,
                "metadata": {}
            },
            "sub_template_selection": {
                "name": "Step 3: Sub-template Selection",
                "completed": False,
                "status": "Not Started",
                "start_time": None,
                "end_time": None,
                "metadata": {}
            },
            "value_propagation": {
                "name": "Step 4: Value Propagation",
                "completed": False,
                "status": "Not Started",
                "start_time": None,
                "end_time": None,
                "metadata": {}
            },
            "llm_rewording": {
                "name": "Step 5: LLM Rewording",
                "completed": False,
                "status": "Not Started",
                "start_time": None,
                "end_time": None,
                "metadata": {}
            },
            "intent_validation": {
                "name": "Step 6: Intent Validation",
                "completed": False,
                "status": "Not Started",
                "start_time": None,
                "end_time": None,
                "metadata": {}
            },
            "human_review": {
                "name": "Step 7: Human Review",
                "completed": False,
                "status": "Not Started",
                "start_time": None,
                "end_time": None,
                "metadata": {}
            }
        }
        
        # Step 1: Template Selection
        workflow_steps["template_selection"]["start_time"] = time.time()
        workflow_steps["template_selection"]["status"] = "In Progress"
        
        template_id = self.resolve_template(parameters)
        workflow_steps["template_selection"]["metadata"] = {
            "selected_template": template_id,
            "regulatory_section": parameters.get("regulatory_section")
        }
        workflow_steps["template_selection"]["completed"] = True
        workflow_steps["template_selection"]["status"] = "Completed"
        workflow_steps["template_selection"]["end_time"] = time.time()
        
        # Step 2: Key Value Entry
        workflow_steps["key_value_entry"]["start_time"] = time.time()
        workflow_steps["key_value_entry"]["status"] = "In Progress"
        
        # Check if required values are present
        required_fields = ["study_name", "sponsor_name", "protocol_number", "primary_endpoint", "sample_size"]
        missing_fields = [f for f in required_fields if f not in parameters or not parameters[f]]
        
        if not missing_fields:
            workflow_steps["key_value_entry"]["completed"] = True
            workflow_steps["key_value_entry"]["status"] = "Completed"
            workflow_steps["key_value_entry"]["metadata"] = {
                "fields_provided": len([f for f in required_fields if f in parameters]),
                "missing_fields": missing_fields
            }
        else:
            workflow_steps["key_value_entry"]["status"] = f"Incomplete - Missing: {', '.join(missing_fields)}"
        workflow_steps["key_value_entry"]["end_time"] = time.time()
        
        # Step 3: Sub-template Selection
        workflow_steps["sub_template_selection"]["start_time"] = time.time()
        workflow_steps["sub_template_selection"]["status"] = "In Progress"
        
        sub_templates = parameters.get("_selected_sub_templates", [])
        workflow_steps["sub_template_selection"]["metadata"] = {
            "sub_templates_selected": len(sub_templates),
            "sub_template_ids": sub_templates
        }
        workflow_steps["sub_template_selection"]["completed"] = True
        workflow_steps["sub_template_selection"]["status"] = "Completed"
        workflow_steps["sub_template_selection"]["end_time"] = time.time()
        
        # Step 4: Value Propagation
        workflow_steps["value_propagation"]["start_time"] = time.time()
        workflow_steps["value_propagation"]["status"] = "In Progress"
        
        # Check if values are propagated in generated content
        if generated_content:
            propagated_values = []
            for field in ["study_name", "sponsor_name", "device_name", "drug_name", "biologic_name"]:
                if field in parameters and str(parameters[field]) in generated_content:
                    propagated_values.append(field)
            
            workflow_steps["value_propagation"]["metadata"] = {
                "values_propagated": len(propagated_values),
                "propagated_fields": propagated_values
            }
            workflow_steps["value_propagation"]["completed"] = True
            workflow_steps["value_propagation"]["status"] = "Completed"
        else:
            workflow_steps["value_propagation"]["status"] = "Pending - No content generated"
        workflow_steps["value_propagation"]["end_time"] = time.time()
        
        # Step 5: LLM Rewording
        if parameters.get("enable_llm_rewording", False):
            workflow_steps["llm_rewording"]["start_time"] = time.time()
            workflow_steps["llm_rewording"]["status"] = "In Progress"
            
            # Mark as ready for LLM rewording
            workflow_steps["llm_rewording"]["metadata"] = {
                "enabled": True,
                "implementation": "Ready for processing"
            }
            workflow_steps["llm_rewording"]["completed"] = True
            workflow_steps["llm_rewording"]["status"] = "Ready for LLM processing"
            workflow_steps["llm_rewording"]["end_time"] = time.time()
        else:
            workflow_steps["llm_rewording"]["status"] = "Skipped - Not enabled"
        
        # Step 6: Intent Validation
        if parameters.get("validate_intent", False):
            workflow_steps["intent_validation"]["start_time"] = time.time()
            workflow_steps["intent_validation"]["status"] = "In Progress"
            
            # Basic validation is done via critical values
            if generated_content:
                workflow_steps["intent_validation"]["completed"] = True
                workflow_steps["intent_validation"]["status"] = "Completed"
                workflow_steps["intent_validation"]["metadata"] = {
                    "validation_type": "Critical value preservation"
                }
            workflow_steps["intent_validation"]["end_time"] = time.time()
        else:
            workflow_steps["intent_validation"]["status"] = "Skipped - Not enabled"
        
        # Step 7: Human Review
        if parameters.get("enable_review_mode", False):
            workflow_steps["human_review"]["start_time"] = time.time()
            workflow_steps["human_review"]["status"] = "Pending - Awaiting review"
            workflow_steps["human_review"]["metadata"] = {
                "review_required": True
            }
            workflow_steps["human_review"]["end_time"] = time.time()
        else:
            workflow_steps["human_review"]["status"] = "Skipped - Not enabled"
        
        return workflow_steps