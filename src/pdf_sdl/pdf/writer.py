"""
PDF Writer
===========
Writes DataDef dictionaries and LinkMeta entries into PDF files using pikepdf.

Supports:
- Adding DataDefs to new and existing PDFs
- Adding LinkMeta to Link Annotations
- Document-catalog /DataDefs discovery array (§5.5)
- Page-level /DataDefs arrays (§5.5)
- Incremental save (preserves existing digital signatures)

Example::

    from pdf_sdl.pdf import SDLWriter
    from pdf_sdl.builder import DataDefBuilder

    datadef = DataDefBuilder.table().trust_author("MyApp v1").build({"rows": [...]})

    with SDLWriter("input.pdf") as writer:
        writer.add_datadef(datadef, page=1)
        writer.save("output.pdf")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pikepdf

from ..models.datadef import DataDef, DataType
from ..models.linkmeta import LinkMeta


class SDLWriter:
    """
    Context-manager-based PDF writer for SDL DataDef and LinkMeta objects.

    Usage::

        with SDLWriter("input.pdf") as w:
            w.add_datadef(datadef, page=1)
            w.add_linkmeta(linkmeta, annot_index=0, page=1)
            w.save("output.pdf")
    """

    SDL_GENERATOR = "pdf-sdl v0.1.0 (https://github.com/Link-Genetic-Inc/pdf-sdl)"

    def __init__(self, source: str | Path | None = None) -> None:
        """
        Parameters
        ----------
        source:
            Path to an existing PDF to open, or None to create a new empty PDF.
        """
        if source is not None:
            self._pdf = pikepdf.open(str(source))
        else:
            self._pdf = pikepdf.new()
            # Add a blank page so the document is valid
            page_dict = pikepdf.Dictionary(
                Type=pikepdf.Name("/Page"),
                MediaBox=pikepdf.Array([0, 0, 595, 842]),
            )
            self._pdf.make_indirect(page_dict)
            self._pdf.pages.append(pikepdf.Page(page_dict))

        self._written_datadefs: list[pikepdf.Object] = []

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "SDLWriter":
        return self

    def __exit__(self, *_: Any) -> None:
        self._pdf.close()

    # ------------------------------------------------------------------
    # DataDef writing
    # ------------------------------------------------------------------

    def add_datadef(
        self,
        datadef: DataDef,
        *,
        page: int | None = None,
        add_to_catalog: bool = True,
    ) -> pikepdf.Object:
        """
        Write a DataDef dictionary (plus its data stream) into the PDF.

        Parameters
        ----------
        datadef:
            The DataDef object to write.
        page:
            1-based page number to also add to the page's /DataDefs array.
            If None, only added to the catalog (unless add_to_catalog=False).
        add_to_catalog:
            Whether to register in the document catalog's /DataDefs array (§5.5).

        Returns
        -------
        The pikepdf indirect object reference for the written DataDef.
        """
        # Build the data stream
        data_bytes = self._encode_data(datadef)
        stream_obj = pikepdf.Stream(self._pdf, data_bytes)
        stream_ref = self._pdf.make_indirect(stream_obj)

        # Build the DataDef dictionary
        dd_dict = pikepdf.Dictionary(
            Type=pikepdf.Name("/DataDef"),
            Version=datadef.version,
            DataType=pikepdf.Name(f"/{datadef.data_type.value}"),
            Format=pikepdf.Name(f"/{datadef.format.value}"),
            Data=stream_ref,
        )

        if datadef.encoding != "UTF-8":
            dd_dict["/Encoding"] = pikepdf.Name(f"/{datadef.encoding}")
        if datadef.schema_uri:
            dd_dict["/Schema"] = datadef.schema_uri
        if datadef.schema_version:
            dd_dict["/SchemaVersion"] = datadef.schema_version
        if datadef.source:
            dd_dict["/Source"] = datadef.source
        if datadef.created:
            dd_dict["/Created"] = datadef.created.strftime("D:%Y%m%d%H%M%S+00'00'")
        if datadef.generator:
            dd_dict["/Generator"] = datadef.generator
        if datadef.trust_level:
            dd_dict["/TrustLevel"] = pikepdf.Name(f"/{datadef.trust_level.value}")
        if datadef.confidence is not None:
            dd_dict["/Confidence"] = datadef.confidence
        if datadef.struct_ref:
            dd_dict["/StructRef"] = pikepdf.String(datadef.struct_ref)
        if datadef.annot_ref:
            dd_dict["/AnnotRef"] = pikepdf.String(datadef.annot_ref)
        if datadef.page_ref is not None:
            dd_dict["/PageRef"] = datadef.page_ref
        if datadef.rect:
            dd_dict["/Rect"] = pikepdf.Array([float(v) for v in datadef.rect])
        if datadef.status_uri:
            dd_dict["/StatusURI"] = datadef.status_uri

        dd_ref = self._pdf.make_indirect(dd_dict)
        self._written_datadefs.append(dd_ref)

        # Register in catalog
        if add_to_catalog:
            self._register_in_catalog(dd_ref)

        # Register on page
        if page is not None:
            self._register_on_page(dd_ref, page)

        return dd_ref

    def add_linkmeta(
        self,
        linkmeta: LinkMeta,
        *,
        annot_index: int = 0,
        page: int = 1,
    ) -> pikepdf.Object:
        """
        Add a LinkMeta dictionary to a Link Annotation on the specified page.

        Parameters
        ----------
        linkmeta:
            The LinkMeta object to write.
        annot_index:
            Index of the annotation in the page's /Annots array (0-based).
        page:
            1-based page number.

        Returns
        -------
        The pikepdf indirect object for the written LinkMeta.
        """
        lm_dict = pikepdf.Dictionary(
            Type=pikepdf.Name("/LinkMeta"),
            Version=linkmeta.version,
        )
        d = linkmeta.to_pdf_dict()
        for key, val in d.items():
            if key in ("Type", "Version"):
                continue
            pk = f"/{key}"
            if isinstance(val, str) and val.startswith("/"):
                lm_dict[pk] = pikepdf.Name(val)
            elif isinstance(val, list):
                lm_dict[pk] = pikepdf.Array([pikepdf.String(u) for u in val])
            elif isinstance(val, dict):
                # Nested dict (e.g. Hash)
                inner = pikepdf.Dictionary()
                for ik, iv in val.items():
                    if isinstance(iv, str) and iv.startswith("/"):
                        inner[f"/{ik}"] = pikepdf.Name(iv)
                    else:
                        inner[f"/{ik}"] = iv
                lm_dict[pk] = inner
            elif isinstance(val, float):
                lm_dict[pk] = val
            elif isinstance(val, int):
                lm_dict[pk] = val
            else:
                lm_dict[pk] = pikepdf.String(str(val))

        lm_ref = self._pdf.make_indirect(lm_dict)

        # Attach to the annotation
        try:
            page_obj = self._pdf.pages[page - 1]
            if "/Annots" in page_obj:
                annots = page_obj["/Annots"]
                if annot_index < len(annots):
                    annot = annots[annot_index]
                    annot["/LinkMeta"] = lm_ref
        except (IndexError, KeyError):
            pass  # Annotation not found – LinkMeta still written as indirect object

        return lm_ref

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(
        self,
        output: str | Path,
        *,
        incremental: bool = False,
        linearize: bool = False,
    ) -> None:
        """
        Save the modified PDF.

        Parameters
        ----------
        output:
            Output file path.
        incremental:
            If True, use incremental save (preserves existing signatures). (§7.1)
        linearize:
            If True, linearize (web-optimized) the output.
        """
        options: dict[str, Any] = {}
        if linearize:
            options["linearize"] = True

        if incremental:
            self._pdf.save(str(output), incremental=True)
        else:
            self._pdf.save(str(output), **options)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _encode_data(self, datadef: DataDef) -> bytes:
        """Serialize the DataDef data to bytes for the PDF stream."""
        if isinstance(datadef.data, str):
            raw = datadef.data
        else:
            raw = json.dumps(datadef.data, ensure_ascii=False, indent=2)
        return raw.encode(datadef.encoding or "utf-8")

    def _register_in_catalog(self, dd_ref: pikepdf.Object) -> None:
        """Add dd_ref to the document catalog's /DataDefs array (§5.5)."""
        catalog = self._pdf.Root
        if "/DataDefs" not in catalog:
            catalog["/DataDefs"] = pikepdf.Array()
        catalog["/DataDefs"].append(dd_ref)

    def _register_on_page(self, dd_ref: pikepdf.Object, page: int) -> None:
        """Add dd_ref to the specified page's /DataDefs array (§5.5)."""
        try:
            page_obj = self._pdf.pages[page - 1]
            if "/DataDefs" not in page_obj:
                page_obj["/DataDefs"] = pikepdf.Array()
            page_obj["/DataDefs"].append(dd_ref)
        except IndexError:
            pass

    @property
    def pdf(self) -> pikepdf.Pdf:
        """Direct access to the underlying pikepdf.Pdf object."""
        return self._pdf
