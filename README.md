| SDL DataDef Validator – Interactive Web Tool | v1.0 | [🔗 Live](https://link-genetic-inc.github.io/pdf-sdl-spec/presentation/SDL_DataDef_Validator_v1_0.html) · [HTML](presentation/SDL_DataDef_Validator_v1_0.html) |# pdf-sdl-spec

## Semantic Data Layer (SDL) for PDF – Technical Specifications and Proposals

Submitted to the PDF Association Technical Working Group / ISO TC 171 SC 2  
Issue [#725 – Lack of Internet-Aware Content Representation in PDF](https://github.com/pdf-association/pdf-issues/issues/725)

**Author:** Christian Nyffenegger, Link Genetic GmbH  
**Status:** Discussion Paper | February 2026

### Presentation & Executive Summary

| Document | Version | Format |
|----------|---------|--------|
| SDL TWG Presentation – PDF Association Technical Working Group | v1.0 | [PPTX](presentation/SDL_TWG_Presentation_v1_0.pptx) |
| SDL Executive Summary – One-Pager | v1.0 | [PDF](presentation/SDL_ExecutiveSummary_v1_0.pdf) |

---

## 🔗 Live Tool

**[SDL DataDef Validator](https://link-genetic-inc.github.io/pdf-sdl-spec/presentation/SDL_DataDef_Validator_v1_0.html)** – Validate DataDef dictionaries directly in your browser. No installation required. Covers all 25 DataTypes, trust levels, conformance levels, and domain examples (financial, pharma, AI provenance, Issue #725 links).

---

## Documents

### Technical Specification

| Document | Version | Format |
|----------|---------|--------|
| SDL DataDef Dictionary Extension to ISO 32000-2 | v1.4.0 | [Markdown](specification/SDL_TechnicalSpecification_DataDef_Dictionary_v1_4_0.md) · [PDF](specification/SDL_TechnicalSpecification_DataDef_Dictionary_v1_4_0.pdf) |
| SDL DataDef Dictionary Extension to ISO 32000-2 | v1.3.0 | [Markdown](specification/SDL_TechnicalSpecification_DataDef_Dictionary_v1_3_0.md) · [PDF](specification/SDL_TechnicalSpecification_DataDef_Dictionary_v1_3_0.pdf) |
| SDL DataDef Dictionary Extension to ISO 32000-2 | v1.2.0 | [Markdown](specification/SDL_TechnicalSpecification_DataDef_Dictionary_v1_2_0.md) · [PDF](specification/SDL_TechnicalSpecification_DataDef_Dictionary_v1_2_0.pdf) |

### Proposals

| Document | Version | Format |
|----------|---------|--------|
| Semantic Data Layer for PDF – LinkMeta Proposal (Issue #725) | v2.3.0 | [Markdown](proposals/PDF_Association_Proposal_LinkMeta_Issue725_v2_3_0.md) · [PDF](proposals/PDF_Association_Proposal_LinkMeta_Issue725_v2_3_0.pdf) |
| Semantic Data Layer for PDF – LinkMeta Proposal (Issue #725) | v2.2.0 | [Markdown](proposals/PDF_Association_Proposal_LinkMeta_Issue725_v2_2_0.md) · [PDF](proposals/PDF_Association_Proposal_LinkMeta_Issue725_v2_2_0.pdf) |

### White Paper

| Document | Version | Format |
|----------|---------|--------|
| From Visual Fidelity to Data Fidelity – Why PDF Needs a Semantic Data Layer | v2.3.0 | [Markdown](whitepaper/SDL_WhitePaper_From_Visual_to_Data_Fidelity_v2_3_0.md) · [PDF](whitepaper/SDL_WhitePaper_From_Visual_to_Data_Fidelity_v2_3_0.pdf) |
| From Visual Fidelity to Data Fidelity – Why PDF Needs a Semantic Data Layer | v2.2.0 | [Markdown](whitepaper/SDL_WhitePaper_From_Visual_to_Data_Fidelity_v2_2_0.md) · [PDF](whitepaper/SDL_WhitePaper_From_Visual_to_Data_Fidelity_v2_2_0.pdf) |

### Annexes

| Document | Version | Format |
|----------|---------|--------|
| SDL Regulatory Landscape Annex – Global Coverage (EU, US, UK, CH, APAC, XBRL) | v2.0 | [PDF](annexes/SDL_RegulatoryLandscape_Annex_v2_0.pdf) |
| SDL Regulatory Landscape Annex – EU Coverage | v1.0 | [PDF](annexes/SDL_RegulatoryLandscape_Annex_v1_0.pdf) |

### Conformance Test Report

| Document | Version | Format |
|----------|---------|--------|
| SDL Conformance Test Report – Reference Implementation (86 tests, 100% pass rate) | v1.3.0 | [PDF](annexes/SDL_ConformanceTestReport_v1_3_0.pdf) |

### Industry Profiles

| Document | Version | Format |
|----------|---------|--------|
| SDL Industry Profile: Financial Services | v1.0 | [Markdown](profiles/SDL_IndustryProfile_Financial_v1_0.md) · [PDF](profiles/SDL_IndustryProfile_Financial_v1_0.pdf) |
| SDL Industry Profile: Pharmaceutical and Life Sciences | v1.0 | [Markdown](profiles/SDL_IndustryProfile_Pharmaceutical_v1_0.md) · [PDF](profiles/SDL_IndustryProfile_Pharmaceutical_v1_0.pdf) |
| SDL Industry Profile: Legal and Compliance | v1.0 | [Markdown](profiles/SDL_IndustryProfile_Legal_v1_0.md) · [PDF](profiles/SDL_IndustryProfile_Legal_v1_0.pdf) |
| SDL Industry Profile: Government and Public Sector | v1.0 | [Markdown](profiles/SDL_IndustryProfile_Government_v1_0.md) · [PDF](profiles/SDL_IndustryProfile_Government_v1_0.pdf) |
| SDL Industry Profile: Scientific Publishing | v1.0 | [Markdown](profiles/SDL_IndustryProfile_Scientific_v1_0.md) · [PDF](profiles/SDL_IndustryProfile_Scientific_v1_0.pdf) |
| SDL Industry Profile: Engineering and Manufacturing | v1.0 | [Markdown](profiles/SDL_IndustryProfile_Engineering_v1_0.md) · [PDF](profiles/SDL_IndustryProfile_Engineering_v1_0.pdf) |

---

## Overview

The **Semantic Data Layer (SDL)** is a proposed extension to ISO 32000-2 (PDF 2.0) that enables machine-readable structured data to be bound directly to visual content elements in PDF documents.

### The problem

PDF has **visual fidelity** – documents look identical everywhere. But it lacks **data fidelity** – the structured data behind a table, chart, formula, or hyperlink is not machine-accessible. Every industry that relies on PDF faces the same consequence: data extraction pipelines that reverse-engineer layout, fragile parsers, and manual re-entry.

### The solution

SDL introduces a single new dictionary type – **DataDef** – that can be attached to any content element in a PDF:

> *"This visual content represents this data, in this format, conforming to this schema."*

A DataDef carries the structured data as an embedded JSON, XML, CSV, or CBOR stream, along with a data type classification, an optional schema URI, provenance information, and a binding to the specific visual element it represents.

### 25 Standard DataTypes

| Category | DataTypes |
|----------|-----------|
| **Data extraction** | `/Table` · `/Chart` · `/Record` · `/Value` · `/Series` · `/Form` |
| **References & links** | `/Link` · `/Reference` |
| **Scientific & engineering** | `/Formula` · `/Code` · `/Measurement` · `/Geospatial` |
| **Governance & compliance** | `/Classification` · `/Provenance` · `/Identity` · `/Translation` · `/Timeline` |
| **Process & risk** | `/Process` · `/Risk` · `/Statistics` · `/Finding` |
| **Legal & materials** | `/License` · `/Obligation` · `/Material` |
| **Extensible** | `/Custom` (requires `/Schema` URI) |

### Key features

- **Fully backward compatible** – existing PDF readers ignore DataDef without error
- **Independent of Tagged PDF** – works in untagged documents
- **Three trust levels** – `/Signed`, `/Author`, `/Enriched` (AI-extracted)
- **Four conformance levels** – SDL Basic, Schema, Provenance, Signed
- **XMP-complementary** – XMP answers "What is this document?", SDL answers "What does this content mean?"

### Issue #725: Internet-Aware Links

The `/Link` DataType directly addresses Issue #725 by adding five missing dimensions to PDF hyperlinks: persistent identification (LinkID, DOI), content integrity (SHA-256 hash), semantic context (title, description), fallback resolution (archive URIs), and status tracking.

---

## Related

- **Reference implementation:** [Link-Genetic-Inc/pdf-sdl](https://github.com/Link-Genetic-Inc/pdf-sdl) – Python library, 25 DataTypes, 86 unit tests
- **Issue #725:** [pdf-association/pdf-issues #725](https://github.com/pdf-association/pdf-issues/issues/725)
- **LinkID URI scheme:** [IANA provisional registration](https://www.iana.org/assignments/uri-schemes/prov/linkid) · [WICG Proposal #238](https://github.com/WICG/proposals/issues/238)

---

## License

Apache 2.0 – see [LICENSE](LICENSE)
