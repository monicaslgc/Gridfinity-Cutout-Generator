"""Tests for the app/services/dimensions/ package.

This package used to be unimportable (see test_app_package_status.py's
history): app/services/dimensions.py (a flat, legacy file) shadowed the
app/services/dimensions/ package directory because the directory had no
__init__.py, and even once that's fixed, app/services/dimensions/fetcher.py
itself contained malformed Python (two different files' contents pasted
together, with all indentation stripped). This whole package - types.py,
units.py, parse.py, wikidata.py, fetcher.py, providers/schema_org.py,
providers/wikipedia.py - was rewritten from scratch based on what app/main.py
actually calls and what the corrupted files' surviving fragments suggested
they were meant to do.

All network calls are mocked; nothing here hits the real Wikidata/Wikipedia
APIs or a real URL.
"""
from __future__ import annotations
import asyncio
from unittest.mock import MagicMock, patch

from app.services.dimensions.types import DimensionsResult
from app.services.dimensions.units import to_mm
from app.services.dimensions.parse import normalize_dims_from_text
from app.services.dimensions import wikidata
from app.services.dimensions.providers import schema_org, wikipedia
from app.services.dimensions.fetcher import fetch_dimensions


# --- types.py --------------------------------------------------------------


def test_merge_missing_fills_gaps_and_prefers_higher_confidence():
    primary = DimensionsResult(dims_mm={"L": 100}, source="wikidata", confidence=0.9)
    secondary = DimensionsResult(dims_mm={"L": 999, "W": 50, "H": 20}, source="wikipedia", confidence=0.4)

    merged = primary.merge_missing(secondary)

    assert merged.dims_mm == {"L": 100, "W": 50, "H": 20}
    assert merged.source == "wikidata"
    assert merged.confidence == 0.9
    assert merged.is_complete()


def test_is_complete_requires_all_three_axes():
    assert not DimensionsResult(dims_mm={"L": 1, "W": 2}).is_complete()
    assert DimensionsResult(dims_mm={"L": 1, "W": 2, "H": 3}).is_complete()


# --- units.py ----------------------------------------------------------------


def test_to_mm_symbol_unitcode_and_wikidata_uri():
    assert to_mm(1, "cm") == 10.0
    assert to_mm(2, "IN") == 50.8
    assert to_mm(1, "http://www.wikidata.org/entity/Q174728") == 10.0


def test_to_mm_unknown_unit_returns_none():
    assert to_mm(5, "furlong") is None
    assert to_mm(5, None) is None


# --- parse.py ------------------------------------------------------------


def test_normalize_dims_from_text_parses_triplet_with_unit():
    assert normalize_dims_from_text("Dimensions: 152 x 106 x 60 mm") == {
        "L": 152.0,
        "W": 106.0,
        "H": 60.0,
    }


def test_normalize_dims_from_text_converts_units():
    assert normalize_dims_from_text("about 15 x 10 x 5 cm") == {
        "L": 150.0,
        "W": 100.0,
        "H": 50.0,
    }


def test_normalize_dims_from_text_no_match_returns_none():
    assert normalize_dims_from_text("no numbers here") is None


def test_normalize_dims_from_text_parses_pair_with_by():
    # Wikipedia's conventional phrasing for flat/2D items, e.g. the real
    # "Credit card" article's "85.60 by 53.98 millimeters" (ISO/IEC 7810
    # ID-1) - confirmed against the live article while investigating why
    # the functional test's candidate items weren't resolving dimensions.
    assert normalize_dims_from_text("85.60 by 53.98 millimeters") == {
        "L": 85.6,
        "W": 53.98,
    }


def test_normalize_dims_from_text_pair_does_not_fabricate_height():
    # A 2-number pair must never invent an "H" - see the note above
    # _PAIR_RE in parse.py for why guessing a thickness would repeat the
    # same mistake the plausibility bound was added to fix earlier this
    # investigation.
    result = normalize_dims_from_text("85.60 by 53.98 millimeters")
    assert "H" not in result


