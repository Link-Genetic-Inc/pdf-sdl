# Changelog

All notable changes to pdf-sdl will be documented in this file.

## [0.1.0] – February 2026

### Added
- **Core models**: `DataDef`, `LinkMeta` with full Pydantic v2 validation
- **18 DataTypes**: Table, Record, Value, Series, Chart, Form, Link, Reference,
  Formula, Code, Measurement, Geospatial, Timeline, Classification, Provenance,
  Identity, Translation, Custom
- **Fluent builders**: `DataDefBuilder` and `LinkMetaBuilder` with chainable API
- **PDF I/O**: `SDLWriter` and `SDLReader` via pikepdf (pikepdf ≥ 8)
- **Conformance validator**: `DataDefValidator` (15 rules) and `LinkMetaValidator` (10 rules)
- **CLI**: `pdf-sdl validate`, `pdf-sdl inspect`, `pdf-sdl inject`, `pdf-sdl version`
- **Trust levels**: Signed, Author, Enriched with confidence scoring
- **Binding mechanisms**: StructRef, AnnotRef, PageRef+Rect, Document-level
- **Issue #725 support**: `/DataType /Link` with persistent IDs, hash integrity, fallback URIs
- **EU AI Act support**: `/DataType /Provenance` with AI model metadata
- **LinkID support**: `linkid:` URI scheme (IANA provisional, October 2025)
- Comprehensive test suite (50+ tests across all modules)
- Three complete usage examples

### Specification
- Implements SDL Technical Specification v1.2.0
- Implements LinkMeta Proposal v2.3.0
- Targets ISO 32000-2 (PDF 2.0) extension
- PDF Association Issue #725 – Internet-Aware Content Representation

### Known Limitations
- Associated Files integration pending TWG guidance (§7.5 of spec)
- CBOR format serialization not yet implemented (JSON/XML/CSV supported)
- Digital signature scope verification requires pkcs7 integration (planned v0.2.0)
- Full-scan object enumeration performance not optimized for large PDFs
