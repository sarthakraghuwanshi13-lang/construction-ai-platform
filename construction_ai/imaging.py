"""Image validation and downscaling before sending to the vision model."""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageOps

from .config import IMAGE_MAX_SIDE, MAX_IMAGES, MAX_UPLOAD_MB


class ImageError(ValueError):
    """The uploaded file is missing, too large or not a readable image."""


@dataclass
class PreparedImage:
    name: str
    data_b64: str
    width: int
    height: int
    media_type: str = "image/jpeg"

    def to_block(self) -> Dict[str, Any]:
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": self.media_type, "data": self.data_b64},
        }

    def to_bytes(self) -> bytes:
        return base64.b64decode(self.data_b64)


def prepare_image(data: bytes, name: str = "image") -> PreparedImage:
    """Validate, orient, flatten to RGB and downscale to a JPEG for the API."""
    if not data:
        raise ImageError("%s: file is empty." % name)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ImageError("%s: larger than %d MB." % (name, MAX_UPLOAD_MB))
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise ImageError("%s: not a readable image (%s)." % (name, type(exc).__name__)) from exc
    try:
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        if min(img.size) < 32:
            raise ImageError("%s: image is too small (%dx%d)." % (name, img.size[0], img.size[1]))
        img.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
    except ImageError:
        raise
    except Exception as exc:
        raise ImageError("%s: could not be processed (%s)." % (name, type(exc).__name__)) from exc
    return PreparedImage(
        name=name,
        data_b64=base64.b64encode(buf.getvalue()).decode("ascii"),
        width=img.size[0],
        height=img.size[1],
    )


def prepare_many(files: Sequence[Tuple[str, bytes]]) -> Tuple[List[PreparedImage], List[str]]:
    """Prepare up to MAX_IMAGES images; return (images, human-readable errors)."""
    images: List[PreparedImage] = []
    errors: List[str] = []
    for i, (name, data) in enumerate(files):
        if i >= MAX_IMAGES:
            errors.append("Only the first %d images are used; ignored: %s" % (MAX_IMAGES, name))
            continue
        try:
            images.append(prepare_image(data, name))
        except ImageError as exc:
            errors.append(str(exc))
    return images, errors
