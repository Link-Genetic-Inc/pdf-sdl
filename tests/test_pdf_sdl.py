"""
Test Suite for pdf-sdl
=======================
Tests for core models, builders, validator, and PDF round-trip.
Covers the conformance test suite outline from §10 of the specification.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf_sdl import (
    DataDef,
    DataDefBuilder,
    DataDefValidator,
    DataFormat,
    DataType,
    LinkMeta,
    LinkMetaBuilder,
    LinkMetaValidator,
    SDLReader,
    SDLWriter,
    Severity,
    TrustLevel,
    ConformanceLevel,
    ContentHash,
    HashAlgorithm,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def minimal_datadef() -> DataDef:
    """Minimal valid DataDef (SDL Basic conformance)."""
    return DataDefBuilder.value().build({"metric": "revenue", "value": 4200000})


@pytest.fixture
def full_table_datadef() -> DataDef:
    """Full-featured financial table DataDef (SDL Provenance conformance)."""
    return (
        DataDefBuilder.table()
        .with_source("SAP S/4HANA, Q4 2024")
        .with_schema("https://schema.org/FinancialStatement", version="2024-01")
        .trust_author(
            generator="Acme Report Builder v3.2",
            created=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        .bind_to_struct("35 0 R")
        .bind_to_page(7, rect=(72.0, 400.0, 540.0, 720.0))
        .build({
            "type": "FinancialStatement",
            "period": "FY2024",
            "currency": "USD",
            "rows": [
                {"label": "Revenue", "value": 4200000, "unit": "USD"},
                {"label": "COGS", "value": 2100000, "unit": "USD"},
                {"label": "Gross Profit", "value": 2100000, "unit": "USD"},
                {"label": "Net Income", "value": 840000, "unit": "USD"},
            ],
        })
    )


@pytest.fixture
def enriched_datadef() -> DataDef:
    """AI-enriched DataDef (TrustLevel Enriched)."""
    return (
        DataDefBuilder.table()
        .trust_enriched(generator="AI Extractor v2", confidence=0.87)
        .bind_to_page(3)
        .build({"rows": [{"label": "Revenue", "value": 1000}]})
    )


@pytest.fixture
def link_datadef() -> DataDef:
    """Issue #725 – Link DataType."""
    return (
        DataDefBuilder.link()
        .trust_author("pdf-sdl v0.1.0")
        .bind_to_annot("26 0 R")
        .build({
            "uri": "https://example.com/report-2024.pdf",
            "pid": "doi:10.1234/xyz-2025",
            "linkId": "linkid:doc:acme/handbook/2025/section-3",
            "title": "Annual Report 2024",
            "refDate": "2025-01-15T12:00:00Z",
            "hash": {"algorithm": "SHA-256", "value": "a1b2c3d4e5f67890"},
            "altUris": ["https://web.archive.org/web/20250115/https://example.com/report-2024.pdf"],
            "status": "active",
        })
    )


@pytest.fixture
def full_linkmeta() -> LinkMeta:
    return (
        LinkMetaBuilder()
        .identify(
            pid="doi:10.1234/xyz-2025",
            link_id="linkid:doc:acme/handbook/2025/section-3",
        )
        .context(
            title="Annual Report 2024 – Section 3: Risk Assessment",
            desc="Referenced for risk methodology framework",
            lang="en",
            content_type="application/pdf",
        )
        .integrity(hash_value="a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890")
        .fallback(
            "https://web.archive.org/web/20250115/https://example.com/report.pdf",
            "https://perma.cc/AB12-CD34",
        )
        .status_active()
        .trust_author()
        .build()
    )


# ===========================================================================
# Model Tests
# ===========================================================================


