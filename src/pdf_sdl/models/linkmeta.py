"""
LinkMeta Dictionary – Model
============================
Python representation of the LinkMeta dictionary as specified in
PDF Association Proposal v2.3.0 (§3).

LinkMeta is an optional dictionary attached to Link Annotations via a new
/LinkMeta key on Table 176 of ISO 32000-2. It adds internet-awareness to
PDF links: identification, context, integrity, fallback, and status.

Issue #725 – Lack of Internet-Aware Content Representation in PDF.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LinkStatus(str, Enum):
    """Live status of the referenced resource (§3.2 /Status)."""
    ACTIVE = "Active"
    ARCHIVED = "Archived"
    BROKEN = "Broken"
    UNKNOWN = "Unknown"


class HashAlgorithm(str, Enum):
    """Supported hash algorithms for content integrity (§3.2 /Hash/Algorithm)."""
    SHA256 = "SHA-256"
    SHA384 = "SHA-384"
    SHA512 = "SHA-512"


class ContentHash(BaseModel):
    """
    Content hash of the target resource at /RefDate (§3.2 Integrity).
    Provides cryptographic proof that the referenced content has not changed.
    """
    model_config = ConfigDict(frozen=True)

    algorithm: HashAlgorithm = Field(
        HashAlgorithm.SHA256,
        description="Hash algorithm",
    )
    value: str = Field(..., description="Hex-encoded hash value")

    def to_pdf_dict(self) -> dict[str, str]:
        return {"Algorithm": f"/{self.algorithm.value}", "Value": self.value}


class LinkMeta(BaseModel):
    """
    LinkMeta Dictionary (§3.2).

    Attached to a Link Annotation via /LinkMeta key.
    Adds five missing dimensions to PDF hyperlinks:
    identification, context, integrity, fallback, and status.

    The existing /A (URI Action) and /PA (Preserved Action) keys remain
    unchanged. LinkMeta adds knowledge *about* the link target without
    affecting how the link *behaves*.
    """
    model_config = ConfigDict(populate_by_name=True)

    # --- Required ---
    type: str = Field("LinkMeta", description="Must be /LinkMeta")
    version: int = Field(1, ge=1, description="Schema version")

    # --- Identification (§3.2) ---
    pid: str | None = Field(
        None,
        description="Persistent Identifier: DOI, ARK, Handle, URN, or other system",
    )
    link_id: str | None = Field(
        None,
        alias="LinkID",
        description="LinkID identifier per IANA linkid: scheme (§5)",
    )

    # --- Context (§3.2) ---
    title: str | None = Field(None, description="Title of the referenced resource")
    desc: str | None = Field(None, description="Purpose of the reference (why this link exists)")
    lang: str | None = Field(None, description="Language of target resource (BCP 47)")
    ref_date: str | None = Field(
        None,
        alias="RefDate",
        description="Timestamp of referencing (PDF Date Format). Recommended.",
    )
    content_type: str | None = Field(
        None,
        alias="ContentType",
        description="MIME type of target resource",
    )

    # --- Integrity (§3.2) ---
    hash: ContentHash | None = Field(
        None,
        description="Content hash of target resource at /RefDate",
    )

    # --- Fallback and Status (§3.2) ---
    alt_uris: list[str] = Field(
        default_factory=list,
        alias="AltURIs",
        description="Alternative URIs, ordered by preference (archives, mirrors)",
    )
    status: LinkStatus | None = Field(None, description="Active | Archived | Broken | Unknown")
    last_checked: str | None = Field(
        None,
        alias="LastChecked",
        description="Last availability check (PDF Date Format)",
    )
    status_uri: str | None = Field(
        None,
        alias="StatusURI",
        description="URI for live status query (opt-in, never automatic)",
    )

    # --- Trust level (§7.2 of LinkMeta proposal) ---
    trust_level: str | None = Field(
        None,
        alias="TrustLevel",
        description="Signed | Author | Enriched",
    )
    generator: str | None = Field(
        None,
        description="Software or service (required when TrustLevel is Enriched)",
    )
    confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Accuracy confidence (required when TrustLevel is Enriched)",
    )

    # --- Internal tracking ---
    annot_ref: str | None = Field(
        None,
        description="Object reference to the Link Annotation this belongs to",
    )

    @model_validator(mode="after")
    def validate_enriched_fields(self) -> "LinkMeta":
        if self.trust_level == "Enriched":
            if not self.generator:
                raise ValueError("generator is required when trust_level is 'Enriched'")
            if self.confidence is None:
                raise ValueError("confidence is required when trust_level is 'Enriched'")
        return self

    def is_minimal(self) -> bool:
        """
        A minimal valid LinkMeta has only /Type, /Version, and optionally /RefDate.
        Even this captures *when* the link was created (§3.3).
        """
        return True  # type and version are always present

    def has_integrity(self) -> bool:
        """True if a content hash is present for integrity verification."""
        return self.hash is not None

    def has_fallback(self) -> bool:
        """True if alternative URIs are defined."""
        return len(self.alt_uris) > 0

    def has_persistent_id(self) -> bool:
        """True if at least one persistent identifier is present."""
        return self.pid is not None or self.link_id is not None

    def capability_score(self) -> int:
        """
        Returns a score 0-5 indicating how many of the five link dimensions
        are covered: identification, context, integrity, fallback, status.
        """
        score = 0
        if self.has_persistent_id():
            score += 1
        if self.title or self.desc or self.ref_date or self.content_type:
            score += 1
        if self.has_integrity():
            score += 1
        if self.has_fallback():
            score += 1
        if self.status is not None:
            score += 1
        return score

    def to_pdf_dict(self) -> dict[str, Any]:
        """Serialize to a flat dict suitable for PDF dictionary construction."""
        d: dict[str, Any] = {"Type": "LinkMeta", "Version": self.version}
        if self.pid:
            d["PID"] = self.pid
        if self.link_id:
            d["LinkID"] = self.link_id
        if self.title:
            d["Title"] = self.title
        if self.desc:
            d["Desc"] = self.desc
        if self.lang:
            d["Lang"] = self.lang
        if self.ref_date:
            d["RefDate"] = self.ref_date
        if self.content_type:
            d["ContentType"] = self.content_type
        if self.hash:
            d["Hash"] = self.hash.to_pdf_dict()
        if self.alt_uris:
            d["AltURIs"] = self.alt_uris
        if self.status:
            d["Status"] = f"/{self.status.value}"
        if self.last_checked:
            d["LastChecked"] = self.last_checked
        if self.status_uri:
            d["StatusURI"] = self.status_uri
        if self.trust_level:
            d["TrustLevel"] = f"/{self.trust_level}"
        if self.generator:
            d["Generator"] = self.generator
        if self.confidence is not None:
            d["Confidence"] = self.confidence
        return d

    def __repr__(self) -> str:
        caps = self.capability_score()
        return (
            f"LinkMeta(pid={self.pid!r}, link_id={self.link_id!r}, "
            f"has_hash={self.has_integrity()}, alt_uris={len(self.alt_uris)}, "
            f"capability={caps}/5)"
        )
