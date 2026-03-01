# pdf-sdl

**Semantic Data Layer (SDL) for PDF** – Python reference implementation of the DataDef dictionary extension to ISO 32000-2.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](https://github.com/Link-Genetic-Inc/pdf-sdl/releases)
[![Tests](https://img.shields.io/badge/tests-68%20passing-brightgreen.svg)](tests/)
[![PDF Association](https://img.shields.io/badge/PDF%20Association-Issue%20%23725-blue.svg)](https://github.com/pdf-association/pdf-issues/issues/725)

Addresses [Issue #725](https://github.com/pdf-association/pdf-issues/issues/725) – *Lack of Internet-Aware Content Representation in PDF* – submitted to the PDF Association Technical Working Group / ISO TC 171 SC 2.

---

## What is the Semantic Data Layer?

PDF excels at visual fidelity. A financial table, a clinical data set, a legal contract — they all look right. But the structured data behind that visual rendering is invisible to machines. Extracting it requires OCR, heuristic parsers, or AI — reverse-engineering a visual problem that should never have existed.

**SDL fixes this at the source.** By binding structured data directly to content elements inside the PDF, SDL makes documents machine-readable without changing how they look or breaking any existing reader.

```
Visual layer  →  PDF page (unchanged, rendered by all readers)
Data layer    →  DataDef dictionary (ignored by legacy readers, consumed by SDL-aware tools)
```

SDL introduces one new dictionary type – **DataDef** – that can be attached to structure elements, annotations, pages, or the document catalog. A DataDef carries the data itself (JSON/XML/CSV/CBOR), a DataType classification, an optional schema URI, provenance metadata, and a binding to the specific visual element it represents.

**Companion repository:** [pdf-sdl-spec](https://github.com/Link-Genetic-Inc/pdf-sdl-spec) – full technical specifications, proposals, industry profiles, TWG presentation, and interactive web validator.

---

## Installation

```bash
pip install pdf-sdl
```

**Requirements:** Python 3.10+

**Dependencies:** `pikepdf`, `pydantic`, `click`, `rich`, `jsonschema`, `python-dateutil`

---

## Quick Start

### Write a DataDef to a PDF

```python
from pdf_sdl import DataDefBuilder, SDLWriter

datadef = (
    DataDefBuilder.table()
    .with_source("SAP S/4HANA, Q4 2024")
    .with_schema("https://schema.org/FinancialStatement")
    .with_schema_version("2024-01")
    .trust_author(generator="MyApp v1.0")
    .bind_to_page(7, rect=[72, 400, 540, 720])
    .build({
        "period": "FY2024",
        "currency": "USD",
        "rows": [
            {"label": "Revenue",      "value": 4200000},
            {"label": "COGS",         "value": 2100000},
            {"label": "Gross Profit", "value": 2100000},
            {"label": "Net Income",   "value":  840000}
        ]
    })
)

with SDLWriter("report.pdf") as writer:
    writer.add_datadef(datadef)
    writer.save("report-sdl.pdf")
```

### Read DataDefs from a PDF

```python
from pdf_sdl import SDLReader

with SDLReader("report-sdl.pdf") as reader:
    for datadef in reader.datadefs():
        print(f"Type: {datadef.data_type}")
        print(f"Data: {datadef.data}")
        print(f"Trust: {datadef.trust_level}")
```

### Validate a DataDef

```python
from pdf_sdl import SDLValidator

validator = SDLValidator()
result = validator.validate(datadef)

if result.is_valid:
    print(f"✓ Valid – Conformance: {result.conformance_level}")
else:
    for error in result.errors:
        print(f"✗ {error}")
```

### Internet-Aware Links (Issue #725)

```python
from pdf_sdl import DataDefBuilder

link = (
    DataDefBuilder.link()
    .trust_author(generator="LinkMeta Processor v1.0")
    .build({
        "uri": "https://www.example.com/report-2024.pdf",
        "linkId": "linkid:doc:acme/report/2024",
        "pid": "doi:10.1234/xyz-2025",
        "title": "Annual Report 2024",
        "refDate": "2025-01-15T12:00:00Z",
        "hash": {"algorithm": "SHA-256", "value": "a1b2c3d4..."},
        "altUris": ["https://web.archive.org/web/20250115/https://www.example.com/report-2024.pdf"],
        "status": "active"
    })
)
```

### CLI

```bash
# Validate a PDF's DataDef objects
pdf-sdl validate report-sdl.pdf

# Extract all DataDefs as JSON
pdf-sdl extract report-sdl.pdf --output data.json

# List DataDefs in a PDF
pdf-sdl list report-sdl.pdf
```

---

## 25 Standard DataTypes

| Category | DataTypes |
|----------|-----------|
| Category | DataTypes |
|----------|-----------| 
| **Data extraction** | `/Table` · `/Chart` · `/Record` · `/Value` · `/Series` · `/Form` |
| **References & links** | `/Link` · `/Reference` |
| **Scientific & engineering** | `/Formula` · `/Code` · `/Measurement` · `/Geospatial` |
| **Governance & compliance** | `/Classification` · `/Provenance` · `/Identity` · `/Translation` · `/Timeline` |
| **Process & risk** | `/Process` · `/Risk` · `/Statistics` · `/Finding` |
| **Legal & materials** | `/License` · `/Obligation` · `/Material` |
| **Extensible** | `/Custom` (requires `/Schema` URI) |

---

## Architecture

```
pdf_sdl/
├── models/       DataDef, DataType, TrustLevel, Format – Pydantic models
├── builder/      Fluent DataDefBuilder API
├── validator/    Conformance validation (SDL Basic → Schema → Provenance → Signed)
├── pdf/          SDLWriter, SDLReader, PDFBinding
└── cli/          Command-line interface (validate, extract, list)
```

### Trust Levels

| Level | Meaning | Required keys |
|-------|---------|---------------|
| `/Signed` | DataDef within digital signature scope | Standard keys |
| `/Author` | Created at authoring time | `/Generator`, `/Created` |
| `/Enriched` | Added post-creation by AI or tools | `/Generator`, `/Created`, `/Confidence` |

### Conformance Levels

| Level | Requirements |
|-------|-------------|
| **SDL Basic** | Required keys + one binding mechanism |
| **SDL Schema** | SDL Basic + `/Schema` URI, data validates |
| **SDL Provenance** | SDL Schema + `/Source`, `/Created`, `/Generator` |
| **SDL Signed** | SDL Provenance + DataDef within signature scope |

---

## Development

```bash
git clone https://github.com/Link-Genetic-Inc/pdf-sdl.git
cd pdf-sdl
pip install -e ".[dev]"

pytest tests/ -v --cov=pdf_sdl   # 68 tests
ruff check src/ tests/
mypy src/
```

---

## Specification

**[github.com/Link-Genetic-Inc/pdf-sdl-spec](https://github.com/Link-Genetic-Inc/pdf-sdl-spec)**

| Document | Description |
|----------|-------------|
| [SDL Technical Specification v1.4.0](https://github.com/Link-Genetic-Inc/pdf-sdl-spec/blob/main/specification/SDL_TechnicalSpecification_DataDef_Dictionary_v1_4_0.pdf) | DataDef dictionary, 25 DataTypes, binding mechanisms, trust levels |
| [LinkMeta Proposal v2.3.0](https://github.com/Link-Genetic-Inc/pdf-sdl-spec/blob/main/proposals/PDF_Association_Proposal_LinkMeta_Issue725_v2_3_0.pdf) | Internet-aware links – direct response to Issue #725 |
| [White Paper v2.3.0](https://github.com/Link-Genetic-Inc/pdf-sdl-spec/blob/main/whitepaper/SDL_WhitePaper_From_Visual_to_Data_Fidelity_v2_3_0.pdf) | From Visual Fidelity to Data Fidelity |
| [Industry Profiles](https://github.com/Link-Genetic-Inc/pdf-sdl-spec/tree/main/profiles) | Financial · Pharmaceutical · Legal · Government · Scientific · Engineering |
| [🔗 Live Validator](https://link-genetic-inc.github.io/pdf-sdl-spec/presentation/SDL_DataDef_Validator_v1_0.html) | Interactive DataDef validation tool |

---

## Standardization

| Track | Body | Status |
|-------|------|--------|
| PDF Extension | PDF Association TWG / ISO TC 171 SC 2 | Discussion Paper (Feb 2026) |
| URI Scheme (LinkID) | IANA | Provisional registration (Oct 2025) |
| Web Platform (LinkID) | WICG | Proposal #238 (Oct 2025) |
| Web Architecture (LinkID) | W3C | TPAC 2025 Breakout Session |

---

## Contributing

Contributions welcome. For TWG-related feedback, please comment on [Issue #725](https://github.com/pdf-association/pdf-issues/issues/725).

---

## License

Apache 2.0 – Link Genetic GmbH
