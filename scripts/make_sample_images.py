"""Generate SYNTHETIC test images (Pillow only) for exercising the upload pipeline.

These are crude drawings stamped "SYNTHETIC TEST IMAGE". They are NOT real site or crack photos.
For the demo video use real photos you own, or openly licensed photos (check the license).

Usage: python scripts/make_sample_images.py
"""
import os
import random

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_data", "images")


def stamp(d, w, h):
    d.rectangle([0, h - 26, w, h], fill=(255, 255, 255))
    d.text((8, h - 20), "SYNTHETIC TEST IMAGE - not a real photograph", fill=(180, 0, 0))


def crack_image():
    random.seed(7)
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (178, 172, 164))
    px = img.load()
    for _ in range(60000):  # plaster-like speckle
        x, y = random.randrange(w), random.randrange(h)
        v = random.randint(-14, 14)
        px[x, y] = tuple(max(0, min(255, c + v)) for c in px[x, y])
    d = ImageDraw.Draw(img)
    x, y = 180, 60
    pts = [(x, y)]
    while y < 480:  # diagonal jagged crack
        x += random.randint(6, 22)
        y += random.randint(14, 34)
        pts.append((x + random.randint(-8, 8), y))
    d.line(pts, fill=(40, 36, 34), width=3)
    d.line([(px_ + 1, py_ + 1) for px_, py_ in pts], fill=(90, 84, 80), width=1)
    d.rectangle([60, 500, 460, 530], fill=(250, 230, 120), outline=(0, 0, 0))  # ruler for scale (1 tick = 1 cm)
    for i in range(0, 41):
        d.line([(60 + i * 10, 500), (60 + i * 10, 512 if i % 5 else 520)], fill=(0, 0, 0))
    d.text((470, 508), "ruler: 40 cm", fill=(0, 0, 0))
    stamp(d, w, h)
    img.save(os.path.join(OUT, "synthetic_crack_wall.png"), optimize=True)


def site_image():
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (170, 210, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 420, w, h], fill=(150, 120, 90))
    for i in range(4):  # concrete frame
        d.rectangle([120 + i * 160, 160, 140 + i * 160, 420], fill=(160, 160, 160))
    for y in (160, 290):
        d.rectangle([120, y, 600, y + 18], fill=(140, 140, 140))

    def worker(x, y, hat, vest):
        d.ellipse([x - 10, y - 50, x + 10, y - 30], fill=(235, 195, 160))
        if hat:
            d.pieslice([x - 12, y - 56, x + 12, y - 34], 180, 360, fill=(250, 210, 0))
        d.rectangle([x - 12, y - 30, x + 12, y + 15], fill=(255, 120, 0) if vest else (70, 90, 120))
        d.line([x - 6, y + 15, x - 6, y + 50], fill=(40, 40, 40), width=5)
        d.line([x + 6, y + 15, x + 6, y + 50], fill=(40, 40, 40), width=5)

    worker(250, 380, True, True)
    worker(420, 380, False, False)
    worker(540, 250, True, False)
    stamp(d, w, h)
    img.save(os.path.join(OUT, "synthetic_site_workers.png"), optimize=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    crack_image()
    site_image()
    print("wrote", sorted(os.listdir(OUT)))
