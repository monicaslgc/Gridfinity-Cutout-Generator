from __future__ import annotations
from ..models import IdentifyResponse, IdentifyCandidate
from .dimensions.wikidata import search_wikidata_qid

# NOTE(why): true multimodal/LLM identification isn't built yet (see the
# top-level README's Development Roadmap). This previously fabricated a
# fake slug ID (e.g. "Qnintendo_switch_pro_c") that could never resolve
# through /dimensions, since that endpoint expects a real Wikidata QID.
# This now resolves free text to a real QID via Wikidata's own search API,
# so the id it returns is something /dimensions can actually look up.


async def identify_from_text(user_input: str) -> IdentifyResponse:
    name = user_input.strip()
    qid = search_wikidata_qid(name) if name else None

    if qid:
        candidates = [IdentifyCandidate(id=qid, name=name, confidence=0.75)]
    else:
        # No Wikidata match - fall back to a clearly-not-a-QID id so
        # /dimensions degrades to its own "not found" handling instead of
        # being handed something that looks like a QID but isn't.
        candidates = [
            IdentifyCandidate(id=f"unresolved:{name}" if name else "unresolved", name=name or "Unknown item", confidence=0.2)
        ]

    return IdentifyResponse(item=name, candidates=candidates)


async def identify_from_image(content: bytes) -> IdentifyResponse:
    # Placeholder: real image-based identification isn't built yet either.
    return IdentifyResponse(
        item="unknown",
        candidates=[IdentifyCandidate(id="unresolved:unknown", name="unknown item", confidence=0.2)],
    )
