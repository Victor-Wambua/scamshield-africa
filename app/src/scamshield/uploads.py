"""Evidence upload handling: magic-byte validation, size limits, EXIF stripping via re-encode,
random storage names outside the web root. Files are served only through authorised endpoints."""

from __future__ import annotations

import hashlib
import io
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


class UploadRejected(ValueError):
    """Raised with a user-safe message when an upload is refused."""


@dataclass
class StoredFile:
    storage_name: str
    mime: str
    size: int
    sha256: str


_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)
_NAME_RE = re.compile(r"^[a-f0-9]{32}\.(png|jpg)$")


def sniff(data: bytes) -> str | None:
    for sig, mime in _SIGNATURES:
        if data.startswith(sig):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def process_image(data: bytes, max_bytes: int, max_pixels: int) -> tuple[bytes, str]:
    """Validate and re-encode. Returns (clean bytes, mime). Raises UploadRejected."""
    if not data:
        raise UploadRejected("The file is empty.")
    if len(data) > max_bytes:
        raise UploadRejected(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
    mime = sniff(data)
    if mime is None:
        raise UploadRejected("Only PNG, JPEG or WebP images are accepted.")
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with Image.open(io.BytesIO(data)) as probe:
            w, h = probe.size
            if w * h > max_pixels:
                raise UploadRejected("The image dimensions are too large.")
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)
            fmt_png = img.mode in ("RGBA", "LA", "P") or mime == "image/png"
            mode = img.mode if (fmt_png and img.mode in ("RGB", "RGBA", "L", "LA")) else ("RGBA" if fmt_png else "RGB")
            clean = Image.frombytes(mode, img.size, img.convert(mode).tobytes())  # fresh pixels: drops EXIF/ICC/text chunks
            out = io.BytesIO()
            if fmt_png:
                clean.save(out, format="PNG")
                return out.getvalue(), "image/png"
            clean.save(out, format="JPEG", quality=88)
            return out.getvalue(), "image/jpeg"
    except UploadRejected:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, SyntaxError) as exc:
        raise UploadRejected("The file is not a readable image.") from exc


def store_image(storage_dir: Path, data: bytes, max_bytes: int, max_pixels: int) -> StoredFile:
    clean, mime = process_image(data, max_bytes, max_pixels)
    ext = "png" if mime == "image/png" else "jpg"
    name = f"{secrets.token_hex(16)}.{ext}"
    shard = storage_dir / name[:2]
    shard.mkdir(parents=True, exist_ok=True)
    (shard / name).write_bytes(clean)
    return StoredFile(name, mime, len(clean), hashlib.sha256(clean).hexdigest())


def path_for(storage_dir: Path, name: str) -> Path | None:
    """Resolve a stored name safely (no traversal). None if the name is not a valid generated name."""
    if not _NAME_RE.match(name):
        return None
    p = (storage_dir / name[:2] / name).resolve()
    if not str(p).startswith(str(storage_dir.resolve())):
        return None
    return p if p.is_file() else None
