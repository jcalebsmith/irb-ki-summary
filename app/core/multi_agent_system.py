"""
Multi-Agent System for Document Generation
Implements specialized agents with orchestration and validation
"""
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import json
import re
from .exceptions import AgentError, AgentCommunicationError, LLMError
from .agent_interfaces import (
    BaseAgent, AgentRole, AgentContext, AgentMessage,
    AgentCapability, agent_registry
)


# AgentRole, AgentMessage, AgentContext, and BaseAgent are now imported from agent_interfaces.py
# This provides better separation of concerns and cleaner interfaces


class ExtractionAgent(BaseAgent):
    """Agent specialized in extracting information from documents."""
    
    def __init__(self, name: str = "ExtractorAgent"):
        super().__init__(name, AgentRole.EXTRACTOR)
        self._capabilities = {
            AgentCapability.REGEX_EXTRACTION: True,
            AgentCapability.STRUCTURED_EXTRACTION: True
        }
        self.extraction_patterns = {
            "study_title": r"(?:Title|Study|Protocol):\s*([^\n]+)",
            "principal_investigator": r"(?:PI|Principal Investigator|Investigator):\s*([^\n]+)",
            "irb_number": r"(?:IRB|Protocol)\s*(?:Number|#):\s*([A-Z0-9-]+)",
            "sponsor": r"(?:Sponsor|Funded by):\s*([^\n]+)",
            "duration": r"(?:Duration|Length|Last):\s*(\d+\s*(?:days?|weeks?|months?|years?))",
            "visits": r"(\d+)\s*(?:visits?|appointments?)",
        }
    
    async def process(self, context: AgentContext) -> dict[str, Any]:
        """Extract key information from document."""
        self.context = context
        
        # Validate input
        if not self.validate_input(context):
            return {"error": "Invalid context for extraction"}
        
        extracted = {}
        doc_text = context.parameters.get("document_text", "")
        
        # Extract using patterns
        for field, pattern in self.extraction_patterns.items():
            match = re.search(pattern, doc_text, re.IGNORECASE)
            if match:
                extracted[field] = match.group(1).strip()
        
        # Store in context
        context.extracted_values.update(extracted)
        
        # Send message to validator
        self.send_message("ValidatorAgent", extracted, "extraction_complete")
        
        return extracted


class GenerationAgent(BaseAgent):
    """Agent specialized in generating content using templates or LLM."""
    
    def __init__(self, name: str = "GeneratorAgent", llm=None):
        super().__init__(name, AgentRole.GENERATOR)
        self.llm = llm
        self._capabilities = {
            AgentCapability.TEMPLATE_GENERATION: True,
            AgentCapability.LLM_GENERATION: llm is not None
        }
    
    async def process(self, context: AgentContext) -> dict[str, Any]:
        """Generate content based on context using LLM or templates."""
        self.context = context
        
        # Validate input
        if not self.validate_input(context):
            return {"error": "Invalid context for generation"}
        
        generated = {}
        extracted = context.extracted_values
        
        if self.llm:
            # Use LLM to generate content
            
            # Generate introduction section
            if "study_title" in extracted:
                prompt = f"""Generate a brief, clear introduction for a research study.
                Study Title: {extracted['study_title']}
                Keep it under 100 words and focus on the purpose and importance."""
                
                try:
                    # Direct OpenAI SDK call through the extractor's client
                    messages = [{"role": "user", "content": prompt}]
                    response = self.llm.client.chat.completions.create(
                        model=self.llm.model,
                        messages=messages,
                        temperature=self.llm.temperature,
                    )
                    generated["section1_intro"] = response.choices[0].message.content.strip()
                except (LLMError, Exception) as e:
                    # Fallback to simple generation on any LLM error
                    generated["section1_intro"] = f"This research study, titled '{extracted['study_title']}', aims to advance our understanding."
            
            # Generate participation details section
            if "duration" in extracted or "visits" in extracted:
                details = []
                if "duration" in extracted:
                    details.append(f"Duration: {extracted['duration']}")
                if "visits" in extracted:
                    details.append(f"Visits: {extracted['visits']}")
                
                if details:
                    prompt = f"""Generate a clear explanation of participation requirements.
                    {' '.join(details)}
                    Write in second person, be concise and clear."""
                    
                    try:
                        messages = [{"role": "user", "content": prompt}]
                        response = self.llm.client.chat.completions.create(
                            model=self.llm.model,
                            messages=messages,
                            temperature=self.llm.temperature,
                        )
                        generated["section5_content"] = response.choices[0].message.content.strip()
                    except (LLMError, Exception) as e:
                        # Fallback on any LLM error
                        if "duration" in extracted and "visits" in extracted:
                            generated["section5_content"] = f"Your participation will last {extracted['duration']} and require {extracted['visits']}."
                        elif "duration" in extracted:
                            generated["section5_content"] = f"Your participation will last {extracted['duration']}."
                        else:
                            generated["section5_content"] = f"Your participation will require {extracted['visits']}."
        else:
            # Fallback to simple generation if no LLM available
            if "study_title" in extracted:
                generated["section1_intro"] = f"This research study, titled '{extracted['study_title']}', aims to advance our understanding."
            
            if "duration" in extracted and "visits" in extracted:
                generated["section5_content"] = f"Your participation will last {extracted['duration']} and require {extracted['visits']}."
        
        # Store generated content
        context.generated_content.update(generated)
        
        # Send to validator
        self.send_message("ValidatorAgent", generated, "generation_complete")
        
        return generated


