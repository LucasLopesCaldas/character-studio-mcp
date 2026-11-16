"""Pose a partir de uma imagem de referência: perna armada para trás, antes do chute.

Uso: python examples/pose_chute_armado.py [pasta_de_saida]
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
r = 0.068 * H
pe_y = -0.20                                    # pé de apoio plantado à frente do corpo (em alturas)
bola = (-0.05 * H, (pe_y - 0.10) * H, r)        # bola no chão, ao lado e à frente do pé de apoio

p = (Pose(S)
     .em_movimento()                                             # chegando na bola: sem equilíbrio estático
     .pes_no_chao("pe.L", em={"pe.L": (0.05, pe_y)})             # pé esquerdo plantado à frente
     .colocar("quadril", (0, 0, 0.46 * H))                       # quadril atrás do pé de apoio, um pouco baixo
     .dobra("canela.L", 0.15)                                    # joelho de apoio pouco dobrado
     .apontar("coxa.R", "tras*0.6 baixo", dobra=0.62)            # perna direita armada para trás, joelho bem dobrado
     .tronco(frente=18, giro=-20)                                # tronco sobre a bola, ombro direito para trás
     .apontar("braco.L", "cima fora*0.8 tras*0.2", dobra=0.10)   # braço esquerdo alto e aberto
     .apontar("braco.R", "tras*0.8 baixo*0.7 fora*0.2", dobra=0.50)   # braço direito para trás, cotovelo dobrado
     .olhar(bola)
     .resolver())
print(p.descrever())
st = p.st

W, Hpx = 720, 900
vis_h = 1.3 * H; cz = vis_h / 2 - 0.08 * H
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
vistas = [("lado (como na referência)", (-6, -0.15, cz), vis_h), ("frente", (0, -6, cz), vis_h), ("três quartos", (-2.6, -2.9, 1.3), None)]
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
img.save(out / "pose_chute_armado.png")
print(out / "pose_chute_armado.png")