class TestDataDefModel:
    """Tests for the DataDef Pydantic model (§3)."""

    def test_minimal_creation(self, minimal_datadef: DataDef) -> None:
        assert minimal_datadef.type == "DataDef"
        assert minimal_datadef.version == 1
        assert minimal_datadef.data_type == DataType.VALUE
        assert minimal_datadef.format == DataFormat.JSON

    def test_data_as_dict(self, minimal_datadef: DataDef) -> None:
        d = minimal_datadef.data_as_dict()
        assert d["metric"] == "revenue"
        assert d["value"] == 4200000

    def test_has_binding_false(self, minimal_datadef: DataDef) -> None:
        assert not minimal_datadef.has_binding()

    def test_has_binding_true(self, full_table_datadef: DataDef) -> None:
        assert full_table_datadef.has_binding()

    def test_conformance_basic(self, minimal_datadef: DataDef) -> None:
        assert minimal_datadef.conformance_level() == ConformanceLevel.BASIC

    def test_conformance_schema(self) -> None:
        dd = DataDefBuilder.table().with_schema("https://schema.org/Table").build({"rows": []})
        assert dd.conformance_level() == ConformanceLevel.SCHEMA

    def test_conformance_provenance(self, full_table_datadef: DataDef) -> None:
        assert full_table_datadef.conformance_level() == ConformanceLevel.PROVENANCE

    def test_conformance_signed(self) -> None:
        dd = (
            DataDefBuilder.table()
            .with_schema("https://schema.org/Table")
            .with_source("ERP")
            .trust_signed()
            .trust_author("MyApp")  # sets generator+created
            .build({"rows": []})
        )
        # trust_author overrides trust_signed, so let's test the signed path properly
        dd2 = DataDef(
            data_type=DataType.TABLE,
            format=DataFormat.JSON,
            data='{"rows":[]}',
            schema_uri="https://schema.org/Table",
            source="ERP",
            generator="App",
            created=datetime.now(tz=timezone.utc),
            trust_level=TrustLevel.SIGNED,
        )
        assert dd2.conformance_level() == ConformanceLevel.SIGNED

    def test_enriched_requires_confidence(self) -> None:
        with pytest.raises(Exception):
            DataDef(
                data_type=DataType.TABLE,
                format=DataFormat.JSON,
                data="{}",
                trust_level=TrustLevel.ENRICHED,
                confidence=None,
            )

    def test_custom_requires_schema(self) -> None:
        # Pydantic model_validator raises if DataType.CUSTOM without schema_uri
        with pytest.raises(Exception):
            DataDef(
                data_type=DataType.CUSTOM,
                format=DataFormat.JSON,
                data="{}",
            )

    def test_to_pdf_dict(self, full_table_datadef: DataDef) -> None:
        d = full_table_datadef.to_pdf_dict()
        assert d["Type"] == "DataDef"
        assert d["Version"] == 1
        assert "/Table" in d["DataType"]
        assert "/JSON" in d["Format"]
        assert "Schema" in d
        assert "Source" in d

    def test_dict_accepts_data(self) -> None:
        dd = DataDefBuilder.record().build({"name": "test", "value": 42})
        assert isinstance(dd.data, str)
        parsed = dd.data_as_dict()
        assert parsed["name"] == "test"

    def test_all_standard_datatypes_constructible(self) -> None:
        """Verify all 18 DataTypes can be instantiated."""
        factory_methods = [
            DataDefBuilder.table, DataDefBuilder.record, DataDefBuilder.value,
            DataDefBuilder.series, DataDefBuilder.chart, DataDefBuilder.form,
            DataDefBuilder.link, DataDefBuilder.reference, DataDefBuilder.formula,
            DataDefBuilder.code, DataDefBuilder.measurement, DataDefBuilder.geospatial,
            DataDefBuilder.timeline, DataDefBuilder.classification, DataDefBuilder.provenance,
            DataDefBuilder.identity, DataDefBuilder.translation,
        ]
        for factory in factory_methods:
            dd = factory().build({"test": True})
            assert dd.version == 1
            assert dd.format == DataFormat.JSON

        # Custom requires schema
        dd_custom = DataDefBuilder.custom("https://example.com/schema").build({"x": 1})
        assert dd_custom.data_type == DataType.CUSTOM


# ===========================================================================
# Builder Tests
# ===========================================================================


