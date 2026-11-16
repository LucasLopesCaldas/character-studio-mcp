"""Teste às cegas 2 — condição COM solucionador: três poses declaradas só por restrições do construtor `Pose`."""
import numpy as np

from character_studio.pose import Pose
from character_studio.poses import altura_assento_ideal


def construir(S, corpo_nome):
    H = S.H
    rh = lambda o: S.rest_head[S.idx[o]]

    # ---------------------------------------------------------------- 1. celular (sentada)
    A = altura_assento_ideal(S)
    quadril_sentado = np.array([0.0, 0.0, A + 0.0775 * H])
    peito_sentado = quadril_sentado + (rh("peito") - rh("quadril"))
    celular_mundo = peito_sentado + np.array([-0.03 * H, -0.17 * H, -0.03 * H])
    # pés à frente: canela vertical sob o joelho, coxa horizontal
    pes = {}
    for s in ("L", "R"):
        coxa = S.idx[f"coxa.{s}"]
        y_joelho = (rh(f"coxa.{s}")[1] - rh("quadril")[1]) - np.linalg.norm(S.rest_vec[coxa])
        pes[f"pe.{s}"] = (rh(f"pe.{s}")[0] / H, y_joelho / H)
    celular = (Pose(S).sentar()
               .pes_no_chao(em=pes)
               .tronco(frente=4)
               .colocar("mao.R", ("peito", "frente*0.17 baixo*0.03 direita*0.03"))
               .palma("mao.R", "cima tras*0.8", peso=6.0)
               .tocar("mao.L", "coxa.L", onde=0.6, lado="frente")
               .olhar(tuple(celular_mundo), cabeca=0.9)
               .resolver().x)

    # ---------------------------------------------------------------- 2. chute (contato com a bola)
    r = 0.068 * H
    bola = np.array([-0.06 * H, -0.31 * H, r])
    contato = bola + np.array([0.0, r * np.sqrt(1 - 0.2 ** 2), -0.2 * r])
    chute = (Pose(S).pes_no_chao("pe.L")
             .colocar("pe.R:ponta", tuple(contato))
             .dobra("canela.R", 0.1)
             .tronco(frente=-12)
             .colocar("mao.L", ("peito", "esquerda*0.30 frente*0.06 baixo*0.05"), peso=15.0)
             .colocar("mao.R", ("peito", "direita*0.22 tras*0.10 baixo*0.10"), peso=15.0)
             .olhar(tuple(bola), cabeca=0.9)
             .resolver().x)

    # ---------------------------------------------------------------- 3. agachada (pegando objeto)
    objeto = np.array([-0.05 * H, -0.25 * H, 0.04 * H])
    agachada = (Pose(S).pes_no_chao()
                .colocar("mao.R", tuple(objeto))
                .tocar("mao.L", "canela.L", onde=0.0, lado="frente cima*0.5")
                .dobra("canela.L", 0.6, peso=2.0)
                .dobra("canela.R", 0.6, peso=2.0)
                .tronco(frente=35)
                .olhar(tuple(objeto), cabeca=0.9)
                .resolver().x)

    return {"celular": celular, "chute": chute, "agachada": agachada}
