"""Medição: com solucionador x sem solucionador.

As mesmas três poses feitas de dois jeitos, uma tentativa cada, sem retoque:
  - COM: restrições declaradas no construtor Pose (o solucionador calcula as articulações);
  - SEM: ângulos de cada osso escritos à mão (cinemática direta), como seria sem a ferramenta.
As duas são medidas pelas mesmas réguas: a lista de intenções da pose (contatos, direções, tronco, olhar)
mais o que ninguém pediu mas tem de valer (limites articulares, ossos se atravessando, equilíbrio).

Uso: python examples/comparar_solver.py [pasta_de_saida] [--sem-imagem] [--outro-corpo]
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.spatial.transform import Rotation as Rot
from character_studio.skeleton import humanoid
from character_studio.solver import (Solver, Alvo, Toque, ApoioChao, ApoioAssento, Direcao, Olhar, Palma, Dobra,
                                     Tronco, SemEquilibrio, rodrigues, DEG)
from character_studio.pose import Pose
from character_studio import poses as receitas
from character_studio.manual import manual as _manual

out = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "out"); out.mkdir(parents=True, exist_ok=True)
# --outro-corpo: repete a medição num personagem de proporções bem diferentes (cabeçudo, pernas curtas, braços longos),
# com as MESMAS restrições e os MESMOS ângulos à mão, para medir o quanto cada jeito se adapta ao corpo.
if "--outro-corpo" in sys.argv:
    from character_studio.skeleton import Proportions
    sk = humanoid(Proportions(height=1.15, head=0.30, hip_height=0.40, thigh=0.165, upper_arm=0.17, forearm=0.16,
                              shoulder_width=0.11, hip_width=0.07))
else:
    sk = humanoid()
S = Solver(sk); H = S.H
r = 0.068 * H


# ------------------------------------------------------------------ "sem solucionador": ângulos à mão
def manual(pos_quadril, ossos):
    return _manual(S, pos_quadril, ossos)


# ------------------------------------------------------------------ réguas
def medir(st, cons):
    contato, direcao, tronco = [], [], []
    parts = []
    S._constraint_residuals(st, cons, parts)
    for c, e in parts:
        if isinstance(c, (Alvo, Toque)):
            contato.append(np.linalg.norm(e) * 100)
        elif isinstance(c, (ApoioChao, ApoioAssento)):
            contato.append(np.abs(e[:2] if isinstance(c, ApoioChao) else e[:1]).max() * 100)
        elif isinstance(c, (Direcao, Olhar, Palma)):
            direcao.append(2 * np.arcsin(min(1, np.linalg.norm(e) / 2)) / DEG)
        elif isinstance(c, Dobra):
            direcao.append(abs(e[0]) / DEG)
        elif isinstance(c, Tronco):
            alvo = rodrigues(np.array([0, 0, c.giro * DEG]))[0] @ rodrigues(np.array([c.frente * DEG, c.lado * DEG, 0]))[0]
            tronco.append(np.linalg.norm(Rot.from_matrix(alvo.T @ st.D[S.idx["peito"]]).as_rotvec()) / DEG)
    lim = np.abs(S._limits(st)); col = S.collision(st)
    m = {"contato_max_cm": max(contato, default=0.0), "direcao_media_graus": float(np.mean(direcao)) if direcao else 0.0,
         "direcao_max_graus": max(direcao, default=0.0), "tronco_graus": max(tronco, default=0.0),
         "limite_articular_graus": float(lim.max() / DEG) if len(lim) else 0.0,
         "atravessa_cm": float(col.max() * 100) if len(col) else 0.0}
    feet = [c for c in cons if isinstance(c, ApoioChao)]
    if feet and not any(isinstance(c, (ApoioAssento, SemEquilibrio)) for c in cons):
        pts = []
        for c in feet:
            i = S.idx[c.pe]; pts += [st.head[i][:2], st.tail[i][:2]]
        m["equilibrio_cm"] = float(np.linalg.norm(S.com(st)[:2] - np.mean(pts, axis=0)) * 100)
    return m


casos = []

# ================================================================== 1. sentada com o celular
alt = receitas.altura_assento_ideal(S)
t = time.time()
com = (Pose(S).sentar()
       .colocar("mao.R", ("peito", "frente*0.17 baixo*0.03 direita*0.03")).palma("mao.R", "cima tras*0.8")
       .tocar("mao.L", "coxa.L", 0.6, "frente")
       .resolver())
cel = tuple(S.point(com.st, "mao.R"))
com = (Pose(S).sentar()
       .colocar("mao.R", ("peito", "frente*0.17 baixo*0.03 direita*0.03")).palma("mao.R", "cima tras*0.8")
       .tocar("mao.L", "coxa.L", 0.6, "frente").olhar(cel)
       .resolver(inicial=com.x))
t_com = time.time() - t
x_sem, n_sem = manual((0, 0, alt + 0.0775 * H), {
    "coxa.L": [("x", -88)], "coxa.R": [("x", -88)], "canela.L": 86, "canela.R": 86, "pe.L": [("x", 2)], "pe.R": [("x", 2)],
    "coluna": [("x", 4)], "peito": [("x", 4)], "pescoco": [("x", 12)], "cabeca": [("x", 22)],
    "braco.R": [("y", 80), ("x", -15), ("z", -25)], "antebraco.R": 95, "mao.R": [("x", -80)],
    "braco.L": [("y", 78), ("x", -25)], "antebraco.L": 60, "mao.L": [("x", 70)]})
casos.append(("sentada com o celular", com, x_sem, n_sem, 5, t_com, [((0, 0.03, alt / 2), (0.42, 0.40, alt))], [], None))

# ================================================================== 2. chute, instante do contato
bola = (-0.06 * H, -0.31 * H, r)
t = time.time()
com = (Pose(S).pes_no_chao("pe.L").dobra("canela.L", 0.14)
       .colocar("pe.R:ponta", (bola[0], bola[1] + 0.85 * r, 0.8 * r)).apontar("pe.R", "frente baixo*0.45").dobra("canela.R", 0.10)
       .tronco(frente=-12, giro=12)
       .apontar("braco.L", "fora frente*0.7 baixo*0.25", dobra=0.20)
       .apontar("braco.R", "fora*0.7 tras*0.7 baixo*0.6", dobra=0.25)
       .olhar(bola).resolver())
t_com = time.time() - t
x_sem, n_sem = manual((0.031 * H, -0.0125 * H, 0.5125 * H), {
    "quadril": [("x", -5), ("z", 8)],
    "coxa.L": [("x", -5)], "canela.L": 20, "pe.L": [("x", -10), ("z", -8)],
    "coxa.R": [("x", -28)], "canela.R": 15, "pe.R": [("x", 25)],
    "coluna": [("x", -3), ("z", 2)], "peito": [("x", -3), ("z", 2)], "pescoco": [("x", 15)], "cabeca": [("x", 25)],
    "braco.L": [("z", -35), ("y", 12)], "antebraco.L": 30,
    "braco.R": [("z", 45), ("y", 31)], "antebraco.R": 38})
casos.append(("chute: contato com a bola", com, x_sem, n_sem, 9, t_com, [], [], bola))

# ================================================================== 3. chute armado (da referência)
pe_y = -0.20
bola3 = (-0.05 * H, (pe_y - 0.10) * H, r)
t = time.time()
com = (Pose(S).em_movimento().pes_no_chao("pe.L", em={"pe.L": (0.05, pe_y)})
       .colocar("quadril", (0, 0, 0.46 * H)).dobra("canela.L", 0.15)
       .apontar("coxa.R", "tras*0.6 baixo", dobra=0.62)
       .tronco(frente=18, giro=-20)
       .apontar("braco.L", "cima fora*0.8 tras*0.2", dobra=0.10)
       .apontar("braco.R", "tras*0.8 baixo*0.7 fora*0.2", dobra=0.50)
       .olhar(bola3).resolver())
t_com = time.time() - t
x_sem, n_sem = manual((0, 0, 0.46 * H), {
    "quadril": [("x", 8), ("z", -10)],
    "coxa.L": [("x", -48)], "canela.L": 22, "pe.L": [("x", 18), ("z", 10)],
    "coxa.R": [("x", 22)], "canela.R": 95,
    "coluna": [("x", 5), ("z", -5)], "peito": [("x", 5), ("z", -5)], "pescoco": [("x", 12)], "cabeca": [("x", 20)],
    "braco.L": [("y", -50), ("z", 10)], "antebraco.L": 15,
    "braco.R": [("y", 45), ("z", 75)], "antebraco.R": 75})
casos.append(("chute armado (referência)", com, x_sem, n_sem, 9, t_com, [], [], bola3))

# ------------------------------------------------------------------ tabela
resultado = []
for titulo, com, x_sem, n_sem, linhas, t_com, *_ in casos:
    st_sem = S.fk(x_sem)
    a, b = medir(com.st, com.cons), medir(st_sem, com.cons)
    resultado.append({"pose": titulo, "com": a, "sem": b, "numeros_sem": n_sem, "linhas_com": linhas, "tempo_solver_s": round(t_com, 1)})
    print(f"\n== {titulo}   (solucionador: {t_com:.1f} s; à mão: {n_sem} números)")
    print(f"{'régua':28s}{'COM':>10s}{'SEM':>10s}")
    for k in a:
        print(f"{k:28s}{a[k]:10.1f}{b[k]:10.1f}")
(out / ("comparacao_solver_outro_corpo.json" if "--outro-corpo" in sys.argv else "comparacao_solver.json")).write_text(json.dumps(resultado, indent=1, ensure_ascii=False))

# ------------------------------------------------------------------ imagem
if "--sem-imagem" not in sys.argv:
    from PIL import Image, ImageDraw, ImageFont
    from character_studio import render as R
    W, Hpx = 540, 675
    vis_h = 1.3 * H; cz = vis_h / 2 - 0.08 * H
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
    grade = Image.new("RGB", (W * 4, Hpx * len(casos)))
    for row, (titulo, com, x_sem, n_sem, linhas, t_com, caixas, alvos, bola_) in enumerate(casos):
        for j, (rot, st) in enumerate([("COM solucionador", com.st), ("SEM (ângulos à mão)", S.fk(x_sem))]):
            for v, cam in enumerate([(0, -6, cz), (-6, -0.15, cz)]):
                R.reset_scene(samples=12, res=(W, Hpx)); R.studio_backdrop(); R.studio_lights()
                R.add_skeleton_visual(st.posed_skeleton(sk))
                for c, s in caixas:
                    R.add_box("assento", c, s)
                if bola_:
                    R.add_marker(bola_, radius=r, hexcolor="#f2f2f2")
                R.camera(cam, (0, -0.15, cz), ortho_scale=vis_h)
                f = out / "_tmp.png"; R.render(f)
                im = Image.open(f).convert("RGB"); d = ImageDraw.Draw(im)
                if v == 0:
                    d.text((12, 10), rot, fill=(15, 15, 15), font=font)
                    d.text((12, 40), titulo, fill=(15, 15, 15), font=small)
                d.text((12, Hpx - 28), "frente" if v == 0 else "lado", fill=(15, 15, 15), font=small)
                grade.paste(im, ((j * 2 + v) * W, row * Hpx))
    (out / "_tmp.png").unlink()
    grade.save(out / "comparacao_solver.png")
    print(out / "comparacao_solver.png")
