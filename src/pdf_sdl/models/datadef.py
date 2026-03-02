"""
DataDef Dictionary – Core Model
================================
Formal Python representation of the DataDef dictionary as specified in
SDL Technical Specification v1.4.0 (§3).

This module defines the Pydantic models for DataDef objects, their entries,
and the full type system (§4), now covering 25 standard DataTypes.
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
    25 standard types as of SDL Technical Specification v1.4.0.
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
    # Process & risk (new in v1.4.0)
    PROCESS = "Process"
    RISK = "Risk"
    STATISTICS = "Statistics"
    FINDING = "Finding"
    # Legal & materials (new in v1.4.0)
    LICENSE = "License"
    OBLIGATION = "Obligation"
    MATERIAL = "Material"
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
# Shared sub-models
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


# ---------------------------------------------------------------------------
# Sub-models – 25 DataTypes (SDL Technical Specification v1.4.0)
# ---------------------------------------------------------------------------

class LinkData(BaseModel):
    """JSON data stream schema for /DataType /Link (§4.2.1). Issue #725."""
    model_config = ConfigDict(populate_by_name=True)

    uri: str = Field(..., description="The target URI (same as the URI Action)")
    pid: str | None = Field(None, description="Persistent Identifier (DOI, ARK, Handle, URN)")
    link_id: str | None = Field(None, alias="linkId", description="LinkID persistent identifier")
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
        None, description="public | internal | confidential | restricted | top-secret"
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
        ..., alias="contentOrigin",
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
        ..., alias="translationMethod",
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
# Sub-models – additional DataTypes
# ---------------------------------------------------------------------------

class ProcessStep(BaseModel):
    """A single step or node in a /DataType /Process stream."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique step identifier")
    type: str = Field(..., description="startEvent | endEvent | task | gateway | subprocess | annotation")
    label: str = Field(..., description="Human-readable step name")
    actor: str | None = Field(None, description="Responsible party or role")
    duration: str | None = Field(None, description="ISO 8601 duration (e.g. PT4H)")
    systems: list[str] = Field(default_factory=list, description="Supporting IT systems")
    references: list[str] = Field(default_factory=list, description="Regulatory or policy references")


class ProcessData(BaseModel):
    """
    Data stream schema for /DataType /Process.
    Captures BPMN 2.0 workflows, SOPs, clinical pathways, and other
    process descriptions embedded in PDF documents.
    Applicable standards: ISO 9001, BPMN 2.0, FDA 21 CFR Part 11,
    ICH Q10, HL7 FHIR Workflow, TOGAF.
    """
    model_config = ConfigDict(populate_by_name=True)

    notation: str | None = Field(None, description="BPMN 2.0 | UML Activity | Flowchart | SIPOC | VSM")
    title: str | None = Field(None, description="Process name")
    version: str | None = Field(None, description="Process version")
    owner: str | None = Field(None, description="Process owner or responsible department")
    scope: str | None = Field(None, description="Process scope description")
    regulatory_references: list[str] = Field(
        default_factory=list, alias="regulatoryReferences",
        description="Applicable regulations or standards"
    )
    steps: list[ProcessStep] = Field(default_factory=list, description="Process steps / nodes")
    flows: list[dict[str, str]] = Field(
        default_factory=list,
        description="Sequence flows: [{from: id, to: id, condition?: str}]"
    )
    kpis: list[dict[str, Any]] = Field(default_factory=list, description="Process KPIs")


class RiskEntry(BaseModel):
    """A single risk in a /DataType /Risk stream."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Risk identifier (e.g. R-001)")
    category: str = Field(..., description="Strategic | Operational | Financial | Compliance | Reputational")
    description: str = Field(..., description="Risk description")
    likelihood: int | None = Field(None, ge=1, le=5, description="Likelihood score 1–5")
    impact: int | None = Field(None, ge=1, le=5, description="Impact score 1–5")
    inherent_risk: int | None = Field(None, alias="inherentRisk", description="Likelihood × Impact")
    controls: list[str] = Field(default_factory=list, description="Existing controls")
    residual_risk: int | None = Field(None, alias="residualRisk", description="Risk after controls")
    owner: str | None = Field(None, description="Risk owner")
    status: str | None = Field(None, description="open | mitigated | accepted | closed")
    review_date: str | None = Field(None, alias="reviewDate", description="ISO 8601")


