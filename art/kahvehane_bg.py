import math, random, sys
from PIL import Image, ImageDraw, ImageFilter, ImageChops

def wood(w, h, seed=3):
    random.seed(seed)
    img = Image.new("RGB", (w, h), (92, 52, 28))
    d = ImageDraw.Draw(img)
    plank = h // 5 if h > w else w // 7
    vertical = h > w
    n = (w if vertical else h)
    # planks run along the long axis
    planks = range(0, (w if vertical else h) + plank, plank)
    for i, p in enumerate(planks):
        base = [(98, 56, 30), (86, 48, 25), (104, 61, 33), (90, 52, 27)][i % 4]
        if vertical: d.rectangle([p, 0, p + plank, h], fill=base)
        else: d.rectangle([0, p, w, p + plank], fill=base)
        # grain
        for g in range(70):
            off = random.uniform(0, plank)
            amp = random.uniform(2, 14); freq = random.uniform(0.002, 0.008); ph = random.uniform(0, 6.28)
            shade = random.randint(-22, 14)
            col = tuple(max(0, min(255, c + shade)) for c in base)
            pts = []
            L = h if vertical else w
            for t in range(0, L + 20, 20):
                o = off + amp * math.sin(t * freq + ph)
                pts.append((p + o, t) if vertical else (t, p + o))
            d.line(pts, fill=col, width=random.choice([1, 1, 2, 3]))
        # seam
        if vertical: d.line([(p, 0), (p, h)], fill=(45, 24, 12), width=4)
        else: d.line([(0, p), (w, p)], fill=(45, 24, 12), width=4)
    return img.filter(ImageFilter.GaussianBlur(0.8))

def shadow(base, drawfn, offset=(18, 22), blur=18, alpha=150):
    m = Image.new("L", base.size, 0)
    drawfn(ImageDraw.Draw(m), 255)
    m = ImageChops.offset(m, *offset).filter(ImageFilter.GaussianBlur(blur))
    m = m.point(lambda v: v * alpha // 255)
    base.paste((15, 8, 4), (0, 0), m)

def tea(img, cx, cy, s):
    d = ImageDraw.Draw(img, "RGBA")
    R = 150 * s
    shadow(img, lambda dd, f: dd.ellipse([cx - R, cy - R, cx + R, cy + R], fill=f))
    d = ImageDraw.Draw(img, "RGBA")
    # saucer: white with red rim and pattern
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(246, 244, 238))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(176, 28, 36), width=int(12 * s))
    for k in range(24):
        a = k * math.pi / 12
        px, py = cx + math.cos(a) * R * 0.86, cy + math.sin(a) * R * 0.86
        r = 7 * s
        d.ellipse([px - r, py - r, px + r, py + r], fill=(176, 28, 36))
    d.ellipse([cx - R * .62, cy - R * .62, cx + R * .62, cy + R * .62], outline=(220, 214, 204), width=int(4 * s))
    # spoon
    a = -0.6; L = R * 1.15
    sx, sy = cx + math.cos(a) * R * 0.35, cy + math.sin(a) * R * 0.35
    ex, ey = cx + math.cos(a) * L, cy + math.sin(a) * L
    d.line([(sx, sy), (ex, ey)], fill=(190, 190, 196), width=int(9 * s))
    d.ellipse([ex - 10 * s, ey - 10 * s, ex + 10 * s, ey + 10 * s], fill=(205, 205, 210))
    # sugar cubes
    for (ox, oy) in [(-0.55, 0.45), (-0.33, 0.62)]:
        x, y = cx + ox * R, cy + oy * R; q = 22 * s
        d.rounded_rectangle([x - q, y - q, x + q, y + q], radius=4 * s, fill=(252, 252, 250), outline=(220, 220, 215))
    # tulip glass from top: outer rim, tea
    g = R * 0.55
    d.ellipse([cx - g, cy - g, cx + g, cy + g], fill=(255, 255, 255, 70), outline=(255, 255, 255, 200), width=int(5 * s))
    t = g * 0.86
    d.ellipse([cx - t, cy - t, cx + t, cy + t], fill=(150, 34, 12))
    t2 = t * 0.78
    d.ellipse([cx - t2, cy - t2, cx + t2, cy + t2], fill=(178, 52, 16))
    # reflection
    d.arc([cx - t * .8, cy - t * .8, cx + t * .8, cy + t * .8], 200, 260, fill=(255, 220, 180, 170), width=int(7 * s))
    d.ellipse([cx + t * .25, cy - t * .55, cx + t * .45, cy - t * .35], fill=(255, 235, 210, 140))