class ValidationAgent(BaseAgent):
    """Agent specialized in validation and intent preservation."""
    
    def __init__(self, name: str = "ValidatorAgent"):
        super().__init__(name, AgentRole.VALIDATOR)
        self._capabilities = {
            AgentCapability.RULE_VALIDATION: True,
            AgentCapability.INTENT_VALIDATION: True,
            AgentCapability.STRUCTURAL_VALIDATION: True
        }
        self.validation_rules = {
            "required_fields": ["study_title", "principal_investigator"],
            "max_lengths": {"study_title": 200, "section1_intro": 500},
            "intent_critical": ["study_title", "irb_number", "duration", "visits"]
        }
    
    async def process(self, context: AgentContext) -> dict[str, Any]:
        """Validate content and check intent preservation."""
        self.context = context
        
        # Validate input
        if not self.validate_input(context):
            return {"error": "Invalid context for validation"}
        
        results = {
            "passed": True,
            "issues": [],
            "warnings": [],
            "intent_preserved": {}
        }
        
        # Check required fields
        for field in self.validation_rules["required_fields"]:
            if field not in context.extracted_values:
                results["issues"].append(f"Required field missing: {field}")
                results["passed"] = False
        
        # Check max lengths
        for field, max_len in self.validation_rules["max_lengths"].items():
            value = context.extracted_values.get(field) or context.generated_content.get(field)
            if value and len(str(value)) > max_len:
                results["warnings"].append(f"{field} exceeds max length of {max_len}")
        
        # Check intent preservation
        for critical_field in self.validation_rules["intent_critical"]:
            if critical_field in context.extracted_values:
                original_value = str(context.extracted_values[critical_field])
                
                # Check if value appears in any generated content
                preserved = False
                for content_key, content_value in context.generated_content.items():
                    if original_value.lower() in str(content_value).lower():
                        preserved = True
                        break
                
                results["intent_preserved"][critical_field] = preserved
                if not preserved and critical_field in context.critical_values:
                    results["issues"].append(f"Critical value '{critical_field}' not preserved in output")
                    results["passed"] = False
        
        # Store validation results
        context.validation_results = results
        
        return results


class OrchestrationAgent(BaseAgent):
    """Agent that orchestrates other agents in a pipeline."""
    
    def __init__(self, name: str = "OrchestratorAgent"):
        super().__init__(name, AgentRole.ORCHESTRATOR)
        self._capabilities = {
            AgentCapability.PIPELINE_ORCHESTRATION: True,
            AgentCapability.PARALLEL_ORCHESTRATION: True
        }
        self.agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent for orchestration"""
        self.agents[agent.name] = agent
    
    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Orchestrate agent collaboration"""
        self.context = context
        results = {}
        
        # Define processing pipeline based on document type
        if context.document_type == "informed-consent-ki":
            pipeline = ["ExtractorAgent", "GeneratorAgent", "ValidatorAgent"]
        else:
            pipeline = ["ExtractorAgent", "ValidatorAgent"]
        
        # Execute pipeline
        for agent_name in pipeline:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                agent_result = await agent.process(context)
                results[agent_name] = agent_result
            
            # Small delay to simulate processing
            await asyncio.sleep(0.1)
        
        return results


class SpecialistAgent(BaseAgent):
    """Base class for domain-specific specialist agents"""
    
    def __init__(self, name: str, specialty: str):
        super().__init__(name, AgentRole.SPECIALIST)
        self.specialty = specialty
    
    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Process document based on specialty"""
        self.context = context
        
        # Base implementation for specialist agents
        results = {
            "specialty": self.specialty,
            "processed": True,
            "recommendations": []
        }
        
        # Template selection specialty
        if self.specialty == "template_selection":
            templates = context.parameters.get("available_templates", {})
            regulatory_section = context.parameters.get("regulatory_section", "device")
            therapeutic_area = context.parameters.get("therapeutic_area", "")
            
            selected_template = f"{regulatory_section}_{therapeutic_area}" if therapeutic_area else regulatory_section
            results["selected_template"] = selected_template
            results["recommendations"].append(f"Selected template: {selected_template}")
        
        # Sub-template selection specialty
        elif self.specialty == "sub_template_selection":
            study_phase = context.parameters.get("study_phase", "")
            study_design = context.parameters.get("study_design", "")
            
            sub_templates = []
            if study_phase:
                sub_templates.append(f"phase_{study_phase}")
            if study_design:
                sub_templates.append(f"design_{study_design}")
            
            results["selected_sub_templates"] = sub_templates
            results["recommendations"].append(f"Selected sub-templates: {', '.join(sub_templates)}")
        
        # Default specialty processing
        else:
            results["recommendations"].append(f"Processing with {self.specialty} specialty")
        
        return results


class ClinicalProtocolAgent(SpecialistAgent):
    """Specialist agent for clinical protocol documents"""
    
    def __init__(self):
        super().__init__("ClinicalProtocolAgent", "clinical_protocol")
        self.sub_templates = {
            "device": ["safety", "efficacy", "fda_requirements"],
            "drug": ["pharmacology", "dosing", "adverse_events"],
            "biologic": ["immunogenicity", "administration", "storage"]
        }
    
    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Process clinical protocol specific requirements"""
        self.context = context
        results = {}
        
        # Determine sub-template based on study type
        study_object = context.extracted_values.get("study_object", "").lower()
        
        if "device" in study_object:
            template_type = "device"
        elif "drug" in study_object or "medication" in study_object:
            template_type = "drug"
        elif "biologic" in study_object or "vaccine" in study_object:
            template_type = "biologic"
        else:
            template_type = "drug"  # Default
        
        results["template_type"] = template_type
        results["required_sections"] = self.sub_templates[template_type]
        
        # Add to context
        context.parameters["clinical_template_type"] = template_type
        
        return results


