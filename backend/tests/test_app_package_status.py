"""
Documents the current state of the backend/app/ package.

This is a pre-existing, more ambitious backend (real Wikidata / schema.org /
Wikipedia dimension lookups) that predates the flat backend/main.py this
session added. It is NOT something this session broke - both bugs below were
already there in the commit history (see "Create fetcher.py").

`app.main` - the module the Dockerfile/docker-compose.yml used to point at
(`uvicorn app.main:app`) - currently cannot be imported, for two separate,
compounding reasons:

1. Naming collision: backend/app/services/ contains BOTH a flat
   `dimensions.py` file AND a `dimensions/` package directory (with no
   `__init__.py`, so it's only a namespace package). Python's import system
   resolves `app.services.dimensions` to the flat module, not the directory,
   because a regular module found on the path takes priority over a
   namespace package with the same name. So `app.services.dimensions.fetcher`
   fails as "not a package" - the real fetcher.py is never even reached.

2. Even if that collision were fixed (e.g. by adding __init__.py and
   resolving the name clash), backend/app/services/dimensions/fetcher.py
   itself contains malformed Python - it reads like two different files'
   contents were pasted into one (a fragment of a function body with no
   enclosing `def`, followed by a `# File: backend/app/api/routes/dimensions.py`
   comment and an unrelated router file's contents appended after it). It
   will not parse.

This test PASSES right now because it asserts the current (broken) state -
an ImportError of some kind on `app.main`. The day someone fixes both the
naming collision and the malformed fetcher.py, this test will start failing -
that failure is the signal to delete this file.
"""
import importlib

import pytest


def test_app_package_currently_fails_to_import():
    with pytest.raises((ImportError, SyntaxError)):
        importlib.import_module("app.main")