def tespih(img, cx, cy, s, rot=0.4):
    random.seed(7)
    pts = []
    n = 33
    # loose loop shape
    for i in range(n):
        u = i / n * 2 * math.pi
        rx, ry = 230 * s, 150 * s
        x = rx * math.cos(u) + 30 * s * math.sin(2 * u)
        y = ry * math.sin(u) + 25 * s * math.cos(3 * u)
        xr = x * math.cos(rot) - y * math.sin(rot); yr = x * math.sin(rot) + y * math.cos(rot)
        pts.append((cx + xr, cy + yr))
    br = 17 * s
    # imame position: between last and first bead, extended outwards
    a0 = pts[0]; tail_dir = (math.cos(rot), math.sin(rot))
    im_c = (a0[0] + tail_dir[0] * 55 * s, a0[1] + tail_dir[1] * 55 * s)
    tassel_end = (im_c[0] + tail_dir[0] * 120 * s + 20 * s, im_c[1] + tail_dir[1] * 120 * s + 40 * s)
    def shape(dd, f):
        for (x, y) in pts: dd.ellipse([x - br, y - br, x + br, y + br], fill=f)
        dd.ellipse([im_c[0] - 30 * s, im_c[1] - 30 * s, im_c[0] + 30 * s, im_c[1] + 30 * s], fill=f)
    shadow(img, shape, offset=(10, 12), blur=8, alpha=140)
    d = ImageDraw.Draw(img, "RGBA")
    # string
    d.line(pts + [pts[0]], fill=(60, 30, 20), width=int(3 * s))
    # tassel (püskül)
    for k in range(26):
        jx = random.uniform(-26, 26) * s; jy = random.uniform(-10, 20) * s
        d.line([im_c, (tassel_end[0] + jx, tassel_end[1] + jy)], fill=(150, 20, 30) if k % 3 else (190, 150, 60), width=int(3 * s))
    for i, (x, y) in enumerate(pts):
        c = (196, 112, 18) if i not in (11, 22) else (40, 26, 18)  # amber with two separators
        d.ellipse([x - br, y - br, x + br, y + br], fill=c)
        d.ellipse([x - br * .75, y - br * .75, x + br * .55, y + br * .55], fill=tuple(min(255, v + 30) for v in c))
        d.ellipse([x - br * .55, y - br * .6, x - br * .1, y - br * .2], fill=(255, 235, 190, 150))
    # imame (long bead)
    w2, h2 = 22 * s, 36 * s
    im = Image.new("RGBA", (int(w2 * 2 + 4), int(h2 * 2 + 4)), (0, 0, 0, 0))
    di = ImageDraw.Draw(im)
    di.ellipse([2, 2, w2 * 2, h2 * 2], fill=(176, 92, 12))
    di.ellipse([w2 * .5, h2 * .4, w2 * .9, h2 * .9], fill=(255, 235, 190, 140))
    im = im.rotate(-math.degrees(rot) + 90, expand=True)
    img.paste(im, (int(im_c[0] - im.width / 2), int(im_c[1] - im.height / 2)), im)

def dice(img, cx, cy, s, rot, face):
    q = 46 * s
    def shape(dd, f): dd.rounded_rectangle([cx - q, cy - q, cx + q, cy + q], radius=12 * s, fill=f)
    shadow(img, shape, offset=(10, 12), blur=8, alpha=150)
    tile = Image.new("RGBA", (int(q * 2 + 2), int(q * 2 + 2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.rounded_rectangle([0, 0, q * 2, q * 2], radius=12 * s, fill=(248, 246, 240), outline=(210, 205, 195), width=2)
    pos = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
           5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}[face]
    for (a, b) in pos:
        x, y = q + a * q * .5, q + b * q * .5; r = 8 * s
        d.ellipse([x - r, y - r, x + r, y + r], fill=(30, 30, 30) if face != 1 else (170, 20, 30))
    tile = tile.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.paste(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)), tile)

def vignette(img, strength=0.65):
    w, h = img.size
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse([-w * .15, -h * .1, w * 1.15, h * 1.1], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(min(w, h) // 5))
    dark = Image.new("RGB", (w, h), (12, 6, 3))
    return Image.composite(img, Image.blend(img, dark, strength), m)

def scene(w, h, out):
    img = wood(w, h)
    s = min(w, h) / 1080
    if h > w:  # portrait (phone): objects toward bottom and top corners so center text stays clear
        tea(img, w * .80, h * .14, s * 1.0)
        tea(img, w * .20, h * .88, s * 1.05)
        tespih(img, w * .62, h * .80, s * .95, rot=-0.5)
        dice(img, w * .18, h * .20, s, 18, 6)
        dice(img, w * .32, h * .16, s, -24, 5)
    else:
        tea(img, w * .14, h * .26, s * .95)
        tea(img, w * .88, h * .78, s * 1.0)
        tespih(img, w * .78, h * .24, s * .9, rot=0.3)
        dice(img, w * .12, h * .78, s, 15, 6)
        dice(img, w * .21, h * .84, s, -22, 6)
    img = vignette(img)
    img.save(out, quality=86, optimize=True)

scene(1080, 1920, sys.argv[1] + "/bg_portrait.jpg")
scene(1600, 1000, sys.argv[1] + "/bg_landscape.jpg")
