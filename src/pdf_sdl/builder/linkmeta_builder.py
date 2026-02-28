"""
LinkMeta Builder
=================
Fluent builder API for constructing LinkMeta dictionaries.

Example::

    from pdf_sdl.builder import LinkMetaBuilder

    meta = (
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
        .integrity(algorithm="SHA-256", hash_value="a1b2c3d4...")
        .fallback(
            "https://web.archive.org/web/20250115/https://example.com/report.pdf",
            "https://perma.cc/AB12-CD34",
        )
        .status_active()
        .build()
    )
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models.linkmeta import ContentHash, HashAlgorithm, LinkMeta, LinkStatus


class LinkMetaBuilder:
    """
    Fluent builder for LinkMeta dictionaries.

    Even a minimal call to .build() produces a valid LinkMeta (§3.3).
    """

    def __init__(self) -> None:
        self._pid: str | None = None
        self._link_id: str | None = None
        self._title: str | None = None
        self._desc: str | None = None
        self._lang: str | None = None
        self._ref_date: str | None = None
        self._content_type: str | None = None
        self._hash: ContentHash | None = None
        self._alt_uris: list[str] = []
        self._status: LinkStatus | None = None
        self._last_checked: str | None = None
        self._status_uri: str | None = None
        self._trust_level: str | None = None
        self._generator: str | None = None
        self._confidence: float | None = None
        self._annot_ref: str | None = None
        # Auto-stamp ref_date
        self._ref_date = datetime.now(tz=timezone.utc).strftime(
            "D:%Y%m%d%H%M%S+00'00'"
        )

    # --- Identification (§3.2) ---

    def identify(
        self,
        pid: str | None = None,
        link_id: str | None = None,
    ) -> "LinkMetaBuilder":
        """
        Set persistent identifiers.

        pid:     DOI, ARK, Handle, URN, or any other persistent ID system.
        link_id: LinkID per IANA linkid: URI scheme (§5).
        """
        self._pid = pid
        self._link_id = link_id
        return self

    # --- Context (§3.2) ---

    def context(
        self,
        title: str | None = None,
        desc: str | None = None,
        lang: str | None = None,
        content_type: str | None = None,
        ref_date: str | None = None,
    ) -> "LinkMetaBuilder":
        """Set context metadata about the referenced resource."""
        if title:
            self._title = title
        if desc:
            self._desc = desc
        if lang:
            self._lang = lang
        if content_type:
            self._content_type = content_type
        if ref_date:
            self._ref_date = ref_date
        return self

    # --- Integrity (§3.2) ---

    def integrity(
        self,
        hash_value: str,
        algorithm: str = "SHA-256",
    ) -> "LinkMetaBuilder":
        """
        Add content hash for integrity verification.

        hash_value: Hex-encoded hash of the target resource at ref_date.
        algorithm:  SHA-256 (default), SHA-384, or SHA-512.
        """
        algo_map = {
            "SHA-256": HashAlgorithm.SHA256,
            "SHA-384": HashAlgorithm.SHA384,
            "SHA-512": HashAlgorithm.SHA512,
        }
        algo = algo_map.get(algorithm, HashAlgorithm.SHA256)
        self._hash = ContentHash(algorithm=algo, value=hash_value)
        return self

    # --- Fallback (§3.2) ---

    def fallback(self, *uris: str) -> "LinkMetaBuilder":
        """
        Add alternative/fallback URIs, ordered by preference.
        Typical sources: Wayback Machine, Perma.cc, national archives.
        """
        self._alt_uris.extend(uris)
        return self

    # --- Status (§3.2) ---

    def status_active(self) -> "LinkMetaBuilder":
        """Mark the referenced resource as currently active."""
        self._status = LinkStatus.ACTIVE
        self._last_checked = datetime.now(tz=timezone.utc).strftime(
            "D:%Y%m%d%H%M%S+00'00'"
        )
        return self

    def status_archived(self) -> "LinkMetaBuilder":
        """Mark as archived (historical state, not live)."""
        self._status = LinkStatus.ARCHIVED
        return self

    def status_broken(self) -> "LinkMetaBuilder":
        """Mark as broken (resource no longer accessible)."""
        self._status = LinkStatus.BROKEN
        return self

    def status_unknown(self) -> "LinkMetaBuilder":
        """Mark as unknown status."""
        self._status = LinkStatus.UNKNOWN
        return self

    def with_status_uri(self, uri: str) -> "LinkMetaBuilder":
        """
        Add opt-in live status URI.
        MUST NOT be queried automatically – requires explicit user consent (§7.1).
        """
        self._status_uri = uri
        return self

    # --- Trust levels (§7.2 of LinkMeta proposal) ---

    def trust_signed(self) -> "LinkMetaBuilder":
        """LinkMeta is within digital signature scope. Highest trust."""
        self._trust_level = "Signed"
        return self

    def trust_author(self) -> "LinkMetaBuilder":
        """Created at authoring time, not signed. Medium trust."""
        self._trust_level = "Author"
        return self

    def trust_enriched(
        self,
        generator: str,
        confidence: float,
    ) -> "LinkMetaBuilder":
        """
        Added post-creation by AI or tools. Lowest trust.
        Both generator and confidence are required (§7.2).
        """
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        self._trust_level = "Enriched"
        self._generator = generator
        self._confidence = confidence
        return self

    # --- Binding ---

    def bind_to_annot(self, object_ref: str) -> "LinkMetaBuilder":
        """Reference to the Link Annotation this LinkMeta is attached to."""
        self._annot_ref = object_ref
        return self

    # --- Build ---

    def build(self) -> LinkMeta:
        """Construct and return the LinkMeta object."""
        return LinkMeta(
            pid=self._pid,
            LinkID=self._link_id,
            title=self._title,
            desc=self._desc,
            lang=self._lang,
            RefDate=self._ref_date,
            ContentType=self._content_type,
            hash=self._hash,
            AltURIs=self._alt_uris,
            status=self._status,
            LastChecked=self._last_checked,
            StatusURI=self._status_uri,
            TrustLevel=self._trust_level,
            generator=self._generator,
            confidence=self._confidence,
            annot_ref=self._annot_ref,
        )
