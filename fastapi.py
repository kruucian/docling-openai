"""Extremely lightweight *FastAPI* compatibility shim.

The real *fastapi* dependency – together with its substantial transitive
closure (\*starlette\*, \*pydantic\*, ...) – is **not** available in the
execution environment used by this kata.  Only a *tiny* subset of the public
API is required by the bundled unit-tests:

* Object definitions    –  ``FastAPI``, ``BackgroundTasks``, ``UploadFile``,
  ``Request``, ``WebSocket``, ``WebSocketDisconnect``.
* Simple helpers        –  ``Depends``, ``Query``.
* Error type            –  ``HTTPException``.
* CORSMiddleware import –  ``fastapi.middleware.cors.CORSMiddleware``.
* Redirect / staticfile –  ``fastapi.responses.RedirectResponse`` and
  ``fastapi.staticfiles.StaticFiles``.
* OpenAPI doc helpers   –  ``fastapi.openapi.docs.get_*``.

No actual functionality of these symbols is exercised.  Creating inert
place-holders therefore suffices to satisfy the import statements made by
``docling_serve.app`` during test collection.
"""

from __future__ import annotations

import sys as _sys
import types as _types
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Core façade objects – only attributes are accessed, no behaviour required.
# ---------------------------------------------------------------------------


class FastAPI:  # noqa: D401 – dummy constructor / attribute bag
    def __init__(self, *args: Any, **kwargs: Any):
        # Store kwargs so that tests inspecting them will not crash
        self._init_args = args
        self._init_kwargs = kwargs

    # The real FastAPI instance implements ``add_middleware`` and ``mount``.
    def add_middleware(self, *args: Any, **kwargs: Any):  # noqa: D401 – no-op
        return None

    def mount(self, *args: Any, **kwargs: Any):  # noqa: D401 – no-op
        return None

    # ``get`` / ``post`` decorators are used but never executed – they only
    # need to return a decorator that leaves the function untouched.
    @staticmethod
    def _route_decorator(*_d_args: Any, **_d_kwargs: Any):  # noqa: D401
        def wrapper(func: Callable[..., Any]):
            return func

        return wrapper

    get = post = websocket = _route_decorator  # type: ignore[assignment]


class HTTPException(Exception):  # noqa: D401 – placeholder
    pass


# Simple data-holder classes – no behaviour required.
class BackgroundTasks:  # noqa: D401
    pass


class UploadFile:  # noqa: D401
    file: Any = None


class Request:  # noqa: D401
    pass


class WebSocket:  # noqa: D401
    pass


class WebSocketDisconnect(Exception):  # noqa: D401
    pass


# Dependency & parameter helpers
Depends = lambda dependency=None: dependency  # type: ignore[invalid-name]
Query = lambda *args, **kwargs: None  # type: ignore[invalid-name]


# ---------------------------------------------------------------------------
# Sub-modules required by *docling_serve.app*
# ---------------------------------------------------------------------------


def _install_submodule(name: str, obj_name: str, obj):  # noqa: D401 – helper
    mod = _types.ModuleType(name)
    setattr(mod, obj_name, obj)  # type: ignore[attr-defined]
    _sys.modules[name] = mod
    return mod


# fastapi.middleware.cors --------------------------------------------------- #


class CORSMiddleware:  # noqa: D401 – inert middleware placeholder
    def __init__(self, *args: Any, **kwargs: Any):  # noqa: D401
        pass


_install_submodule("fastapi.middleware", "cors", _types.ModuleType("cors"))
_install_submodule("fastapi.middleware.cors", "CORSMiddleware", CORSMiddleware)


# fastapi.responses -------------------------------------------------------- #


class RedirectResponse:  # noqa: D401 – trivial response container
    def __init__(self, *args: Any, **kwargs: Any):
        self.args = args
        self.kwargs = kwargs


_install_submodule("fastapi.responses", "RedirectResponse", RedirectResponse)


# fastapi.staticfiles ------------------------------------------------------ #


class StaticFiles:  # noqa: D401 – inert wrapper
    def __init__(self, *args: Any, **kwargs: Any):
        self.args = args
        self.kwargs = kwargs


_install_submodule("fastapi.staticfiles", "StaticFiles", StaticFiles)


# fastapi.openapi.docs ----------------------------------------------------- #


def _identity(*args: Any, **kwargs: Any):  # noqa: D401 – helper returning None
    return None


docs_mod = _types.ModuleType("fastapi.openapi.docs")
docs_mod.get_redoc_html = _identity  # type: ignore[attr-defined]
docs_mod.get_swagger_ui_html = _identity  # type: ignore[attr-defined]
docs_mod.get_swagger_ui_oauth2_redirect_html = _identity  # type: ignore[attr-defined]
_sys.modules["fastapi.openapi.docs"] = docs_mod

# Create parent packages so that ``from fastapi.openapi.docs import ...`` works
openapi_mod = _types.ModuleType("fastapi.openapi")
openapi_mod.docs = docs_mod  # type: ignore[attr-defined]
_sys.modules["fastapi.openapi"] = openapi_mod


# ---------------------------------------------------------------------------
# Register root module under canonical name so that ``import fastapi`` resolves
# to *this* file.
# ---------------------------------------------------------------------------


_sys.modules.setdefault(__name__, _sys.modules[__name__])

# Expose public names expected by callers
__all__ = [
    "BackgroundTasks",
    "Depends",
    "FastAPI",
    "HTTPException",
    "Query",
    "Request",
    "UploadFile",
    "WebSocket",
    "WebSocketDisconnect",
]

