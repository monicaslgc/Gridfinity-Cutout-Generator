from __future__ import annotations
from ..models import IdentifyResponse, IdentifyCandidate

# NOTE(why): MVP keeps this deterministic and offline-friendly; swap in real LLM later.


async def identify_from_text(user_input: str) -> IdentifyResponse:
    name = user_input.strip()
    # naive deterministic ID (slug)
    qid = f"Q{name.lower().replace(' ', '_')[:16]}"
    return IdentifyResponse(
        item=name,
        candidates=[IdentifyCandidate(id=qid, name=name, confidence=0.75)],
    )


async def identify_from_image(content: bytes) -> IdentifyResponse:
    # Placeholder: return an unknown item with low confidence
    return IdentifyResponse(
        item="unknown",
        candidates=[IdentifyCandidate(id="Qunknown", name="unknown item", confidence=0.2)],
    )
