"""
PDF Reader
===========
Reads and extracts DataDef dictionaries and LinkMeta entries from PDF files.

Supports discovery via:
- Document catalog /DataDefs array (§5.5)
- Page-level /DataDefs arrays (§5.5)
- Annotation /LinkMeta entries
- Full document object scan (fallback)

Example::

    from pdf_sdl.pdf import SDLReader

    with SDLReader("document.pdf") as reader:
        datadefs = reader.find_datadefs()
        linkmetas = reader.find_linkmetas()
        for dd in datadefs:
            print(dd.data_type, dd.conformance_level())
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pikepdf

from ..models.datadef import DataDef, DataFormat, DataType, TrustLevel
from ..models.linkmeta import ContentHash, HashAlgorithm, LinkMeta, LinkStatus


class SDLReader:
    """
    Context-manager-based PDF reader for SDL DataDef and LinkMeta objects.

    Discovery strategy (§5.5):
    1. Check document catalog /DataDefs array
    2. Check each page's /DataDefs array
    3. Check annotations for /LinkMeta
    4. (Optional) full scan for any /Type /DataDef object
    """

    def __init__(self, source: str | Path) -> None:
        self._path = Path(source)
        self._pdf = pikepdf.open(str(source))

    def __enter__(self) -> "SDLReader":
        return self

    def __exit__(self, *_: Any) -> None:
        self._pdf.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_datadefs(self, *, full_scan: bool = False) -> list[DataDef]:
        """
        Find all DataDef objects in the document.

        Parameters
        ----------
        full_scan:
            If True, scan all indirect objects in the file (slower but complete).
            Default: use catalog + page arrays only.
        """
        refs: set[int] = set()
        datadefs: list[DataDef] = []

        # 1. Catalog discovery
        catalog = self._pdf.Root
        if "/DataDefs" in catalog:
            for ref in catalog["/DataDefs"]:
                obj_id = self._obj_id(ref)
                if obj_id not in refs:
                    refs.add(obj_id)
                    dd = self._parse_datadef(ref)
                    if dd:
                        datadefs.append(dd)

        # 2. Page-level discovery
        for page in self._pdf.pages:
            if "/DataDefs" in page:
                for ref in page["/DataDefs"]:
                    obj_id = self._obj_id(ref)
                    if obj_id not in refs:
                        refs.add(obj_id)
                        dd = self._parse_datadef(ref)
                        if dd:
                            datadefs.append(dd)

        # 3. Full scan (optional)
        if full_scan:
            for obj in self._pdf.objects:
                try:
                    if (
                        isinstance(obj, pikepdf.Dictionary)
                        and obj.get("/Type") == pikepdf.Name("/DataDef")
                        and self._obj_id(obj) not in refs
                    ):
                        refs.add(self._obj_id(obj))
                        dd = self._parse_datadef(obj)
                        if dd:
                            datadefs.append(dd)
                except Exception:
                    continue

        return datadefs

    def find_linkmetas(self) -> list[LinkMeta]:
        """
        Find all LinkMeta dictionaries by scanning annotations on all pages.
        """
        linkmetas: list[LinkMeta] = []
        for page_num, page in enumerate(self._pdf.pages, start=1):
            if "/Annots" not in page:
                continue
            for annot_idx, annot in enumerate(page["/Annots"]):
                try:
                    annot_obj = annot
                    if hasattr(annot, "obj"):
                        annot_obj = annot.obj
                    if "/LinkMeta" in annot_obj:
                        lm = self._parse_linkmeta(
                            annot_obj["/LinkMeta"],
                            annot_ref=f"page {page_num} annot {annot_idx}",
                        )
                        if lm:
                            linkmetas.append(lm)
                except Exception:
                    continue
        return linkmetas

    def get_datadef_count(self) -> int:
        """Returns the number of DataDef objects discoverable via catalog."""
        catalog = self._pdf.Root
        if "/DataDefs" in catalog:
            return len(list(catalog["/DataDefs"]))
        return 0

    def summary(self) -> dict[str, Any]:
        """Return a summary of SDL content in the document."""
        datadefs = self.find_datadefs()
        linkmetas = self.find_linkmetas()
        type_counts: dict[str, int] = {}
        for dd in datadefs:
            k = dd.data_type.value
            type_counts[k] = type_counts.get(k, 0) + 1
        return {
            "source": str(self._path),
            "datadef_count": len(datadefs),
            "linkmeta_count": len(linkmetas),
            "datatype_breakdown": type_counts,
            "conformance_levels": [dd.conformance_level().value for dd in datadefs],
        }

    # ------------------------------------------------------------------
    # Internal parsers
    # ------------------------------------------------------------------

    def _parse_datadef(self, obj: pikepdf.Object) -> DataDef | None:
        """Parse a pikepdf object into a DataDef model."""
        try:
            if hasattr(obj, "obj"):
                obj = obj.obj

            if not isinstance(obj, pikepdf.Dictionary):
                return None
            if obj.get("/Type") != pikepdf.Name("/DataDef"):
                return None

            # Required keys
            data_type_name = str(obj.get("/DataType", "/Custom")).lstrip("/")
            format_name = str(obj.get("/Format", "/JSON")).lstrip("/")

            try:
                data_type = DataType(data_type_name)
            except ValueError:
                data_type = DataType.CUSTOM

            try:
                fmt = DataFormat(format_name)
            except ValueError:
                fmt = DataFormat.JSON

            # Read data stream
            data_str = ""
            if "/Data" in obj:
                data_obj = obj["/Data"]
                if hasattr(data_obj, "obj"):
                    data_obj = data_obj.obj
                if isinstance(data_obj, pikepdf.Stream):
                    raw = data_obj.read_bytes()
                    data_str = raw.decode("utf-8", errors="replace")
                elif isinstance(data_obj, pikepdf.Dictionary):
                    data_str = "{}"

            # Optional keys
            trust_level = None
            tl_val = obj.get("/TrustLevel")
            if tl_val:
                try:
                    trust_level = TrustLevel(str(tl_val).lstrip("/"))
                except ValueError:
                    pass

            confidence = None
            if "/Confidence" in obj:
                confidence = float(obj["/Confidence"])

            created = None
            if "/Created" in obj:
                try:
                    created_str = str(obj["/Created"]).lstrip("D:")
                    created = datetime.strptime(created_str[:14], "%Y%m%d%H%M%S")
                except Exception:
                    pass

            rect = None
            if "/Rect" in obj:
                try:
                    r = obj["/Rect"]
                    rect = (float(r[0]), float(r[1]), float(r[2]), float(r[3]))
                except Exception:
                    pass

            return DataDef(
                version=int(obj.get("/Version", 1)),
                data_type=data_type,
                format=fmt,
                data=data_str,
                encoding=str(obj.get("/Encoding", "UTF-8")).lstrip("/"),
                schema_uri=self._str_or_none(obj.get("/Schema")),
                schema_version=self._str_or_none(obj.get("/SchemaVersion")),
                source=self._str_or_none(obj.get("/Source")),
                created=created,
                generator=self._str_or_none(obj.get("/Generator")),
                trust_level=trust_level,
                confidence=confidence,
                struct_ref=self._str_or_none(obj.get("/StructRef")),
                annot_ref=self._str_or_none(obj.get("/AnnotRef")),
                page_ref=self._int_or_none(obj.get("/PageRef")),
                rect=rect,
                status_uri=self._str_or_none(obj.get("/StatusURI")),
            )
        except Exception:
            return None

    def _parse_linkmeta(self, obj: pikepdf.Object, annot_ref: str = "") -> LinkMeta | None:
        """Parse a pikepdf object into a LinkMeta model."""
        try:
            if hasattr(obj, "obj"):
                obj = obj.obj
            if not isinstance(obj, pikepdf.Dictionary):
                return None

            status = None
            s_val = obj.get("/Status")
            if s_val:
                try:
                    status = LinkStatus(str(s_val).lstrip("/"))
                except ValueError:
                    pass

            hash_obj = None
            if "/Hash" in obj:
                h = obj["/Hash"]
                algo_str = str(h.get("/Algorithm", "/SHA-256")).lstrip("/")
                try:
                    algo = HashAlgorithm(algo_str)
                except ValueError:
                    algo = HashAlgorithm.SHA256
                hash_val = self._str_or_none(h.get("/Value")) or ""
                hash_obj = ContentHash(algorithm=algo, value=hash_val)

            alt_uris: list[str] = []
            if "/AltURIs" in obj:
                alt_uris = [str(u) for u in obj["/AltURIs"]]

            trust_level = self._str_or_none(obj.get("/TrustLevel"))
            if trust_level:
                trust_level = trust_level.lstrip("/")

            confidence = None
            if "/Confidence" in obj:
                confidence = float(obj["/Confidence"])

            return LinkMeta(
                pid=self._str_or_none(obj.get("/PID")),
                LinkID=self._str_or_none(obj.get("/LinkID")),
                title=self._str_or_none(obj.get("/Title")),
                desc=self._str_or_none(obj.get("/Desc")),
                lang=self._str_or_none(obj.get("/Lang")),
                RefDate=self._str_or_none(obj.get("/RefDate")),
                ContentType=self._str_or_none(obj.get("/ContentType")),
                hash=hash_obj,
                AltURIs=alt_uris,
                status=status,
                LastChecked=self._str_or_none(obj.get("/LastChecked")),
                StatusURI=self._str_or_none(obj.get("/StatusURI")),
                TrustLevel=trust_level,
                generator=self._str_or_none(obj.get("/Generator")),
                confidence=confidence,
                annot_ref=annot_ref,
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _obj_id(obj: pikepdf.Object) -> int:
        try:
            return obj.objgen[0] if hasattr(obj, "objgen") else id(obj)
        except Exception:
            return id(obj)

    @staticmethod
    def _str_or_none(val: Any) -> str | None:
        if val is None:
            return None
        s = str(val)
        return s if s else None

    @staticmethod
    def _int_or_none(val: Any) -> int | None:
        if val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None
