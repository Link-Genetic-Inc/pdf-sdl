"""
DataDef Builder
================
Fluent builder API for constructing DataDef objects.

Provides factory methods for all 18 standard DataTypes and a chainable
builder for the common DataDef entries.

Example::

    from pdf_sdl.builder import DataDefBuilder

    datadef = (
        DataDefBuilder.table()
        .with_source("SAP S/4HANA, Q4 2024")
        .with_schema("https://schema.org/FinancialStatement")
        .trust_author(generator="Acme Report Builder v3.2")
        .bind_to_struct("35 0 R")
        .build({"period": "FY2024", "rows": [...]})
    )
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..models.datadef import (
    DataDef,
    DataFormat,
    DataType,
    TrustLevel,
)


class DataDefBuilder:
    """
    Fluent builder for DataDef objects.

    Typically instantiated via the factory class methods (e.g. DataDefBuilder.table()).
    """

    def __init__(self, data_type: DataType, format: DataFormat = DataFormat.JSON) -> None:
        self._data_type = data_type
        self._format = format
        self._encoding: str = "UTF-8"
        self._schema_uri: str | None = None
        self._schema_version: str | None = None
        self._source: str | None = None
        self._created: datetime | None = None
        self._generator: str | None = None
        self._trust_level: TrustLevel | None = None
        self._confidence: float | None = None
        self._struct_ref: str | None = None
        self._annot_ref: str | None = None
        self._page_ref: int | None = None
        self._rect: tuple[float, float, float, float] | None = None
        self._status_uri: str | None = None

    # ------------------------------------------------------------------
    # Factory methods for all 18 DataTypes
    # ------------------------------------------------------------------

    @classmethod
    def table(cls, format: DataFormat = DataFormat.JSON) -> "DataDefBuilder":
        """Tabular data (financial statements, statistics, comparison tables)."""
        return cls(DataType.TABLE, format)

    @classmethod
    def record(cls, format: DataFormat = DataFormat.JSON) -> "DataDefBuilder":
        """Single structured record (invoice, patient record, case metadata)."""
        return cls(DataType.RECORD, format)

    @classmethod
    def value(cls, format: DataFormat = DataFormat.JSON) -> "DataDefBuilder":
        """Single data point or metric (KPI, measurement, score)."""
        return cls(DataType.VALUE, format)

    @classmethod
    def series(cls, format: DataFormat = DataFormat.JSON) -> "DataDefBuilder":
        """Time series or ordered sequence (stock prices, sensor data)."""
        return cls(DataType.SERIES, format)

    @classmethod
    def chart(cls, format: DataFormat = DataFormat.JSON) -> "DataDefBuilder":
        """Data underlying a visual chart (bar, line, pie chart)."""
        return cls(DataType.CHART, format)

    @classmethod
    def form(cls, format: DataFormat = DataFormat.JSON) -> "DataDefBuilder":
        """Structured form data with field semantics."""
        return cls(DataType.FORM, format)

    @classmethod
    def link(cls) -> "DataDefBuilder":
        """
        Internet reference with metadata (Issue #725).
        Use LinkMetaBuilder for standalone LinkMeta dictionaries.
        """
        return cls(DataType.LINK, DataFormat.JSON)

    @classmethod
    def reference(cls, format: DataFormat = DataFormat.JSON) -> "DataDefBuilder":
        """Bibliographic or documentary citation."""
        return cls(DataType.REFERENCE, format)

    @classmethod
    def formula(cls) -> "DataDefBuilder":
        """Mathematical/logical expression (LaTeX + MathML)."""
        return cls(DataType.FORMULA, DataFormat.JSON)

    @classmethod
    def code(cls) -> "DataDefBuilder":
        """Source code or executable snippet."""
        return cls(DataType.CODE, DataFormat.JSON)

    @classmethod
    def measurement(cls) -> "DataDefBuilder":
        """Dimensional or physical measurement."""
        return cls(DataType.MEASUREMENT, DataFormat.JSON)

    @classmethod
    def geospatial(cls) -> "DataDefBuilder":
        """Location or geographic data (GeoJSON)."""
        return cls(DataType.GEOSPATIAL, DataFormat.JSON)

    @classmethod
    def timeline(cls) -> "DataDefBuilder":
        """Chronological event sequence (milestones, phases)."""
        return cls(DataType.TIMELINE, DataFormat.JSON)

    @classmethod
    def classification(cls) -> "DataDefBuilder":
        """Document/element classification (confidentiality, retention, regime)."""
        return cls(DataType.CLASSIFICATION, DataFormat.JSON)

    @classmethod
    def provenance(cls) -> "DataDefBuilder":
        """Content origin and generation method (EU AI Act compliance)."""
        return cls(DataType.PROVENANCE, DataFormat.JSON)

    @classmethod
    def identity(cls) -> "DataDefBuilder":
        """Structured party/signer identity."""
        return cls(DataType.IDENTITY, DataFormat.JSON)

    @classmethod
    def translation(cls) -> "DataDefBuilder":
        """Translation metadata and source binding."""
        return cls(DataType.TRANSLATION, DataFormat.JSON)

    @classmethod
    def custom(cls, schema_uri: str, format: DataFormat = DataFormat.JSON) -> "DataDefBuilder":
        """Domain-specific data. Requires schema_uri (§4.11)."""
        b = cls(DataType.CUSTOM, format)
        b._schema_uri = schema_uri
        return b

    # ------------------------------------------------------------------
    # Builder chain methods
    # ------------------------------------------------------------------

    def with_source(self, source: str) -> "DataDefBuilder":
        """Origin system or description."""
        self._source = source
        return self

    def with_schema(
        self, uri: str, version: str | None = None
    ) -> "DataDefBuilder":
        """URI to a formal schema definition. Upgrades to SDL Schema conformance."""
        self._schema_uri = uri
        self._schema_version = version
        return self

    def with_encoding(self, encoding: str) -> "DataDefBuilder":
        self._encoding = encoding
        return self

    def with_status_uri(self, uri: str) -> "DataDefBuilder":
        """Opt-in live status URI. Never queried automatically."""
        self._status_uri = uri
        return self

    # --- Trust levels (§6) ---

    def trust_signed(self) -> "DataDefBuilder":
        """
        Mark as Signed – DataDef is within digital signature scope.
        Highest trust level; no additional keys required here.
        """
        self._trust_level = TrustLevel.SIGNED
        return self

    def trust_author(
        self,
        generator: str,
        created: datetime | None = None,
    ) -> "DataDefBuilder":
        """
        Mark as Author – created at authoring time.
        Upgrades to SDL Provenance conformance when combined with schema + source.
        """
        self._trust_level = TrustLevel.AUTHOR
        self._generator = generator
        self._created = created or datetime.now(tz=timezone.utc)
        return self

    def trust_enriched(
        self,
        generator: str,
        confidence: float,
        created: datetime | None = None,
    ) -> "DataDefBuilder":
        """
        Mark as Enriched – added post-creation by AI/tools.
        Requires confidence score (0.0–1.0) per §6.1.
        """
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        self._trust_level = TrustLevel.ENRICHED
        self._generator = generator
        self._confidence = confidence
        self._created = created or datetime.now(tz=timezone.utc)
        return self

    # --- Binding mechanisms (§5) ---

    def bind_to_struct(self, object_ref: str) -> "DataDefBuilder":
        """
        Structure element binding (§5.2) – highest specificity.
        E.g. '35 0 R' for object 35.
        """
        self._struct_ref = object_ref
        return self

    def bind_to_annot(self, object_ref: str) -> "DataDefBuilder":
        """Annotation binding (§5.3) – for Link, Widget, and other annotations."""
        self._annot_ref = object_ref
        return self

    def bind_to_page(
        self,
        page: int,
        rect: tuple[float, float, float, float] | None = None,
    ) -> "DataDefBuilder":
        """
        Spatial binding (§5.4) – for untagged documents.
        page is 1-based. rect is [x0, y0, x1, y1] in PDF user space.
        """
        self._page_ref = page
        self._rect = rect
        return self

    # --- Build ---

    def build(self, data: dict[str, Any] | str | list[Any]) -> DataDef:
        """
        Construct and return the DataDef object.

        Parameters
        ----------
        data:
            The structured data – as a dict (will be JSON-serialized),
            a JSON string, or a list.
        """
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            data_str = data

        return DataDef(
            data_type=self._data_type,
            format=self._format,
            data=data_str,
            encoding=self._encoding,
            schema_uri=self._schema_uri,
            schema_version=self._schema_version,
            source=self._source,
            created=self._created,
            generator=self._generator,
            trust_level=self._trust_level,
            confidence=self._confidence,
            struct_ref=self._struct_ref,
            annot_ref=self._annot_ref,
            page_ref=self._page_ref,
            rect=self._rect,
            status_uri=self._status_uri,
        )
