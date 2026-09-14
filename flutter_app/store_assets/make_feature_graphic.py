"""Builds the Play Store feature graphic (1024x500) from the real app assets.

Uses the shipped brand mark (assets/icon/app_icon_foreground.png), real AR model
renders as background texture, and the exact hex values from lib/config/theme.dart,
so the banner matches the app instead of approximating it.

Run from flutter_app/:  python store_assets/make_feature_graphic.py
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
import glob
import os

W, H = 1024, 500

# --- brand palette (lib/config/theme.dart) ---
BG_DARK = (11, 17, 24)        # #0B1118 backgroundDark
SURFACE = (22, 30, 42)        # #161E2A surfaceDark
ORANGE = (249, 115, 22)       # #F97316 primary
ORANGE_DK = (234, 88, 12)     # #EA580C primaryDark
TEXT = (248, 250, 252)        # #F8FAFC textDark
MUTED = (148, 163, 184)       # #94A3B8 mutedDark
TEAL = (45, 212, 191)         # logo teal accent

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'play_feature_graphic_1024x500.png')
MARK = os.path.join(ROOT, 'assets', 'icon', 'app_icon_foreground.png')
AR_DIR = os.path.join(ROOT, 'assets', 'models', 'ar_thumbnails')


def radial_bg():
    """#0B1118 base lifting toward #161E2A away from the logo."""
    bg = Image.new('RGB', (W, H), SURFACE)
    d = ImageDraw.Draw(bg)
    cx, cy = int(W * 0.26), H // 2
    max_r = int((W ** 2 + H ** 2) ** 0.5)
    for i in range(70, 0, -1):
        t = i / 70.0
        r = int(max_r * t * 0.8)
        col = tuple(int(BG_DARK[c] + (SURFACE[c] - BG_DARK[c]) * t) for c in range(3))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return bg


