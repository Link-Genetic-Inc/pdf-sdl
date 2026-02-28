"""
DataDef Dictionary – Core Model
================================
Formal Python representation of the DataDef dictionary as specified in
SDL Technical Specification v1.2.0 (§3).

This module defines the Pydantic models for DataDef objects, their entries,
and the full type system (§4).
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations (§3.2, §4.1, §6.1)
# ---------------------------------------------------------------------------


class DataFormat(str, Enum):
    """Serialization format for the DataDef data stream (§3.2 /Format)."""
    JSON = "JSON"
    XML = "XML"
    CSV = "CSV"
    CBOR = "CBOR"


class DataType(str, Enum):
    """
    Standard DataType values (§4.1).
    Classifies the semantic category of the structured data.
    """
    # Data extraction
    TABLE = "Table"
    RECORD = "Record"
    VALUE = "Value"
    SERIES = "Series"
    CHART = "Chart"
    FORM = "Form"
    # References and links
    LINK = "Link"
    REFERENCE = "Reference"
    # Scientific / engineering
    FORMULA = "Formula"
    CODE = "Code"
    MEASUREMENT = "Measurement"
    GEOSPATIAL = "Geospatial"
    TIMELINE = "Timeline"
    # Governance / compliance
    CLASSIFICATION = "Classification"
    PROVENANCE = "Provenance"
    IDENTITY = "Identity"
    TRANSLATION = "Translation"
    # Extensible
    CUSTOM = "Custom"


class TrustLevel(str, Enum):
    """
    Trust level classification for DataDef provenance (§6.1).

    SIGNED   – DataDef is within the scope of a digital signature.
    AUTHOR   – Created by the document author at authoring time.
    ENRICHED – Added post-creation by AI, extraction tools, or third-party services.
    """
    SIGNED = "Signed"
    AUTHOR = "Author"
    ENRICHED = "Enriched"


class ConformanceLevel(str, Enum):
    """SDL conformance levels (§8.1)."""
    BASIC = "SDL Basic"
    SCHEMA = "SDL Schema"
    PROVENANCE = "SDL Provenance"
    SIGNED = "SDL Signed"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class HashValue(BaseModel):
    """Content hash of a target resource (used in LinkMeta and /Link DataType)."""
    model_config = ConfigDict(frozen=True)

    algorithm: str = Field(
        ...,
        description="Hash algorithm: SHA-256, SHA-384, or SHA-512",
        pattern=r"^SHA-(256|384|512)$",
    )
    value: str = Field(..., description="Hex-encoded hash value")


class LinkData(BaseModel):
    """
    JSON data stream schema for /DataType /Link (§4.2.1).
    Addresses Issue #725 – Internet-Aware Content Representation.
    """
    model_config = ConfigDict(populate_by_name=True)

    uri: str = Field(..., description="The target URI (same as the URI Action)")
    pid: str | None = Field(None, description="Persistent Identifier (DOI, ARK, Handle, URN)")
    link_id: str | None = Field(None, alias="linkId", description="LinkID persistent identifier (linkid: URI scheme)")
    title: str | None = Field(None, description="Title of the referenced resource")
    description: str | None = Field(None, description="Purpose of the reference")
    language: str | None = Field(None, description="Language of target (BCP 47)")
    content_type: str | None = Field(None, alias="contentType", description="MIME type of target")
    ref_date: str | None = Field(None, alias="refDate", description="ISO 8601 timestamp of referencing")
    hash: HashValue | None = Field(None, description="Content hash at refDate")
    alt_uris: list[str] = Field(default_factory=list, alias="altUris", description="Fallback URIs, ordered by preference")
    status: str | None = Field(None, description="active | archived | broken | unknown")
    last_checked: str | None = Field(None, alias="lastChecked", description="Last availability check (ISO 8601)")
    status_uri: str | None = Field(None, alias="statusUri", description="URI for live status query (opt-in only)")


class FormulaData(BaseModel):
    """Data stream schema for /DataType /Formula (§4.3)."""
    latex: str | None = Field(None, description="LaTeX representation")
    mathml: str | None = Field(None, description="MathML representation (W3C standard)")
    variables: dict[str, Any] = Field(default_factory=dict, description="Variable definitions")
    result: float | str | None = Field(None, description="Computed result, if applicable")
    context: str | None = Field(None, description="What the formula represents")


class CodeData(BaseModel):
    """Data stream schema for /DataType /Code (§4.4)."""
    language: str = Field(..., description="Programming language identifier")
    language_version: str | None = Field(None, alias="languageVersion")
    source: str = Field(..., description="Complete source code")
    dependencies: list[str] = Field(default_factory=list)
    executable: bool = Field(False, description="Whether the code is self-contained and runnable")
    license: str | None = Field(None, description="SPDX license identifier")
    repository: str | None = Field(None, description="Source repository URI")


class TimelineEvent(BaseModel):
    """A single event or phase in a /DataType /Timeline stream."""
    model_config = ConfigDict(populate_by_name=True)

    label: str
    date: str | None = None
    date_start: str | None = Field(None, alias="dateStart")
    date_end: str | None = Field(None, alias="dateEnd")
    type: str = Field("event", description="milestone | phase | deadline | event")
    critical: bool = False


class TimelineData(BaseModel):
    """Data stream schema for /DataType /Timeline (§4.5)."""
    title: str | None = None
    events: list[TimelineEvent] = Field(default_factory=list)
    dependencies: list[dict[str, str]] = Field(default_factory=list)


class IdentityData(BaseModel):
    """Data stream schema for /DataType /Identity (§4.6)."""
    name: str = Field(..., description="Full legal name of the party")
    role: str | None = None
    organization: str | None = None
    organization_id: str | None = Field(None, alias="organizationId")
    jurisdiction: str | None = Field(None, description="ISO 3166 code")
    capacity: str | None = Field(None, description="authorized signatory | witness | notary | agent")
    qualifications: list[str] = Field(default_factory=list)
    contact_email: str | None = Field(None, alias="contactEmail")
    signed_date: str | None = Field(None, alias="signedDate")


class ClassificationData(BaseModel):
    """Data stream schema for /DataType /Classification (§4.7)."""
    confidentiality: str | None = Field(
        None,
        description="public | internal | confidential | restricted | top-secret",
    )
    retention_years: int | None = Field(None, alias="retentionYears")
    retention_basis: str | None = Field(None, alias="retentionBasis")
    regulatory_regime: list[str] = Field(default_factory=list, alias="regulatoryRegime")
    jurisdiction: str | None = None
    personal_data: bool | None = Field(None, alias="personalData")
    personal_data_categories: list[str] = Field(default_factory=list, alias="personalDataCategories")
    handling_instructions: str | None = Field(None, alias="handlingInstructions")
    declassification_date: str | None = Field(None, alias="declassificationDate")


class ProvenanceData(BaseModel):
    """Data stream schema for /DataType /Provenance (§4.8). EU AI Act compliance support."""
    model_config = ConfigDict(populate_by_name=True)

    content_origin: str = Field(
        ...,
        alias="contentOrigin",
        description="human-authored | ai-generated | ai-assisted | translated | compiled",
    )
    model: str | None = None
    model_provider: str | None = Field(None, alias="modelProvider")
    model_version: str | None = Field(None, alias="modelVersion")
    generation_date: str | None = Field(None, alias="generationDate")
    prompt: str | None = Field(None, description="May be omitted for confidentiality")
    human_reviewed: bool | None = Field(None, alias="humanReviewed")
    human_reviewer: str | None = Field(None, alias="humanReviewer")
    review_date: str | None = Field(None, alias="reviewDate")
    edited_after_generation: bool | None = Field(None, alias="editedAfterGeneration")
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    watermark: str | None = None


class TranslationData(BaseModel):
    """Data stream schema for /DataType /Translation (§4.9)."""
    model_config = ConfigDict(populate_by_name=True)

    original_language: str = Field(..., alias="originalLanguage", description="BCP 47")
    translated_language: str = Field(..., alias="translatedLanguage", description="BCP 47")
    translation_method: str = Field(
        ...,
        alias="translationMethod",
        description="human-professional | human-non-professional | machine | machine-post-edited | ai-assisted",
    )
    translator: str | None = None
    certification_standard: str | None = Field(None, alias="certificationStandard")
    translation_date: str | None = Field(None, alias="translationDate")
    source_document: dict[str, Any] | None = Field(None, alias="sourceDocument")
    reviewed_by: str | None = Field(None, alias="reviewedBy")
    disclaimer: str | None = None


class MeasurementEntry(BaseModel):
    """A single measurement within /DataType /Measurement."""
    label: str
    value: float
    unit: str
    tolerance: str | None = None
    min: float | None = None
    max: float | None = None
    standard: str | None = None


class MeasurementData(BaseModel):
    """Data stream schema for /DataType /Measurement (§4.10)."""
    measurements: list[MeasurementEntry] = Field(default_factory=list)
    material: str | None = None
    standard: str | None = None
    coordinate_system: str | None = Field(None, alias="coordinateSystem")
    scale: str | None = None


# ---------------------------------------------------------------------------
# Core DataDef Model
# ---------------------------------------------------------------------------


class DataDef(BaseModel):
    """
    DataDef Dictionary (§3.2).

    The central object of the Semantic Data Layer. Carries structured data
    and binds it to a visual content element in a PDF document.

    Required keys: type, version, data_type, format, data.
    """
    model_config = ConfigDict(populate_by_name=True)

    # --- Required entries ---
    type: str = Field("DataDef", description="Must be /DataDef")
    version: int = Field(1, ge=1, description="Specification version")
    data_type: DataType = Field(..., description="Classification of the data (§4)")
    format: DataFormat = Field(..., description="Serialization format of the data stream")
    data: str | dict[str, Any] = Field(..., description="The structured data content (inline or reference)")

    # --- Identification / provenance ---
    encoding: str = Field("UTF-8", description="Character encoding. Default: UTF-8")
    schema_uri: str | None = Field(None, description="URI to a formal schema definition")
    schema_version: str | None = Field(None)
    source: str | None = Field(None, description="Origin system or description")
    created: datetime | None = Field(None, description="When the DataDef was generated")
    generator: str | None = Field(None, description="Software or service that produced the DataDef")

    # --- Trust ---
    trust_level: TrustLevel | None = Field(None, description="Signed | Author | Enriched (§6)")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Required when trust_level is Enriched")

    # --- Binding (§5) ---
    struct_ref: str | None = Field(None, description="Object reference to a structure element")
    annot_ref: str | None = Field(None, description="Object reference to an annotation")
    page_ref: int | None = Field(None, ge=1, description="Page number (1-based)")
    rect: tuple[float, float, float, float] | None = Field(None, description="Bounding box [x0 y0 x1 y1]")

    # --- Status / live ---
    status_uri: str | None = Field(None, description="URI for live status queries (opt-in)")

    # --- Computed / metadata ---
    object_id: str | None = Field(None, description="PDF object ID once written (e.g. '50 0 R')")

    @model_validator(mode="after")
    def validate_enriched_requires_confidence(self) -> "DataDef":
        if self.trust_level == TrustLevel.ENRICHED and self.confidence is None:
            raise ValueError(
                "confidence is required when trust_level is TrustLevel.ENRICHED (§6.1)"
            )
        return self

    @model_validator(mode="after")
    def validate_custom_requires_schema(self) -> "DataDef":
        if self.data_type == DataType.CUSTOM and self.schema_uri is None:
            raise ValueError(
                "schema_uri is required when data_type is DataType.CUSTOM (§4.11)"
            )
        return self

    @field_validator("data", mode="before")
    @classmethod
    def coerce_data(cls, v: Any) -> Any:
        """Accept dict, str, or JSON-serializable objects."""
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return v

    def data_as_dict(self) -> Any:
        """Parse and return the data stream as a Python object."""
        if isinstance(self.data, str):
            return json.loads(self.data)
        return self.data

    def has_binding(self) -> bool:
        """Returns True if at least one binding mechanism is present (§5)."""
        return any([self.struct_ref, self.annot_ref, self.page_ref is not None])

    def conformance_level(self) -> ConformanceLevel:
        """Determine the highest conformance level satisfied by this DataDef (§8.1)."""
        if (
            self.trust_level == TrustLevel.SIGNED
            and self.schema_uri is not None
            and self.source is not None
            and self.created is not None
            and self.generator is not None
        ):
            return ConformanceLevel.SIGNED
        if (
            self.schema_uri is not None
            and self.source is not None
            and self.created is not None
            and self.generator is not None
        ):
            return ConformanceLevel.PROVENANCE
        if self.schema_uri is not None:
            return ConformanceLevel.SCHEMA
        return ConformanceLevel.BASIC

    def to_pdf_dict(self) -> dict[str, Any]:
        """
        Serialize to a flat dict suitable for conversion to PDF dictionary entries.
        Uses PDF name convention (forward slash prefix implied).
        """
        d: dict[str, Any] = {
            "Type": "DataDef",
            "Version": self.version,
            "DataType": f"/{self.data_type.value}",
            "Format": f"/{self.format.value}",
        }
        if self.encoding != "UTF-8":
            d["Encoding"] = f"/{self.encoding}"
        if self.schema_uri:
            d["Schema"] = self.schema_uri
        if self.schema_version:
            d["SchemaVersion"] = self.schema_version
        if self.source:
            d["Source"] = self.source
        if self.created:
            d["Created"] = self.created.strftime("D:%Y%m%d%H%M%S+00'00'")
        if self.generator:
            d["Generator"] = self.generator
        if self.trust_level:
            d["TrustLevel"] = f"/{self.trust_level.value}"
        if self.confidence is not None:
            d["Confidence"] = self.confidence
        if self.struct_ref:
            d["StructRef"] = self.struct_ref
        if self.annot_ref:
            d["AnnotRef"] = self.annot_ref
        if self.page_ref is not None:
            d["PageRef"] = self.page_ref
        if self.rect:
            d["Rect"] = list(self.rect)
        if self.status_uri:
            d["StatusURI"] = self.status_uri
        return d

    def __repr__(self) -> str:
        return (
            f"DataDef(type={self.data_type.value!r}, format={self.format.value!r}, "
            f"trust={self.trust_level}, conformance={self.conformance_level().value!r})"
        )
