"""Vendor/format adapter registry.

The adapters distinguish *real decoding support* from vendor identification.  A vendor name
is never inferred merely because an adapter exists.  Standard containers and CCTV containers
that FFmpeg can actually demux are supported; OEM filesystem/protocol adapters remain explicit
extension points until validated against real OEM evidence.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class NormalizedEvidence:
    video_path: str
    vendor: str
    source_format: str
    channels: Optional[int] = None
    recording_start: Optional[str] = None
    notes: Optional[str] = None
    capabilities: Dict[str, str] = field(default_factory=dict)


class VendorAdapter:
    vendor = "Unknown"
    status = "IDENTIFICATION ONLY"
    supported_extensions: tuple[str, ...] = ()

    def can_handle(self, path: str, metadata: Optional[dict]) -> bool:
        return Path(path).suffix.lower().lstrip(".") in self.supported_extensions

    def parse(self, path: str, metadata: Optional[dict] = None) -> NormalizedEvidence:
        raise NotImplementedError


class StandardContainerAdapter(VendorAdapter):
    vendor = "Standard container"
    status = "SUPPORTED"
    supported_extensions = ("mp4", "mkv", "avi", "mov", "ts", "mts", "m2ts", "webm")

    def parse(self, path: str, metadata: Optional[dict] = None) -> NormalizedEvidence:
        return NormalizedEvidence(
            video_path=path, vendor="Unknown", source_format=Path(path).suffix.lower().lstrip("."),
            notes="Standard container; original evidence remains unchanged.",
            capabilities={"acquisition": "SUPPORTED", "filesystem_parser": "NOT APPLICABLE",
                          "format_decoder": "FFmpeg/standard container", "metadata_parser": "FFprobe"},
        )


class FfmpegCctvAdapter(VendorAdapter):
    """Real CCTV container decoding through the local FFmpeg installation.

    `.dav` maps to FFmpeg's `dhav` demuxer and `.ifv` to its IFV demuxer.  This does not
    claim vendor-specific filesystem parsing; it only decodes a supported container.
    """
    vendor = "CCTV container (FFmpeg)"
    status = "SUPPORTED"
    supported_extensions = ("dav", "ifv")

    def parse(self, path: str, metadata: Optional[dict] = None) -> NormalizedEvidence:
        ext = Path(path).suffix.lower().lstrip(".")
        return NormalizedEvidence(
            video_path=path, vendor="Unknown", source_format=ext,
            notes=f"FFmpeg CCTV demuxer available for .{ext}; vendor attribution requires evidence.",
            capabilities={"acquisition": "SUPPORTED_AS_FILE", "filesystem_parser": "NOT IMPLEMENTED",
                          "format_decoder": "SUPPORTED_VIA_FFMPEG", "metadata_parser": "FFprobe"},
        )


class RawVideoAdapter(VendorAdapter):
    vendor = "Raw video stream"
    status = "SUPPORTED"
    supported_extensions = ("h264", "264", "h265", "hevc")

    def parse(self, path: str, metadata: Optional[dict] = None) -> NormalizedEvidence:
        ext = Path(path).suffix.lower().lstrip(".")
        return NormalizedEvidence(
            video_path=path, vendor="Unknown", source_format=ext,
            notes="Raw elementary stream; timestamps/container metadata may be unavailable.",
            capabilities={"acquisition": "SUPPORTED_AS_FILE", "filesystem_parser": "NOT APPLICABLE",
                          "format_decoder": "FFmpeg", "metadata_parser": "FFprobe"},
        )


class OemIdentificationAdapter(VendorAdapter):
    """Explicit OEM boundary: identification can be performed elsewhere, parsing cannot."""
    status = "ADAPTER ARCHITECTURE READY - REQUIRES OEM SAMPLE/PROTOCOL"

    def __init__(self, vendor: str):
        self.vendor = vendor

    def parse(self, path: str, metadata: Optional[dict] = None) -> NormalizedEvidence:
        raise NotImplementedError(
            f"{self.vendor}: proprietary filesystem/acquisition protocol is not implemented; "
            "this adapter is identification-only."
        )


ADAPTERS: List[VendorAdapter] = [StandardContainerAdapter(), FfmpegCctvAdapter(), RawVideoAdapter()]
ADAPTERS.extend(OemIdentificationAdapter(v) for v in
                ("Dahua", "Hikvision", "CP Plus", "Honeywell", "TP-Link", "Godrej", "Uniview", "Matrix"))


def adapter_for(path: str, metadata: Optional[dict] = None) -> VendorAdapter:
    for adapter in ADAPTERS:
        if adapter.can_handle(path, metadata):
            return adapter
    return StandardContainerAdapter()


def normalize(path: str, metadata: Optional[dict] = None) -> NormalizedEvidence:
    return adapter_for(path, metadata).parse(path, metadata)


def support_matrix() -> Dict[str, str]:
    return {a.vendor: a.status for a in ADAPTERS}


def capability_matrix() -> Dict[str, dict]:
    return {
        a.vendor: {
            "status": a.status,
            "extensions": list(a.supported_extensions),
            "vendor_identification": "SEPARATE_EVIDENCE_BASED_STEP",
            "acquisition_adapter": "FILE_INGESTION" if a.status == "SUPPORTED" else "NOT IMPLEMENTED",
            "filesystem_parser": "NOT IMPLEMENTED" if "filesystem_parser" not in (a.__class__.__dict__) else "SEE_ADAPTER",
            "format_decoder": "FFMPEG" if isinstance(a, (FfmpegCctvAdapter, StandardContainerAdapter, RawVideoAdapter)) else "NOT IMPLEMENTED",
            "metadata_parser": "FFPROBE" if a.status == "SUPPORTED" else "NOT IMPLEMENTED",
        }
        for a in ADAPTERS
    }
