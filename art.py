"""Turn avatar.png into the ASCII portrait the card shows. Run locally once (needs Pillow).

    python art.py            -> art.txt
"""
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).parent
COLS = 64
RAMP = " .'`,:;!|ijkxmM%#@"  # sparse -> dense
CROP = (85, 20, 375, 345)    # head and shoulders of the 460 px avatar
NECK_Y = 290                 # contrast is stretched over the head only, so the black shirt can't eat the range
ROWS = round(COLS * (CROP[3] - CROP[1]) / (CROP[2] - CROP[0]) / 2.24)  # a Consolas cell is 2.24x taller than wide


def backdrop(img):
    """Flood-fill the flat grey studio backdrop in from the top and sides (grey = low saturation)."""
    w, h = img.size
    px = img.load()

    def grey(xy):
        r, g, b = px[xy]
        return max(r, g, b) - min(r, g, b) < 16 and 40 < (r + g + b) / 3 < 150

    seeds = [(x, 0) for x in range(w)] + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    bg, q = set(), deque(s for s in seeds if grey(s))
    bg.update(q)
    while q:
        x, y = q.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= n[0] < w and 0 <= n[1] < h and n not in bg and grey(n):
                bg.add(n)
                q.append(n)
    mask = Image.new("L", img.size, 255)
    for xy in bg:
        mask.putpixel(xy, 0)
    return mask


def render(lum, fg):
    rows = []
    for y in range(ROWS):
        line = ""
        for x in range(COLS):
            if fg.getpixel((x, y)) < 128:
                line += " "
                continue
            v = lum.getpixel((x, y)) / 255  # bright -> dense: the card is light glyphs on black
            line += RAMP[max(1, min(len(RAMP) - 1, round(v * (len(RAMP) - 1))))]
        rows.append(line.rstrip())
    return "\n".join(rows) + "\n"


img = Image.open(HERE / "avatar.png").convert("RGB")
mask = backdrop(img)
head = mask.copy()
ImageDraw.Draw(head).rectangle((0, NECK_Y, *img.size), fill=0)
lum = ImageOps.equalize(img.convert("L"), mask=head)
lum, fg = (im.crop(CROP).resize((COLS, ROWS), Image.BOX) for im in (lum, mask))
(HERE / "art.txt").write_text(render(lum, fg))
print((HERE / "art.txt").read_text())
