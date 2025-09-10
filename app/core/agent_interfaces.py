"""
Agent interfaces and protocols for the multi-agent system.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class AgentRole(Enum):
    """Standardized roles for agents in the system."""
    EXTRACTOR = "extractor"      # Extracts information from documents
    GENERATOR = "generator"      # Generates new content
    VALIDATOR = "validator"      # Validates content and rules
    TRANSFORMER = "transformer"  # Transforms content format
    ROUTER = "router"           # Routes tasks to appropriate agents
    SPECIALIST = "specialist"   # Domain-specific processing
    ORCHESTRATOR = "orchestrator"  # Coordinates other agents


@dataclass
class AgentMessage:
    """
    Message format for inter-agent communication.
    
    Attributes:
        sender: Name/ID of the sending agent
        recipient: Name/ID of the receiving agent
        content: The message payload
        message_type: Type of message (info, request, response, error)
        correlation_id: Optional ID for tracking related messages
        metadata: Additional message metadata
        timestamp: When the message was created
    """
    sender: str
    recipient: str
    content: Any
    message_type: str
    correlation_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentContext:
    """
    Shared context for agent collaboration.
    
    This context is passed between agents and accumulates results
    as the document generation pipeline progresses.
    """
    document_type: str
    parameters: dict[str, Any]
    extracted_values: dict[str, Any] = field(default_factory=dict)
    generated_content: dict[str, str] = field(default_factory=dict)
    transformed_content: dict[str, Any] = field(default_factory=dict)
    validation_results: dict[str, Any] = field(default_factory=dict)
    critical_values: list[str] = field(default_factory=list)
    messages: list[AgentMessage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: AgentMessage) -> None:
        """Add a message to the context."""
        self.messages.append(message)
    
    def get_messages_for(self, recipient: str) -> list[AgentMessage]:
        """Get all messages for a specific recipient."""
        return [msg for msg in self.messages if msg.recipient == recipient]
    
    def clear_messages_for(self, recipient: str) -> None:
        """Clear messages for a specific recipient after processing."""
        self.messages = [msg for msg in self.messages if msg.recipient != recipient]


@runtime_checkable
class IAgent(Protocol):
    """Protocol defining the interface all agents must implement."""
    
    name: str
    role: AgentRole
    
    async def process(self, context: AgentContext) -> dict[str, Any]:
        """Process the context and return results."""
        ...
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate that the agent can process the given context."""
        ...
    
    def get_capabilities(self) -> dict[str, Any]:
        """Return the agent's capabilities and requirements."""
        ...


@runtime_checkable
class IExtractionAgent(Protocol):
    """Protocol for agents that extract information from documents."""
    
    async def extract(self, text: str, patterns: dict[str, str]) -> dict[str, Any]:
        """Extract information using provided patterns."""
        ...


@runtime_checkable
class IGenerationAgent(Protocol):
    """Protocol for agents that generate content."""
    
    async def generate(self, template: str, context: dict[str, Any]) -> str:
        """Generate content using a template and context."""
        ...


@runtime_checkable
class IValidationAgent(Protocol):
    """Protocol for agents that validate content."""
    
    async def validate_rules(self, content: Any, rules: dict[str, Any]) -> dict[str, Any]:
        """Validate content against a set of rules."""
        ...