class IntentPreservationAgent(BaseAgent):
    """Agent focused on preserving original intent in generated content"""
    
    def __init__(self):
        super().__init__("IntentPreservationAgent", AgentRole.VALIDATOR)
        self.semantic_equivalents = {
            "study": ["research", "trial", "investigation", "protocol"],
            "participant": ["subject", "patient", "volunteer"],
            "risk": ["hazard", "danger", "adverse event", "side effect"],
            "benefit": ["advantage", "improvement", "positive outcome"]
        }
    
    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Check semantic intent preservation"""
        self.context = context
        results = {
            "semantic_preservation": {},
            "recommendations": []
        }
        
        # Check each critical value
        for field in context.critical_values:
            if field in context.extracted_values:
                original = str(context.extracted_values[field])
                
                # Check for semantic equivalents
                preserved = False
                for content in context.generated_content.values():
                    content_str = str(content).lower()
                    
                    # Direct match
                    if original.lower() in content_str:
                        preserved = True
                        break
                    
                    # Semantic equivalent match
                    for key_term in original.lower().split():
                        if key_term in self.semantic_equivalents:
                            for equivalent in self.semantic_equivalents[key_term]:
                                if equivalent in content_str:
                                    preserved = True
                                    break
                
                results["semantic_preservation"][field] = preserved
                
                if not preserved:
                    results["recommendations"].append(
                        f"Consider adding '{original}' or its equivalent to preserve intent for {field}"
                    )
        
        return results


class MultiAgentPool:
    """Enhanced pool for managing multiple agents"""
    
    def __init__(self, llm=None):
        self.agents: Dict[str, BaseAgent] = {}
        self.llm = llm
        self.orchestrator = OrchestrationAgent()
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """Initialize default agents"""
        # Core agents
        self.register_agent(ExtractionAgent())
        self.register_agent(GenerationAgent(llm=self.llm))  # Pass LLM to generation agent
        self.register_agent(ValidationAgent())
        self.register_agent(IntentPreservationAgent())
        
        # Specialist agents
        self.register_agent(ClinicalProtocolAgent())
        
        # Register all with orchestrator
        for agent in self.agents.values():
            self.orchestrator.register_agent(agent)
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent in the pool"""
        self.agents[agent.name] = agent
        if hasattr(self, 'orchestrator'):
            self.orchestrator.register_agent(agent)
    
    async def orchestrate(self, 
                         agents: list[BaseAgent], 
                         parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Enhanced orchestration with agent collaboration
        
        Args:
            agents: List of agents to use (can be names or instances)
            parameters: Document parameters
            
        Returns:
            Combined results from all agents
        """
        # Create shared context
        context = AgentContext(
            document_type=parameters.get("document_type", "unknown"),
            parameters=parameters,
            critical_values=parameters.get("critical_values", [])
        )
        
        # If specific agents requested, use them
        if agents:
            results = {}
            for agent in agents:
                if isinstance(agent, str):
                    agent = self.agents.get(agent)
                if agent:
                    agent_result = await agent.process(context)
                    results[agent.name] = agent_result
        else:
            # Use orchestrator for automatic pipeline
            results = await self.orchestrator.process(context)
        
        # Compile final results
        return {
            "extracted_values": context.extracted_values,
            "generated_content": context.generated_content,
            "validation_results": context.validation_results,
            "agent_results": results,
            "messages": [
                {
                    "from": msg.sender, 
                    "to": msg.recipient,
                    "type": msg.message_type,
                    "content": str(msg.content)[:100]  # Truncate for display
                }
                for msg in context.messages
            ]
        }
    
    def get_specialists_for_document(self, document_type: str) -> List[BaseAgent]:
        """Get specialist agents for a document type"""
        specialists = []
        for agent in self.agents.values():
            if agent.role == AgentRole.SPECIALIST:
                if hasattr(agent, 'specialty'):
                    if document_type.lower() in agent.specialty:
                        specialists.append(agent)
        return specialists