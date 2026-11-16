"""MVP: renderiza só os ossos do esqueleto em pose T (frente com nomes + três quartos).

Uso: python examples/ossos_tpose.py [pasta_de_saida]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont
from character_studio.skeleton import humanoid
from character_studio import render as R

out = Path(sys.argv[1] if len(sys.argv) > 1 else "out"); out.mkdir(parents=True, exist_ok=True)
W, Hpx = 1080, 1350
sk = humanoid()
H = max(b.tail[2] for b in sk.bones.values())
span = 2 * max(abs(b.tail[0]) for b in sk.bones.values())

# frente, ortográfica (permite projetar os nomes com exatidão)
vis_w = max(span * 1.2, (H * 1.2) * W / Hpx)   # largura visível em metros
vis_h = vis_w * Hpx / W
cz = vis_h / 2 - 0.12 * H
R.reset_scene(res=(W, Hpx)); R.studio_backdrop(); R.studio_lights(); R.add_skeleton_visual(sk)
R.camera((0, -6, cz), (0, 0, cz), ortho_scale=max(vis_w, vis_h))
R.render(out / "ossos_frente.png")

# três quartos, perspectiva
R.reset_scene(res=(W, Hpx)); R.studio_backdrop(); R.studio_lights(); R.add_skeleton_visual(sk)
R.camera((1.9, -3.3, 1.2), (0, 0, H * 0.52), lens=50)
R.render(out / "ossos_3q.png")

# nomes na vista de frente
img = Image.open(out / "ossos_frente.png").convert("RGB")
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
except OSError:
    font = ImageFont.load_default()
ppm = W / vis_w
def px(p):
    return (W / 2 + p[0] * ppm, Hpx / 2 - (p[2] - cz) * ppm)
for b in sk.bones.values():
    if b.role == "raiz" or b.side == "R":
        continue
    mid = (b.head + b.tail) / 2
    x, y = px(mid)
    name = b.name.replace(".L", "")
    tw = d.textlength(name, font=font)
    if b.side == "C":
        tx, ty = x - 110 - tw, y - 12
        d.line([(x - 14, y), (tx + tw + 6, y)], fill=(40, 40, 40), width=2)
    elif b.role in ("coxa", "canela", "pe"):
        tx, ty = x + 70, y - 12
        d.line([(x + 14, y), (tx - 6, y)], fill=(40, 40, 40), width=2)
    else:
        tx, ty = x - tw / 2, y - 62
        d.line([(x, y - 16), (x, y - 34)], fill=(40, 40, 40), width=2)
    d.text((tx, ty), name, fill=(20, 20, 20), font=font)
img.save(out / "ossos_frente.png")

both = Image.new("RGB", (W * 2, Hpx))
both.paste(img, (0, 0)); both.paste(Image.open(out / "ossos_3q.png").convert("RGB"), (W, 0))
both.save(out / "ossos_tpose.png")
print(out / "ossos_tpose.png")
