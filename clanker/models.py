"""Simple model management with .env-based configuration."""

import os
from enum import Enum
from typing import Optional, Union, Dict, List

from dotenv import load_dotenv

# Load environment variables at module import
load_dotenv()

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.mistral import MistralModel


class ModelTier(str, Enum):
    """Model capability tiers for automatic selection."""
    LOW = "low"        # Fast, cheap tasks
    MEDIUM = "medium"  # Balanced performance
    HIGH = "high"      # Maximum quality


# Tier preferences (ordered by preference)
TIER_MODELS = {
    ModelTier.LOW: [
        "openai:gpt-5-nano-2025-08-07",
        "anthropic:claude-3-5-haiku-latest",
    ],
    ModelTier.MEDIUM: [
        "openai:gpt-5-mini-2025-08-07",
        "anthropic:claude-sonnet-4-0",
        "anthropic:claude-3-7-sonnet-latest",
    ],
    ModelTier.HIGH: [
        "openai:gpt-5-2025-08-07",
        "anthropic:claude-opus-4-1",
        "anthropic:claude-3-7-sonnet-latest",
    ],
}


def _get_available_providers() -> Dict[str, Optional[str]]:
    """Get providers with configured API keys from environment."""
    return {
        "openai": os.getenv("OPENAI_API_KEY"),
        "anthropic": os.getenv("ANTHROPIC_API_KEY"),
        "google": os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
        "groq": os.getenv("GROQ_API_KEY"),
        "mistral": os.getenv("MISTRAL_API_KEY"),
    }


def get_model(spec: Union[str, ModelTier]) -> Model:
    """Get model by tier or explicit name.
    
    Args:
        spec: ModelTier (LOW/MEDIUM/HIGH) or explicit "provider:model" string
        
    Returns:
        Pydantic AI Model instance
        
    Raises:
        ValueError: If model not available (no API key or unknown model)
        
    Examples:
        # Tier-based (automatic selection)
        model = get_model(ModelTier.LOW)
        
        # Explicit model
        model = get_model("openai:gpt-4o")
        model = get_model("claude-sonnet-4-0")  # Auto-detects anthropic
    """
    if isinstance(spec, ModelTier):
        # Try each model in tier until one is available
        last_error = None
        for model_str in TIER_MODELS[spec]:
            try:
                return _create_model(model_str)
            except ValueError as e:
                last_error = e
                continue
        
        # No models available for tier - provide helpful error
        available = list_available_providers()
        if not available:
            raise ValueError(
                f"No models available for tier '{spec.value}'. "
                f"Please set API keys in .env file:\n"
                f"  OPENAI_API_KEY=...\n"
                f"  ANTHROPIC_API_KEY=...\n"
                f"  GOOGLE_API_KEY=...\n"
                f"  GROQ_API_KEY=..."
            )
        else:
            raise ValueError(
                f"No models available for tier '{spec.value}'. "
                f"Available providers: {', '.join(available)}. "
                f"Last error: {last_error}"
            )
    else:
        # Direct model string - fail clearly if not available
        return _create_model(spec)


def _create_model(model_str: str) -> Model:
    """Create model instance, with clear errors if unavailable.
    
    Args:
        model_str: Model identifier like "openai:gpt-4o" or "gpt-4o"
        
    Returns:
        Pydantic AI Model instance
        
    Raises:
        ValueError: If provider not configured or model unknown
    """
    provider, model_name = _parse_model_string(model_str)
    
    providers = _get_available_providers()
    api_key = providers.get(provider)
    
    if not api_key:
        env_var = f"{provider.upper()}_API_KEY"
        if provider == "google":
            env_var = "GOOGLE_API_KEY or GEMINI_API_KEY"
        raise ValueError(
            f"Model '{model_str}' requires {env_var} in .env file"
        )
    
    # Create appropriate Pydantic AI model
    if provider == "openai":
        return OpenAIChatModel(model_name, api_key=api_key)
    elif provider == "anthropic":
        return AnthropicModel(model_name, api_key=api_key)
    elif provider == "google":
        return GeminiModel(model_name, api_key=api_key)
    elif provider == "groq":
        return GroqModel(model_name, api_key=api_key)
    elif provider == "mistral":
        return MistralModel(model_name, api_key=api_key)
    else:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Supported: openai, anthropic, google, groq, mistral"
        )


def _parse_model_string(model_str: str) -> tuple[str, str]:
    """Parse 'provider:model' string or infer provider from model name.
    
    Args:
        model_str: Model identifier
        
    Returns:
        Tuple of (provider, model_name)
        
    Raises:
        ValueError: If provider cannot be determined
    """
    if ":" in model_str:
        provider, model_name = model_str.split(":", 1)
        return provider.lower(), model_name
    
    # Infer provider from common model name patterns
    model_lower = model_str.lower()
    
    if model_str.startswith(("gpt-", "o1-", "o1")):
        return "openai", model_str
    elif model_str.startswith("claude"):
        return "anthropic", model_str
    elif model_str.startswith("gemini"):
        return "google", model_str
    elif model_str.startswith(("llama", "mixtral")):
        return "groq", model_str
    elif model_str.startswith("mistral"):
        return "mistral", model_str
    else:
        raise ValueError(
            f"Cannot infer provider for model '{model_str}'. "
            f"Use explicit format 'provider:model' (e.g., 'openai:gpt-4o')"
        )


def list_available_providers() -> List[str]:
    """List providers that have API keys configured.
    
    Returns:
        List of configured provider names
    """
    return [
        provider 
        for provider, api_key in _get_available_providers().items() 
        if api_key
    ]


def list_available_models() -> Dict[str, List[str]]:
    """List all accessible models organized by provider.
    
    Returns:
        Dict mapping provider names to their known models
    """
    available_models = {}
    providers = _get_available_providers()
    
    # Extract unique models from tier definitions
    all_model_strings = set()
    for tier_models in TIER_MODELS.values():
        all_model_strings.update(tier_models)
    
    # Group by available providers
    for model_str in all_model_strings:
        if ":" in model_str:
            provider, model_name = model_str.split(":", 1)
            if providers.get(provider):  # Only if API key exists
                if provider not in available_models:
                    available_models[provider] = []
                if model_name not in available_models[provider]:
                    available_models[provider].append(model_name)
    
    # Sort model lists
    for models in available_models.values():
        models.sort()
    
    return available_models


def create_agent(
    spec: Union[str, ModelTier] = ModelTier.MEDIUM,
    **agent_kwargs
) -> Agent:
    """Convenience function to create a Pydantic AI agent.
    
    Args:
        spec: Model specification (tier or explicit name)
        **agent_kwargs: Additional arguments for Agent
        
    Returns:
        Configured Pydantic AI Agent
        
    Examples:
        agent = create_agent(ModelTier.LOW)
        agent = create_agent("anthropic:claude-sonnet-4-0")
    """    
    model = get_model(spec)
    return Agent(model, **agent_kwargs)