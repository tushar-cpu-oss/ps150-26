"""Pure (database-free) vendor inference from evidence metadata.

Only text matches on real metadata tags / filename are used. Confidence is categorical
("low" / "none") - never a fabricated number.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

VENDOR_PATTERNS = {
    "Hikvision": [r"hikvision", r"hik-?vision"],
    "Dahua": [r"dahua"],
    "CP Plus": [r"cp[\s_-]?plus"],
    "Honeywell": [r"honeywell"],
    "TP-Link": [r"tp[\s_-]?link", r"\bvigi\b"],
    "Godrej": [r"godrej"],
    "Uniview": [r"uniview"],
    "Matrix": [r"\bmatrix\b"],
}
UNKNOWN_NOTE = "Vendor could not be determined from available evidence metadata."
FIELD_KEYS = {
    "model": ("model", "model_name", "device_model"),
    "serial_number": ("serial", "serial_number", "serialnumber"),
    "firmware": ("firmware", "firmware_version", "fw_version"),
}


def _collect_fields(meta: Dict[str, Any], filename: str) -> List[Tuple[str, str]]:
    fields = [("filename", filename or "")]
    for k, v in (meta.get("tags") or {}).items():
        fields.append((f"format tag '{k}'", str(v)))
    for i, tags in enumerate(meta.get("stream_tags") or []):
        for k, v in tags.items():
            fields.append((f"stream {i} tag '{k}'", str(v)))
    return fields


def infer_from_metadata(meta: Optional[Dict[str, Any]], filename: str) -> Dict[str, Any]:
    meta = meta or {}
    fields = _collect_fields(meta, filename)
    manufacturer, basis = "Unknown", UNKNOWN_NOTE
    for vendor, patterns in VENDOR_PATTERNS.items():
        for where, text in fields:
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                manufacturer = vendor
                basis = (f"Keyword match for '{vendor}' in {where}. This is a text match only and "
                         f"is not verified against the device.")
                break
        if manufacturer != "Unknown":
            break
    found: Dict[str, Optional[str]] = {"model": None, "serial_number": None, "firmware": None}
    all_tags = {**(meta.get("tags") or {})}
    for t in meta.get("stream_tags") or []:
        all_tags.update(t)
    lowered = {k.lower(): v for k, v in all_tags.items()}
    for field, keys in FIELD_KEYS.items():
        for k in keys:
            if k in lowered:
                found[field] = lowered[k]
                break
    known = manufacturer != "Unknown"
    return {"manufacturer": manufacturer, "confidence": "low" if known else None,
            "identification_method": "metadata_keyword_match" if known else "insufficient_evidence",
            "confidence_basis": basis, **found}
