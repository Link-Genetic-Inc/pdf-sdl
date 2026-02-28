"""
pdf-sdl CLI
============
Command-line interface for the pdf-sdl library.

Commands:
    validate    Validate SDL DataDef/LinkMeta objects in a PDF
    inspect     Inspect and display all SDL content in a PDF
    inject      Inject a DataDef or LinkMeta into a PDF
    version     Show version information

Usage::

    pdf-sdl validate document.pdf
    pdf-sdl inspect report.pdf --format json
    pdf-sdl inject report.pdf --type table --data data.json --page 3
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="pdf-sdl")
def cli() -> None:
    """
    pdf-sdl – Semantic Data Layer for PDF.

    Reference implementation of the SDL DataDef extension to ISO 32000-2.
    Issue #725 – Lack of Internet-Aware Content Representation in PDF.
    """


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--full-scan", is_flag=True, help="Scan all objects (slower but complete)")
@click.option("--strict", is_flag=True, help="Exit with code 1 if any warnings")
@click.option("--json-output", is_flag=True, help="Output results as JSON")
def validate(
    pdf_path: Path,
    full_scan: bool,
    strict: bool,
    json_output: bool,
) -> None:
    """Validate SDL conformance of a PDF file."""
    try:
        from ..pdf.reader import SDLReader
        from ..validator.conformance import DataDefValidator, LinkMetaValidator
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        sys.exit(2)

    results_data: dict = {"file": str(pdf_path), "datadefs": [], "linkmetas": [], "summary": {}}

    with SDLReader(pdf_path) as reader:
        datadefs = reader.find_datadefs(full_scan=full_scan)
        linkmetas = reader.find_linkmetas()

    dd_validator = DataDefValidator()
    lm_validator = LinkMetaValidator()

    dd_results = [dd_validator.validate(dd) for dd in datadefs]
    lm_results = [lm_validator.validate(lm) for lm in linkmetas]

    all_passed = all(r.passed for r in dd_results + lm_results)
    has_warnings = any(r.warnings for r in dd_results + lm_results)

    if json_output:
        output = {
            "file": str(pdf_path),
            "passed": all_passed,
            "datadef_count": len(datadefs),
            "linkmeta_count": len(linkmetas),
            "results": [
                {
                    "type": "DataDef",
                    "passed": r.passed,
                    "conformance": r.conformance_level,
                    "errors": [{"rule": i.rule_id, "msg": i.message} for i in r.errors],
                    "warnings": [{"rule": i.rule_id, "msg": i.message} for i in r.warnings],
                }
                for r in dd_results
            ],
        }
        click.echo(json.dumps(output, indent=2))
    else:
        # Rich output
        console.print()
        status_str = "[bold green]PASS[/bold green]" if all_passed else "[bold red]FAIL[/bold red]"
        console.print(Panel(
            f"[bold]{pdf_path.name}[/bold]\n"
            f"Status: {status_str}  |  "
            f"DataDefs: {len(datadefs)}  |  LinkMetas: {len(linkmetas)}",
            title="pdf-sdl Validation",
            border_style="blue",
        ))

        if datadefs:
            t = Table(box=box.SIMPLE, title="DataDef Results")
            t.add_column("#", style="dim")
            t.add_column("DataType")
            t.add_column("Conformance")
            t.add_column("Trust")
            t.add_column("Status")
            t.add_column("Issues")

            for i, (dd, r) in enumerate(zip(datadefs, dd_results), 1):
                status_cell = "[green]✓ PASS[/green]" if r.passed else "[red]✗ FAIL[/red]"
                issues_str = ", ".join(f"{x.rule_id}" for x in r.issues[:3])
                if len(r.issues) > 3:
                    issues_str += f" +{len(r.issues)-3}"
                t.add_row(
                    str(i),
                    dd.data_type.value,
                    r.conformance_level,
                    str(dd.trust_level.value if dd.trust_level else "—"),
                    status_cell,
                    issues_str or "—",
                )
            console.print(t)

            # Detail issues
            for i, (dd, r) in enumerate(zip(datadefs, dd_results), 1):
                if r.issues:
                    console.print(f"\n[bold]DataDef #{i} ({dd.data_type.value}) issues:[/bold]")
                    for issue in r.issues:
                        color = "red" if issue.severity.value == "ERROR" else "yellow" if issue.severity.value == "WARNING" else "blue"
                        console.print(f"  [{color}]{issue.severity.value}[/{color}] [{issue.rule_id}] {issue.message}")

        if not datadefs and not linkmetas:
            console.print("\n[yellow]No SDL DataDef or LinkMeta objects found in this PDF.[/yellow]")
            console.print("Use [bold]pdf-sdl inject[/bold] to add SDL content.")

        console.print()

    exit_code = 0
    if not all_passed:
        exit_code = 1
    elif strict and has_warnings:
        exit_code = 1
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["rich", "json"]), default="rich")
@click.option("--full-scan", is_flag=True)
def inspect(pdf_path: Path, output_format: str, full_scan: bool) -> None:
    """Inspect all SDL content in a PDF file."""
    try:
        from ..pdf.reader import SDLReader
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        sys.exit(2)

    with SDLReader(pdf_path) as reader:
        summary = reader.summary()
        datadefs = reader.find_datadefs(full_scan=full_scan)
        linkmetas = reader.find_linkmetas()

    if output_format == "json":
        output = {
            "file": str(pdf_path),
            "summary": summary,
            "datadefs": [dd.model_dump(mode="json", exclude_none=True) for dd in datadefs],
            "linkmetas": [lm.model_dump(mode="json", exclude_none=True) for lm in linkmetas],
        }
        click.echo(json.dumps(output, indent=2, default=str))
        return

    console.print()
    console.print(Panel(
        f"[bold]{pdf_path.name}[/bold]\n"
        f"DataDefs: [cyan]{summary['datadef_count']}[/cyan]  |  "
        f"LinkMetas: [cyan]{summary['linkmeta_count']}[/cyan]",
        title="SDL Inspection",
        border_style="cyan",
    ))

    if datadefs:
        t = Table(title="DataDef Objects", box=box.ROUNDED)
        t.add_column("#")
        t.add_column("Type")
        t.add_column("Format")
        t.add_column("Trust")
        t.add_column("Conformance")
        t.add_column("Binding")
        t.add_column("Schema")

        for i, dd in enumerate(datadefs, 1):
            binding = (
                "StructRef" if dd.struct_ref else
                "AnnotRef" if dd.annot_ref else
                f"Page {dd.page_ref}" if dd.page_ref else
                "Document"
            )
            t.add_row(
                str(i),
                f"[cyan]{dd.data_type.value}[/cyan]",
                dd.format.value,
                str(dd.trust_level.value if dd.trust_level else "—"),
                dd.conformance_level().value,
                binding,
                "✓" if dd.schema_uri else "—",
            )
        console.print(t)

    if linkmetas:
        t = Table(title="LinkMeta Objects", box=box.ROUNDED)
        t.add_column("#")
        t.add_column("PID")
        t.add_column("LinkID")
        t.add_column("Title")
        t.add_column("Hash")
        t.add_column("Fallbacks")
        t.add_column("Status")
        t.add_column("Score")

        for i, lm in enumerate(linkmetas, 1):
            t.add_row(
                str(i),
                (lm.pid or "—")[:30],
                (lm.link_id or "—")[:35],
                (lm.title or "—")[:40],
                "✓" if lm.has_integrity() else "—",
                str(len(lm.alt_uris)),
                lm.status.value if lm.status else "—",
                f"{lm.capability_score()}/5",
            )
        console.print(t)

    if datadefs:
        console.print("\n[bold]Data Previews:[/bold]")
        for i, dd in enumerate(datadefs, 1):
            try:
                data = dd.data_as_dict()
                preview = json.dumps(data, indent=2)[:300]
                if len(json.dumps(data)) > 300:
                    preview += "\n  ... (truncated)"
                console.print(Panel(
                    preview,
                    title=f"DataDef #{i} – {dd.data_type.value}",
                    border_style="dim",
                ))
            except Exception:
                pass
    console.print()


# ---------------------------------------------------------------------------
# inject
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--type", "data_type", required=True,
              type=click.Choice([
                  "table", "record", "value", "series", "chart", "form",
                  "link", "reference", "formula", "code", "measurement",
                  "geospatial", "timeline", "classification", "provenance",
                  "identity", "translation", "custom"
              ]))
@click.option("--data", "data_file", type=click.Path(exists=True, path_type=Path),
              help="JSON file containing the data stream")
@click.option("--data-inline", help="Inline JSON string")
@click.option("--page", type=int, default=None, help="Page number (1-based) for spatial binding")
@click.option("--source", help="Origin system description")
@click.option("--generator", help="Generator software name")
@click.option("--schema", help="Schema URI")
@click.option("--trust", type=click.Choice(["author", "enriched", "signed"]), default="author")
@click.option("--confidence", type=float, default=None)
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None,
              help="Output path (default: overwrite input)")
@click.option("--incremental", is_flag=True, help="Use incremental save (preserves signatures)")
def inject(
    pdf_path: Path,
    data_type: str,
    data_file: Path | None,
    data_inline: str | None,
    page: int | None,
    source: str | None,
    generator: str | None,
    schema: str | None,
    trust: str,
    confidence: float | None,
    output: Path | None,
    incremental: bool,
) -> None:
    """Inject a DataDef into a PDF file."""
    try:
        from ..builder.datadef_builder import DataDefBuilder
        from ..pdf.writer import SDLWriter
        from ..models.datadef import DataType
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        sys.exit(2)

    # Load data
    if data_file:
        data = json.loads(data_file.read_text(encoding="utf-8"))
    elif data_inline:
        data = json.loads(data_inline)
    else:
        console.print("[red]Either --data or --data-inline is required[/red]")
        sys.exit(1)

    # Build DataDef
    type_map = {t.value.lower(): t for t in DataType}
    dt = type_map.get(data_type.lower(), DataType.CUSTOM)

    builder = DataDefBuilder(dt)

    if source:
        builder.with_source(source)
    if schema:
        builder.with_schema(schema)

    if trust == "author":
        builder.trust_author(generator=generator or "pdf-sdl CLI v0.1.0")
    elif trust == "enriched":
        conf = confidence if confidence is not None else 0.75
        builder.trust_enriched(
            generator=generator or "pdf-sdl CLI v0.1.0",
            confidence=conf,
        )
    elif trust == "signed":
        builder.trust_signed()

    if page:
        builder.bind_to_page(page)

    datadef = builder.build(data)

    output_path = output or pdf_path

    with SDLWriter(pdf_path) as writer:
        writer.add_datadef(datadef, page=page)
        writer.save(output_path, incremental=incremental)

    console.print(f"[green]✓[/green] DataDef ({data_type}) injected into [bold]{output_path}[/bold]")
    console.print(f"  Conformance: {datadef.conformance_level().value}")
    console.print(f"  Trust: {datadef.trust_level.value if datadef.trust_level else 'none'}")


# ---------------------------------------------------------------------------
# version info
# ---------------------------------------------------------------------------


@cli.command("version")
def show_version() -> None:
    """Show detailed version and specification information."""
    console.print(Panel(
        "[bold cyan]pdf-sdl[/bold cyan] v0.1.0\n\n"
        "Semantic Data Layer for PDF – Python Reference Implementation\n"
        "Specification: SDL Technical Specification v1.2.0\n"
        "Proposal: LinkMeta / Issue #725 v2.3.0\n\n"
        "Author:   Christian Nyffenegger, Link Genetic GmbH\n"
        "Target:   PDF Association TWG / ISO TC 171 SC 2\n"
        "License:  Apache 2.0\n"
        "GitHub:   https://github.com/Link-Genetic-Inc/pdf-sdl\n"
        "Issue #725: https://github.com/pdf-association/pdf-issues/issues/725",
        title="pdf-sdl",
        border_style="cyan",
    ))