@runtime_checkable
class IOrchestrationAgent(Protocol):
    """Protocol for agents that orchestrate other agents."""
    
    async def orchestrate(self, agents: list[IAgent], context: AgentContext) -> dict[str, Any]:
        """Orchestrate a pipeline of agents."""
        ...


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Provides common functionality for agent implementation including
    message handling, context management, and basic validation.
    """
    
    def __init__(self, name: str, role: AgentRole):
        """
        Initialize the agent.
        
        Args:
            name: Unique name for the agent
            role: The role this agent plays in the system
        """
        self.name = name
        self.role = role
        self._context: Optional[AgentContext] = None
        self._capabilities: dict[str, Any] = {}
    
    @property
    def context(self) -> Optional[AgentContext]:
        """Get the current context."""
        return self._context
    
    @context.setter
    def context(self, value: AgentContext) -> None:
        """Set the current context."""
        self._context = value
    
    @abstractmethod
    async def process(self, context: AgentContext) -> dict[str, Any]:
        """
        Process the context and return results.
        
        Args:
            context: The agent context to process
            
        Returns:
            Dictionary containing processing results
        """
        pass
    
    def validate_input(self, context: AgentContext) -> bool:
        """
        Validate that the agent can process the given context.
        
        Args:
            context: The context to validate
            
        Returns:
            True if the context is valid for processing
        """
        # Default implementation - override in subclasses for specific validation
        return context is not None and context.document_type
    
    def get_capabilities(self) -> dict[str, Any]:
        """
        Return the agent's capabilities and requirements.
        
        Returns:
            Dictionary describing agent capabilities
        """
        return {
            "name": self.name,
            "role": self.role.value,
            "capabilities": self._capabilities
        }
    
    def send_message(self, recipient: str, content: Any, 
                    message_type: str = "info",
                    correlation_id: Optional[str] = None) -> None:
        """
        Send a message to another agent.
        
        Args:
            recipient: Name of the recipient agent
            content: Message content
            message_type: Type of message
            correlation_id: Optional ID for message correlation
        """
        if self._context:
            message = AgentMessage(
                sender=self.name,
                recipient=recipient,
                content=content,
                message_type=message_type,
                correlation_id=correlation_id
            )
            self._context.add_message(message)
    
    def receive_messages(self) -> list[AgentMessage]:
        """
        Receive messages addressed to this agent.
        
        Returns:
            List of messages for this agent
        """
        if not self._context:
            return []
        return self._context.get_messages_for(self.name)
    
    def clear_messages(self) -> None:
        """Clear all messages for this agent."""
        if self._context:
            self._context.clear_messages_for(self.name)
    
    async def handle_error(self, error: Exception, context: AgentContext) -> dict[str, Any]:
        """
        Handle errors during processing.
        
        Args:
            error: The exception that occurred
            context: The context being processed
            
        Returns:
            Error information dictionary
        """
        error_info = {
            "agent": self.name,
            "error": str(error),
            "error_type": type(error).__name__,
            "context_state": {
                "has_extracted": bool(context.extracted_values),
                "has_generated": bool(context.generated_content),
                "has_validation": bool(context.validation_results)
            }
        }
        
        # Send error message to orchestrator
        self.send_message(
            "OrchestratorAgent",
            error_info,
            "error"
        )
        
        return error_info


class AgentCapability:
    """Defines capabilities that agents can have."""
    
    # Extraction capabilities
    REGEX_EXTRACTION = "regex_extraction"
    LLM_EXTRACTION = "llm_extraction"
    STRUCTURED_EXTRACTION = "structured_extraction"
    
    # Generation capabilities
    TEMPLATE_GENERATION = "template_generation"
    LLM_GENERATION = "llm_generation"
    RULE_BASED_GENERATION = "rule_based_generation"
    
    # Validation capabilities
    RULE_VALIDATION = "rule_validation"
    INTENT_VALIDATION = "intent_validation"
    STRUCTURAL_VALIDATION = "structural_validation"
    
    # Transformation capabilities
    FORMAT_TRANSFORM = "format_transform"
    SCHEMA_TRANSFORM = "schema_transform"
    
    # Orchestration capabilities
    PIPELINE_ORCHESTRATION = "pipeline_orchestration"
    PARALLEL_ORCHESTRATION = "parallel_orchestration"
    CONDITIONAL_ORCHESTRATION = "conditional_orchestration"


class AgentRegistry:
    """
    Registry for managing available agents in the system.
    
    This registry allows dynamic agent registration and discovery,
    making the system more extensible.
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._agents: dict[str, IAgent] = {}
        self._agents_by_role: dict[AgentRole, list[IAgent]] = {}
        self._agents_by_capability: dict[str, list[IAgent]] = {}
    
    def register(self, agent: IAgent) -> None:
        """
        Register an agent in the registry.
        
        Args:
            agent: The agent to register
        """
        self._agents[agent.name] = agent
        
        # Index by role
        if agent.role not in self._agents_by_role:
            self._agents_by_role[agent.role] = []
        self._agents_by_role[agent.role].append(agent)
        
        # Index by capabilities
        capabilities = agent.get_capabilities().get("capabilities", {})
        for capability in capabilities:
            if capability not in self._agents_by_capability:
                self._agents_by_capability[capability] = []
            self._agents_by_capability[capability].append(agent)
    
    def get_agent(self, name: str) -> Optional[IAgent]:
        """
        Get an agent by name.
        
        Args:
            name: The agent name
            
        Returns:
            The agent if found, None otherwise
        """
        return self._agents.get(name)
    
    def get_agents_by_role(self, role: AgentRole) -> list[IAgent]:
        """
        Get all agents with a specific role.
        
        Args:
            role: The agent role
            
        Returns:
            List of agents with the specified role
        """
        return self._agents_by_role.get(role, [])
    
    def get_agents_by_capability(self, capability: str) -> list[IAgent]:
        """
        Get all agents with a specific capability.
        
        Args:
            capability: The capability to search for
            
        Returns:
            List of agents with the specified capability
        """
        return self._agents_by_capability.get(capability, [])
    
    def list_agents(self) -> list[dict[str, Any]]:
        """
        List all registered agents.
        
        Returns:
            List of agent information dictionaries
        """
        return [agent.get_capabilities() for agent in self._agents.values()]


# Global agent registry instance
agent_registry = AgentRegistry()