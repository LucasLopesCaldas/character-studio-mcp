"""Pose livre: chutando uma bola de futebol, no instante do contato (só ossos; frente, lado e três quartos).

Uso: python examples/pose_chute.py [pasta_de_saida]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont
from character_studio.skeleton import humanoid
from character_studio.solver import Solver
from character_studio.pose import Pose
from character_studio import render as R

out = Path(sys.argv[1] if len(sys.argv) > 1 else "out"); out.mkdir(parents=True, exist_ok=True)
sk = humanoid(); S = Solver(sk); H = S.H
r = 0.068 * H                                   # raio da bola
bola = (-0.06 * H, -0.31 * H, r)                # bola no chão, à frente e do lado do pé que chuta

p = (Pose(S)
     .pes_no_chao("pe.L")                                    # só o pé esquerdo apoia
     .dobra("canela.L", 0.14)                                # joelho de apoio levemente dobrado
     .colocar("pe.R:ponta", (bola[0], bola[1] + 0.85 * r, 0.8 * r))   # ponta do pé direito encosta atrás da bola
     .apontar("pe.R", "frente baixo*0.45")                   # peito do pé esticado
     .dobra("canela.R", 0.10)                                # perna do chute quase esticada
     .tronco(frente=-12, giro=12)                            # tronco para trás, girando com o chute
     .apontar("braco.L", "fora frente*0.7 baixo*0.25", dobra=0.20)    # braço oposto abre à frente
     .apontar("braco.R", "fora*0.7 tras*0.7 baixo*0.6", dobra=0.25)   # braço do lado do chute vai para trás
     .olhar(bola)
     .resolver())
print(p.descrever())
st = p.st

W, Hpx = 720, 900
vis_h = 1.3 * H; cz = vis_h / 2 - 0.08 * H
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
vistas = [("frente", (0, -6, cz), vis_h), ("lado", (-6, -0.15, cz), vis_h), ("três quartos", (-2.3, -3.2, 1.3), None)]
img = Image.new("RGB", (W * 3, Hpx))
for k, (nome, cam, ortho) in enumerate(vistas):
    R.reset_scene(samples=24, res=(W, Hpx)); R.studio_backdrop(); R.studio_lights()
    R.add_skeleton_visual(st.posed_skeleton(sk))
    R.add_marker(bola, radius=r, hexcolor="#f2f2f2")
    R.camera(cam, (0, -0.15, cz if ortho else 0.5 * H), ortho_scale=ortho, lens=50)
    f = out / "_tmp.png"; R.render(f)
    im = Image.open(f).convert("RGB")
    ImageDraw.Draw(im).text((16, 14), nome, fill=(15, 15, 15), font=font)
    img.paste(im, (k * W, 0))
(out / "_tmp.png").unlink()
img.save(out / "pose_chute.png")
print(out / "pose_chute.png")