def test_normalize_dims_from_text_prefers_triplet_over_pair():
    # When a real triplet is present, don't fall back to pair-matching.
    assert normalize_dims_from_text("152 x 106 x 60 mm") == {
        "L": 152.0,
        "W": 106.0,
        "H": 60.0,
    }


# --- wikidata.py ----------------------------------------------------------


def test_search_wikidata_qid_returns_first_result():
    fake_response = MagicMock()
    fake_response.json.return_value = {"search": [{"id": "Q19842071"}]}
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.wikidata.requests.get", return_value=fake_response) as mock_get:
        qid = wikidata.search_wikidata_qid("Nintendo Switch Pro Controller")
    assert qid == "Q19842071"
    mock_get.assert_called_once()


def test_search_wikidata_qid_no_results_returns_none():
    fake_response = MagicMock()
    fake_response.json.return_value = {"search": []}
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.wikidata.requests.get", return_value=fake_response):
        assert wikidata.search_wikidata_qid("gibberish query xyz") is None


def test_search_wikidata_qid_network_failure_returns_none():
    with patch("app.services.dimensions.wikidata.requests.get", side_effect=Exception("boom")):
        assert wikidata.search_wikidata_qid("anything") is None


def test_fetch_wikidata_dimensions_rejects_malformed_qid_without_a_request():
    with patch("app.services.dimensions.wikidata.requests.get") as mock_get:
        result = wikidata.fetch_wikidata_dimensions("unresolved:something")
    assert result is None
    mock_get.assert_not_called()


def test_fetch_wikidata_dimensions_parses_sparql_bindings():
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "results": {
            "bindings": [
                {
                    "itemLabel": {"value": "Nintendo Switch Pro Controller"},
                    "length": {"value": "0.152"},
                    "width": {"value": "0.106"},
                    "height": {"value": "0.06"},
                }
            ]
        }
    }
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.wikidata.requests.get", return_value=fake_response):
        result = wikidata.fetch_wikidata_dimensions("Q19842071")

    assert result is not None
    assert result.dims_mm == {"L": 152.0, "W": 106.0, "H": 60.0}
    assert result.name == "Nintendo Switch Pro Controller"
    assert result.confidence == 0.9


def test_fetch_wikidata_dimensions_no_bindings_returns_none():
    fake_response = MagicMock()
    fake_response.json.return_value = {"results": {"bindings": []}}
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.wikidata.requests.get", return_value=fake_response):
        assert wikidata.fetch_wikidata_dimensions("Q1") is None


# --- providers/schema_org.py -----------------------------------------------

_PRODUCT_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Widget",
 "depth":{"@type":"QuantitativeValue","value":15,"unitCode":"CMT"},
 "width":{"@type":"QuantitativeValue","value":10,"unitCode":"CMT"},
 "height":{"@type":"QuantitativeValue","value":5,"unitCode":"CMT"}}
