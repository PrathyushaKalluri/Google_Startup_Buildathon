from __future__ import annotations

import json
from typing import Any, Dict, Optional

from services.common.config import settings
from services.common.logging import get_logger

logger = get_logger("keepwell.llm")


class KeepwellLLMClient:
    """
    Google GenAI SDK wrapper reading model IDs exclusively from env vars (Contract C1/C4).
    Supports Gemini Developer API (default) and Agent Platform / Vertex AI
    (when GOOGLE_GENAI_USE_VERTEXAI=true). Falls back gracefully with degraded=True
    when offline or when API quota/network is unavailable.
    """

    def __init__(self) -> None:
        self._client: Any = None
        if settings.gemini_api_key or settings.google_genai_use_vertexai:
            try:
                from google import genai  # type: ignore

                if settings.google_genai_use_vertexai:
                    self._client = genai.Client(
                        vertexai=True,
                        project=settings.gcp_project_id,
                        location=settings.gcp_region,
                    )
                else:
                    self._client = genai.Client(api_key=settings.gemini_api_key)
            except Exception as exc:
                logger.warning("genai_init_fallback", extra={"extra_fields": {"error": str(exc)}})

    def generate_structured(
        self,
        prompt: str,
        model_tier: str = "fast",  # fast | agent | pro
        fallback: Optional[Dict[str, Any]] = None,
        use_live_network: bool = False,
    ) -> Dict[str, Any]:
        model_name = {
            "fast": settings.gemini_model_fast,
            "agent": settings.gemini_model_agent,
            "pro": settings.gemini_model_pro,
        }.get(model_tier, settings.gemini_model_fast)

        if use_live_network and self._client is not None:
            try:
                resp = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                data = json.loads(resp.text)
                data["_model_version"] = model_name
                data["_degraded"] = False
                return data
            except Exception as exc:
                logger.warning(
                    "genai_call_degraded",
                    extra={"extra_fields": {"model": model_name, "error": str(exc)}},
                )

        out = dict(fallback or {})
        out["_model_version"] = f"{model_name}-deterministic-fallback"
        out["_degraded"] = True
        return out


llm_client = KeepwellLLMClient()
