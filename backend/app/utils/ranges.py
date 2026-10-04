"""HTTP Range header parsing (single range) for video seeking. No third-party imports."""
from typing import Optional, Tuple

from app.utils.errors import AppError


def parse_range(header: Optional[str], size: int) -> Optional[Tuple[int, int]]:
    """Return inclusive (start, end) or None if no Range header. Raises 416 if unsatisfiable."""
    if not header:
        return None
    if not header.startswith("bytes=") or "," in header:
        return None  # ignore unsupported/multi-range -> serve full file
    spec = header[6:].strip()
    try:
        a, b = spec.split("-", 1)
        if a == "":                      # suffix range: last N bytes
            n = int(b)
            if n <= 0:
                raise ValueError
            start, end = max(0, size - n), size - 1
        else:
            start = int(a)
            end = int(b) if b else size - 1
    except ValueError:
        return None
    end = min(end, size - 1)
    if start < 0 or start >= size or start > end:
        raise AppError(416, "RANGE_NOT_SATISFIABLE", "Requested range is not satisfiable.")
    return start, end
