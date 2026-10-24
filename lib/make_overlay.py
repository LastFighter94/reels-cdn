
"""Usage: make_overlay.py "<title with *accent* words>" "<cta text>" out_dir [frame.jpg]
If frame.jpg (a frame of the source video) is given, the accent colour and plate
opacity are picked to harmonise with that video; the choice is printed."""
import sys, re, os, math, colorsys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_X = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
WHITE = (255, 255, 255, 255)
PLATE = (12, 12, 14, 205)

title, cta, out = sys.argv[1], sys.argv[2], sys.argv[3]
frame = sys.argv[4] if len(sys.argv) > 4 else None

# ---- harmonious (analogous) accent ----
PALETTE = {  # manual override names -> rgb
    "yellow": (255, 214, 74), "gold": (247, 200, 92), "orange": (255, 159, 67), "coral": (255, 120, 110),
    "pink": (255, 140, 200), "mint": (110, 230, 180), "cyan": (110, 205, 255), "lime": (200, 240, 90),
    "lavender": (190, 165, 255), "sand": (240, 210, 160),
}
def hsl_rgb(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return (round(r * 255), round(g * 255), round(b * 255))
def name_of(h):
    for lim, n in [(15, "coral"), (40, "orange"), (65, "gold"), (95, "lime"), (165, "green"),
                   (200, "teal"), (250, "sky blue"), (290, "lavender"), (335, "pink"), (361, "coral")]:
        if h < lim: return n
accent_rgb, accent_name = PALETTE["gold"], "gold"
if frame:
    im = Image.open(frame).convert("RGB").resize((90, 160))
    raw = im.tobytes(); px = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
    hist = [0.0] * 36; top_lum = 0.0; colour_w = 0.0
    for idx, (r, g, b) in enumerate(px):
        h, l, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if idx < 90 * 60: top_lum += l          # title area (top ~third)
        if sat > 0.2 and 0.12 < l < 0.9:
            w = sat * (1 - abs(l - 0.5))
            hist[int(h * 36) % 36] += w; colour_w += w
    top_lum /= 90 * 60
    PLATE = (12, 12, 14, 225 if top_lum > 0.55 else 200)
    if colour_w / len(px) > 0.06:            # enough colour in the shot, else keep gold
        sm = [sum(hist[(k + d) % 36] for d in (-2, -1, 0, 1, 2)) for k in range(36)]
        peak = max(range(36), key=lambda k: sm[k])
        xs = ys = 0.0
        for d in range(-3, 4):
            k = (peak + d) % 36; ang = math.radians(k * 10 + 5)
            xs += hist[k] * math.cos(ang); ys += hist[k] * math.sin(ang)
        hue = math.degrees(math.atan2(ys, xs)) % 360
        if 10 <= hue < 55:          # skin, wood, warm lamps -> warm gold family
            hue = 44
        light = 0.74 if 190 <= hue < 300 else 0.68   # blues/purples need more light to read
        sat_a = 0.85 if 30 <= hue < 70 else 0.7      # gold may be rich; other hues softer
        accent_rgb, accent_name = hsl_rgb(hue, sat_a, light), name_of(hue)
if os.environ.get("ACCENT"):
    accent_name = os.environ["ACCENT"]; accent_rgb = PALETTE[accent_name]
ACCENT = accent_rgb + (255,)
print(f"accent={accent_name} rgb={accent_rgb}")

tokens = []
for part in re.split(r"(\*[^*]+\*)", title):
    if not part:
        continue
    acc = part.startswith("*")
    for j, w in enumerate([w for w in part.strip("*").split(" ") if w]):
        if tokens and not acc and j == 0 and not part[0].isspace() and w[0] in ",.:;!?)…»":
            tokens.append(("\x00" + w, acc))
        else:
            tokens.append((w, acc))

size = 62
font = ImageFont.truetype(FONT, size)
fontx = ImageFont.truetype(FONT_X, size)
maxw = 860
space = font.getlength(" ")

def wlen(t):
    return (fontx if t[1] else font).getlength(t[0].lstrip("\x00"))

def wrap_seg(seg, limit):
    lines, cur, cw = [], [], 0
    for t in seg:
        l = wlen(t)
        if t[0].startswith("\x00") and cur:
            cur.append(t); cw += l; continue
        add = l if not cur else cw + space + l
        if cur and add > limit:
            lines.append(cur); cur, cw = [t], l
        else:
            cur.append(t); cw = add
    lines.append(cur)
    return lines

segs, cur = [], []
for t in tokens:
    if t[0].startswith("(") and cur:
        segs.append(cur); cur = []
    cur.append(t)
segs.append(cur)
lines = []
for seg in segs:
    n = len(wrap_seg(seg, maxw)); lim = maxw
    while lim > 300 and len(wrap_seg(seg, lim - 10)) == n:
        lim -= 10
    lines += wrap_seg(seg, lim)

def line_w(line):
    return sum(wlen(t) for t in line) + space * sum(1 for t in line[1:] if not t[0].startswith("\x00"))

plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
pd = ImageDraw.Draw(plate)
lh = int(size * 1.22)
padx, pady = 30, 14
y0 = 270   # title top
if os.environ.get('TITLE_BOTTOM'):
    y0 = int(os.environ['TITLE_BOTTOM']) - len(lines) * lh
asc, desc = font.getmetrics()
for i, line in enumerate(lines):
    lw = line_w(line)
    x = (W - lw) / 2
    y = y0 + i * lh
    pd.rounded_rectangle([x - padx, y - pady, x + lw + padx, y + lh + pady - 6], radius=26, fill=PLATE)
shadow = plate.copy().filter(ImageFilter.GaussianBlur(14))
sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sh.putalpha(shadow.getchannel("A").point(lambda a: int(a * 0.5)))
img = Image.alpha_composite(sh, plate)
d = ImageDraw.Draw(img)
for i, line in enumerate(lines):
    lw = line_w(line)
    x = (W - lw) / 2
    y = y0 + i * lh + (lh - (asc + desc)) / 2 - 4
    for t in line:
        f = fontx if t[1] else font
        w = t[0]
        if w.startswith("\x00"):
            w = w[1:]; x -= space
        d.text((x, y), w.replace("\xa0", " "), font=f, fill=ACCENT if t[1] else WHITE)
        x += f.getlength(w) + space
img.save(f"{out}/title.png")

cf = ImageFont.truetype(FONT, 44)
tile, gap, n_ar = 56, 10, 3
tw = cf.getlength(cta) if cta else 0
inner = tw + (24 if cta else 0) + n_ar * tile + (n_ar - 1) * gap
bw, bh = int(inner + 56), 92
S = 3
btn = Image.new("RGBA", (bw * S + 40 * S, bh * S + 40 * S), (0, 0, 0, 0))
ox, oy = 20 * S, 20 * S
shl = Image.new("RGBA", btn.size, (0, 0, 0, 0))
ImageDraw.Draw(shl).rounded_rectangle([ox, oy + 6 * S, ox + bw * S, oy + bh * S + 6 * S], radius=bh * S // 2, fill=(0, 0, 0, 120))
btn = Image.alpha_composite(btn, shl.filter(ImageFilter.GaussianBlur(10 * S)))
bd = ImageDraw.Draw(btn)
bd.rounded_rectangle([ox, oy, ox + bw * S, oy + bh * S], radius=bh * S // 2, fill=(255, 255, 255, 235))
x = ox + 28 * S
if cta:
    cfs = ImageFont.truetype(FONT, 44 * S)
    a, dsc = cfs.getmetrics()
    bd.text((x, oy + (bh * S - (a + dsc)) / 2 - 2 * S), cta, font=cfs, fill=(20, 20, 22, 255))
    x += (tw + 24) * S
for k in range(n_ar):
    tx, ty = x, oy + (bh - tile) / 2 * S
    bd.rounded_rectangle([tx, ty, tx + tile * S, ty + tile * S], radius=14 * S, fill=(46, 120, 255, 255))
    cx, cy, u = tx + tile * S / 2, ty + tile * S / 2, S
    bd.rectangle([cx - 5 * u, cy - 17 * u, cx + 5 * u, cy + 3 * u], fill=WHITE)
    bd.polygon([(cx - 16 * u, cy), (cx + 16 * u, cy), (cx, cy + 18 * u)], fill=WHITE)
    x += (tile + gap) * S
btn = btn.resize((btn.width // S, btn.height // S), Image.LANCZOS)
btn.save(f"{out}/cta.png")
print(len(lines), "lines; cta", btn.size)