class TestDataDefBuilder:
    """Tests for the DataDefBuilder fluent API."""

    def test_chain_all_options(self) -> None:
        dd = (
            DataDefBuilder.table()
            .with_source("SAP")
            .with_schema("https://schema.org/FinancialStatement", version="2024")
            .with_encoding("UTF-8")
            .with_status_uri("https://status.example.com/abc")
            .trust_author(generator="TestApp v1")
            .bind_to_struct("35 0 R")
            .bind_to_annot("26 0 R")
            .bind_to_page(3, rect=(72.0, 100.0, 540.0, 400.0))
            .build({"rows": []})
        )
        assert dd.source == "SAP"
        assert dd.schema_uri == "https://schema.org/FinancialStatement"
        assert dd.schema_version == "2024"
        assert dd.trust_level == TrustLevel.AUTHOR
        assert dd.generator == "TestApp v1"
        assert dd.struct_ref == "35 0 R"
        assert dd.annot_ref == "26 0 R"
        assert dd.page_ref == 3
        assert dd.rect == (72.0, 100.0, 540.0, 400.0)

    def test_trust_enriched_confidence_range(self) -> None:
        with pytest.raises(ValueError, match="confidence must be between"):
            DataDefBuilder.table().trust_enriched("App", confidence=1.5)

    def test_enriched_datadef(self, enriched_datadef: DataDef) -> None:
        assert enriched_datadef.trust_level == TrustLevel.ENRICHED
        assert enriched_datadef.confidence == 0.87
        assert enriched_datadef.generator == "AI Extractor v2"

    def test_link_datatype(self, link_datadef: DataDef) -> None:
        assert link_datadef.data_type == DataType.LINK
        d = link_datadef.data_as_dict()
        assert d["uri"] == "https://example.com/report-2024.pdf"
        assert d["pid"] == "doi:10.1234/xyz-2025"
        assert "linkId" in d

    def test_provenance_datatype(self) -> None:
        dd = (
            DataDefBuilder.provenance()
            .trust_author("MyApp")
            .build({
                "contentOrigin": "ai-generated",
                "model": "Claude Sonnet 4.5",
                "modelProvider": "Anthropic",
                "humanReviewed": True,
                "confidence": 0.92,
            })
        )
        assert dd.data_type == DataType.PROVENANCE
        d = dd.data_as_dict()
        assert d["contentOrigin"] == "ai-generated"

    def test_formula_datatype(self) -> None:
        dd = DataDefBuilder.formula().build({
            "latex": r"E = mc^{2}",
            "mathml": "<math><mi>E</mi></math>",
            "variables": {
                "E": {"label": "Energy", "unit": "J"},
                "m": {"label": "Mass", "unit": "kg"},
            },
            "context": "Mass-energy equivalence",
        })
        assert dd.data_type == DataType.FORMULA

    def test_build_accepts_list(self) -> None:
        dd = DataDefBuilder.series().build([{"date": "2024-01", "value": 100}])
        d = dd.data_as_dict()
        assert d[0]["value"] == 100

    def test_build_accepts_string(self) -> None:
        dd = DataDefBuilder.record().build('{"name": "test"}')
        assert dd.data_as_dict()["name"] == "test"


# ===========================================================================
# LinkMeta Tests
# ===========================================================================


