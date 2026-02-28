"""
Conformance Validator
======================
Validates DataDef and LinkMeta objects against the SDL conformance rules
defined in §8 of the Technical Specification v1.2.0.

Returns structured ValidationResult objects with pass/fail/warn per rule.

Example::

    from pdf_sdl.validator import DataDefValidator, LinkMetaValidator

    result = DataDefValidator().validate(datadef)
    if not result.passed:
        for issue in result.issues:
            print(f"[{issue.severity}] {issue.rule_id}: {issue.message}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import json

from ..models.datadef import DataDef, DataType, TrustLevel, ConformanceLevel
from ..models.linkmeta import LinkMeta


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    rule_id: str
    severity: Severity
    message: str
    field: str | None = None


@dataclass
class ValidationResult:
    """Result of a conformance validation run."""
    passed: bool
    conformance_level: str
    issues: list[ValidationIssue] = field(default_factory=list)
    rule_count: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.conformance_level} "
            f"– {len(self.errors)} error(s), {len(self.warnings)} warning(s)"
        )


# ---------------------------------------------------------------------------
# DataDef Validator
# ---------------------------------------------------------------------------


class DataDefValidator:
    """
    Validates a DataDef object against the SDL conformance rules (§8.2).

    Rules implemented:
    - DD-001  /Type must be 'DataDef'
    - DD-002  /Version must be >= 1
    - DD-003  /DataType must be a known value or /Custom with schema
    - DD-004  /Format must be a known value
    - DD-005  /Data must be present and non-empty
    - DD-006  At least one binding mechanism must be present
    - DD-007  /Confidence must be in [0.0, 1.0]
    - DD-008  /Confidence is required when TrustLevel is Enriched
    - DD-009  /Generator and /Created recommended for Author/Enriched
    - DD-010  /Custom DataType requires /Schema URI
    - DD-011  /Data must be parseable in declared /Format
    - DD-012  /PageRef must be >= 1 if present
    - DD-013  /Schema URI should use https://
    - DD-014  /Rect requires /PageRef
    - DD-015  /Confidence 0.0 on Signed is suspicious
    """

    def validate(self, datadef: DataDef) -> ValidationResult:
        issues: list[ValidationIssue] = []
        rules_run = 0

        def add(rule_id: str, sev: Severity, msg: str, fld: str | None = None) -> None:
            issues.append(ValidationIssue(rule_id, sev, msg, fld))

        # DD-001 Type
        rules_run += 1
        if datadef.type != "DataDef":
            add("DD-001", Severity.ERROR, f"/Type must be 'DataDef', got '{datadef.type}'", "type")

        # DD-002 Version
        rules_run += 1
        if datadef.version < 1:
            add("DD-002", Severity.ERROR, "/Version must be >= 1", "version")

        # DD-003 DataType
        rules_run += 1
        try:
            DataType(datadef.data_type)
        except ValueError:
            add("DD-003", Severity.ERROR, f"Unknown /DataType: {datadef.data_type}", "data_type")

        # DD-004 Format
        rules_run += 1
        valid_formats = {"JSON", "XML", "CSV", "CBOR"}
        if datadef.format.value not in valid_formats:
            add("DD-004", Severity.ERROR, f"Unknown /Format: {datadef.format}", "format")

        # DD-005 Data present
        rules_run += 1
        if not datadef.data:
            add("DD-005", Severity.ERROR, "/Data must be present and non-empty", "data")

        # DD-006 At least one binding
        rules_run += 1
        if not datadef.has_binding():
            add(
                "DD-006",
                Severity.WARNING,
                "No binding mechanism present. DataDef is document-level only. "
                "Consider /StructRef, /AnnotRef, or /PageRef for element-level binding (§5).",
                "binding",
            )

        # DD-007 Confidence range
        rules_run += 1
        if datadef.confidence is not None and not 0.0 <= datadef.confidence <= 1.0:
            add("DD-007", Severity.ERROR, "/Confidence must be between 0.0 and 1.0", "confidence")

        # DD-008 Enriched requires confidence
        rules_run += 1
        if datadef.trust_level == TrustLevel.ENRICHED and datadef.confidence is None:
            add(
                "DD-008",
                Severity.ERROR,
                "/Confidence is required when /TrustLevel is /Enriched (§6.1)",
                "confidence",
            )

        # DD-009 Author/Enriched provenance
        rules_run += 1
        if datadef.trust_level in (TrustLevel.AUTHOR, TrustLevel.ENRICHED):
            if not datadef.generator:
                add(
                    "DD-009",
                    Severity.WARNING,
                    "/Generator recommended when TrustLevel is Author or Enriched",
                    "generator",
                )
            if not datadef.created:
                add(
                    "DD-009",
                    Severity.WARNING,
                    "/Created recommended when TrustLevel is Author or Enriched",
                    "created",
                )

        # DD-010 Custom requires schema
        rules_run += 1
        if datadef.data_type == DataType.CUSTOM and not datadef.schema_uri:
            add(
                "DD-010",
                Severity.ERROR,
                "/Schema URI is required for /DataType /Custom (§4.11)",
                "schema_uri",
            )

        # DD-011 Data parseability
        rules_run += 1
        if datadef.data and datadef.format.value == "JSON":
            data_str = datadef.data if isinstance(datadef.data, str) else json.dumps(datadef.data)
            try:
                json.loads(data_str)
            except json.JSONDecodeError as e:
                add(
                    "DD-011",
                    Severity.ERROR,
                    f"/Data is not valid JSON: {e}",
                    "data",
                )

        # DD-012 PageRef >= 1
        rules_run += 1
        if datadef.page_ref is not None and datadef.page_ref < 1:
            add("DD-012", Severity.ERROR, "/PageRef must be >= 1 (1-based page number)", "page_ref")

        # DD-013 Schema URI security
        rules_run += 1
        if datadef.schema_uri and not datadef.schema_uri.startswith("https://"):
            add(
                "DD-013",
                Severity.WARNING,
                "/Schema URI should use HTTPS for security",
                "schema_uri",
            )

        # DD-014 Rect requires PageRef
        rules_run += 1
        if datadef.rect and datadef.page_ref is None:
            add(
                "DD-014",
                Severity.WARNING,
                "/Rect is present but /PageRef is missing. Spatial binding (§5.4) requires both.",
                "rect",
            )

        # DD-015 Suspicious confidence on Signed
        rules_run += 1
        if datadef.trust_level == TrustLevel.SIGNED and datadef.confidence == 0.0:
            add(
                "DD-015",
                Severity.WARNING,
                "/Confidence 0.0 on a /Signed DataDef is suspicious (§6.3)",
                "confidence",
            )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return ValidationResult(
            passed=passed,
            conformance_level=datadef.conformance_level().value,
            issues=issues,
            rule_count=rules_run,
        )

    def validate_batch(self, datadefs: list[DataDef]) -> list[ValidationResult]:
        """Validate a list of DataDef objects and return all results."""
        return [self.validate(dd) for dd in datadefs]


# ---------------------------------------------------------------------------
# LinkMeta Validator
# ---------------------------------------------------------------------------


class LinkMetaValidator:
    """
    Validates a LinkMeta dictionary against the specification rules.

    Rules implemented:
    - LM-001  /Type must be 'LinkMeta'
    - LM-002  /Version must be >= 1
    - LM-003  /Confidence required for Enriched trust level
    - LM-004  /Generator required for Enriched trust level
    - LM-005  /RefDate recommended
    - LM-006  /Hash/Algorithm must be a supported value
    - LM-007  /AltURIs should use known archive services
    - LM-008  /StatusURI warning about privacy (§7.1)
    - LM-009  /Hash value should be non-empty
    - LM-010  At least one dimension beyond minimal recommended
    """

    KNOWN_ARCHIVE_DOMAINS = {
        "web.archive.org",
        "perma.cc",
        "archive.today",
        "europarchive.org",
        "archiveweb.page",
    }

    def validate(self, linkmeta: LinkMeta) -> ValidationResult:
        issues: list[ValidationIssue] = []
        rules_run = 0

        def add(rule_id: str, sev: Severity, msg: str, fld: str | None = None) -> None:
            issues.append(ValidationIssue(rule_id, sev, msg, fld))

        # LM-001 Type
        rules_run += 1
        if linkmeta.type != "LinkMeta":
            add("LM-001", Severity.ERROR, f"/Type must be 'LinkMeta', got '{linkmeta.type}'", "type")

        # LM-002 Version
        rules_run += 1
        if linkmeta.version < 1:
            add("LM-002", Severity.ERROR, "/Version must be >= 1", "version")

        # LM-003 + LM-004 Enriched requirements
        rules_run += 2
        if linkmeta.trust_level == "Enriched":
            if linkmeta.confidence is None:
                add("LM-003", Severity.ERROR, "/Confidence required for Enriched trust level", "confidence")
            if not linkmeta.generator:
                add("LM-004", Severity.ERROR, "/Generator required for Enriched trust level", "generator")

        # LM-005 RefDate recommended
        rules_run += 1
        if not linkmeta.ref_date:
            add(
                "LM-005",
                Severity.WARNING,
                "/RefDate is recommended (§3.2) – captures when the link was created",
                "ref_date",
            )

        # LM-006 Hash algorithm
        rules_run += 1
        if linkmeta.hash:
            valid_algos = {"SHA-256", "SHA-384", "SHA-512"}
            if linkmeta.hash.algorithm.value not in valid_algos:
                add("LM-006", Severity.ERROR, f"Unsupported /Hash/Algorithm: {linkmeta.hash.algorithm}", "hash")

        # LM-007 AltURIs quality
        rules_run += 1
        for uri in linkmeta.alt_uris:
            domain = uri.split("/")[2] if len(uri.split("/")) > 2 else ""
            if domain and domain not in self.KNOWN_ARCHIVE_DOMAINS:
                add(
                    "LM-007",
                    Severity.WARNING,
                    f"AltURI domain '{domain}' is not a known archive service. "
                    "Consider web.archive.org, perma.cc, or national archives.",
                    "alt_uris",
                )

        # LM-008 StatusURI privacy
        rules_run += 1
        if linkmeta.status_uri:
            add(
                "LM-008",
                Severity.INFO,
                "/StatusURI is present. Ensure it is NEVER queried automatically "
                "without explicit user consent (§7.1 privacy requirement).",
                "status_uri",
            )

        # LM-009 Hash value non-empty
        rules_run += 1
        if linkmeta.hash and not linkmeta.hash.value:
            add("LM-009", Severity.ERROR, "/Hash/Value must be non-empty", "hash")

        # LM-010 Capability recommendation
        rules_run += 1
        cap = linkmeta.capability_score()
        if cap < 2:
            add(
                "LM-010",
                Severity.INFO,
                f"LinkMeta covers {cap}/5 link dimensions. "
                "Consider adding: identification (/PID or /LinkID), context (/Title, /Desc), "
                "integrity (/Hash), fallback (/AltURIs), status (/Status).",
            )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        level = f"Capability {linkmeta.capability_score()}/5"
        return ValidationResult(
            passed=passed,
            conformance_level=level,
            issues=issues,
            rule_count=rules_run,
        )
