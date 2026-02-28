"""
Examples for pdf-sdl
====================
Three complete examples demonstrating SDL in real-world scenarios.

Run:
    python examples/examples.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf_sdl import (
    DataDefBuilder,
    DataDefValidator,
    LinkMetaBuilder,
    LinkMetaValidator,
    SDLReader,
    SDLWriter,
)


# ---------------------------------------------------------------------------
# Example 1: Financial Table
# ---------------------------------------------------------------------------


def example_financial_table() -> None:
    """
    Example 1: Embedding a financial table with SDL.

    A CFO report PDF contains a Q4 revenue table. With SDL, the structured
    data travels alongside the visual rendering, enabling direct extraction
    without OCR or NLP.
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Financial Table DataDef")
    print("="*60)

    datadef = (
        DataDefBuilder.table()
        .with_source("SAP S/4HANA, Q4 2024 Close")
        .with_schema("https://schema.org/FinancialStatement", version="2024-01")
        .trust_author(
            generator="Acme Report Builder v3.2",
            created=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        .bind_to_page(7, rect=(72.0, 400.0, 540.0, 720.0))
        .build({
            "type": "FinancialStatement",
            "period": "FY2024",
            "currency": "USD",
            "rows": [
                {"label": "Revenue",      "value": 4_200_000, "unit": "USD"},
                {"label": "COGS",         "value": 2_100_000, "unit": "USD"},
                {"label": "Gross Profit", "value": 2_100_000, "unit": "USD"},
                {"label": "Net Income",   "value":   840_000, "unit": "USD"},
            ],
        })
    )

    print(f"  DataDef created: {datadef}")
    print(f"  Conformance: {datadef.conformance_level().value}")
    print(f"  Binding: page={datadef.page_ref}, rect={datadef.rect}")

    # Validate
    result = DataDefValidator().validate(datadef)
    print(f"  Validation: {result}")

    # Write to PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = Path(f.name)

    with SDLWriter() as writer:
        writer.add_datadef(datadef, page=1)
        writer.save(pdf_path)

    print(f"  Written to: {pdf_path}")

    # Read back
    with SDLReader(pdf_path) as reader:
        found = reader.find_datadefs()
        summary = reader.summary()

    print(f"  Read back: {len(found)} DataDef(s)")
    if found:
        data = found[0].data_as_dict()
        revenue = data["rows"][0]["value"]
        print(f"  Revenue extracted: ${revenue:,}")

    pdf_path.unlink(missing_ok=True)
    print("  ✓ Example 1 complete")


# ---------------------------------------------------------------------------
# Example 2: Link with Integrity (Issue #725)
# ---------------------------------------------------------------------------


def example_link_integrity() -> None:
    """
    Example 2: Internet-aware link with integrity verification.

    A pharmaceutical regulatory submission references an FDA guideline.
    With LinkMeta, the reference captures what version was cited, proves
    content integrity, and provides fallback to archives.

    Addresses Issue #725 – Lack of Internet-Aware Content Representation in PDF.
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Internet-Aware Link (Issue #725)")
    print("="*60)

    linkmeta = (
        LinkMetaBuilder()
        .identify(
            pid="doi:10.1234/fda-guideline-2025",
            link_id="linkid:doc:fda/guidelines/2025/ich-q10",
        )
        .context(
            title="FDA – ICH Q10 Pharmaceutical Quality System (2025 revision)",
            desc="Referenced for quality management system requirements",
            lang="en",
            content_type="application/pdf",
        )
        .integrity(
            hash_value="a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
            algorithm="SHA-256",
        )
        .fallback(
            "https://web.archive.org/web/20250115/https://fda.gov/guidelines/ich-q10.pdf",
            "https://perma.cc/AB12-CD34",
        )
        .status_active()
        .trust_author()
        .build()
    )

    print(f"  LinkMeta created: {linkmeta}")
    print(f"  Capability score: {linkmeta.capability_score()}/5")
    print(f"  Has integrity:    {linkmeta.has_integrity()}")
    print(f"  Has fallback:     {linkmeta.has_fallback()} ({len(linkmeta.alt_uris)} URIs)")
    print(f"  Persistent IDs:   PID={linkmeta.pid}, LinkID={linkmeta.link_id}")

    # Validate
    result = LinkMetaValidator().validate(linkmeta)
    print(f"  Validation: {result}")

    # Also show the equivalent DataDef /Link form
    link_datadef = (
        DataDefBuilder.link()
        .trust_author("Pharma Doc Generator v2")
        .bind_to_annot("26 0 R")
        .build({
            "uri": "https://fda.gov/guidelines/ich-q10.pdf",
            "pid": "doi:10.1234/fda-guideline-2025",
            "linkId": "linkid:doc:fda/guidelines/2025/ich-q10",
            "title": "FDA – ICH Q10 Pharmaceutical Quality System",
            "refDate": "2025-01-15T12:00:00Z",
            "hash": {
                "algorithm": "SHA-256",
                "value": "a1b2c3d4e5f6789012345678901234567890",
            },
            "altUris": [
                "https://web.archive.org/web/20250115/https://fda.gov/guidelines/ich-q10.pdf"
            ],
            "status": "active",
        })
    )

    print(f"\n  Equivalent DataDef /Link: {link_datadef}")
    print("  ✓ Example 2 complete")


# ---------------------------------------------------------------------------
# Example 3: AI Provenance (EU AI Act compliance)
# ---------------------------------------------------------------------------


def example_ai_provenance() -> None:
    """
    Example 3: EU AI Act compliance with /Provenance DataType.

    An executive summary is generated by an AI model and reviewed by a human.
    The /Provenance DataType makes this machine-readable for regulatory compliance.
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: AI Provenance (EU AI Act)")
    print("="*60)

    # AI-generated content → Enriched trust level
    provenance_dd = (
        DataDefBuilder.provenance()
        .trust_enriched(
            generator="Anthropic Claude Sonnet 4.5 via Corporate AI Platform v1.2",
            confidence=0.92,
        )
        .bind_to_struct("48 0 R")
        .build({
            "contentOrigin": "ai-generated",
            "model": "Claude Sonnet 4.5",
            "modelProvider": "Anthropic",
            "modelVersion": "claude-sonnet-4-5-20250929",
            "generationDate": "2025-12-01T10:00:00Z",
            "prompt": "Generate executive summary of Q4 financial results",
            "humanReviewed": True,
            "humanReviewer": "J. Mueller, Finance Director",
            "reviewDate": "2025-12-02T14:30:00Z",
            "editedAfterGeneration": True,
            "confidence": 0.92,
            "watermark": "C2PA manifest ID: urn:uuid:abc123-def456",
        })
    )

    print(f"  Provenance DataDef: {provenance_dd}")
    print(f"  Trust level: {provenance_dd.trust_level.value}")
    print(f"  Confidence: {provenance_dd.confidence}")

    data = provenance_dd.data_as_dict()
    print(f"  AI model: {data['model']} by {data['modelProvider']}")
    print(f"  Human reviewed: {data['humanReviewed']} by {data['humanReviewer']}")
    print(f"  Edited after generation: {data['editedAfterGeneration']}")

    # Validate
    result = DataDefValidator().validate(provenance_dd)
    print(f"  Validation: {result}")

    # Classification DataDef (what regulatory regimes apply)
    classification_dd = (
        DataDefBuilder.classification()
        .trust_author("Document Management System v3")
        .build({
            "confidentiality": "internal",
            "retentionYears": 10,
            "retentionBasis": "FINMA Circular 2008/21",
            "regulatoryRegime": ["FINMA", "GDPR", "EU-AI-Act"],
            "jurisdiction": "CH",
            "personalData": False,
            "handlingInstructions": "Do not distribute outside finance department",
        })
    )

    print(f"\n  Classification DataDef: {classification_dd}")
    cdata = classification_dd.data_as_dict()
    print(f"  Regimes: {cdata['regulatoryRegime']}")
    print(f"  Retention: {cdata['retentionYears']} years ({cdata['retentionBasis']})")
    print("  ✓ Example 3 complete")


# ---------------------------------------------------------------------------
# Run all examples
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    example_financial_table()
    example_link_integrity()
    example_ai_provenance()

    print("\n" + "="*60)
    print("All examples completed successfully.")
    print("For more, see: https://github.com/Link-Genetic-Inc/pdf-sdl")
    print("="*60 + "\n")
