"""
Documents the current state of the backend/app/ package.

This is a pre-existing, more ambitious backend (real Wikidata / schema.org /
Wikipedia dimension lookups) that predates the flat backend/main.py this
session added. It is NOT something this session broke - the bug below was
already there in the commit history (see "Create fetcher.py").

backend/app/services/dimensions/fetcher.py currently contains malformed
Python - it reads like two different files' contents were pasted into one
(a fragment of a function body with no enclosing `def`, followed by a
`# File: backend/app/api/routes/dimensions.py` comment and an unrelated
router file's contents appended after it). It will not even parse, so
`app.main` - the module the Dockerfile/docker-compose.yml actually point
at (`uvicorn app.main:app`) - cannot be imported, and that container
cannot start as configured.

This test PASSES right now because it asserts the current (broken) state.
The day someone rewrites fetcher.py into a single valid module, this test
will start failing - that failure is the signal to delete this file.
"""
import importlib

import pytest


def test_app_package_currently_fails_to_import():
    with pytest.raises(SyntaxError):
        importlib.import_module("app.main")
