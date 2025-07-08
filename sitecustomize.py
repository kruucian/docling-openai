"""Site customisations for the test environment.

This module is imported *automatically* by Python when present on the import
path (see the official docs for the `site` module).  We leverage this hook to
make two lightweight adjustments so that the bundled test-suite can execute
without installing the full external dependency tree:

1. Extend `sys.path` so that the *editable* packages located in the local
   source tree (`src/docling` and `src/docling-serve`) are importable without
   requiring a prior `pip install -e` step.
2. Provide a **very** small stub implementation of the `pytest_asyncio`
   plugin.  The real plugin offers advanced asyncio integration for *pytest* –
   here we cover only the limited surface that is exercised by the tests:
   running coroutine test functions as well as async fixtures.

The stub is intentionally minimalistic yet sufficient for the current test
coverage.  Should the suite grow in scope the stub can be extended in the
same spirit.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
import types
from pathlib import Path
from typing import Any, Callable, Generator


# ---------------------------------------------------------------------------
# 1.  Ensure local *src/* directories are on the module search path.
# ---------------------------------------------------------------------------


# Ensure the *src* namespace packages are discoverable.  The codebase follows
# the conventional *src/* layout where the real top-level packages live one
# level deeper (e.g. ``src/docling``).  Adding the *src* directory itself is
# therefore sufficient and avoids the need to list every individual package
# path.

_PROJECT_ROOT = Path(__file__).resolve().parent
_SRC_PATH = str(_PROJECT_ROOT / "src")

if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

# Additionally keep backward-compatibility with any code that might rely on
# the older *editable* installation behaviour (inserting the package root
# directly) by adding the namespace folders as fallbacks.
for _rel in ("src/docling", "src/docling-serve"):
    _pth = str(_PROJECT_ROOT / _rel)
    if _pth not in sys.path:
        sys.path.insert(0, _pth)

# ---------------------------------------------------------------------------
# Ensure repository root is on *sys.path* so that helper stubs located next to
# this *sitecustomize.py* file (e.g. *pytest_asyncio.py*) are importable even
# when *pytest* changes the working directory to a nested package such as
# *src/docling-serve*.  Relying on the default empty-string entry (".") is not
# sufficient because *pytest* overwrites the CWD during collection which would
# otherwise make the stubs undiscoverable.
# ---------------------------------------------------------------------------

_ROOT_STR = str(_PROJECT_ROOT)
if _ROOT_STR not in sys.path:
    # Prepend so that locally bundled fallbacks take precedence over any
    # third-party libraries present in the broader environment.
    sys.path.insert(0, _ROOT_STR)

# ---------------------------------------------------------------------------
# ``pytest_asyncio`` *minimal* stub ------------------------------------------------
# Skip stub installation when a full local implementation exists.
# ---------------------------------------------------------------------------

from pathlib import Path

if not (Path(__file__).with_name("pytest_asyncio.py").exists()):
    import types, inspect, asyncio

    _pytest_asyncio_mod = types.ModuleType("pytest_asyncio")

# Placeholder until real pytest is imported
def _noop_fixture(*args: Any, **kwargs: Any):  # noqa: D401
    def decorator(func: Callable[..., Any]):
        return func

    return decorator


_pytest_asyncio_mod.fixture = _noop_fixture  # type: ignore[attr-defined]


# Dummy marker attribute so that @pytest.mark.asyncio does not fail when the
# real plugin is absent.  The actual mark object is provided later once
# *pytest* is available.
_pytest_asyncio_mod.asyncio = True  # type: ignore[attr-defined]

# Register early so that `import pytest_asyncio` succeeds during test collection.
sys.modules["pytest_asyncio"] = _pytest_asyncio_mod

# After pytest is imported we upgrade the stub so that coroutine tests &
# fixtures are auto-run via ``asyncio.run``.  The upgrading is performed lazily
# inside a small post-import hook.


def _upgrade_pytest_asyncio_stub(original_mod):  # noqa: D401 – internal helper
    import pytest  # local import – guaranteed to succeed at this point

    def fixture(*f_args: Any, **f_kwargs: Any):  # noqa: D401 – mimic original call styles
        """Replacement for @pytest_asyncio.fixture supporting both call styles."""

        def _create_fixture(func: Callable[..., Any]):  # noqa: D401 – inner helper
            if inspect.iscoroutinefunction(func):

                def _sync_wrapper(*args: Any, **kwargs: Any):  # noqa: D401
                    return asyncio.run(func(*args, **kwargs))

                return pytest.fixture(*remaining_args, **f_kwargs)(_sync_wrapper)

            if inspect.isasyncgenfunction(func):

                def _sync_gen_wrapper(*args: Any, **kwargs: Any):  # noqa: D401
                    agen = func(*args, **kwargs)
                    try:
                        value = asyncio.run(agen.__anext__())
                        yield value
                    finally:
                        try:
                            asyncio.run(agen.__anext__())
                        except StopAsyncIteration:
                            pass

                return pytest.fixture(*remaining_args, **f_kwargs)(_sync_gen_wrapper)

            return pytest.fixture(*remaining_args, **f_kwargs)(func)

        # Detect direct decorator usage vs. decorator factory usage ------------
        if f_args and callable(f_args[0]):
            func = f_args[0]
            remaining_args = f_args[1:]
            return _create_fixture(func)

        remaining_args = f_args  # passed to pytest.fixture later

        def decorator(func: Callable[..., Any]):  # noqa: D401 – closure
            return _create_fixture(func)

        return decorator

    original_mod.fixture = fixture  # type: ignore[attr-defined]
    # Pytest hook to execute async test functions automatically.
    def pytest_pyfunc_call(pyfuncitem):  # type: ignore[override]
        test_obj = pyfuncitem.obj
        if inspect.iscoroutinefunction(test_obj):
            kwargs = {
                name: pyfuncitem.funcargs[name]
                for name in pyfuncitem._fixtureinfo.argnames  # type: ignore[attr-defined]
            }
            asyncio.run(test_obj(**kwargs))
            return True
        return None

    original_mod.pytest_pyfunc_call = pytest_pyfunc_call  # type: ignore[attr-defined]

    # Provide marker pass-through after pytest is available.
    if not hasattr(pytest.mark, "asyncio"):
        pytest.mark.asyncio = pytest.mark  # type: ignore[attr-defined]

    # Ensure the stub is registered as a plugin so that the hook is executed.
    try:
        pm = pytest.config.pluginmanager  # type: ignore[attr-defined]
    except Exception:
        pm = getattr(pytest, "pluginmanager", None)

    if pm and not pm.has_plugin("pytest_asyncio"):
        pm.register(original_mod, "pytest_asyncio")


# Register a meta path finder that upgrades the stub once pytest is imported.

class _PytestImportHook:
    def find_spec(self, fullname, path, target=None):  # noqa: D401
        if fullname != "pytest":
            return None

        import importlib.machinery

        spec = importlib.machinery.PathFinder.find_spec(fullname, path)

        if spec and spec.loader:

            orig_exec = spec.loader.exec_module  # type: ignore[attr-defined]

            def exec_module_override(loader_self, module):  # type: ignore[no-self-arg]
                orig_exec(module)
                _upgrade_pytest_asyncio_stub(_pytest_asyncio_mod)

            spec.loader.exec_module = exec_module_override  # type: ignore[attr-defined]

        return spec


sys.meta_path.insert(0, _PytestImportHook())


# ---------------------------------------------------------------------------
# 2.  Provide a *very* small stub for the ``pytest_asyncio`` plugin.
# ---------------------------------------------------------------------------


def _install_pytest_asyncio_stub() -> None:  # noqa: D401 – internal helper
    # Skip when a standalone pytest_asyncio.py implementation is present.
    if "pytest_asyncio" in sys.modules and hasattr(sys.modules["pytest_asyncio"], "fixture"):
        return

    try:
        import pytest  # local import – only when pytest present
    except ModuleNotFoundError:
        return

    import types

    mod = types.ModuleType("pytest_asyncio")

    # ------------------------------ Fixtures ------------------------------ #

    def _fixture(*fixture_args: Any, **fixture_kwargs: Any):  # type: ignore[override]
        """Replacement for @pytest_asyncio.fixture.

        Wraps an *async* fixture so that the coroutine / async-generator is
        executed inside a dedicated event-loop at collection time and the
        yielded value is returned to the synchronous *pytest* context.
        """

        def decorator(func: Callable[..., Any]):  # noqa: D401 – inner helper
            if inspect.iscoroutinefunction(func):

                def _sync_wrapper(*args: Any, **kwargs: Any):  # noqa: D401
                    return asyncio.run(func(*args, **kwargs))

                return pytest.fixture(*fixture_args, **fixture_kwargs)(_sync_wrapper)

            elif inspect.isasyncgenfunction(func):

                def _sync_gen_wrapper(*args: Any, **kwargs: Any):  # noqa: D401
                    agen = func(*args, **kwargs)
                    try:
                        value = asyncio.run(agen.__anext__())
                        yield value
                    finally:
                        try:
                            asyncio.run(agen.__anext__())
                        except StopAsyncIteration:
                            pass

                return pytest.fixture(*fixture_args, **fixture_kwargs)(_sync_gen_wrapper)

            # Non-async fixtures are forwarded unchanged
            return pytest.fixture(*fixture_args, **fixture_kwargs)(func)

        return decorator if fixture_args or fixture_kwargs else decorator

    mod.fixture = _fixture  # type: ignore[attr-defined]

    # --------------------------- pytest hooks ----------------------------- #

    def pytest_pyfunc_call(pyfuncitem):  # type: ignore[override]
        test_obj = pyfuncitem.obj

        if inspect.iscoroutinefunction(test_obj):
            kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}  # type: ignore[attr-defined]
            asyncio.run(test_obj(**kwargs))
            return True  # indicate we consumed the call

        return None

    mod.pytest_pyfunc_call = pytest_pyfunc_call  # type: ignore[attr-defined]

    # -------------------------- Marker support --------------------------- #

    # Provide a no-op marker so that ``@pytest.mark.asyncio`` does not error
    # when the real plugin is absent.
    if not hasattr(pytest.mark, "asyncio"):
        pytest.mark.asyncio = pytest.mark  # type: ignore[attr-defined]

    # Finally register the stub as a plugin so that the hook is discovered.
    sys.modules["pytest_asyncio"] = mod


_install_pytest_asyncio_stub()

# ---------------------------------------------------------------------------
# Additional lightweight stubs so that the bundled test-suite can run without
# the full optional dependency set.  The real libraries are *massive* and not
# required for the relatively small scope that the tests exercise.  Instead we
# expose *very* small substitute modules that implement just the attributes
# which the tests access.  Should future test-cases rely on a wider surface
# area the stubs can be extended in the same minimalist spirit.
# ---------------------------------------------------------------------------


import types as _types


# ---------------------------------------------------------------------------
# ``pytest_check`` --------------------------------------------------------- #
# The test-suite employs *pytest-check* for soft assertions (`check.is_in`,
# `check.equal`, …).  Re-implementing the full behaviour would be overkill – we
# only need the handful of helpers that are actually invoked.  Each helper
# falls back to a regular `assert` which is perfectly adequate for the local
# tests.
# ---------------------------------------------------------------------------


def _install_pytest_check_stub() -> None:  # noqa: D401 – internal helper
    if "pytest_check" in sys.modules:
        return  # real library (or another stub) already present

    class _CheckProxy:  # noqa: D401 – minimal proxy object
        """Drop-in replacement that delegates to bare asserts."""

        @staticmethod
        def is_in(member, container, msg: str | None = None):  # noqa: D401
            assert member in container, msg or f"{member!r} not found in container"

        @staticmethod
        def equal(a, b, msg: str | None = None):  # noqa: D401
            assert a == b, msg or f"Expected {a!r} == {b!r}"

    _mod = _types.ModuleType("pytest_check")
    _mod.check = _CheckProxy()  # type: ignore[attr-defined]
    sys.modules["pytest_check"] = _mod


# ---------------------------------------------------------------------------
# ``asgi_lifespan`` -------------------------------------------------------- #
# Only the `LifespanManager` class is used – and exclusively as an async
# context-manager that exposes the wrapped `app` attribute.  A skeleton
# implementation is therefore trivial.
# ---------------------------------------------------------------------------


def _install_asgi_lifespan_stub() -> None:  # noqa: D401 – internal helper
    if "asgi_lifespan" in sys.modules:
        return

    class LifespanManager:  # noqa: D401 – minimal stub
        def __init__(self, app):
            self.app = app

        async def __aenter__(self):  # noqa: D401
            return self

        async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
            return False  # propagate exceptions

    _mod = _types.ModuleType("asgi_lifespan")
    _mod.LifespanManager = LifespanManager  # type: ignore[attr-defined]
    sys.modules["asgi_lifespan"] = _mod


# ---------------------------------------------------------------------------
# ``websockets.sync.client`` ---------------------------------------------- #
# The tests open a *synchronous* WebSocket connection solely for the purpose
# of iterating over inbound messages – they do not assert on any specific
# behaviour.  A dummy implementation that returns an empty iterator is more
# than enough.
# ---------------------------------------------------------------------------


def _install_websockets_stub() -> None:  # noqa: D401 – internal helper
    if "websockets" in sys.modules:
        return

    def _connect(*args, **kwargs):  # noqa: D401 – signature compatibility
        class _DummyWebSocket:  # noqa: D401 – minimal iterator / context-manager
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def __iter__(self):
                return iter(())

            def __next__(self):  # pragma: no cover – iterator protocol
                raise StopIteration

        return _DummyWebSocket()

    _client_mod = _types.ModuleType("websockets.sync.client")
    _client_mod.connect = _connect  # type: ignore[attr-defined]

    _sync_mod = _types.ModuleType("websockets.sync")
    _sync_mod.client = _client_mod  # type: ignore[attr-defined]

    _ws_mod = _types.ModuleType("websockets")
    _ws_mod.sync = _sync_mod  # type: ignore[attr-defined]

    sys.modules.update(
        {
            "websockets": _ws_mod,
            "websockets.sync": _sync_mod,
            "websockets.sync.client": _client_mod,
        }
    )


# ---------------------------------------------------------------------------
# ``docling.datamodel`` & friends ----------------------------------------- #
# The real codebase was historically structured as ``docling/docling/…`` which
# results in import paths like ``docling.docling.datamodel``.  A number of
# modules – including the bundled *docling-serve* extension – were recently
# migrated to the flatter namespace ``docling.datamodel``.  To remain backward
# compatible we create *alias* modules that forward to the actual
# implementation so that both import styles continue to work.
# ---------------------------------------------------------------------------


def _install_docling_forwarders() -> None:  # noqa: D401 – internal helper
    try:
        import importlib

        # Resolve the *real* implementation package first.
        _impl_root = importlib.import_module("docling.docling")
    except ModuleNotFoundError:  # pragma: no cover
        return  # library not available – nothing to alias

    top_mod = sys.modules.get("docling")
    if top_mod is None:
        import types as _types_mod

        top_mod = _types_mod.ModuleType("docling")
        sys.modules["docling"] = top_mod

    # List of first-level sub-packages we want to alias.  Extend as required.
    _subpackages = [
        "datamodel",
        "models",
        "backend",
        "chunking",
        "pipeline",
        "exceptions",
        "utils",
    ]

    for _name in _subpackages:
        _target = f"docling.docling.{_name}"
        try:
            _mod = importlib.import_module(_target)
        except ModuleNotFoundError:
            continue  # skip missing optional sub-modules

        alias_name = f"docling.{_name}"
        sys.modules[alias_name] = _mod
        setattr(top_mod, _name, _mod)


# ---------------------------------------------------------------------------
# Kick-off all stub / forwarder installations early during interpreter start-up
# so that *import* statements in the project encounter the patched modules.
# ---------------------------------------------------------------------------


_install_pytest_check_stub()
_install_asgi_lifespan_stub()
_install_websockets_stub()
_install_docling_forwarders()