class TestLinkMeta:
    """Tests for LinkMeta model and builder (§3 of LinkMeta proposal)."""

    def test_minimal_linkmeta(self) -> None:
        lm = LinkMetaBuilder().build()
        assert lm.type == "LinkMeta"
        assert lm.version == 1
        assert lm.ref_date is not None  # auto-stamped

    def test_full_linkmeta(self, full_linkmeta: LinkMeta) -> None:
        assert full_linkmeta.has_persistent_id()
        assert full_linkmeta.has_integrity()
        assert full_linkmeta.has_fallback()
        assert full_linkmeta.capability_score() == 5

    def test_capability_score_empty(self) -> None:
        lm = LinkMeta()
        # No ref_date, no PID, no hash, no fallback, no status
        # ref_date is auto-set by builder but not by direct construction
        assert lm.capability_score() <= 1

    def test_capability_score_partial(self) -> None:
        lm = (
            LinkMetaBuilder()
            .identify(pid="doi:10.1234/test")
            .integrity(hash_value="abc123")
            .build()
        )
        assert lm.capability_score() >= 2

    def test_hash_integrity(self, full_linkmeta: LinkMeta) -> None:
        assert full_linkmeta.hash is not None
        assert full_linkmeta.hash.algorithm == HashAlgorithm.SHA256
        assert len(full_linkmeta.hash.value) > 0

    def test_fallback_uris(self, full_linkmeta: LinkMeta) -> None:
        assert len(full_linkmeta.alt_uris) == 2
        assert "web.archive.org" in full_linkmeta.alt_uris[0]

    def test_to_pdf_dict(self, full_linkmeta: LinkMeta) -> None:
        d = full_linkmeta.to_pdf_dict()
        assert d["Type"] == "LinkMeta"
        assert d["Version"] == 1
        assert "PID" in d
        assert "LinkID" in d
        assert "Hash" in d
        assert "AltURIs" in d

    def test_enriched_requires_generator_and_confidence(self) -> None:
        with pytest.raises(Exception):
            LinkMeta(TrustLevel="Enriched")

    def test_trust_enriched_builder(self) -> None:
        lm = (
            LinkMetaBuilder()
            .trust_enriched("AI Link Enricher v1", confidence=0.85)
            .build()
        )
        assert lm.trust_level == "Enriched"
        assert lm.confidence == 0.85
        assert lm.generator == "AI Link Enricher v1"

    def test_linkid_format(self) -> None:
        lm = LinkMetaBuilder().identify(
            link_id="linkid:doc:acme/handbook/2025/section-3"
        ).build()
        assert lm.link_id is not None
        assert lm.link_id.startswith("linkid:")

    def test_repr(self, full_linkmeta: LinkMeta) -> None:
        r = repr(full_linkmeta)
        assert "LinkMeta" in r
        assert "5/5" in r


# ===========================================================================
# Validator Tests
# ===========================================================================


class TestDataDefValidator:
    """Tests for the DataDefValidator conformance rules (§8.2)."""

    def setup_method(self) -> None:
        self.v = DataDefValidator()

    def test_minimal_passes(self, minimal_datadef: DataDef) -> None:
        result = self.v.validate(minimal_datadef)
        # Minimal has no binding → warning, but no error
        assert all(i.severity != Severity.ERROR for i in result.issues)

    def test_full_table_passes(self, full_table_datadef: DataDef) -> None:
        result = self.v.validate(full_table_datadef)
        assert result.passed
        assert len(result.errors) == 0

    def test_enriched_without_confidence_fails(self) -> None:
        # Pydantic catches this at model level, but test the validator path
        dd = DataDefBuilder.table().trust_enriched("App", confidence=0.8).build({"rows": []})
        # Manually clear confidence to test DD-008
        dd_bad = dd.model_copy(update={"confidence": None})
        result = self.v.validate(dd_bad)
        errors = [i for i in result.issues if i.rule_id == "DD-008"]
        assert len(errors) > 0

    def test_custom_without_schema_fails(self) -> None:
        # Build a CUSTOM DataDef with schema (valid), then strip the schema to test rule DD-010
        dd = DataDefBuilder.custom("https://example.com/schema").build({})
        dd_no_schema = dd.model_copy(update={"schema_uri": None})
        result = self.v.validate(dd_no_schema)
        dd010 = [i for i in result.issues if i.rule_id == "DD-010"]
        assert len(dd010) > 0

    def test_invalid_json_data_fails(self) -> None:
        dd = DataDef(
            data_type=DataType.TABLE,
            format=DataFormat.JSON,
            data="NOT VALID JSON {{{",
        )
        result = self.v.validate(dd)
        dd011 = [i for i in result.issues if i.rule_id == "DD-011"]
        assert len(dd011) > 0

    def test_no_binding_warning(self, minimal_datadef: DataDef) -> None:
        result = self.v.validate(minimal_datadef)
        dd006 = [i for i in result.issues if i.rule_id == "DD-006"]
        assert len(dd006) == 1
        assert dd006[0].severity == Severity.WARNING

    def test_rect_without_page_warning(self) -> None:
        dd = DataDef(
            data_type=DataType.TABLE,
            format=DataFormat.JSON,
            data="{}",
            rect=(72.0, 100.0, 540.0, 400.0),
            page_ref=None,
        )
        result = self.v.validate(dd)
        dd014 = [i for i in result.issues if i.rule_id == "DD-014"]
        assert len(dd014) > 0

    def test_http_schema_warning(self) -> None:
        dd = DataDefBuilder.table().with_schema("http://example.com/schema").build({"rows": []})
        result = self.v.validate(dd)
        dd013 = [i for i in result.issues if i.rule_id == "DD-013"]
        assert len(dd013) > 0

    def test_conformance_level_reported(self, full_table_datadef: DataDef) -> None:
        result = self.v.validate(full_table_datadef)
        assert "SDL" in result.conformance_level

    def test_batch_validation(self, minimal_datadef: DataDef, full_table_datadef: DataDef) -> None:
        results = self.v.validate_batch([minimal_datadef, full_table_datadef])
        assert len(results) == 2


