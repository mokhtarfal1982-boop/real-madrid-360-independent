"""Generate the app icons and the social preview image for Real Madrid 360."""
import sys
from PIL import Image, ImageDraw, ImageFont

FONTS = sys.argv[1]
OUT = sys.argv[2]
NIGHT = (7, 16, 31)
STAND = (13, 26, 48)
WHITE = (244, 246, 250)
STEEL = (143, 163, 191)
STEEL2 = (185, 198, 216)
GOLD = (216, 178, 94)

barlow = lambda s: ImageFont.truetype(f"{FONTS}/BarlowCondensed-700.ttf", s)
plex = lambda s, w=700: ImageFont.truetype(f"{FONTS}/PlexArabic-arabic-{w}.ttf", s, layout_engine=ImageFont.Layout.RAQM)


def mark(draw, cx, cy, r, text_size):
    # gold ring, navy gap, white disc, navy "360"
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GOLD)
    g = max(2, round(r * 0.07))
    draw.ellipse((cx - r + g, cy - r + g, cx + r - g, cy + r - g), fill=NIGHT)
    g2 = g + max(2, round(r * 0.06))
    draw.ellipse((cx - r + g2, cy - r + g2, cx + r - g2, cy + r - g2), fill=WHITE)
    f = barlow(text_size)
    draw.text((cx, cy + text_size * 0.04), "360", font=f, fill=NIGHT, anchor="mm")


def icon(size, path, padding=0.14):
    s = size * 4
    img = Image.new("RGB", (s, s), NIGHT)
    d = ImageDraw.Draw(img)
    r = int(s * (0.5 - padding))
    mark(d, s // 2, s // 2, r, int(r * 0.92))
    img = img.resize((size, size), Image.LANCZOS)
    img = img.quantize(colors=20, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    img.save(path, optimize=True)


def og(path, W=600, H=315):
    # 600x315 keeps the file under the connector's upload limit
    s = W / 1200
    img = Image.new("RGB", (W, H), NIGHT)
    d = ImageDraw.Draw(img)
    for x in range(0, W, max(8, int(26 * s))):
        d.line([(x, 0), (x, H)], fill=(18, 30, 52), width=max(1, int(2 * s)))
    d.rectangle((0, H - max(4, int(10 * s)), W, H), fill=GOLD)
    mark(d, int(250 * s), int(300 * s), int(150 * s), int(140 * s))
    right = W - int(90 * s)
    d.text((right, int(196 * s)), "ريال مدريد", font=plex(int(100 * s), 700), fill=WHITE, anchor="rs", direction="rtl", language="ar")
    d.text((right, int(372 * s)), "360", font=barlow(int(150 * s)), fill=WHITE, anchor="rs")
    d.text((right, int(452 * s)), "المباراة القادمة والنتائج والترتيب", font=plex(int(36 * s), 500), fill=STEEL2, anchor="rs", direction="rtl", language="ar")
    d.text((right, int(506 * s)), "والغيابات وآخر الأخبار بمصادرها", font=plex(int(36 * s), 500), fill=STEEL2, anchor="rs", direction="rtl", language="ar")
    d.text((right, int(574 * s)), "بتوقيت السعودية", font=plex(int(30 * s), 600), fill=GOLD, anchor="rs", direction="rtl", language="ar")
    img = img.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    img.save(path, optimize=True)


icon(192, f"{OUT}/icon-192.png")
icon(180, f"{OUT}/apple-touch-icon.png", padding=0.10)
og(f"{OUT}/og.png")
print("done")
