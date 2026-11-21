"""Renders the multimodal WhatsApp inputs: phone-style photos (stickers, error displays, TDS meter, invoice, carton, scenes) and voice notes.
Photos are synthetic renders with real camera artefacts (perspective, blur, noise, glare, JPEG). They test the pipeline (OCR, vision, language);
replace with real phone photos for the final demo (see CAPTURE_KIT.md). Voice notes are synthesised speech degraded to phone quality (Opus)."""
import os, io, json, math, wave, subprocess, random
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.signal import butter, lfilter
from common import *
from catalogue import *
from people import HH, APPS
from world import CENTRE_NUMBERS
from stories import STORIES, GROUND_TRUTH

FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=False, mono=False):
    n = "DejaVuSansMono-Bold.ttf" if (mono and bold) else "DejaVuSansMono.ttf" if mono else "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(FD + n, sz)

R = random.Random(4242)
NR = np.random.default_rng(4242)

# ---------------------------------------------------------------------------------- camera effects
def camera(img, blur=0.0, noise=6.0, persp=0.04, glare=0.0, exposure=1.0, motion=0, jpeg=78, vignette=0.25, warm=0.0, size=(1280, 960)):
    a = np.array(img.convert("RGB")).astype(np.float32)
    h, w = a.shape[:2]
    if persp:
        dx = lambda: R.uniform(-persp, persp) * w
        dy = lambda: R.uniform(-persp, persp) * h
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = np.float32([[dx(), dy()], [w + dx(), dy()], [w + dx(), h + dy()], [dx(), h + dy()]])
        M = cv2.getPerspectiveTransform(src, dst)
        a = cv2.warpPerspective(a, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    if motion:
        k = np.zeros((motion, motion)); k[motion // 2, :] = 1 / motion
        a = cv2.filter2D(a, -1, k)
    if blur:
        a = cv2.GaussianBlur(a, (0, 0), blur)
    if glare:
        yy, xx = np.mgrid[0:h, 0:w]
        cx, cy = R.uniform(0.2, 0.8) * w, R.uniform(0.15, 0.6) * h
        g = np.exp(-(((xx - cx) / (0.18 * w)) ** 2 + ((yy - cy) / (0.12 * h)) ** 2))
        a += glare * 255 * g[..., None]
    if vignette:
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        a *= (1 - vignette * np.clip(d - 0.4, 0, 1))[..., None]
    a *= exposure
    if warm:
        a[..., 0] *= 1 + warm; a[..., 2] *= 1 - warm
    a += NR.normal(0, noise, a.shape)
    a = np.clip(a, 0, 255).astype(np.uint8)
    im = Image.fromarray(a)
    im.thumbnail(size)
    return im

def save_jpeg(im, path, q=78):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "JPEG", quality=q, optimize=True)   # no EXIF, like a WhatsApp-recompressed image

def texture(w, h, base, var=10, scale=3):
    n = NR.normal(0, var, (h // scale + 1, w // scale + 1, 1))
    n = cv2.resize(n[..., 0], (w, h), interpolation=cv2.INTER_CUBIC)[..., None]
    arr =np.clip(np.array(base, dtype=np.float32)[None, None, :] + n, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)

# ---------------------------------------------------------------------------------- seven-segment
SEG = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg",
       "E": "adefg", "F": "aefg", "H": "bcefg", "P": "abefg", "U": "bcdef", "d": "bcdeg", "n": "ceg", "b": "cdefg", "r": "eg", "o": "cdeg", "L": "def", "c": "deg", "-": "g", " ": ""}
def seven(draw, ch, x, y, w, h, on, off, t=None):
    t = t or max(3, w // 6)
    segs = SEG.get(ch, "")
    def hseg(cx, cy): return [(cx - w / 2 + t, cy - t / 2), (cx + w / 2 - t, cy - t / 2), (cx + w / 2 - t / 2 - 1, cy), (cx + w / 2 - t, cy + t / 2), (cx - w / 2 + t, cy + t / 2), (cx - w / 2 + t / 2 + 1, cy)]
    def vseg(cx, cy): return [(cx - t / 2, cy - h / 4 + t / 2), (cx, cy - h / 4 + t), (cx + t / 2, cy - h / 4 + t / 2), (cx + t / 2, cy + h / 4 - t / 2), (cx, cy + h / 4 - t), (cx - t / 2, cy + h / 4 - t / 2)]
    pos = {"a": hseg(x, y - h / 2 + t / 2), "g": hseg(x, y), "d": hseg(x, y + h / 2 - t / 2), "f": vseg(x - w / 2 + t / 2, y - h / 4), "b": vseg(x + w / 2 - t / 2, y - h / 4),
           "e": vseg(x - w / 2 + t / 2, y + h / 4), "c": vseg(x + w / 2 - t / 2, y + h / 4)}
    for s, poly in pos.items():
        draw.polygon(poly, fill=on if s in segs else off)

def digits(text, w, h, on, off, bg, pad=14, gap=10):
    n = len(text)
    dw = int(h * 0.55)
    W = pad * 2 + n * dw + (n - 1) * gap
    img = Image.new("RGB", (W, h + pad * 2), bg)
    d = ImageDraw.Draw(img)
    for i, ch in enumerate(text):
        cx = pad + i * (dw + gap) + dw / 2
        seven(d, ch, cx, pad + h / 2, dw, h, on, off)
    return img

def glow(img, color, amount=2.0):
    a = np.array(img).astype(np.float32)
    b = cv2.GaussianBlur(a, (0, 0), 6)
    return Image.fromarray(np.clip(a + b * amount * 0.5, 0, 255).astype(np.uint8))

# ---------------------------------------------------------------------------------- renderers
def r_sticker(app_key, quality="good", spec=None):
    """Rating plate. spec overrides fields for appliances not in the database."""
    if app_key in APPS:
        a = APPS[app_key]; m = MODEL_BY_CODE[a["model"]]
        brand, model, serial, year = a["brand"], a["model"], a["serial"], (a["purchase"].year if a["purchase"] else 2021)
        cat, specs = m[1], m[6]
    else:
        brand, model, serial, year = spec["brand"], spec["model"], spec["serial"], spec["year"]
        m = MODEL_BY_CODE[model]; cat, specs = m[1], m[6]
    W, H = 1100, 760
    panel = texture(W, H, (205, 207, 210), 5)
    d = ImageDraw.Draw(panel)
    d.rounded_rectangle([40, 40, W - 40, H - 40], 14, fill=(245, 245, 242), outline=(120, 120, 120), width=3)
    d.text((70, 62), brand.upper(), font=font(52, True), fill=(20, 54, 110))
    d.text((W - 380, 78), {"air_conditioner": "SPLIT AIR CONDITIONER", "refrigerator": "REFRIGERATOR", "washing_machine": "WASHING MACHINE",
                           "water_purifier": "WATER PURIFIER", "water_heater": "WATER HEATER"}[cat], font=font(22, True), fill=(60, 60, 60))
    d.line([60, 135, W - 60, 135], fill=(90, 90, 90), width=3)
    rows = [("MODEL", model), ("SERIAL NO.", serial or "-"), ("MFG DATE", f"{R.randint(1, 12):02d}/{max(2019, year)}")]
    if cat == "air_conditioner":
        rows += [("RATED VOLTAGE", "220-240 V ~ 50 Hz"), ("COOLING CAPACITY", f"{int(specs['tonnage'] * 3517)} W"), ("RATED INPUT", f"{int(specs['tonnage'] * 1000 + 70)} W"),
                 ("REFRIGERANT", f"R32   CHARGE {int(specs['tonnage'] * 520 + 260)} g"), ("STAR RATING", f"{specs['star']} STAR")]
    elif cat == "washing_machine":
        rows += [("RATED VOLTAGE", "220-240 V ~ 50 Hz"), ("RATED CAPACITY", f"{specs['kg']} kg"), ("WATER PRESSURE", "0.03 - 0.8 MPa"), ("RATED POWER", "480 W")]
    elif cat == "water_purifier":
        rows += [("RATED VOLTAGE", "230 V ~ 50 Hz"), ("INPUT TDS", "UP TO 2000 ppm"), ("TANK", f"{specs['tank_l']} L"), ("STAGES", specs["stages"])]
    elif cat == "water_heater":
        rows += [("RATED VOLTAGE", "230 V ~ 50 Hz"), ("RATED POWER", f"{specs['power_w']} W"), ("CAPACITY", f"{specs['litres']} L"), ("MAX PRESSURE", "0.8 MPa")]
    else:
        rows += [("RATED VOLTAGE", "220-240 V ~ 50 Hz"), ("GROSS VOLUME", f"{specs['litres']} L"), ("REFRIGERANT", "R600a")]
    y = 160
    for k, v in rows:
        d.text((70, y), k, font=font(24), fill=(70, 70, 70))
        d.text((420, y - 2), str(v), font=font(30, True, True), fill=(10, 10, 10))
        y += 52
    # barcode
    x = 70
    for _ in range(70):
        wd = R.choice([2, 3, 5]); d.rectangle([x, H - 140, x + wd, H - 70], fill=(15, 15, 15)); x += wd + R.choice([2, 3, 4])
    d.text((70, H - 66), f"{serial or ''}", font=font(18, False, True), fill=(30, 30, 30))
    d.text((W - 330, H - 100), "MADE IN INDIA", font=font(20, True), fill=(60, 60, 60))
    kw = dict(good=dict(blur=0.8, noise=4, persp=0.03, glare=0.1, exposure=1.0),
              blurry=dict(blur=3.2, noise=9, persp=0.05, glare=0.25, exposure=0.82, motion=5),
              very_blurry=dict(blur=7.5, noise=14, persp=0.06, glare=0.35, exposure=0.7, motion=11))[quality]
    return camera(panel, **kw)

def r_display(kind, code):
    W, H = 1280, 960
    bg = texture(W, H, (214, 214, 208), 6, 4)
    d = ImageDraw.Draw(bg)
    if kind.startswith("ac_"):
        # indoor unit seen from below-front: white body, louvre, display window
        d.rounded_rectangle([90, 250, W - 90, 640], 60, fill=(238, 240, 242), outline=(190, 192, 196), width=4)
        d.rounded_rectangle([110, 520, W - 110, 620], 40, fill=(226, 228, 232))
        d.text((170, 330), "AEROVANE" if "aerovane" in kind else "ZENITH", font=font(46, True), fill=(80, 90, 110))
        for i in range(9):
            d.line([200 + i * 100, 560, 230 + i * 100, 600], fill=(190, 192, 198), width=3)
        win = digits(code, 0, 70, (255, 40, 30), (60, 12, 12), (22, 8, 8))
        win = glow(win, (255, 40, 30), 2.0)
        d.rounded_rectangle([W - 430, 330, W - 150, 470], 18, fill=(30, 30, 34))
        win = win.resize((220, int(220 * win.height / win.width))) if win.width > 220 else win
        bg.paste(win, (W - 400 + (220 - win.width) // 2, 360))
        d.ellipse([W - 190, 345, W - 170, 365], fill=(255, 150, 20))
        d.text((W - 430, 480), "RUN  TIMER  ALERT", font=font(16), fill=(110, 110, 120))
    elif kind.startswith("washer"):
        d.rounded_rectangle([60, 180, W - 60, 760], 30, fill=(236, 238, 240), outline=(170, 172, 176), width=4)
        d.rectangle([60, 180, W - 60, 440], fill=(226, 230, 236))
        d.ellipse([140, 230, 380, 470], fill=(200, 204, 212), outline=(120, 124, 132), width=5)
        d.line([260, 250, 260, 300], fill=(60, 60, 66), width=8)
        win = glow(digits(code, 0, 110, (255, 80, 30), (60, 24, 14), (16, 10, 10)), (255, 80, 30), 1.8)
        d.rounded_rectangle([470, 250, 830, 430], 16, fill=(20, 14, 14))
        bg.paste(win, (470 + (360 - win.width) // 2, 280))
        for i, lbl in enumerate(["START", "TEMP", "SPIN", "SOIL"]):
            bx = 880 + (i % 2) * 150; by = 250 + (i // 2) * 95
            d.rounded_rectangle([bx, by, bx + 130, by + 70], 16, fill=(212, 216, 222), outline=(130, 134, 140), width=2)
            d.text((bx + 16, by + 24), lbl, font=font(20, True), fill=(60, 64, 72))
        d.text((480, 450), "WAVECREST", font=font(36, True), fill=(30, 60, 120))
        d.ellipse([300, 520, 720, 940], fill=(150, 154, 160), outline=(90, 94, 100), width=10)
    else:  # fridge display
        d.rounded_rectangle([280, 60, W - 280, 900], 28, fill=(222, 226, 230), outline=(170, 174, 180), width=4)
        d.rounded_rectangle([340, 140, W - 340, 330], 24, fill=(12, 18, 26))
        win = glow(digits(code, 0, 120, (90, 200, 255), (14, 38, 54), (10, 16, 22)), (90, 200, 255), 1.6)
        bg.paste(win, ((W - win.width) // 2, 160))
        d.text((360, 345), "FREEZER   FRIDGE   ECO", font=font(22), fill=(100, 110, 120))
        d.text((W // 2 - 110, 400), "ZENITH", font=font(44, True), fill=(40, 60, 100))
        d.line([W // 2, 450, W // 2, 880], fill=(170, 174, 180), width=4)
    return camera(bg, blur=1.0, noise=5, persp=0.035, glare=0.18, exposure=0.95, vignette=0.3)

def r_tds(value):
    W, H = 1280, 960
    bg = texture(W, H, (176, 154, 128), 12, 5)   # kitchen counter
    d = ImageDraw.Draw(bg)
    d.polygon([(0, 700), (W, 640), (W, H), (0, H)], fill=(196, 188, 176))
    body = Image.new("RGB", (900, 260), (244, 244, 246))
    bd = ImageDraw.Draw(body)
    bd.rounded_rectangle([0, 0, 899, 259], 60, fill=(246, 246, 248), outline=(170, 172, 176), width=4)
    bd.rounded_rectangle([60, 50, 520, 210], 18, fill=(150, 172, 138), outline=(60, 70, 60), width=4)
    lcd = digits(str(value), 0, 100, (34, 42, 30), (140, 160, 128), (150, 172, 138), pad=8, gap=8)
    body.paste(lcd, (70 + (440 - lcd.width) // 2, 60))
    bd.text((420, 170), "ppm", font=font(30, True), fill=(34, 42, 30))
    bd.ellipse([620, 90, 700, 170], fill=(60, 90, 200)); bd.text((628, 115), "ON", font=font(22, True), fill=(255, 255, 255))
    bd.text((740, 80), "TDS", font=font(44, True), fill=(60, 60, 70)); bd.text((740, 140), "METER", font=font(26), fill=(90, 90, 100))
    body = body.rotate(-7, expand=True, fillcolor=(0, 0, 0)).convert("RGBA")
    mask = Image.new("L", body.size, 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, body.height - 1], 60, fill=255)
    bg.paste(body.convert("RGB"), (180, 300), mask)
    bg.paste(Image.new("RGB", (20, 20), (0, 0, 0)), (0, 0))
    # a glass of water in the foreground
    d.ellipse([930, 640, 1130, 700], fill=(200, 215, 225), outline=(150, 160, 170), width=3)
    d.rectangle([940, 460, 1120, 670], fill=(214, 226, 234), outline=(160, 172, 182), width=3)
    return camera(bg, blur=1.2, noise=7, persp=0.04, glare=0.1, exposure=1.0, warm=0.04)

def r_scene_ac_leak():
    W, H = 960, 1280
    wall = texture(W, H, (226, 214, 190), 5, 6)
    d = ImageDraw.Draw(wall, "RGBA")
    d.rounded_rectangle([60, 40, W - 60, 300], 50, fill=(240, 242, 244), outline=(200, 202, 206), width=4)
    d.rounded_rectangle([90, 230, W - 90, 285], 30, fill=(228, 230, 234))
    d.text((120, 90), "AEROVANE", font=font(40, True), fill=(90, 100, 120))
    for x0 in (300, 470, 560, 700):
        for k in range(0, R.randint(560, 900), 3):
            w = 14 + R.randint(0, 6)
            d.rectangle([x0 + k * 0.01, 300 + k, x0 + w, 301 + k], fill=(120, 100, 70, 4))
    # water streaks and stains running down the wall
    for x0, ln in ((330, 860), (480, 720), (620, 940), (720, 600)):
        for t in range(0, ln, 4):
            wob = 6 * math.sin(t / 60.0)
            d.ellipse([x0 + wob - 18, 300 + t - 10, x0 + wob + 18, 300 + t + 10], fill=(110, 96, 70, 7))
    d.polygon([(0, 1090), (W, 1070), (W, H), (0, H)], fill=(198, 196, 190, 255))
    for xx in range(0, W, 160):
        d.line([xx, 1090, xx - 40, H], fill=(170, 168, 162, 255), width=3)
    d.ellipse([260, 1120, 780, 1230], fill=(120, 138, 150, 150))
    d.ellipse([320, 1140, 700, 1200], fill=(170, 190, 202, 120))
    for _ in range(14):
        x = R.randint(300, 700); y = R.randint(300, 1000); d.ellipse([x, y, x + 8, y + 16], fill=(180, 205, 225, 190))
    return camera(wall, blur=1.1, noise=7, persp=0.04, glare=0.12, exposure=0.95, vignette=0.35, warm=0.03, size=(960, 1280))

def r_scene_geyser():
    W, H = 960, 1280
    wall = texture(W, H, (208, 222, 226), 4, 6)
    d = ImageDraw.Draw(wall, "RGBA")
    for x in range(0, W, 120): d.line([x, 0, x, H], fill=(170, 186, 192, 255), width=3)
    for y in range(0, H, 120): d.line([0, y, W, y], fill=(170, 186, 192, 255), width=3)
    d.rounded_rectangle([210, 130, 750, 850], 90, fill=(244, 240, 228), outline=(188, 182, 168), width=5)
    d.text((340, 250), "HEATWELL", font=font(48, True), fill=(40, 70, 130))
    d.ellipse([320, 420, 360, 460], fill=(255, 60, 40)); d.text((380, 424), "HEATING", font=font(24), fill=(90, 90, 90))
    d.ellipse([320, 490, 360, 530], fill=(60, 60, 60)); d.text((380, 494), "READY", font=font(24), fill=(90, 90, 90))
    d.rectangle([300, 850, 360, 1010], fill=(170, 176, 180)); d.rectangle([590, 850, 650, 1010], fill=(170, 176, 180))
    d.rectangle([296, 990, 366, 1020], fill=(190, 150, 70)); d.rectangle([586, 990, 656, 1020], fill=(190, 150, 70))
    for t in range(0, 150, 3):
        d.ellipse([310 - 10, 860 + t - 4, 350 + 10, 860 + t + 12], fill=(146, 84, 40, 12))   # rust streak below the inlet
    d.ellipse([312, 1010, 352, 1050], fill=(150, 90, 50, 160))
    d.line([530, 120, 520, 20], fill=(30, 30, 30), width=10)       # power cable
    d.ellipse([240, 880, 330, 960], fill=(140, 150, 156, 170))     # wet patch
    return camera(wall, blur=1.0, noise=7, persp=0.04, glare=0.2, exposure=0.92, vignette=0.35, size=(960, 1280))

def r_scene_frost():
    W, H = 1280, 960
    im = texture(W, H, (210, 216, 222), 6, 4)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([60, 40, W - 60, H - 40], outline=(120, 130, 140), width=10)
    d.rectangle([80, 60, W - 80, 520], fill=(222, 232, 240))
    # heavy frost on the back wall and ice build-up
    fr = NR.normal(0, 1, (H // 4, W // 4)); fr = cv2.resize(fr, (W, H), interpolation=cv2.INTER_CUBIC)
    base = np.array(im).astype(np.float32)
    base[60:520, 80:W - 80] += (fr[60:520, 80:W - 80, None] * 28 + 30)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([80, 520, W - 80, 560], fill=(150, 160, 170)); d.rectangle([80, 700, W - 80, 740], fill=(150, 160, 170))
    for _ in range(40):
        x = R.randint(120, W - 160); y = R.randint(90, 500); r = R.randint(20, 70); d.ellipse([x, y, x + r, y + r * 0.7], fill=(255, 255, 255, 120))
    d.rectangle([180, 600, 460, 700], fill=(200, 150, 60, 255)); d.text((200, 630), "ICE CREAM", font=font(30, True), fill=(255, 255, 255))
    d.rectangle([520, 610, 760, 700], fill=(90, 150, 200, 255)); d.rectangle([800, 590, 1060, 700], fill=(230, 230, 230, 255))
    d.text((220, 20), "", font=font(10))
    for _ in range(60):
        x = R.randint(100, W - 120); y = R.randint(560, 900); d.ellipse([x, y, x + 12, y + 12], fill=(255, 255, 255, 90))
    return camera(im, blur=1.1, noise=7, persp=0.045, glare=0.18, exposure=0.9, vignette=0.4, size=(1280, 960))

def r_invoice(spec):
    W, H = 1000, 1400
    paper = texture(W, H, (250, 249, 245), 2, 8)
    d = ImageDraw.Draw(paper)
    d.text((60, 50), spec["retailer"].upper(), font=font(40, True), fill=(20, 40, 90))
    d.text((60, 100), "Shop 12, Commercial Complex, Madhapur, Hyderabad 500081", font=font(20), fill=(60, 60, 60))
    d.text((60, 130), "GSTIN: 36AAAAA0000A1Z5   |   Ph: 040-0000 0000", font=font(20), fill=(60, 60, 60))
    d.line([50, 175, W - 50, 175], fill=(30, 30, 30), width=3)
    d.text((60, 195), "TAX INVOICE", font=font(32, True), fill=(10, 10, 10))
    d.text((60, 255), f"Invoice no: {spec['invoice_no']}", font=font(22, False, True), fill=(10, 10, 10))
    d.text((560, 255), f"Date: {spec['date']}", font=font(22, False, True), fill=(10, 10, 10))
    d.text((60, 300), f"Customer: {spec['customer']}", font=font(22), fill=(10, 10, 10))
    d.text((60, 332), f"Address: {spec['address']}", font=font(22), fill=(10, 10, 10))
    d.rectangle([50, 395, W - 50, 440], fill=(228, 234, 244))
    for x, t in ((60, "Description"), (610, "Qty"), (690, "Rate"), (830, "Amount")):
        d.text((x, 404), t, font=font(22, True), fill=(10, 10, 10))
    d.text((60, 460), spec["item"], font=font(22, True), fill=(10, 10, 10))
    d.text((60, 495), f"Model: {spec['model']}", font=font(21, False, True), fill=(20, 20, 20))
    d.text((60, 525), f"Indoor S/N: {spec['serial']}", font=font(21, False, True), fill=(20, 20, 20))
    d.text((60, 555), f"Outdoor S/N: {spec['serial']}-O", font=font(21, False, True), fill=(20, 20, 20))
    d.text((620, 460), "1", font=font(22), fill=(10, 10, 10)); d.text((690, 460), f"{spec['rate']:,}", font=font(22), fill=(10, 10, 10)); d.text((830, 460), f"{spec['rate']:,}", font=font(22), fill=(10, 10, 10))
    gst = round(spec["rate"] * 0.28 / 1.28)
    d.line([50, 640, W - 50, 640], fill=(120, 120, 120), width=2)
    d.text((560, 660), f"Taxable value  {spec['rate'] - gst:,}", font=font(21), fill=(10, 10, 10))
    d.text((560, 695), f"GST 28%        {gst:,}", font=font(21), fill=(10, 10, 10))
    d.text((560, 740), f"TOTAL  Rs {spec['rate']:,}", font=font(30, True), fill=(10, 10, 10))
    d.text((60, 800), "Payment: UPI", font=font(21), fill=(40, 40, 40))
    d.text((60, 860), "Installation: NOT INCLUDED. Free installation to be arranged with the brand.", font=font(20), fill=(40, 40, 40))
    d.text((60, 890), "Warranty: as per brand terms. Goods once sold will not be taken back.", font=font(20), fill=(40, 40, 40))
    d.text((W - 380, 1180), "For Digital Plaza Electronics", font=font(21), fill=(40, 40, 40)); d.text((W - 330, 1240), "Authorised signatory", font=font(18), fill=(90, 90, 90))
    bg = texture(1400, 1500, (150, 112, 78), 12, 5)
    bg.paste(paper, (200, 50))
    return camera(bg, blur=0.9, noise=5, persp=0.035, glare=0.08, exposure=0.98, size=(1280, 1280), warm=0.03)

def r_carton(spec):
    W, H = 1280, 960
    box = texture(W, H, (186, 148, 102), 8, 5)
    d = ImageDraw.Draw(box)
    d.rectangle([0, 380, W, 440], fill=(170, 134, 92))
    d.text((90, 90), "ZENITH", font=font(110, True), fill=(30, 40, 80)); d.text((90, 230), "AURA  5 STAR  INVERTER SPLIT AC", font=font(40, True), fill=(30, 40, 80))
    lab = Image.new("RGB", (760, 330), (252, 252, 250)); ld = ImageDraw.Draw(lab)
    ld.text((24, 14), "ZENITH  1.5 TON  INDOOR UNIT", font=font(28, True), fill=(10, 10, 10))
    ld.text((24, 62), f"MODEL: {spec['model']}", font=font(26, False, True), fill=(10, 10, 10))
    ld.text((24, 98), f"S/N: {spec['serial']}", font=font(26, False, True), fill=(10, 10, 10))
    ld.text((24, 134), "REFRIGERANT: R32   NET WT: 9.8 kg", font=font(22), fill=(10, 10, 10))
    x = 24
    for _ in range(60):
        wd = R.choice([2, 3, 5]); ld.rectangle([x, 190, x + wd, 280], fill=(10, 10, 10)); x += wd + R.choice([2, 3, 4])
    ld.text((24, 288), spec["serial"], font=font(18, False, True), fill=(10, 10, 10))
    box.paste(lab, (330, 520))
    return camera(box, blur=1.0, noise=6, persp=0.04, glare=0.12, exposure=0.95)

# ---------------------------------------------------------------------------------- voice
VOICES = {}
def _load_tts():
    if VOICES: return
    from piper import PiperVoice
    from kokoro_onnx import Kokoro
    VOICES["te"] = PiperVoice.load("/tmp/ttstest/te_IN-venkatesh-medium.onnx")
    VOICES["k"] = Kokoro("/tmp/ttstest/kokoro.onnx", "/tmp/ttstest/voices.bin")

def tts(text, voice):
    _load_tts()
    if voice == "te_m":
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            VOICES["te"].synthesize_wav(text, w)
        buf.seek(0)
        with wave.open(buf, "rb") as w:
            sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return x, sr
    lang, vname, spd = {"hi_f": ("hi", "hf_alpha", 0.95), "hi_m": ("hi", "hm_omega", 0.95), "en_m": ("en-us", "am_michael", 0.98)}[voice]
    x, sr = VOICES["k"].create(text, voice=vname, speed=spd, lang=lang)
    return np.asarray(x, dtype=np.float32), sr

def phone_audio(x, sr, noise_kind, out_path):
    if sr != 16000:
        n = int(len(x) * 16000 / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32); sr = 16000
    x = x / (np.abs(x).max() + 1e-6) * 0.7
    b, a = butter(4, [280 / 8000, 3600 / 8000], btype="band"); x = lfilter(b, a, x)
    lead = np.zeros(int(sr * R.uniform(0.35, 0.8))); tail = np.zeros(int(sr * R.uniform(0.4, 0.9)))
    x = np.concatenate([lead, x, tail])
    t = np.arange(len(x)) / sr
    nz = NR.normal(0, 1, len(x))
    if noise_kind == "room_fan":
        bed = 0.012 * np.sin(2 * np.pi * 50 * t) + 0.01 * lfilter(*butter(2, 600 / 8000), nz)
    elif noise_kind == "street_light":
        bed = 0.02 * lfilter(*butter(2, [150 / 8000, 2500 / 8000], btype="band"), nz) + 0.01 * np.sin(2 * np.pi * 90 * t)
    else:  # traffic
        bed = 0.045 * lfilter(*butter(2, [80 / 8000, 3000 / 8000], btype="band"), nz) * (1 + 0.5 * np.sin(2 * np.pi * 0.3 * t))
        for _ in range(3):
            c = R.uniform(0.5, max(0.6, len(x) / sr - 0.5)); i = int(c * sr)
            burst = 0.06 * np.sin(2 * np.pi * R.choice([420, 480]) * t[: int(0.3 * sr)]) * np.hanning(int(0.3 * sr))
            if i + len(burst) < len(x): x[i:i + len(burst)] += burst
    x = np.clip(x + bed, -0.99, 0.99)
    x = np.tanh(x * 1.4) / np.tanh(1.4)
    tmp = out_path + ".wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:a", "libopus", "-b:a", "16k", "-application", "voip", out_path], check=True)
    os.remove(tmp)
    return len(x) / sr

# ---------------------------------------------------------------------------------- orchestration

def _render_image(m, s):
    r = m["render"]
    if r == "sticker": return r_sticker(m["sticker"], m["quality"])
    if r == "sticker_unlisted": return r_sticker(None, m["quality"], spec=dict(brand="zenith", model="ZN-CS15I3", serial="ZN21CS0366118", year=2021))
    if r == "display": return r_display(m["display"], m["code"])
    if r == "tds": return r_tds(m["value"])
    if r == "scene_ac_leak": return r_scene_ac_leak()
    if r == "scene_geyser": return r_scene_geyser()
    if r == "scene_frost": return r_scene_frost()
    p = s["new_purchase"]
    if r == "invoice":
        return r_invoice(dict(retailer=p["retailer"], invoice_no=p["invoice_no"], date="20-Nov-2026", customer=s["sender"], address="Flat 904, Tower 2, Raintree Towers, HITEC City, Hyderabad",
                              item="ZENITH AURA 1.5 TON 5 STAR INVERTER SPLIT AC", model=p["model"], serial=p["serial"], rate=58990))
    if r == "carton": return r_carton(dict(model=p["model"], serial=p["serial"]))
    raise ValueError(r)

def _resolve_phone(s):
    """Phone the case arrives from. Known cases use the household/member number on record; new cases get a fresh number."""
    if s["existing"]:
        hh = HH[f"hh_{s['id'].lower()}"]
        pf = (s.get("payload") or {}).get("phone_from", "")
        if pf.startswith("member:"):
            nm = pf.split(":", 1)[1]
            return next(m["phone"] for m in hh["members"] if m["name"] == nm), True
        return next((m["phone"] for m in hh["members"] if m["name"] == s["sender"]), hh["phone"]), True
    return unique_phone(), False

def _persona_md(s):
    p = s["persona"]
    lines = [f"# Persona card, case {s['id']}", "",
             f"Play this household when the agent calls back, asks questions or runs a video session. Answer only what is asked, in the language below, and do not volunteer the secret.", "",
             f"- Trigger: {s['trigger'].replace('_', ' ')} (channel {s['channel']})",
             f"- Who: {p['who']}", f"- Technology: {p['tech']}", f"- Attitude: {p['attitude']}", "", "## When asked", ""]
    for k, v in p["when_asked"].items():
        lines.append(f"- **{k}**: {v}")
    lines += ["", "## Secret (the real situation, never offered unprompted)", "", p["secret"], ""]
    return "\n".join(lines)

def build_inbox(outdir):
    """Writes app-facing inputs (inbox.json + media) and persona cards. Returns (events, voice_ground_truth, phones)."""
    os.makedirs(outdir, exist_ok=True)
    events, gt_voice, phones = [], {}, {}
    pers = os.path.join(os.path.dirname(os.path.abspath(outdir)), "evaluator_only", "personas"); os.makedirs(pers, exist_ok=True)
    for s in STORIES:
        cid = s["id"]; sub = os.path.join(outdir, cid); os.makedirs(sub, exist_ok=True)
        sender_phone, known = _resolve_phone(s); phones[cid] = sender_phone
        voice_line, wa_line = CENTRE_NUMBERS[s["centre"]]
        trig = s["trigger"]; media = []
        ev = {"case_id": cid, "trigger": trig, "channel": s["channel"], "number_known_to_keepwell": known}
        if trig in ("household_message", "household_call"):
            ev.update(from_phone=sender_phone, sender_profile_name=s["sender"], to_number=(voice_line if trig == "household_call" else wa_line))
        msgs = []
        for i, m in enumerate(s.get("msgs", []), 1):
            hh_, mm_ = map(int, m["t"].split(":"))
            ts = ist(2026, 11, 21, hh_, mm_) + dt.timedelta(seconds=R.randint(0, 50))
            base = {"id": f"evt.{R.randint(10**13, 10**14 - 1)}", "timestamp": str(int(ts.timestamp())), "timestamp_iso": ts.isoformat()}
            t = m["type"]
            if t == "text":
                msgs.append({**base, "type": "text", "text": {"body": m["text"]}})
            elif t == "location":
                msgs.append({**base, "type": "location", "location": {"latitude": m["lat"], "longitude": m["lon"], "name": m.get("name")}})
            elif t in ("audio", "call"):
                fn = f"{i:02d}_{'call' if t == 'call' else 'voice'}.ogg"
                x, sr = tts(m["script"], m["voice"])
                dur = phone_audio(x, sr, m["noise"], os.path.join(sub, fn))
                if t == "audio":
                    msgs.append({**base, "type": "audio", "audio": {"file": f"{cid}/{fn}", "mime_type": "audio/ogg; codecs=opus", "voice": True, "duration_s": round(dur, 1)}})
                else:
                    msgs.append({**base, "type": "call", "call": {"direction": "inbound", "dialled_number": voice_line, "caller_number": sender_phone, "answered": True,
                                                                    "recording": {"file": f"{cid}/{fn}", "mime_type": "audio/ogg; codecs=opus", "duration_s": round(dur, 1)}}})
                gt_voice[f"{cid}/{fn}"] = {"kind": t, "language": m["lang"], "speaker_voice": m["voice"], "background": m["noise"], "transcript_original_script": m["script"]}
            elif t == "image":
                fn = f"{i:02d}_photo.jpg"
                save_jpeg(_render_image(m, s), os.path.join(sub, fn))
                rec = {"file": f"{cid}/{fn}", "mime_type": "image/jpeg", "caption": m.get("caption") or None}
                if trig in ("brand_forward", "retailer_handover"):
                    media.append(rec)
                else:
                    msgs.append({**base, "type": "image", "image": rec})
        if trig in ("household_message", "household_call"):
            ev["messages"] = msgs
        else:
            p = dict(s["payload"]); pf = p.pop("phone_from", None)
            hh_t = int(p["received"].split(":")[0]); mm_t = int(p["received"].split(":")[1])
            p["received_at"] = ist(2026, 11, 21, hh_t, mm_t).isoformat(); p.pop("received", None)
            p["customer"] = {"name": s["sender"].replace("Tenant (Rohit)", "Rohit"), "phone": sender_phone}
            if media: p["attachments"] = media
            p["source"] = {"channel": s["channel"], "system_id": f"{p.get('brand') or 'retailer'}-integration"}
            ev["payload"] = p
        events.append(ev)
        with open(os.path.join(pers, f"{cid}.md"), "w", encoding="utf-8") as f:
            f.write(_persona_md(s))
        # per-case payload file for the brand / retailer channels
        if trig == "brand_forward":
            os.makedirs(os.path.join(outdir, "brand_requests"), exist_ok=True)
            with open(os.path.join(outdir, "brand_requests", f"{cid}.json"), "w", encoding="utf-8") as f: json.dump(ev["payload"], f, ensure_ascii=False, indent=2)
        if trig == "retailer_handover":
            os.makedirs(os.path.join(outdir, "retailer_handovers"), exist_ok=True)
            with open(os.path.join(outdir, "retailer_handovers", f"{cid}.json"), "w", encoding="utf-8") as f: json.dump(ev["payload"], f, ensure_ascii=False, indent=2)
    with open(os.path.join(outdir, "inbox.json"), "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    return events, gt_voice, phones