class RiskData(BaseModel):
    """
    Data stream schema for /DataType /Risk.
    Captures risk registers and assessments embedded in PDF documents.
    Applicable standards: ISO 31000:2018, COSO ERM, Basel III/IV,
    Solvency II, NIST SP 800-30, ICH Q9.
    """
    model_config = ConfigDict(populate_by_name=True)

    framework: str | None = Field(
        None, description="ISO 31000:2018 | COSO ERM | Basel III | Solvency II | NIST SP 800-30"
    )
    assessment_date: str | None = Field(None, alias="assessmentDate", description="ISO 8601")
    assessment_scope: str | None = Field(None, alias="assessmentScope")
    likelihood_scale: str | None = Field(
        None, alias="likelihoodScale", description="Description of likelihood scoring scale"
    )
    impact_scale: str | None = Field(
        None, alias="impactScale", description="Description of impact scoring scale"
    )
    risks: list[RiskEntry] = Field(default_factory=list)
    overall_risk_rating: str | None = Field(None, alias="overallRiskRating")
    approved_by: str | None = Field(None, alias="approvedBy")


class StatisticsGroup(BaseModel):
    """A single group or cohort in a /DataType /Statistics stream."""
    name: str
    n: int | None = Field(None, description="Sample size")
    mean: float | None = None
    sd: float | None = Field(None, description="Standard deviation")
    median: float | None = None
    min: float | None = None
    max: float | None = None
    ci_lower: float | None = Field(None, alias="ciLower", description="Confidence interval lower bound")
    ci_upper: float | None = Field(None, alias="ciUpper", description="Confidence interval upper bound")


class StatisticsData(BaseModel):
    """
    Data stream schema for /DataType /Statistics.
    Captures statistical analyses, clinical trial results, and quantitative
    research outputs embedded in PDF documents.
    Applicable standards: CDISC (SDTM, ADaM, DEFINE-XML), APA 7th edition,
    OSF pre-registration, CONSORT, PRISMA, STROBE.
    """
    model_config = ConfigDict(populate_by_name=True)

    analysis: str | None = Field(None, description="Statistical test or analysis type")
    software: str | None = Field(None, description="Statistical software (e.g. R 4.3, SAS 9.4, SPSS 29)")
    preregistered: bool | None = Field(None, description="Whether analysis was pre-registered")
    preregistration_url: str | None = Field(None, alias="preregistrationUrl")
    reporting_standard: str | None = Field(
        None, alias="reportingStandard", description="CONSORT | PRISMA | STROBE | CDISC | APA"
    )
    groups: list[StatisticsGroup] = Field(default_factory=list)
    result: dict[str, Any] = Field(
        default_factory=dict,
        description="Test statistic, p-value, effect size, confidence interval"
    )
    variables: list[dict[str, Any]] = Field(
        default_factory=list, description="Variable definitions with roles and units"
    )