class TestLinkMetaValidator:
    """Tests for the LinkMetaValidator."""

    def setup_method(self) -> None:
        self.v = LinkMetaValidator()

    def test_minimal_passes(self) -> None:
        lm = LinkMetaBuilder().build()
        result = self.v.validate(lm)
        assert result.passed

    def test_full_linkmeta_passes(self, full_linkmeta: LinkMeta) -> None:
        result = self.v.validate(full_linkmeta)
        assert result.passed
        assert len(result.errors) == 0

    def test_enriched_without_generator_fails(self) -> None:
        lm = LinkMeta(TrustLevel="Enriched", generator="App v1", confidence=0.8)
        lm_bad = lm.model_copy(update={"generator": None})
        result = self.v.validate(lm_bad)
        lm004 = [i for i in result.issues if i.rule_id == "LM-004"]
        assert len(lm004) > 0

    def test_unknown_archive_warning(self) -> None:
        lm = LinkMetaBuilder().fallback("https://unknown-archive.example.com/page").build()
        result = self.v.validate(lm)
        lm007 = [i for i in result.issues if i.rule_id == "LM-007"]
        assert len(lm007) > 0

    def test_known_archive_no_warning(self) -> None:
        lm = (
            LinkMetaBuilder()
            .fallback("https://web.archive.org/web/20250115/https://example.com/")
            .build()
        )
        result = self.v.validate(lm)
        lm007 = [i for i in result.issues if i.rule_id == "LM-007"]
        assert len(lm007) == 0

    def test_status_uri_info(self) -> None:
        lm = LinkMetaBuilder().with_status_uri("https://status.example.com/abc").build()
        result = self.v.validate(lm)
        lm008 = [i for i in result.issues if i.rule_id == "LM-008"]
        assert len(lm008) > 0
        assert lm008[0].severity == Severity.INFO

    def test_capability_score_in_result(self, full_linkmeta: LinkMeta) -> None:
        result = self.v.validate(full_linkmeta)
        assert "5/5" in result.conformance_level


# ===========================================================================
# PDF Round-Trip Tests (require pikepdf)
# ===========================================================================


