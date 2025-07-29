"""
Custom LLM implementation using direct HTTP calls to OpenAI API.
This bypasses the OpenAI client library issues in Cloud Run environment.
"""

import asyncio
import json
from typing import Any, List, Mapping, Optional, Dict
import httpx
from langchain.llms.base import LLM
from langchain.schema import Generation, LLMResult
from langchain.callbacks.manager import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from src.config import settings
from src.monitoring.logger import get_logger

logger = get_logger(__name__)


class CustomOpenAILLM(LLM):
    """Custom LLM that uses direct HTTP calls to OpenAI API."""
    
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 1000
    api_key: str = ""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_name = kwargs.get("model", settings.openai_model)
        self.temperature = kwargs.get("temperature", 0.7)
        self.max_tokens = kwargs.get("max_tokens", 1000)
        self.api_key = kwargs.get("api_key", settings.openai_api_key)
    
    @property
    def _llm_type(self) -> str:
        return "custom_openai"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the OpenAI API synchronously."""
        # Run the async call in a sync context
        return asyncio.run(self._acall(prompt, stop, run_manager, **kwargs))
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the OpenAI API asynchronously."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            if stop:
                payload["stop"] = stop
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
            content = result["choices"][0]["message"]["content"]
            logger.info("custom_llm_call_success", model=self.model_name, prompt_length=len(prompt))
            return content
            
        except Exception as e:
            logger.error("custom_llm_call_failed", error=str(e), model=self.model_name)
            raise e
    
    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


class CustomChatOpenAI:
    """Chat-compatible wrapper for the custom LLM."""
    
    def __init__(self, model: str = None, temperature: float = 0.7, api_key: str = None, **kwargs):
        self.llm = CustomOpenAILLM(
            model=model or settings.openai_model,
            temperature=temperature,
            api_key=api_key or settings.openai_api_key,
            **kwargs
        )
    
    def __call__(self, messages, **kwargs):
        """Convert chat messages to a single prompt and call the LLM."""
        # Convert chat messages to a single prompt
        if isinstance(messages, list):
            # Handle list of message dicts
            prompt_parts = []
            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "system":
                        prompt_parts.append(f"System: {content}")
                    elif role == "user":
                        prompt_parts.append(f"User: {content}")
                    elif role == "assistant":
                        prompt_parts.append(f"Assistant: {content}")
                else:
                    prompt_parts.append(str(msg))
            prompt = "\n\n".join(prompt_parts)
        else:
            prompt = str(messages)
        
        return self.llm(prompt, **kwargs)
    
    async def arun(self, input_text: str, **kwargs):
        """Async run method for agent compatibility."""
        return await self.llm._acall(input_text, **kwargs)
    
    def predict(self, text: str, **kwargs):
        """Predict method for compatibility."""
        return self.llm(text, **kwargs)
    
    async def apredict(self, text: str, **kwargs):
        """Async predict method for compatibility."""
        return await self.llm._acall(text, **kwargs)