class FindingData(BaseModel):
    """
    Data stream schema for /DataType /Finding.
    Captures audit and inspection findings, non-conformances, and
    observations embedded in PDF reports.
    Applicable standards: GAAS, PCAOB AS 2201, ISAE 3000, ISO 19011,
    ICH E6(R2) GCP, FDA 21 CFR Part 820, SOC 2.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(None, description="Finding identifier (e.g. F-2025-001)")
    type: str | None = Field(
        None, description="critical | major | minor | observation | opportunity"
    )
    title: str | None = Field(None)
    description: str | None = Field(None)
    standard_reference: str | None = Field(
        None, alias="standardReference",
        description="Applicable standard clause (e.g. ISO 9001:2015 §8.4.1)"
    )
    audited_process: str | None = Field(None, alias="auditedProcess")
    evidence: list[str] = Field(default_factory=list, description="Supporting evidence references")
    risk_rating: str | None = Field(None, alias="riskRating", description="high | medium | low")
    corrective_action: str | None = Field(None, alias="correctiveAction")
    due_date: str | None = Field(None, alias="dueDate", description="ISO 8601")
    responsible_party: str | None = Field(None, alias="responsibleParty")
    status: str | None = Field(None, description="open | in-progress | closed | verified")
    closed_date: str | None = Field(None, alias="closedDate", description="ISO 8601")
    audit_id: str | None = Field(None, alias="auditId", description="Parent audit or inspection ID")


class LicenseData(BaseModel):
    """
    Data stream schema for /DataType /License.
    Captures rights management, software licensing, and data licensing
    information embedded in PDF documents.
    Applicable standards: SPDX 2.3, Creative Commons, Open Data Commons,
    FRAND licensing, EUPL.
    """
    model_config = ConfigDict(populate_by_name=True)

    spdx_id: str | None = Field(
        None, alias="spdxId", description="SPDX license identifier (e.g. Apache-2.0, CC-BY-4.0)"
    )
    name: str | None = Field(None, description="Full license name")
    url: str | None = Field(None, description="License text URL")
    licensor: str | None = Field(None, description="Rights holder")
    licensee: str | None = Field(None, description="Rights recipient (omit for public licenses)")
    scope: str | None = Field(
        None, description="software | data | content | patent | trademark | database"
    )
    effective_date: str | None = Field(None, alias="effectiveDate", description="ISO 8601")
    expiry_date: str | None = Field(None, alias="expiryDate", description="ISO 8601")
    jurisdiction: str | None = Field(None, description="Governing jurisdiction (ISO 3166)")
    permissions: list[str] = Field(
        default_factory=list,
        description="Permitted uses: reproduce | distribute | modify | sublicense | commercial | patent-use"
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions: attribution | share-alike | copyleft | notice | source-disclosure"
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Limitations: no-warranty | no-liability | no-trademark"
    )
    royalty: dict[str, Any] | None = Field(
        None, description="Royalty terms: {rate, basis, currency, frand: bool}"
    )


class ObligationData(BaseModel):
    """
    Data stream schema for /DataType /Obligation.
    Captures contractual obligations, covenants, and legal commitments
    embedded in PDF documents.
    Applicable standards: FIBO (Financial Industry Business Ontology),
    LKIF (Legal Knowledge Interchange Format), LegalRuleML,
    Swiss Code of Obligations, UNIDROIT PICC.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(None, description="Obligation identifier (e.g. OBL-001)")
    type: str | None = Field(
        None,
        description="payment | delivery | confidentiality | non-compete | reporting | indemnification | warranty"
    )
    obligor: str | None = Field(None, description="Party bearing the obligation")
    obligee: str | None = Field(None, description="Party to whom the obligation is owed")
    description: str | None = Field(None, description="Obligation text or summary")
    due_date: str | None = Field(None, alias="dueDate", description="ISO 8601 due date")
    recurring: bool | None = Field(None, description="Whether the obligation recurs")
    recurrence: str | None = Field(None, description="ISO 8601 recurrence rule (RRULE) or natural language")
    amount: dict[str, Any] | None = Field(
        None, description="Monetary amount: {value: number, currency: str, basis: str}"
    )
    condition: str | None = Field(None, description="Triggering condition (if conditional obligation)")
    governing_law: str | None = Field(None, alias="governingLaw", description="Governing legal system")
    status: str | None = Field(None, description="pending | active | fulfilled | breached | waived")
    clause_ref: str | None = Field(
        None, alias="clauseRef", description="Contract clause reference (e.g. §4.2)"
    )


class MaterialData(BaseModel):
    """
    Data stream schema for /DataType /Material.
    Captures chemical substance data, material specifications, and
    safety information embedded in PDF documents.
    Applicable standards: GHS (UN Globally Harmonized System), EU CLP Regulation,
    REACH (EC 1907/2006), Ph. Eur. (European Pharmacopoeia), USP,
    CAS Registry, ISO 10993, ASTM.
    """
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(None, description="Substance or material name")
    iupac_name: str | None = Field(None, alias="iupacName", description="IUPAC systematic name")
    cas_number: str | None = Field(None, alias="casNumber", description="CAS Registry Number")
    ec_number: str | None = Field(None, alias="ecNumber", description="EC (EINECS/ELINCS) number")
    inchi: str | None = Field(None, description="IUPAC International Chemical Identifier")
    smiles: str | None = Field(None, description="SMILES notation")
    molecular_formula: str | None = Field(None, alias="molecularFormula")
    molecular_weight: float | None = Field(None, alias="molecularWeight", description="g/mol")
    purity: str | None = Field(None, description="Purity specification (e.g. ≥ 99.5%)")
    grade: str | None = Field(
        None, description="Ph. Eur. | USP | NF | ACS | HPLC | Technical | Food"
    )
    physical_state: str | None = Field(
        None, alias="physicalState", description="solid | liquid | gas | plasma"
    )
    ghs_hazard_classes: list[str] = Field(
        default_factory=list, alias="ghsHazardClasses",
        description="GHS hazard classification codes (e.g. Flam. Liq. 2, Skin Irrit. 2)"
    )
    h_statements: list[str] = Field(
        default_factory=list, alias="hStatements",
        description="GHS Hazard statements (e.g. H225, H315)"
    )
    p_statements: list[str] = Field(
        default_factory=list, alias="pStatements",
        description="GHS Precautionary statements (e.g. P210, P264)"
    )
    reach_registered: bool | None = Field(None, alias="reachRegistered")
    svhc: bool | None = Field(None, description="Substance of Very High Concern (REACH SVHC list)")
    storage_conditions: str | None = Field(None, alias="storageConditions")
    shelf_life: str | None = Field(None, alias="shelfLife", description="ISO 8601 duration or text")
    sds_url: str | None = Field(None, alias="sdsUrl", description="Safety Data Sheet URL")


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
        """Serialize to a flat dict suitable for PDF dictionary entries."""
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
