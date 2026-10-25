import base64
import io
import unittest

from PIL import Image

from construction_ai.imaging import ImageError, prepare_image, prepare_many


def png_bytes(size=(100, 80), mode="RGB", color=(200, 10, 10)):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


class ImagingTests(unittest.TestCase):
    def test_valid_png_becomes_jpeg(self):
        p = prepare_image(png_bytes(), "a.png")
        raw = base64.b64decode(p.data_b64)
        self.assertEqual(Image.open(io.BytesIO(raw)).format, "JPEG")
        self.assertEqual(p.media_type, "image/jpeg")
        self.assertEqual(p.to_block()["source"]["type"], "base64")

    def test_large_image_downscaled(self):
        p = prepare_image(png_bytes((4000, 3000)), "big.png")
        self.assertLessEqual(max(p.width, p.height), 1568)

    def test_rgba_flattened(self):
        p = prepare_image(png_bytes((64, 64), "RGBA", (0, 0, 0, 0)), "t.png")
        self.assertEqual(p.width, 64)

    def test_empty_garbage_tiny_rejected(self):
        for bad in (b"", b"not an image at all"):
            with self.assertRaises(ImageError):
                prepare_image(bad, "bad")
        with self.assertRaises(ImageError):
            prepare_image(png_bytes((10, 10)), "tiny.png")

    def test_oversize_rejected(self):
        with self.assertRaises(ImageError):
            prepare_image(b"0" * (9 * 1024 * 1024), "huge.bin")

    def test_prepare_many_collects_errors_and_caps(self):
        files = [("ok%d.png" % i, png_bytes()) for i in range(5)] + [("bad.png", b"zzz")]
        imgs, errs = prepare_many(files)
        self.assertEqual(len(imgs), 4)
        self.assertTrue(any("Only the first 4" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
