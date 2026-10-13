"""Bounded loopback proposals; no credentials, payment transport or gate decisions."""

import asyncio
import json
import time

import httpx

from .config import Settings
from .llm import ChatCompletionsAnalyst
from .models import Problem, Recommendation

OLLAMA_URL = "http://127.0.0.1:11434/v1"
MODEL = "phi4-mini:latest"
PROPOSAL_SECONDS = 45
MAX_RESPONSE_BYTES = 65536


def demo_settings(planning_mode):
    return Settings(
        payment_mode="offline",
        ai_mode="real" if planning_mode == "local_ai" else "deterministic",
        llm_base_url=OLLAMA_URL if planning_mode == "local_ai" else "",
        llm_model=MODEL if planning_mode == "local_ai" else "",
        llm_format="json_schema" if planning_mode == "local_ai" else "json_object",
    )


class BoundedOllamaTransport(httpx.AsyncBaseTransport):
    """Use the existing parser with a fixed endpoint and bounded streamed envelope."""

    def __init__(self, inner=None):
        self.inner = inner or httpx.AsyncHTTPTransport(retries=0)

    async def handle_async_request(self, request):
        if request.method != "POST" or str(request.url) != OLLAMA_URL + "/chat/completions":
            raise Problem("LOCAL_AI_ENDPOINT_REJECTED", 503)
        body = json.loads(request.content)
        if body["model"] != MODEL or request.headers.get("authorization"):
            raise Problem("LOCAL_AI_ENDPOINT_REJECTED", 503)
        body.update(max_tokens=384, temperature=0)
        bounded = httpx.Request("POST", request.url, json=body, extensions=request.extensions)
        try:
            response = await self.inner.handle_async_request(bounded)
        except httpx.TimeoutException:
            raise Problem("LOCAL_AI_REQUEST_EXPIRED", 504) from None
        content = bytearray()
        try:
            async for chunk in response.aiter_bytes(chunk_size=8192):
                content.extend(chunk)
                if len(content) > MAX_RESPONSE_BYTES:
                    raise Problem("LOCAL_AI_OUTPUT_TOO_LARGE", 502)
        finally:
            await response.aclose()
        return httpx.Response(response.status_code, content=bytes(content))

    async def aclose(self):
        await self.inner.aclose()


class LocalProposal:
    def __init__(self, *, transport=None, timeout=PROPOSAL_SECONDS):
        self.transport, self.timeout = transport, timeout
        self.seconds = None

    async def analyze(self, message, facts):
        analyst = ChatCompletionsAnalyst(
            demo_settings("local_ai"), transport=BoundedOllamaTransport(self.transport)
        )
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self.timeout):
                return await analyst.analyze(message, facts)
        except TimeoutError:
            raise Problem("LOCAL_AI_REQUEST_EXPIRED", 504) from None
        finally:
            self.seconds = round(time.perf_counter() - started, 6)
            await analyst.close()


class PreparedAnalyst:
    """Pass an already parsed recommendation into the unchanged consumer pipeline."""

    def __init__(self):
        self.value = None

    async def analyze(self, message, facts):
        if self.value is None:
            raise Problem("LOCAL_AI_PROPOSAL_REQUIRED", 409)
        return Recommendation.model_validate(self.value.model_dump())

    async def close(self):
        self.value = None
