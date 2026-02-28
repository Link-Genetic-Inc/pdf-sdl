# pdf-sdl

**Semantic Data Layer for PDF** – Python reference implementation of the DataDef extension to ISO 32000-2.

Addresses [Issue #725](https://github.com/pdf-association/pdf-issues/issues/725) – Lack of Internet-Aware Content Representation in PDF.

## Quick Start

```python
from pdf_sdl import DataDefBuilder, SDLWriter, SDLReader

datadef = (
    DataDefBuilder.table()
    .with_source("SAP S/4HANA, Q4 2024")
    .with_schema("https://schema.org/FinancialStatement")
    .trust_author(generator="MyApp v1.0")
    .bind_to_page(7)
    .build({"period": "FY2024", "rows": [{"label": "Revenue", "value": 4200000}]})
)

with SDLWriter("report.pdf") as writer:
    writer.add_datadef(datadef)
    writer.save("report-sdl.pdf")
```

See `examples/examples.py` for complete usage.

## License
Apache 2.0 – Link Genetic GmbH