</script>
</head><body></body></html>
"""


def test_fetch_schema_org_dimensions_parses_product_jsonld():
    fake_response = MagicMock()
    fake_response.text = _PRODUCT_HTML
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.providers.schema_org.requests.get", return_value=fake_response):
        result = schema_org.fetch_schema_org_dimensions("https://example.com/widget")

    assert result is not None
    assert result.dims_mm == {"L": 150.0, "W": 100.0, "H": 50.0}
    assert result.name == "Widget"


def test_fetch_schema_org_dimensions_no_product_block_returns_none():
    fake_response = MagicMock()
    fake_response.text = "<html><body>no jsonld here</body></html>"
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.providers.schema_org.requests.get", return_value=fake_response):
        assert schema_org.fetch_schema_org_dimensions("https://example.com/nothing") is None


# --- providers/wikipedia.py -------------------------------------------------


def test_fetch_wikipedia_dimensions_parses_extract_text():
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "query": {"pages": {"123": {"extract": "The Widget measures 152 x 106 x 60 mm and weighs 246g."}}}
    }
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.providers.wikipedia.requests.get", return_value=fake_response):
        result = wikipedia.fetch_wikipedia_dimensions("Widget")

    assert result is not None
    assert result.dims_mm == {"L": 152.0, "W": 106.0, "H": 60.0}
    assert result.confidence == 0.4


def test_fetch_wikipedia_dimensions_no_match_returns_none():
    fake_response = MagicMock()
    fake_response.json.return_value = {"query": {"pages": {"123": {"extract": "no dims here"}}}}
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.providers.wikipedia.requests.get", return_value=fake_response):
        assert wikipedia.fetch_wikipedia_dimensions("Widget") is None


def test_fetch_wikipedia_dimensions_parses_pair_extract():
    # Integration check for the real gap found this investigation: the
    # "Credit card" Wikipedia article states its size as a 2-number "by"
    # pair, not a 3-number triplet - this is what lets that fallback
    # actually contribute L/W instead of silently matching nothing.
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "query": {"pages": {"123": {"extract": "The Widget measures 85.60 by 53.98 millimeters."}}}
    }
    fake_response.raise_for_status.return_value = None
    with patch("app.services.dimensions.providers.wikipedia.requests.get", return_value=fake_response):
        result = wikipedia.fetch_wikipedia_dimensions("Widget")

    assert result is not None
    assert result.dims_mm == {"L": 85.6, "W": 53.98}
    assert not result.is_complete()


# --- fetcher.py orchestration -----------------------------------------------


def test_fetch_dimensions_uses_qid_directly_when_given():
    wd_result = DimensionsResult(dims_mm={"L": 1, "W": 2, "H": 3}, source="Wikidata", confidence=0.9)
    with patch("app.services.dimensions.fetcher.fetch_wikidata_dimensions", return_value=wd_result) as mock_wd, patch(
        "app.services.dimensions.fetcher.search_wikidata_qid"
    ) as mock_search:
        result, resolved_qid = asyncio.run(fetch_dimensions(qid="Q123"))

    mock_search.assert_not_called()
    mock_wd.assert_called_once_with("Q123")
    assert resolved_qid == "Q123"
    assert result is wd_result


def test_fetch_dimensions_resolves_query_to_qid_first():
    wd_result = DimensionsResult(dims_mm={"L": 1, "W": 2, "H": 3}, source="Wikidata", confidence=0.9)
    with patch("app.services.dimensions.fetcher.search_wikidata_qid", return_value="Q999") as mock_search, patch(
        "app.services.dimensions.fetcher.fetch_wikidata_dimensions", return_value=wd_result
    ) as mock_wd:
        result, resolved_qid = asyncio.run(fetch_dimensions(query="some gadget"))

    mock_search.assert_called_once_with("some gadget")
    mock_wd.assert_called_once_with("Q999")
    assert resolved_qid == "Q999"
    assert result is wd_result


def test_fetch_dimensions_falls_back_to_urls_then_wikipedia():
    partial = DimensionsResult(name="Thing", dims_mm={"L": 10}, source="Wikidata", confidence=0.6)
    url_result = DimensionsResult(dims_mm={"W": 20}, source="schema.org Product markup", confidence=0.85)
    wiki_result = DimensionsResult(dims_mm={"H": 30}, source="Wikipedia (text extract)", confidence=0.4)

    with patch(
        "app.services.dimensions.fetcher.fetch_wikidata_dimensions", return_value=partial
    ), patch(
        "app.services.dimensions.fetcher.fetch_schema_org_dimensions", return_value=url_result
    ) as mock_schema, patch(
        "app.services.dimensions.fetcher.fetch_wikipedia_dimensions", return_value=wiki_result
    ) as mock_wiki:
        result, _ = asyncio.run(fetch_dimensions(qid="Q1", extra_urls=["https://example.com/a"]))

    mock_schema.assert_called_once_with("https://example.com/a")
    mock_wiki.assert_called_once()
    assert result.dims_mm == {"L": 10, "W": 20, "H": 30}
    assert result.is_complete()


def test_fetch_dimensions_no_sources_match_returns_none():
    with patch("app.services.dimensions.fetcher.fetch_wikidata_dimensions", return_value=None), patch(
        "app.services.dimensions.fetcher.fetch_wikipedia_dimensions", return_value=None
    ):
        result, resolved_qid = asyncio.run(fetch_dimensions(qid="Q1"))

    assert result is None
    assert resolved_qid == "Q1"
