"""Mede as poses entregues por duas sessões independentes (com e sem solucionador) contra o briefing.

Lê testes/opus_com.py e testes/opus_sem.py dos ramos teste-opus-com e teste-opus-sem (git show), sem misturar os ramos.
Uso: python examples/medir_sessoes.py [pasta_de_saida] [--sem-imagem]
"""
import sys, subprocess, json, importlib.util
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import numpy as np
from character_studio.skeleton import humanoid
from character_studio.solver import (Solver, Alvo, Toque, ApoioChao, ApoioAssento, Direcao, Olhar, Palma, Dobra, Tronco,
                                     SemEquilibrio)
from character_studio.pose import vetor
from character_studio.medicao import medir
from character_studio import poses as receitas

out = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "out"); out.mkdir(parents=True, exist_ok=True)
sk = humanoid(); S = Solver(sk); H = S.H
r = 0.068 * H


def carregar(ramo, arquivo):
    src = subprocess.run(["git", "show", f"origin/{ramo}:testes/{arquivo}"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    f = out / f"_{arquivo}"; f.write_text(src)
    spec = importlib.util.spec_from_file_location(arquivo[:-3], f); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    x = m.construir(S); f.unlink()
    return x, src


def dobra(osso, graus):
    lo, hi = S.spec[S.idx[osso]]["faixa"]
    return Dobra(osso, (graus - lo) / (hi - lo))


def intencoes(nome, st):
    """As réguas de cada pose, tiradas do briefing (as que dependem do corpo são calculadas no estado medido)."""
    pe = S.rest_head[S.idx["pe.L"]]
    if nome == "celular":
        alt = receitas.altura_assento_ideal(S)
        pk = S.idx["peito"]
        cel = st.head[pk] + st.D[pk] @ (vetor("frente*0.17 baixo*0.03 direita*0.03") * H)
        return [ApoioAssento(alt), ApoioChao("pe.L"), ApoioChao("pe.R"), Tronco(0, 0, 0),
                Alvo("mao.R", tuple(vetor("frente*0.17 baixo*0.03 direita*0.03") * H), ref="peito"),
                Palma("mao.R", tuple(vetor("cima tras*0.8"))), Toque("mao.L", "coxa.L", 0.6, (0, -1, 0)), Olhar(tuple(cel))]
    if nome == "chute_contato":
        b = (-0.06 * H, -0.31 * H, r)
        return [ApoioChao("pe.L", ponto=(pe[0], pe[1])), dobra("canela.L", 23),
                Alvo("pe.R:ponta", (b[0], b[1] + 0.85 * r, 0.8 * r)), Direcao("pe.R", tuple(vetor("frente baixo*0.45"))),
                dobra("canela.R", 17), Tronco(-12, 0, 12),
                Direcao("braco.L", tuple(vetor("fora frente*0.7 baixo*0.25", "L"))), dobra("antebraco.L", 32),
                Direcao("braco.R", tuple(vetor("fora*0.7 tras*0.7 baixo*0.6", "R"))), dobra("antebraco.R", 39), Olhar(b)]
    if nome == "chute_armado":
        b = (-0.05 * H, -0.30 * H, r)
        return [SemEquilibrio(), ApoioChao("pe.L", ponto=(0.05 * H, -0.20 * H)), dobra("canela.L", 24),
                Alvo("quadril", (0, 0, 0.46 * H)), Direcao("coxa.R", tuple(vetor("tras*0.6 baixo", "R"))), dobra("canela.R", 94),
                Tronco(18, 0, -20),
                Direcao("braco.L", tuple(vetor("cima fora*0.8 tras*0.2", "L"))), dobra("antebraco.L", 18),
                Direcao("braco.R", tuple(vetor("tras*0.8 baixo*0.7 fora*0.2", "R"))), dobra("antebraco.R", 75), Olhar(b)]


entregas = {"COM": carregar("teste-opus-com", "opus_com.py"), "SEM": carregar("teste-opus-sem", "opus_sem.py")}
resultado = {}
for nome in ("celular", "chute_contato", "chute_armado"):
    ms = {}
    for k, (xs, _) in entregas.items():
        st = S.fk(np.asarray(xs[nome], float))
        ms[k] = medir(S, st, intencoes(nome, st))
    resultado[nome] = ms
    print(f"\n== {nome}\n{'régua':28s}{'COM':>10s}{'SEM':>10s}")
    for regua in ms["COM"]:
        print(f"{regua:28s}{ms['COM'][regua]:10.1f}{ms['SEM'][regua]:10.1f}")
(out / "medicao_sessoes.json").write_text(json.dumps(resultado, indent=1, ensure_ascii=False))

if "--sem-imagem" not in sys.argv:
    from PIL import Image, ImageDraw, ImageFont
    from character_studio import render as R
    W, Hpx = 540, 675
    vis_h = 1.3 * H; cz = vis_h / 2 - 0.08 * H
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
    alt = receitas.altura_assento_ideal(S)
    cena = {"celular": ([((0, 0.03, alt / 2), (0.42, 0.40, alt))], None),
            "chute_contato": ([], (-0.06 * H, -0.31 * H, r)), "chute_armado": ([], (-0.05 * H, -0.30 * H, r))}
    grade = Image.new("RGB", (W * 4, Hpx * 3))
    for row, nome in enumerate(cena):
        caixas, bola = cena[nome]
        for j, k in enumerate(("COM", "SEM")):
            st = S.fk(np.asarray(entregas[k][0][nome], float))
            for v, cam in enumerate([(0, -6, cz), (-6, -0.15, cz)]):
                R.reset_scene(samples=12, res=(W, Hpx)); R.studio_backdrop(); R.studio_lights()
                R.add_skeleton_visual(st.posed_skeleton(sk))
                for c, s in caixas:
                    R.add_box("assento", c, s)
                if bola:
                    R.add_marker(bola, radius=r, hexcolor="#f2f2f2")
                R.camera(cam, (0, -0.15, cz), ortho_scale=vis_h)
                f = out / "_tmp.png"; R.render(f)
                im = Image.open(f).convert("RGB"); d = ImageDraw.Draw(im)
                if v == 0:
                    d.text((12, 10), f"Opus 5.5 {k} solucionador", fill=(15, 15, 15), font=font)
                    d.text((12, 40), nome, fill=(15, 15, 15), font=small)
                d.text((12, Hpx - 28), "frente" if v == 0 else "lado", fill=(15, 15, 15), font=small)
                grade.paste(im, ((j * 2 + v) * W, row * Hpx))
    (out / "_tmp.png").unlink()
    grade.save(out / "medicao_sessoes.png")
    print(out / "medicao_sessoes.png")
