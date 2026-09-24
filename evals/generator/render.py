"""Render synthetic receipt images with Pillow.

Every image carries a repeated diagonal watermark "SYNTHETIC SAMPLE - NOT A VALID
INVOICE" (ADR G3) and mild, seeded scan noise (rotation, blur, JPEG compression).
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WATERMARK = "SYNTHETIC SAMPLE - NOT A VALID INVOICE"
WIDTH = 640
MARGIN = 28
LINE_H = 22

_FONT_CANDIDATES = {
    "regular": ["DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                "C:/Windows/Fonts/consola.ttf", "Menlo.ttc"],
    "bold": ["DejaVuSansMono-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
             "C:/Windows/Fonts/consolab.ttf", "Menlo.ttc"],
}
_font_cache: dict = {}


def _font(kind: str = "regular", size: int = 15):
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    font = None
    for cand in _FONT_CANDIDATES[kind]:
        try:
            font = ImageFont.truetype(cand, size)
            break
        except OSError:
            continue
    if font is None:  # Pillow >= 10.1 ships a scalable default font
        font = ImageFont.load_default(size=size)
    _font_cache[key] = font
    return font


def money(x: float) -> str:
    return f"{x:,.2f}"


def _lines_for(spec: dict) -> list[tuple[str, str]]:
    """Return (style, text) lines. style in {title, bold, text, rule, small}."""
    out: list[tuple[str, str]] = []
    out.append(("title", spec["vendor"]))
    out.append(("small", f"{spec.get('address', '')}, {spec['vendor_city']}".strip(", ")))
    if spec.get("vendor_gstin"):
        out.append(("small", f"GSTIN: {spec['vendor_gstin']}"))
    out.append(("rule", ""))
    out.append(("bold", spec.get("title", "RECEIPT")))
    no_label = spec.get("invoice_label", "Invoice No")
    dt = spec["date"].strftime("%d-%m-%Y")
    if spec.get("time"):
        dt += f"  {spec['time']}"
    out.append(("text", f"{no_label}: {spec['invoice_no']}"))
    out.append(("text", f"Date: {dt}"))
    for line in spec.get("bill_to") or []:
        out.append(("text", line))
    for line in spec.get("meta_lines", []):
        out.append(("text", line))
    out.append(("rule", ""))
    if spec.get("itemised", True):
        out.append(("bold", f"{'Item':<26}{'Qty':>4}{'Rate':>10}{'Amount':>12}"))
        for desc, qty, rate, amt in spec["items"]:
            desc = desc[:26]
            out.append(("text", f"{desc:<26}{qty:>4}{money(rate):>10}{money(amt):>12}"))
        out.append(("rule", ""))
        out.append(("text", f"{'Subtotal':<40}{money(spec['subtotal']):>12}"))
        for label, amt in spec.get("taxes", []):
            out.append(("text", f"{label:<40}{money(amt):>12}"))
    else:
        out.append(("text", f"{spec.get('lump_label', 'Food & Beverages'):<40}{money(spec['total']):>12}"))
    out.append(("rule", ""))
    out.append(("bold", f"{'TOTAL (Rs.)':<40}{money(spec['total']):>12}"))
    out.append(("text", f"Paid by: {spec['payment']}"))
    for line in spec.get("footer", []):
        out.append(("small", line))
    out.append(("small", "Thank you. Visit again."))
    return out


_WM_LAYER = None


def _draw_watermark(img: Image.Image) -> Image.Image:
    """Composite a cached, pre-rotated watermark layer (built once for speed)."""
    global _WM_LAYER
    if _WM_LAYER is None:
        big = (2400, 2400)
        layer = Image.new("RGBA", big, (255, 255, 255, 0))
        d = ImageDraw.Draw(layer)
        f = _font("bold", 22)
        for y in range(0, big[1], 140):
            d.text((0, y), (WATERMARK + "   ") * 6, font=f, fill=(200, 30, 30, 70))
        layer = layer.rotate(28, resample=Image.BICUBIC)
        cx, cy = big[0] // 2, big[1] // 2
        _WM_LAYER = layer.crop((cx - WIDTH // 2, cy - 800, cx + WIDTH // 2, cy + 800))
    wm = _WM_LAYER.crop((0, 0, img.width, img.height))
    return Image.alpha_composite(img.convert("RGBA"), wm)


def _wrap(text: str, width: int = 58) -> list[str]:
    out, cur = [], ""
    for word in text.split(" "):
        if len(cur) + len(word) + 1 > width and cur:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    out.append(cur)
    return out


def render_receipt(spec: dict, path: Path, rng: random.Random) -> None:
    lines = []
    for style, text in _lines_for(spec):
        if style in ("text", "small") and len(text) > 58:
            lines += [(style, t) for t in _wrap(text)]
        else:
            lines.append((style, text))
    height = MARGIN * 2 + LINE_H * (len(lines) + 1)
    img = Image.new("RGB", (WIDTH, height), (252, 251, 247))
    d = ImageDraw.Draw(img)
    y = MARGIN
    total_box = None
    for style, text in lines:
        if style == "rule":
            d.line((MARGIN, y + LINE_H // 2, WIDTH - MARGIN, y + LINE_H // 2), fill=(90, 90, 90), width=1)
        elif style == "title":
            d.text((MARGIN, y - 2), text, font=_font("bold", 20), fill=(20, 20, 20))
        elif style == "bold":
            d.text((MARGIN, y), text, font=_font("bold", 15), fill=(20, 20, 20))
            if text.startswith("TOTAL"):
                total_box = y
        elif style == "small":
            d.text((MARGIN, y + 2), text, font=_font("regular", 13), fill=(60, 60, 60))
        else:
            d.text((MARGIN, y), text, font=_font("regular", 15), fill=(25, 25, 25))
        y += LINE_H

    # Anomaly: visibly tampered total (patched box, different font size and offset).
    if spec.get("tamper_total") is not None and total_box is not None:
        f = _font("bold", 15)
        x_end = MARGIN + f.getlength("M" * 52)
        x0 = MARGIN + f.getlength("M" * 39)
        d.rectangle((x0, total_box - 1, x_end + 4, total_box + LINE_H - 3), fill=(255, 255, 255))
        txt = money(spec["tamper_total"])
        f2 = _font("regular", 17)
        d.text((x_end - f2.getlength(txt) + 6, total_box + 1), txt, font=f2, fill=(10, 10, 10))

    img = _draw_watermark(img).convert("RGB")
    # Scan noise.
    img = img.rotate(rng.uniform(-1.8, 1.8), resample=Image.BICUBIC, expand=True, fillcolor=(235, 235, 232))
    if rng.random() < 0.5:
        img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.2, 0.8)))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=rng.randint(62, 88))
