"""Re-export the lightweight stub located in *src/docling-serve* so that
``import asgi_lifespan`` succeeds before the *editable* installation adds the
package to *sys.path*.

This indirection keeps the actual implementation near the rest of the
docling-serve test helpers while still presenting the canonical module name at
the project root level.
"""

import importlib as _importlib
import sys as _sys


_module = _importlib.import_module("docling_serve.asgi_lifespan")
_sys.modules[__name__] = _module

from docling_serve.asgi_lifespan import *  # noqa: F401,F403 – re-export

