"""Pose livre: chutando uma bola de futebol (só ossos; frente, lado e três quartos).

Uso: python examples/pose_chute.py [pasta_de_saida]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from character_studio.skeleton import humanoid
from character_studio.solver import Solver, Direcao, Olhar, Dobra, Tronco, ApoioChao, unit
from character_studio import render as R

out = Path(sys.argv[1] if len(sys.argv) > 1 else "out"); out.mkdir(parents=True, exist_ok=True)
sk = humanoid(); S = Solver(sk); H = S.H
raio_bola = 0.068 * H
pe_apoio = S.rest_head[S.idx["pe.L"]]

cons = [
    ApoioChao("pe.L", ponto=(pe_apoio[0], pe_apoio[1])),      # só o pé esquerdo no chão
    Dobra("canela.L", 0.12),                                  # joelho de apoio levemente dobrado
    Direcao("coxa.R", (-0.10, -0.80, -0.60)), Dobra("canela.R", 0.10),   # perna direita à frente, quase esticada
    Direcao("pe.R", (0.0, -0.85, -0.52)),                     # peito do pé esticado
    Tronco(frente=-10, giro=14),                              # tronco para trás, girando com o chute
    Direcao("braco.L", (0.70, -0.55, -0.20)), Dobra("antebraco.L", 0.22),  # braço oposto à frente
    Direcao("braco.R", (-0.60, 0.55, -0.55)), Dobra("antebraco.R", 0.25),  # braço do lado do chute para trás
]
x, st, rep = S.solve(cons)
i = S.idx["pe.R"]
bola = st.tail[i] + unit(st.tail[i] - st.head[i]) * raio_bola * 0.9 + np.array([0, -0.01, 0.01])
x, st, rep = S.solve(cons + [Olhar(tuple(bola))], inicial=x)
i = S.idx["pe.R"]
bola = st.tail[i] + unit(st.tail[i] - st.head[i]) * raio_bola * 0.9 + np.array([0, -0.01, 0.01])
print(rep)
print("centro de massa:", S.com(st).round(3), " pé de apoio:", st.head[S.idx["pe.L"]].round(3))

W, Hpx = 720, 900
vis_h = 1.3 * H; cz = vis_h / 2 - 0.08 * H
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
vistas = [("frente", (0, -6, cz), vis_h), ("lado", (-6, -0.15, cz), vis_h), ("três quartos", (-2.3, -3.2, 1.3), None)]
img = Image.new("RGB", (W * 3, Hpx))
for k, (nome, cam, ortho) in enumerate(vistas):
    R.reset_scene(samples=24, res=(W, Hpx)); R.studio_backdrop(); R.studio_lights()
    R.add_skeleton_visual(st.posed_skeleton(sk))
    R.add_marker(bola, radius=raio_bola, hexcolor="#f2f2f2")
    R.camera(cam, (0, -0.15, cz if ortho else 0.5 * H), ortho_scale=ortho, lens=50)
    f = out / "_tmp.png"; R.render(f)
    im = Image.open(f).convert("RGB")
    ImageDraw.Draw(im).text((16, 14), nome, fill=(15, 15, 15), font=font)
    img.paste(im, (k * W, 0))
(out / "_tmp.png").unlink()
img.save(out / "pose_chute.png")
print(out / "pose_chute.png")
