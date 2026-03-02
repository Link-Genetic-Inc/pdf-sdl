"""
pdf-sdl – Semantic Data Layer for PDF
======================================
Reference implementation of the SDL DataDef extension to ISO 32000-2.
Addresses Issue #725 – Lack of Internet-Aware Content Representation in PDF.

Specification: SDL Technical Specification v1.4.0
Proposal:      LinkMeta / Issue #725 v2.3.0
Author:        Christian Nyffenegger, Link Genetic GmbH

Quick Start::

    from pdf_sdl import DataDefBuilder, SDLWriter, SDLReader

    # Build a financial table DataDef
    datadef = (
        DataDefBuilder.table()
        .with_source("SAP S/4HANA, Q4 2024")
        .with_schema("https://schema.org/FinancialStatement")
        .trust_author(generator="MyApp v1.0")
        .bind_to_page(7, rect=(72, 400, 540, 720))
        .build({
            "period": "FY2024",
            "currency": "USD",
            "rows": [
                {"label": "Revenue", "value": 4200000, "unit": "USD"},
                {"label": "Net Income", "value": 840000, "unit": "USD"},
            ]
        })
    )

    # Write to PDF
    with SDLWriter("report.pdf") as writer:
        writer.add_datadef(datadef)
        writer.save("report-sdl.pdf")

    # Read back
    with SDLReader("report-sdl.pdf") as reader:
        for dd in reader.find_datadefs():
            print(dd.data_type, dd.conformance_level())
"""

__version__ = "0.1.0"
__author__ = "Christian Nyffenegger, Link Genetic GmbH"
__spec_version__ = "SDL Technical Specification v1.4.0"
__issue__ = "PDF Association Issue #725"

# Core models
from .models.datadef import (
    DataDef,
    DataFormat,
    DataType,
    TrustLevel,
    ConformanceLevel,
    LinkData,
    FormulaData,
    CodeData,
    TimelineData,
    TimelineEvent,
    IdentityData,
    ClassificationData,
    ProvenanceData,
    TranslationData,
    MeasurementData,
    MeasurementEntry,
    HashValue,
    # New in v1.4.0
    ProcessData,
    ProcessStep,
    RiskData,
    RiskEntry,
    StatisticsData,
    StatisticsGroup,
    FindingData,
    LicenseData,
    ObligationData,
    MaterialData,
)
from .models.linkmeta import (
    LinkMeta,
    LinkStatus,
    ContentHash,
    HashAlgorithm,
)

# Builders
from .builder.datadef_builder import DataDefBuilder
from .builder.linkmeta_builder import LinkMetaBuilder

# PDF I/O
from .pdf.writer import SDLWriter
from .pdf.reader import SDLReader

# Validator
from .validator.conformance import (
    DataDefValidator,
    LinkMetaValidator,
    ValidationResult,
    ValidationIssue,
    Severity,
)

__all__ = [
    # Models
    "DataDef",
    "DataFormat",
    "DataType",
    "TrustLevel",
    "ConformanceLevel",
    "LinkData",
    "FormulaData",
    "CodeData",
    "TimelineData",
    "TimelineEvent",
    "IdentityData",
    "ClassificationData",
    "ProvenanceData",
    "TranslationData",
    "MeasurementData",
    "MeasurementEntry",
    "HashValue",
    # New in v1.4.0
    "ProcessData",
    "ProcessStep",
    "RiskData",
    "RiskEntry",
    "StatisticsData",
    "StatisticsGroup",
    "FindingData",
    "LicenseData",
    "ObligationData",
    "MaterialData",
    "LinkMeta",
    "LinkStatus",
    "ContentHash",
    "HashAlgorithm",
    # Builders
    "DataDefBuilder",
    "LinkMetaBuilder",
    # PDF I/O
    "SDLWriter",
    "SDLReader",
    # Validation
    "DataDefValidator",
    "LinkMetaValidator",
    "ValidationResult",
    "ValidationIssue",
    "Severity",
]
