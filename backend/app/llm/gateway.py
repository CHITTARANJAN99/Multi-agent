import abc
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai

from app.config.settings import settings
from app.core.logging_config import logger
from app.core.errors import LLMGatewayError

class LLMProvider(abc.ABC):
    """
    Abstract Base Class defining the standard interface for LLM client providers.
    """
    @abc.abstractmethod
    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        pass

    @abc.abstractmethod
    async def generate_stream(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
        pass

    @abc.abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        if not self.api_key:
            logger.warning("OpenAI API key missing. OpenAI provider will fail to run requests.")
        self.client = AsyncOpenAI(
            api_key=self.api_key or "dummy",
            base_url=self.base_url
        )

    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI completion error: {e}", exc_info=True)
            raise LLMGatewayError(f"OpenAI error: {str(e)}")

    async def generate_stream(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}", exc_info=True)
            raise LLMGatewayError(f"OpenAI stream error: {str(e)}")

    async def get_embedding(self, text: str) -> List[float]:
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=[text]
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}", exc_info=True)
            raise LLMGatewayError(f"OpenAI embedding error: {str(e)}")

class ClaudeProvider(LLMProvider):
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        if not self.api_key:
            logger.warning("Anthropic API key missing. Claude provider will fail to run requests.")
        self.client = AsyncAnthropic(api_key=self.api_key or "dummy")

    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        try:
            system_prompt = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    user_messages.append({"role": msg["role"], "content": msg["content"]})

            response = await self.client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                messages=user_messages,  # type: ignore
                system=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens or 4096
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            logger.error(f"Anthropic Claude completion error: {e}", exc_info=True)
            raise LLMGatewayError(f"Claude error: {str(e)}")

    async def generate_stream(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
        try:
            system_prompt = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    user_messages.append({"role": msg["role"], "content": msg["content"]})

            async with self.client.messages.stream(
                model=settings.ANTHROPIC_MODEL,
                messages=user_messages,  # type: ignore
                system=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens or 4096
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic Claude streaming error: {e}", exc_info=True)
            raise LLMGatewayError(f"Claude stream error: {str(e)}")

    async def get_embedding(self, text: str) -> List[float]:
        raise NotImplementedError("Claude does not natively support text embeddings.")

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            logger.warning("Gemini API key missing. Gemini provider will fail to run requests.")

    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        try:
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            # Map roles and merge messages for Gemini syntax
            gemini_contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_contents.append({"role": role, "parts": [msg["content"]]})
                
            config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            response = await model.generate_content_async(contents=gemini_contents, generation_config=config)
            return response.text
        except Exception as e:
            logger.error(f"Gemini completion error: {e}", exc_info=True)
            raise LLMGatewayError(f"Gemini error: {str(e)}")

    async def generate_stream(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
        try:
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            gemini_contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_contents.append({"role": role, "parts": [msg["content"]]})
                
            config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            response = await model.generate_content_async(contents=gemini_contents, generation_config=config, stream=True)
            async for chunk in response:
                yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}", exc_info=True)
            raise LLMGatewayError(f"Gemini stream error: {str(e)}")

    async def get_embedding(self, text: str) -> List[float]:
        try:
            result = await asyncio.to_thread(
                genai.embed_content,
                model="models/embedding-001",
                contents=text,
                task_type="retrieval_document"
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}", exc_info=True)
            raise LLMGatewayError(f"Gemini embedding error: {str(e)}")

class LLMGateway:
    """
    Gateway routing requests to the appropriate LLM provider depending on request settings or defaults.
    """
    def __init__(self, provider_name: Optional[str] = None):
        self.provider_name = (provider_name or settings.DEFAULT_PROVIDER).lower()
        self.provider: LLMProvider = self._resolve_provider(self.provider_name)

    def _resolve_provider(self, name: str) -> LLMProvider:
        if name == "openai":
            return OpenAIProvider()
        elif name == "anthropic" or name == "claude":
            return ClaudeProvider()
        elif name == "gemini":
            return GeminiProvider()
        else:
            logger.error(f"Unsupported LLM provider: {name}. Defaulting to OpenAI.")
            return OpenAIProvider()

    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        return await self.provider.generate(messages, temperature=temperature, max_tokens=max_tokens)

    async def generate_stream(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
        async for chunk in self.provider.generate_stream(messages, temperature=temperature, max_tokens=max_tokens):
            yield chunk

    async def get_embedding(self, text: str) -> List[float]:
        try:
            return await self.provider.get_embedding(text)
        except (NotImplementedError, Exception) as e:
            logger.warning(f"Default provider {self.provider_name} failed to generate embedding: {e}. Attempting fallback...")
            for fallback_name in ["openai", "gemini"]:
                if fallback_name == self.provider_name:
                    continue
                try:
                    fallback_prov = self._resolve_provider(fallback_name)
                    return await fallback_prov.get_embedding(text)
                except Exception as fallback_err:
                    logger.debug(f"Fallback {fallback_name} failed: {fallback_err}")
            
            logger.critical("All embedding providers failed. Returning zero vector.")
            return [0.0] * 1536