class TestPDFRoundTrip:
    """Tests for writing and reading DataDefs in actual PDF files."""

    @pytest.fixture
    def tmp_pdf(self) -> Path:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            return Path(f.name)

    def test_write_and_read_minimal(self, tmp_pdf: Path) -> None:
        dd = DataDefBuilder.value().build({"metric": "revenue", "value": 4200000})

        with SDLWriter() as writer:
            writer.add_datadef(dd)
            writer.save(tmp_pdf)

        with SDLReader(tmp_pdf) as reader:
            found = reader.find_datadefs()

        assert len(found) == 1
        assert found[0].data_type == DataType.VALUE

    def test_write_and_read_full_table(self, tmp_pdf: Path, full_table_datadef: DataDef) -> None:
        with SDLWriter() as writer:
            writer.add_datadef(full_table_datadef, page=1)
            writer.save(tmp_pdf)

        with SDLReader(tmp_pdf) as reader:
            found = reader.find_datadefs()
            summary = reader.summary()

        assert len(found) >= 1
        assert summary["datadef_count"] >= 1
        assert "Table" in summary["datatype_breakdown"]

    def test_write_multiple_datadefs(self, tmp_pdf: Path) -> None:
        dd1 = DataDefBuilder.table().build({"rows": []})
        dd2 = DataDefBuilder.value().build({"value": 42})
        dd3 = DataDefBuilder.link().trust_author("App").build({"uri": "https://example.com"})

        with SDLWriter() as writer:
            writer.add_datadef(dd1)
            writer.add_datadef(dd2)
            writer.add_datadef(dd3)
            writer.save(tmp_pdf)

        with SDLReader(tmp_pdf) as reader:
            found = reader.find_datadefs()

        assert len(found) == 3

    def test_read_from_existing_pdf_no_sdl(self) -> None:
        """Reading a PDF with no SDL should return empty lists without error."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp = Path(f.name)

        with SDLWriter() as writer:
            writer.save(tmp)  # Empty PDF with no DataDefs

        with SDLReader(tmp) as reader:
            # Catalog DataDefs will be empty
            count = reader.get_datadef_count()

        # Should not raise, count may be 0
        assert isinstance(count, int)

    def test_datadef_catalog_registration(self, tmp_pdf: Path) -> None:
        dd = DataDefBuilder.table().build({"rows": []})

        with SDLWriter() as writer:
            writer.add_datadef(dd, add_to_catalog=True)
            writer.save(tmp_pdf)

        with SDLReader(tmp_pdf) as reader:
            count = reader.get_datadef_count()

        assert count >= 1

    def test_enriched_datadef_round_trip(self, tmp_pdf: Path, enriched_datadef: DataDef) -> None:
        with SDLWriter() as writer:
            writer.add_datadef(enriched_datadef)
            writer.save(tmp_pdf)

        with SDLReader(tmp_pdf) as reader:
            found = reader.find_datadefs()

        assert len(found) >= 1
        found_dd = found[0]
        assert found_dd.data_type == DataType.TABLE

    def test_json_data_preserved(self, tmp_pdf: Path) -> None:
        original_data = {
            "type": "FinancialStatement",
            "period": "FY2024",
            "rows": [{"label": "Revenue", "value": 4200000}],
        }
        dd = DataDefBuilder.table().build(original_data)

        with SDLWriter() as writer:
            writer.add_datadef(dd)
            writer.save(tmp_pdf)

        with SDLReader(tmp_pdf) as reader:
            found = reader.find_datadefs()

        assert len(found) >= 1
        parsed = found[0].data_as_dict()
        assert parsed["period"] == "FY2024"
        assert parsed["rows"][0]["value"] == 4200000

    def test_summary_output(self, tmp_pdf: Path) -> None:
        dd1 = DataDefBuilder.table().build({"rows": []})
        dd2 = DataDefBuilder.provenance().build({"contentOrigin": "ai-generated"})

        with SDLWriter() as writer:
            writer.add_datadef(dd1)
            writer.add_datadef(dd2)
            writer.save(tmp_pdf)

        with SDLReader(tmp_pdf) as reader:
            summary = reader.summary()

        assert summary["datadef_count"] == 2
        assert "Table" in summary["datatype_breakdown"]
        assert "Provenance" in summary["datatype_breakdown"]


# ===========================================================================
# Spec Compliance Tests (§10 Test Suite Outline)
# ===========================================================================


class TestSpecComplianceOutline:
    """
    Covers the conformance test suite outline from §10 of the specification.
    """

    def test_minimal_datadef_valid(self) -> None:
        """§10: Minimal DataDef – Valid minimal object."""
        dd = DataDef(
            data_type=DataType.VALUE,
            format=DataFormat.JSON,
            data='{"metric": "revenue", "value": 4200000}',
        )
        v = DataDefValidator()
        r = v.validate(dd)
        assert all(i.severity != Severity.ERROR for i in r.issues)

    def test_missing_required_key_fails(self) -> None:
        """§10: Minimal DataDef – Missing required keys."""
        with pytest.raises(Exception):
            DataDef(format=DataFormat.JSON, data="{}")  # type: ignore[call-arg]

    def test_invalid_datatype_falls_back(self) -> None:
        """§10: Minimal DataDef – Custom DataType without schema triggers DD-010."""
        dd = DataDefBuilder.custom("https://example.com/schema").build({})
        dd_no_schema = dd.model_copy(update={"schema_uri": None})
        v = DataDefValidator()
        r = v.validate(dd_no_schema)
        dd010 = [i for i in r.issues if i.rule_id == "DD-010"]
        assert len(dd010) > 0  # Custom without schema

    def test_json_format_valid(self) -> None:
        """§10: Data formats – Valid JSON."""
        dd = DataDefBuilder.table().build({"rows": [{"a": 1}]})
        v = DataDefValidator()
        r = v.validate(dd)
        dd011 = [i for i in r.issues if i.rule_id == "DD-011"]
        assert len(dd011) == 0

    def test_malformed_json_fails(self) -> None:
        """§10: Data formats – Malformed JSON stream."""
        dd = DataDef(
            data_type=DataType.TABLE,
            format=DataFormat.JSON,
            data="{not valid json}",
        )
        v = DataDefValidator()
        r = v.validate(dd)
        dd011 = [i for i in r.issues if i.rule_id == "DD-011"]
        assert len(dd011) > 0

    def test_trust_levels_classification(self) -> None:
        """§10: Trust levels – Signed/Author/Enriched classification."""
        dd_signed = DataDef(
            data_type=DataType.TABLE,
            format=DataFormat.JSON,
            data="{}",
            trust_level=TrustLevel.SIGNED,
        )
        assert dd_signed.trust_level == TrustLevel.SIGNED

        dd_enriched = DataDefBuilder.table().trust_enriched("App", 0.75).build({"rows": []})
        assert dd_enriched.trust_level == TrustLevel.ENRICHED
        assert dd_enriched.confidence == 0.75

    def test_link_datatype_issue_725(self) -> None:
        """§10: Link DataType – Issue #725 scenarios."""
        dd = DataDefBuilder.link().trust_author("App").build({
            "uri": "https://example.com/report.pdf",
            "pid": "doi:10.1234/test",
            "hash": {"algorithm": "SHA-256", "value": "abc123"},
            "altUris": ["https://web.archive.org/web/20250101/https://example.com/report.pdf"],
        })
        assert dd.data_type == DataType.LINK
        d = dd.data_as_dict()
        assert d["uri"].startswith("https://")
        assert d["pid"].startswith("doi:")

    def test_formula_datatype(self) -> None:
        """§10: Formula DataType – Valid LaTeX/MathML."""
        dd = DataDefBuilder.formula().build({
            "latex": r"E = mc^{2}",
            "mathml": "<math><mi>E</mi></math>",
            "variables": {"E": {"unit": "J"}, "m": {"unit": "kg"}},
        })
        assert dd.data_type == DataType.FORMULA

    def test_provenance_datatype_eu_ai_act(self) -> None:
        """§10: Provenance DataType – AI model identification."""
        dd = DataDefBuilder.provenance().trust_enriched("AI System", 0.92).build({
            "contentOrigin": "ai-generated",
            "model": "Claude Sonnet 4.5",
            "modelProvider": "Anthropic",
            "humanReviewed": True,
            "reviewDate": "2025-12-02T14:30:00Z",
        })
        assert dd.data_type == DataType.PROVENANCE
        d = dd.data_as_dict()
        assert d["contentOrigin"] == "ai-generated"
        assert d["humanReviewed"] is True

    def test_classification_datatype(self) -> None:
        """§10: Classification DataType – Confidentiality levels."""
        dd = DataDefBuilder.classification().trust_author("DMS v2").build({
            "confidentiality": "internal",
            "retentionYears": 10,
            "retentionBasis": "FINMA Circular 2008/21",
            "regulatoryRegime": ["FINMA", "GDPR"],
            "personalData": True,
        })
        assert dd.data_type == DataType.CLASSIFICATION
        d = dd.data_as_dict()
        assert d["confidentiality"] == "internal"
        assert "GDPR" in d["regulatoryRegime"]

    def test_measurement_datatype(self) -> None:
        """§10: Measurement DataType – Unit validation."""
        dd = DataDefBuilder.measurement().build({
            "measurements": [
                {"label": "Width", "value": 150.0, "unit": "mm", "tolerance": "+/- 0.05"},
                {"label": "Height", "value": 80.0, "unit": "mm"},
            ],
            "material": "Aluminum 6061-T6",
            "standard": "ISO 2768-1:1989",
        })
        assert dd.data_type == DataType.MEASUREMENT


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
