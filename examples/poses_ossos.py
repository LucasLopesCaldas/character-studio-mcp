"""Grade de validação: poses resolvidas pelo solucionador, só nos ossos (frente e lado).

Uso: python examples/poses_ossos.py [pasta_de_saida]
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from character_studio.skeleton import humanoid
from character_studio.solver import Solver, Alvo, Direcao, Olhar, Dobra, Tronco, Palma, Toque
from character_studio import poses
from character_studio import render as R

out = Path(sys.argv[1] if len(sys.argv) > 1 else "out"); out.mkdir(parents=True, exist_ok=True)
sk = humanoid(); S = Solver(sk); H = S.H
cenas = []   # (titulo, estado, relatorio, caixas, alvos)

def resolver(titulo, cons, chute=None, inicial=None, caixas=(), alvos=()):
    t = time.time()
    x, st, rep = S.solve(cons, inicial=inicial, chute=chute)
    print(f"== {titulo}  ({time.time() - t:.1f} s)\n{rep}")
    cenas.append((titulo, st, rep, caixas, alvos))
    return x, st

# 1. em pé
cons, chute = poses.em_pe(S)
resolver("em pé", cons, chute)

# 2. sentada
alt = poses.altura_assento_ideal(S)
assento = [((0, 0.03, alt / 2), (0.42, 0.40, alt))]
cons_s, chute = poses.sentar(S, alt)
x_s, st_s = resolver("sentada", cons_s, chute, caixas=assento)

# 3. sentada com o celular: mão direita à frente do peito, esquerda na coxa, olhando o celular
peito = st_s.head[S.idx["peito"]]
cel = (peito[0] - 0.03 * H, peito[1] - 0.17 * H, peito[2] - 0.03 * H)
cons = cons_s + [Alvo("mao.R", cel), Palma("mao.R", (0.2, 0.6, 0.75), peso=2), Olhar(cel),
                 Toque("mao.L", "coxa.L", onde=0.6, lado=(0, -1, 0))]
resolver("sentada com o celular", cons, inicial=x_s, caixas=assento, alvos=[cel])

# 4. sentada, mão no rosto (queixo apoiado na mão esquerda)
cons = cons_s + [Toque("mao.L", "cabeca", onde=0.42, lado=(0.55, -0.6, -0.58)), Tronco(frente=10)]
resolver("sentada, mão no rosto", cons, inicial=x_s, caixas=assento)

# 5. alcançar um ponto alto com a mão direita, em pé
alto = (-0.22 * H, -0.18 * H, 1.03 * H)
cons, chute = poses.em_pe(S)
resolver("alcançando no alto", cons + [Alvo("mao.R", alto), Olhar(alto)], chute, alvos=[alto])

# 6. pose livre: o salto do Jordan (no ar, pernas abertas, braço esquerdo no alto)
cons = [Alvo("quadril", (0, 0, 0.66 * H)),
        Direcao("braco.L", (0.30, -0.05, 1.0)), Dobra("antebraco.L", 0.0),
        Direcao("braco.R", (-0.9, 0.0, -0.45)), Dobra("antebraco.R", 0.05),
        Direcao("coxa.L", (0.72, -0.05, -0.68)), Dobra("canela.L", 0.12),
        Direcao("coxa.R", (-0.80, 0.05, -0.60)), Dobra("canela.R", 0.18),
        Tronco(lado=-6)]
resolver("pose livre: salto do Jordan", cons)

# ---------------------------------------------------------------- render da grade
W, Hpx = 540, 675
vis_h = 1.45 * H; vis_w = vis_h * W / Hpx; cz = vis_h / 2 - 0.08 * H
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
except OSError:
    font = small = ImageFont.load_default()
grade = Image.new("RGB", (W * 4, Hpx * 3), (30, 30, 34))
for k, (titulo, st, rep, caixas, alvos) in enumerate(cenas):
    for j, cam in enumerate([(0, -6, cz), (6, 0, cz)]):
        R.reset_scene(samples=12, res=(W, Hpx)); R.studio_backdrop(); R.studio_lights()
        R.add_skeleton_visual(st.posed_skeleton(sk))
        for c, s in caixas:
            R.add_box("assento", c, s)
        for a in alvos:
            R.add_marker(a)
        R.camera(cam, (0, 0, cz), ortho_scale=vis_h)
        f = out / "_tmp.png"; R.render(f)
        im = Image.open(f).convert("RGB")
        d = ImageDraw.Draw(im)
        if j == 0:
            d.text((14, 12), titulo, fill=(15, 15, 15), font=font)
            for n, a in enumerate(rep.avisos[:3]):
                d.text((14, 46 + 22 * n), "! " + a, fill=(170, 20, 30), font=small)
        d.text((14, Hpx - 30), "frente" if j == 0 else "lado", fill=(15, 15, 15), font=small)
        col = (k % 2) * 2 + j; row = k // 2
        grade.paste(im, (col * W, row * Hpx))
(out / "_tmp.png").unlink()
grade.save(out / "poses_ossos.png")
print(out / "poses_ossos.png")
