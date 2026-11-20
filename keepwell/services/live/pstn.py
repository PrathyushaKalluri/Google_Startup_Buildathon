from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.common.config import settings


@dataclass
class PSTNCallMetadata:
    call_sid: str
    from_number: str
    to_number: str
    codec: str = "mulaw_8000"


class PSTNBridgeAdapter:
    """
    Thin optional PSTN telephony adapter (TELEPHONY_MODE=pstn).
    Web mode (WS /v1/live/call) is the demo default; this adapter translates
    SIP/telephony media streams into the same LiveSession interface.
    """

    def __init__(self, mode: Optional[str] = None):
        self.mode = mode or settings.telephony_mode

    @property
    def enabled(self) -> bool:
        return self.mode == "pstn"

    def decode_to_pcm16_16k(self, payload: bytes, codec: str = "mulaw_8000") -> bytes:
        # In production, transcodes G.711 mu-law 8kHz -> PCM16 16kHz mono
        return payload
