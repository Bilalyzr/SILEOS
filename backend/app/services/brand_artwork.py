"""Code-rendered brand artwork for crawlers and public course shares."""
from functools import lru_cache
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


@lru_cache(maxsize=64)
def render_banner(
    title="Your next discovery starts here.",
    description="A little curiosity. A world of possibility.",
):
    image = Image.new("RGB", (1200, 630))
    draw = ImageDraw.Draw(image)
    for x in range(1200):
        t = x / 1199
        draw.line([(x, 0), (x, 630)], fill=(255, int(248 - 61 * t), int(237 - 112 * t)))
    draw.rounded_rectangle((25, 25, 1175, 605), radius=34, outline="#fff9ed", width=2)
    for r in (145, 185, 225):
        draw.ellipse((1030 - r, 280 - r, 1030 + r, 280 + r), outline="#e6ae7a", width=2)
    draw.rounded_rectangle(
        (940, 195, 1090, 370), radius=28, fill="#ffe9ce", outline="#fff7e9", width=3
    )
    draw.line(
        [
            (968, 240),
            (996, 240),
            (1015, 251),
            (1034, 240),
            (1063, 240),
            (1063, 318),
            (1034, 318),
            (1015, 329),
            (996, 318),
            (968, 318),
            (968, 240),
        ],
        fill="#ab571f",
        width=4,
    )
    draw.line([(1015, 251), (1015, 329)], fill="#ab571f", width=4)
    font_path = Path(__file__).resolve().parents[1] / "assets" / "PlusJakartaSans.ttf"

    def font(size):
        use_tamil = any("\u0b80" <= ch <= "\u0bff" for ch in title + description)
        chosen = (
            font_path.parent / "fonts" / "NotoSansTamil.ttf"
            if use_tamil
            else (
                font_path.parent / "fonts" / "Inter-Bold.ttf"
                if size >= 50
                else font_path
            )
        )
        try:
            return ImageFont.truetype(str(chosen), size)
        except OSError:
            return ImageFont.load_default(size=size)

    draw.text(
        (65, 60), "SASHAINFINITY / KEEP DISCOVERING", font=font(21), fill="#884219"
    )

    def wrapped(text, max_width, size, max_lines):
        lines = []
        line = ""
        for word in " ".join(text.split())[:600].split(" "):
            candidate = (line + " " + word).strip()
            if draw.textlength(candidate, font=font(size)) <= max_width:
                line = candidate
                continue
            if line:
                lines.append(line)
            line = word
            while draw.textlength(line, font=font(size)) > max_width:
                cut = len(line) - 1
                while (
                    cut > 1 and draw.textlength(line[:cut], font=font(size)) > max_width
                ):
                    cut -= 1
                lines.append(line[:cut])
                line = line[cut:]
        if line:
            lines.append(line)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            while draw.textlength(lines[-1] + "…", font=font(size)) > max_width:
                lines[-1] = lines[-1][:-1]
            lines[-1] += "…"
        return lines

    for n, line in enumerate(wrapped(title, 765, 55, 3)):
        draw.text((65, 145 + n * 73), line, font=font(55), fill="#512d14")
    for n, line in enumerate(wrapped(description, 780, 25, 2)):
        draw.text((65, 416 + n * 37), line, font=font(25), fill="#75503a")
    draw.line([(65, 537), (1135, 537)], fill="#dca371", width=1)
    draw.text(
        (65, 565),
        "Learn with purpose. Share your progress.",
        font=font(21),
        fill="#884219",
    )
    out = BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()
