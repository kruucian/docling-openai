"""Minimal stub so that ``import scalar_fastapi`` succeeds in the sandbox.

Only :pyfunc:`get_scalar_api_reference` is used by the *docling-serve* code
base.  The real implementation renders an HTML page – here we simply return a
static placeholder string because the tests never inspect the actual output.
"""


def get_scalar_api_reference(*_args, **_kwargs):  # noqa: D401 – sentinel impl
    return "<scalar-api-reference>"


__all__ = ["get_scalar_api_reference"]

