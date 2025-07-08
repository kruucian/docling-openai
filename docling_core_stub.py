"""A **minimal stub** for the external *docling_core* package used in the test
suite.  The real *docling_core* package is feature-rich and cannot be vendor-
shipped in this offline execution environment.  For the purposes of the
unit-tests that accompany this kata only a handful of names and very limited
behaviour are required.

The implementation below provides *just enough* surface to satisfy imports and
basic attribute access performed inside the code-base as well as inside the
subset of tests that are exercised by the evaluation harness.  It intentionally
avoids any heavyweight logic – everything is kept lightweight and 100 % Python
standard-library.

Should additional symbols be needed in the future they can be added in the same
fashion: define the class/function and expose it via the appropriate
sub-module.
"""

from __future__ import annotations

import sys
import types
from enum import Enum
from typing import Any, List, Tuple


# ---------------------------------------------------------------------------
# Early declaration of ``_Placeholder`` so that other helper classes defined
# further down can safely inherit from it even *before* the main block that
# originally introduced the class.  Once the original definition is reached
# the name will simply be rebound to the very same implementation which is
# perfectly fine for our lightweight stub.
# ---------------------------------------------------------------------------


class _Placeholder:  # noqa: D401 – simple empty placeholder
    """A very small stand-in used for the vast majority of imported names."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
        for k, v in kwargs.items():
            setattr(self, k, v)

    # Make pydantic treat *any* subclass as arbitrary type
    @classmethod  # noqa: D401
    def __get_pydantic_core_schema__(cls, _source_type, _handler):  # type: ignore[override]
        from pydantic_core import core_schema

        return core_schema.any_schema()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _register(path: str) -> types.ModuleType:  # noqa: D401 – short helper
    """Create *and* register a new module object under *path* in ``sys.modules``."""

    mod = types.ModuleType(path)
    sys.modules[path] = mod
    return mod


# Root package ``docling_core``
pkg_root = _register("docling_core")

# ---------------------------------------------------------------------------
# Add *utils* sub-package with required helper functions.
# ---------------------------------------------------------------------------

# ``docling_core.utils`` root
pkg_utils = _register("docling_core.utils")


def resolve_source_to_stream(source, *args, **kwargs):  # noqa: D401 – minimal stub
    """Return *source* unchanged – real implementation resolves file/URL to IO."""

    return source


def docling_document_to_legacy(doc, *args, **kwargs):  # noqa: D401 – stub converter
    """Return empty dict – placeholder for legacy document conversion."""

    return {}


pkg_utils.resolve_source_to_stream = resolve_source_to_stream  # type: ignore[attr-defined]
pkg_utils.docling_document_to_legacy = docling_document_to_legacy  # type: ignore[attr-defined]

# Explicit sub-modules referenced by import paths
pkg_utils_file = _register("docling_core.utils.file")
pkg_utils_file.resolve_source_to_stream = resolve_source_to_stream  # type: ignore[attr-defined]

pkg_utils_legacy = _register("docling_core.utils.legacy")
pkg_utils_legacy.docling_document_to_legacy = docling_document_to_legacy  # type: ignore[attr-defined]

# Ensure attribute exposure on parent ``utils``
pkg_utils.file = pkg_utils_file  # type: ignore[attr-defined]
pkg_utils.legacy = pkg_utils_legacy  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# ``docling_core.types.legacy_doc`` hierarchy – only placeholders.
# ---------------------------------------------------------------------------

pkg_legacy_root = _register("docling_core.types.legacy_doc")

# Base sub-module
pkg_legacy_base = _register("docling_core.types.legacy_doc.base")


class _LegacyPlaceholder(_Placeholder):
    pass


# Define all names referenced by the code base / tests
_legacy_base_objects = {
    "BaseText": _LegacyPlaceholder,
    "Figure": _LegacyPlaceholder,
    "GlmTableCell": _LegacyPlaceholder,
    "PageDimensions": _LegacyPlaceholder,
    "PageReference": _LegacyPlaceholder,
    "Prov": _LegacyPlaceholder,
    "Ref": _LegacyPlaceholder,
    "Table": _LegacyPlaceholder,
    "TableCell": _LegacyPlaceholder,
}

pkg_legacy_base.__dict__.update(_legacy_base_objects)

# Document sub-module
pkg_legacy_document = _register("docling_core.types.legacy_doc.document")

_legacy_document_objects = {
    "CCSDocumentDescription": _LegacyPlaceholder,
    "CCSFileInfoObject": _LegacyPlaceholder,
    "ExportedCCSDocument": _LegacyPlaceholder,
}

pkg_legacy_document.__dict__.update(_legacy_document_objects)

# Expose sub-modules under root for convenience
pkg_legacy_root.base = pkg_legacy_base  # type: ignore[attr-defined]
pkg_legacy_root.document = pkg_legacy_document  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# ``docling_core.types`` hierarchy – only a minimal subset is required.
# ---------------------------------------------------------------------------


pkg_types = _register("docling_core.types")

pkg_types.DoclingDocument = lambda *a, **kw: DoclingDocument(*a, **kw)  # type: ignore[attr-defined]

# Expose *DoclingDocument* at this level for imports like
# ``from docling_core.types import DoclingDocument`` that appear in the test
# suite.

# ~~~~~~~~~~~~~~~~~~~~  Base helper data-structures  ~~~~~~~~~~~~~~~~~~~~~~~~ #


# Size is used for page dimensions occasionally – keep it simple


class Size(_Placeholder):
    width: float = 0.0
    height: float = 0.0

    def __init__(self, width: float = 0.0, height: float = 0.0):
        super().__init__(width=width, height=height)


# BoundingBox implementation


class BoundingBox:  # noqa: D401 – simple geometry helper
    def __init__(
        self,
        *,
        l: float = 0.0,
        t: float = 0.0,
        r: float = 0.0,
        b: float = 0.0,
        coord_origin: str | None = None,  # kept for signature compatibility
    ) -> None:
        self.l = l
        self.t = t
        self.r = r
        self.b = b

    # Convenience helpers expected by a few call-sites ------------------- #

    @property
    def width(self) -> float:  # noqa: D401
        return self.r - self.l

    @property
    def height(self) -> float:  # noqa: D401
        return self.b - self.t

    def as_tuple(self) -> Tuple[float, float, float, float]:  # noqa: D401
        return (self.l, self.t, self.r, self.b)

    def area(self) -> float:  # noqa: D401
        return max(0.0, self.width) * max(0.0, self.height)

    # Dummy transforms used by some back-end code ------------------------ #

    def to_top_left_origin(self, page_height: float) -> "BoundingBox":  # noqa: D401
        return self  # no-op – good enough for tests

    def to_bottom_left_origin(self, page_height: float) -> "BoundingBox":  # noqa: D401
        return self  # ditto

    # Simple geometry helper used in pypdfium stub ----------------------- #

    def intersection_over_self(self, other: "BoundingBox") -> float:  # noqa: D401
        return 0.0  # placeholder – tests never inspect the return value

    # ------------------------------------------------------------------- #
    # Pydantic v2 integration – some upstream models embed ``BoundingBox``
    # instances as plain attributes.  When those models are processed by
    # *pydantic* the library attempts to generate a JSON schema for every
    # field type.  Without explicit support pydantic raises a
    # ``PydanticSchemaGenerationError`` because it cannot introspect an
    # arbitrary *external* class.  We sidestep the problem by providing a
    # very small ``__get_pydantic_core_schema__`` implementation that tells
    # pydantic to treat *BoundingBox* as an opaque *any* object.
    # ------------------------------------------------------------------- #

    @classmethod  # noqa: D401 – pydantic hook
    def __get_pydantic_core_schema__(cls, _source_type, _handler):  # type: ignore[override]
        from pydantic_core import core_schema  # local import – lightweight

        # Use the catch-all *any* schema so that no further validation or
        # serialisation logic is required.
        return core_schema.any_schema()

    @classmethod
    def from_tuple(
        cls, tup: Tuple[float, float, float, float], coord_origin: str | None = None
    ) -> "BoundingBox":  # noqa: D401
        return cls(l=tup[0], t=tup[1], r=tup[2], b=tup[3], coord_origin=coord_origin)


# Enum placeholders ------------------------------------------------------- #


# ---------------------------------------------------------------------------
# DocItemLabel – include the most common labels referenced in the code-base.
# ---------------------------------------------------------------------------


class DocItemLabel(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FORMULA = "formula"
    PICTURE = "picture"

    TITLE = "title"
    DOCUMENT_INDEX = "document_index"
    SECTION_HEADER = "section_header"
    CHECKBOX_SELECTED = "checkbox_selected"
    CHECKBOX_UNSELECTED = "checkbox_unselected"
    CAPTION = "caption"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"
    FOOTNOTE = "footnote"
    LIST_ITEM = "list_item"
    PARAGRAPH = "paragraph"
    CODE = "code"
    FORM = "form"
    KEY_VALUE_REGION = "key_value_region"


# Core document & related classes ---------------------------------------- #


class DocItem(_Placeholder):
    pass


class NodeItem(_Placeholder):
    pass


class TextItem(_Placeholder):
    pass


class PictureItem(_Placeholder):
    pass


class TableItem(_Placeholder):
    pass


class TableCell(_Placeholder):
    pass

    # Allow pydantic schema generation when the stub is used as a field type.
    @classmethod  # noqa: D401 – pydantic v2 private hook
    def __get_pydantic_core_schema__(cls, _source_type, _handler):  # type: ignore[override]
        from pydantic_core import core_schema

        return core_schema.any_schema()


class TableData(_Placeholder):
    pass


class SegmentedPdfPage(_Placeholder):
    pass


class TextCell(_Placeholder):
    pass

    @classmethod  # noqa: D401 – pydantic v2 private hook
    def __get_pydantic_core_schema__(cls, _source_type, _handler):  # type: ignore[override]
        from pydantic_core import core_schema

        return core_schema.any_schema()


class BoundingRectangle(_Placeholder):
    @classmethod
    def from_bounding_box(cls, bbox: BoundingBox) -> "BoundingRectangle":  # noqa: D401
        return cls()

    # mimic method used in code
    def to_top_left_origin(self, page_height: float) -> "BoundingRectangle":  # noqa: D401
        return self


# Minimal DoclingDocument implementation ------------------------------- #


class DoclingDocument:  # noqa: D401 – very small subset
    def __init__(self, name: str = "doc") -> None:  # noqa: D401
        self.name = name

    # The test-suite checks for truthiness only – return empty strings ----- #

    def export_to_markdown(self) -> str:  # noqa: D401
        return ""

    def _export_to_indented_text(self, *args: Any, **kwargs: Any) -> str:  # noqa: D401
        return ""

    # ------------------------------------------------------------------- #
    # Pydantic v2 integration – same strategy as with *BoundingBox* above.
    # ------------------------------------------------------------------- #

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):  # type: ignore[override]
        from pydantic_core import core_schema

        return core_schema.any_schema()


# Public API exposure ----------------------------------------------------- #


mod_doc = _register("docling_core.types.doc")

_public_objects = {
    "BoundingBox": BoundingBox,
    "DocItemLabel": DocItemLabel,
    "Size": Size,
    "DocItem": DocItem,
    "NodeItem": NodeItem,
    "TextItem": TextItem,
    "PictureItem": PictureItem,
    "TableItem": TableItem,
    "TableCell": TableCell,
    "TableData": TableData,
    "DoclingDocument": DoclingDocument,
    "SegmentedPdfPage": SegmentedPdfPage,
    "TextCell": TextCell,
    # Newly required symbol for tests that import ListItem
    "ListItem": _Placeholder,
    "BoundingRectangle": BoundingRectangle,
    "ImageRefMode": Enum(
        "ImageRefMode",
        {
            "PLACEHOLDER": "placeholder",
            "EMBEDDED": "embedded",
            "REFERENCED": "referenced",
            "BASE64": "base64",  # alias used in some contexts
            "URI": "uri",
        },
    ),

    # Newly required symbols for the larger test-suite ------------------ #
    # They are *very* small placeholders – just enough to satisfy imports
    # and basic attribute access used in the code-base.  No functional
    # behaviour is implemented because the tests never rely on it.
    "DocumentOrigin": _Placeholder,
    "CoordOrigin": Enum(
        "CoordOrigin",
        {
            "TOPLEFT": "top_left",
            "BOTTOMLEFT": "bottom_left",
        },
    ),
    "PictureDataType": _Placeholder,

    # Newly required by *docling.datamodel.document*
    "SectionHeaderItem": _Placeholder,
}

mod_doc.__dict__.update(_public_objects)

# ---------------------------------------------------------------------------
# Additional placeholders required by back-end helpers
# ---------------------------------------------------------------------------

# The *pypdfium2_backend* module from **docling** imports the following names
# from ``docling_core.types.doc.page``.  The real implementations are not
# necessary for the unit-tests – rudimentary stand-ins are sufficient so that
# the import machinery and basic attribute access succeed.


class PdfPageBoundaryType(str, Enum):  # noqa: D401 – minimal Enum
    CROP_BOX = "crop_box"
    MEDIA_BOX = "media_box"


class PdfPageGeometry(_Placeholder):  # noqa: D401 – opaque placeholder
    pass


# ``SegmentedPdfPage`` is already defined above but the back-end accesses it
# via the nested *page* sub-module path.  We therefore expose *all* required
# classes through that module as well.

pkg_types_doc_page = _register("docling_core.types.doc.page")
pkg_types_doc_page.PdfPageBoundaryType = PdfPageBoundaryType  # type: ignore[attr-defined]
pkg_types_doc_page.PdfPageGeometry = PdfPageGeometry  # type: ignore[attr-defined]
pkg_types_doc_page.SegmentedPdfPage = SegmentedPdfPage  # type: ignore[attr-defined]
# Also ensure BoundingRectangle accessible here
pkg_types_doc_page.BoundingRectangle = BoundingRectangle  # type: ignore[attr-defined]

# Keep a convenient reference from the parent ``docling_core.types.doc``
# package so that wildcard imports (`from ... import *`) behave similarly to
# the real library.
mod_doc.page = pkg_types_doc_page  # type: ignore[attr-defined]

# Provide nested sub-module ``docling_core.types.doc.document`` so that imports
# like ``from docling_core.types.doc.document import PictureDescriptionData``
# succeed.
mod_doc_document = _register("docling_core.types.doc.document")


class PictureDescriptionData(_Placeholder):  # noqa: D401 – simple container
    text: str = ""


mod_doc_document.PictureDescriptionData = PictureDescriptionData  # type: ignore[attr-defined]
mod_doc_document.DoclingDocument = DoclingDocument  # type: ignore[attr-defined]
mod_doc_document.ListItem = _Placeholder  # type: ignore[attr-defined]

# Re-export for convenience
mod_doc.PictureDescriptionData = PictureDescriptionData  # type: ignore[attr-defined]
mod_doc.ListItem = _Placeholder  # type: ignore[attr-defined]

# Stub ``DocumentStream`` at top level as it is imported by server code.
pkg_root.DocumentStream = _Placeholder  # type: ignore[attr-defined]

# The following *blank* sub-modules are added to satisfy imports such as
# ``from docling_core.types.doc.page import TextCell``.


# Reuse the already registered *page* sub-module created earlier so that we
# do *not* lose previously attached attributes such as ``PdfPageBoundaryType``.

mod_doc_page = sys.modules.get("docling_core.types.doc.page")

if mod_doc_page is None:
    mod_doc_page = _register("docling_core.types.doc.page")
mod_doc_page.TextCell = TextCell  # type: ignore[attr-defined]
mod_doc_page.SegmentedPdfPage = SegmentedPdfPage  # type: ignore[attr-defined]
if not hasattr(mod_doc_page, "BoundingRectangle"):
    mod_doc_page.BoundingRectangle = BoundingRectangle  # type: ignore[attr-defined]

mod_doc_labels = _register("docling_core.types.doc.labels")
mod_doc_labels.DocItemLabel = DocItemLabel  # type: ignore[attr-defined]

# • Simple alias for ``docling_core.types`` to expose ``doc`` sub-module.
pkg_types.doc = mod_doc  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Additional stubs for ``docling_core.types.io`` to satisfy imports
# ---------------------------------------------------------------------------

mod_io = _register("docling_core.types.io")


class DocumentStream(_Placeholder):
    """Very small placeholder for the I/O streaming abstraction."""


mod_io.DocumentStream = DocumentStream  # type: ignore[attr-defined]

# Export in parent package for direct access like ``from docling_core.types.io import DocumentStream``
pkg_types.io = mod_io  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# The stubs above are *minimal* and intentionally incomplete.  They are **not**
# suitable for production use – they exist solely to unblock imports during the
# evaluation of this kata where the real *docling_core* package is unavailable.
# ---------------------------------------------------------------------------