def ar_texture(img):
    """Scatter real AR model renders across the right side at low opacity.

    These are the actual 3D models the app ships (Hilbert curve, lattice,
    horned sphere...), so the texture is product-truthful rather than decorative
    filler.
    """
    files = sorted(glob.glob(os.path.join(AR_DIR, '*.webp')))
    if not files:
        return img
    # (file index, centre x, centre y, size, opacity) — kept faint and pushed to
    # the outer right so the models read as depth, never as competing subjects
    spots = [
        (1, 965, 350, 250, 0.09),
        (0, 905, 110, 165, 0.07),
        (2, 640, 425, 140, 0.06),
        (4, 800, 250, 120, 0.05),
    ]
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for idx, cx, cy, size, alpha in spots:
        if idx >= len(files):
            continue
        m = Image.open(files[idx]).convert('RGBA')
        m = m.crop(m.getbbox()) if m.getbbox() else m
        m = m.resize((size, size), Image.LANCZOS)
        # desaturate + dim so the models read as texture, never as subjects
        rgb = ImageEnhance.Color(m.convert('RGB')).enhance(0.35)
        rgb = ImageEnhance.Brightness(rgb).enhance(0.75)
        tile = rgb.convert('RGBA')
        a = m.split()[3].point(lambda p: int(p * alpha))
        tile.putalpha(a)
        layer.alpha_composite(tile, (cx - size // 2, cy - size // 2))
    layer = layer.filter(ImageFilter.GaussianBlur(0.6))
    return Image.alpha_composite(img.convert('RGBA'), layer)


def vignette(img):
    """Darken the outer edges so the centre lockup pops."""
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    for i in range(40):
        t = i / 40.0
        a = int(120 * (t ** 2))
        d.rectangle([i * 2, i, W - i * 2, H - i], outline=a)
    dark = Image.new('RGBA', (W, H), BG_DARK + (255,))
    dark.putalpha(mask.filter(ImageFilter.GaussianBlur(30)))
    return Image.alpha_composite(img.convert('RGBA'), dark)


def load_font(names, size):
    for n in names:
        for path in (
            f'C:/Windows/Fonts/{n}',
            os.path.expanduser(f'~/AppData/Local/Microsoft/Windows/Fonts/{n}'),
        ):
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
    return ImageFont.load_default()


def main():
    img = radial_bg()
    img = ar_texture(img)

    # --- brand mark: real app icon foreground, double glow + crisp copy ---
    mark = Image.open(MARK).convert('RGBA')
    mark = mark.crop(mark.getbbox())
    target_h = 268
    scale = target_h / mark.height
    mark = mark.resize((int(mark.width * scale), target_h), Image.LANCZOS)

    mx, my = 78, (H - mark.height) // 2

    # wide soft bloom + tighter hot glow
    for blur, strength in ((60, 0.55), (22, 0.85)):
        glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        tint = Image.new('RGBA', mark.size, ORANGE + (255,))
        tint.putalpha(mark.split()[3].point(lambda p: int(p * strength)))
        glow.paste(tint, (mx, my), tint)
        glow = glow.filter(ImageFilter.GaussianBlur(blur))
        img = Image.alpha_composite(img.convert('RGBA'), glow)

    img.paste(mark, (mx, my), mark)

    # --- type ---
    # The mark already carries "SASHA" and the "Democratize Education" script,
    # so the type block only adds the product name and what the app actually is.
    d = ImageDraw.Draw(img)
    tx = mx + mark.width + 52
    RIGHT_MARGIN = 56
    avail = W - tx - RIGHT_MARGIN

    def head_font(sz):
        return load_font(['PlusJakartaSans-Bold.ttf', 'Inter-Bold.ttf',
                          'segoeuib.ttf', 'arialbd.ttf'], sz)

    sub = load_font(['Inter-Regular.ttf', 'segoeui.ttf', 'arial.ttf'], 22)
    subm = load_font(['Inter-Medium.ttf', 'Inter-Regular.ttf',
                      'segoeui.ttf', 'arial.ttf'], 20)

    title, track = 'SASHAINFINITY', 2
    size = 48
    head = head_font(size)
    while sum(d.textlength(c, font=head) + track
              for c in title) - track > avail and size > 24:
        size -= 2
        head = head_font(size)

    ty = H // 2 - 78
    x = tx
    for ch in title:
        d.text((x, ty), ch, font=head, fill=TEXT)
        x += d.textlength(ch, font=head) + track

    # thin orange rule under the wordmark
    rule_y = ty + size + 14
    d.rectangle([tx, rule_y, tx + 58, rule_y + 3], fill=ORANGE)

    # "LMS" chip
    chip_y = rule_y + 18
    cw = d.textlength('LMS', font=subm)
    d.rounded_rectangle([tx, chip_y, tx + cw + 22, chip_y + 32], radius=16,
                        fill=ORANGE_DK)
    d.text((tx + 11, chip_y + 5), 'LMS', font=subm, fill=TEXT)

    # value line
    tag_y = chip_y + 50
    lead, tail = 'Courses, AR models', ' & an AI tutor'
    d.text((tx, tag_y), lead, font=sub, fill=ORANGE)
    d.text((tx + d.textlength(lead, font=sub), tag_y), tail, font=sub, fill=MUTED)

    # three proof points, teal bullets
    feats = ['100+ interactive 3D models', 'Tamil & English', 'Certificates']
    fy = tag_y + 40
    for f in feats:
        d.ellipse([tx + 1, fy + 7, tx + 8, fy + 14], fill=TEAL)
        d.text((tx + 18, fy), f, font=subm, fill=MUTED)
        fy += 27

    img = vignette(img)

    img.convert('RGB').save(OUT, 'PNG', optimize=True)
    out = Image.open(OUT)
    kb = os.path.getsize(OUT) / 1024
    print(f'{OUT}\n{out.size[0]}x{out.size[1]} {out.mode} {kb:.0f}KB')
    print('spec 1024x500:', out.size == (1024, 500))


if __name__ == '__main__':
    main()
