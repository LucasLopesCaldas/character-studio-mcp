"""Teste às cegas: três poses declaradas só com o construtor `Pose` (condição COM solucionador)."""
from __future__ import annotations
import numpy as np

from character_studio.pose import Pose
from character_studio import poses

# faixas das dobradiças (graus): joelho 2..150, cotovelo 3..148 -> fração de dobra 0..1
def _joelho(graus):
    return (graus - 2.0) / 148.0


def _cotovelo(graus):
    return (graus - 3.0) / 145.0


def construir(S):
    H = S.H
    i = S.idx

    # ---------------------------------------------------------------- 1. celular
    altura = poses.altura_assento_ideal(S)
    # onde a mão direita deve ficar (estimativa para o olhar): peito em repouso, baixado junto com o quadril
    dz = (altura + 0.0775 * H) - S.rest_head[i["quadril"]][2]
    peito = S.rest_head[i["peito"]] + np.array([0, 0, dz])
    mao_r = peito + np.array([-0.03, -0.17, -0.03]) * H
    celular = (Pose(S)
               .sentar(altura, centro=(0.0, 0.0))
               .tronco(0, 0, 0)
               .colocar("mao.R", ("peito", "frente*0.17 baixo*0.03 direita*0.03"))
               .palma("mao.R", "cima tras*0.8")
               .tocar("mao.L", "coxa.L", 0.6, "frente")
               .olhar(tuple(mao_r), cabeca=0.6)
               .resolver().x)

    # ---------------------------------------------------------------- 2. chute_contato
    r = 0.068 * H
    bola = np.array([-0.06 * H, -0.31 * H, r])
    chute_contato = (Pose(S)
                     .pes_no_chao("pe.L", em={"pe.L": (0.053, 0.0)})
                     .dobra("canela.L", _joelho(23))
                     .colocar("pe.R:ponta", (bola[0], bola[1] + 0.85 * r, 0.8 * r))
                     .apontar("pe.R", "frente baixo*0.45")
                     .dobra("canela.R", _joelho(17))
                     .tronco(frente=-12, giro=12)
                     .apontar("braco.L", "fora frente*0.7 baixo*0.25", dobra=_cotovelo(32))
                     .apontar("braco.R", "fora*0.7 tras*0.7 baixo*0.6", dobra=_cotovelo(39))
                     .olhar(tuple(bola), cabeca=0.6)
                     .resolver().x)

    # ---------------------------------------------------------------- 3. chute_armado
    bola2 = np.array([-0.05 * H, -0.30 * H, r])
    chute_armado = (Pose(S)
                    .em_movimento()
                    .pes_no_chao("pe.L", em={"pe.L": (0.05, -0.20)})
                    .dobra("canela.L", _joelho(24))
                    .colocar("quadril", (0.0, 0.0, 0.46 * H))
                    .apontar("coxa.R", "tras*0.6 baixo", dobra=_joelho(94))
                    .tronco(frente=18, giro=-20)
                    .apontar("braco.L", "cima fora*0.8 tras*0.2", dobra=_cotovelo(18))
                    .apontar("braco.R", "tras*0.8 baixo*0.7 fora*0.2", dobra=_cotovelo(75))
                    .olhar(tuple(bola2), cabeca=0.6)
                    .resolver().x)

    return {"celular": celular, "chute_contato": chute_contato, "chute_armado": chute_armado}


if __name__ == "__main__":
    from character_studio.skeleton import humanoid
    from character_studio.solver import Solver
    S = Solver(humanoid())
    out = construir(S)
    for k, v in out.items():
        print(k, v.shape, S.nvar)
