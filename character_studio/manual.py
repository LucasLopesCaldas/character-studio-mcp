"""Pose por ângulos escritos à mão (cinemática direta), sem solucionador.

Convenções:
  - Metros; X = esquerda da personagem, Y = costas, Z = cima (ela olha para -Y).
  - O repouso é a pose T: braços na horizontal ao longo de X (palmas para baixo), pernas retas para baixo.
  - Cada osso gira em relação ao repouso, no referencial do osso pai (com todos em repouso, os eixos são os do mundo).
  - Rotação positiva pela regra da mão direita. Exemplos no repouso:
      * ("x", +a) inclina o que aponta para cima em direção à frente; numa coxa (aponta para baixo), +x leva a perna para TRÁS.
      * braço esquerdo (aponta para +X): ("y", +a) desce o braço; ("z", +a) leva o braço para trás; ("x", a) torce o braço.
  - Ossos de bola: lista [(eixo, graus), ...] aplicada em ordem, sempre nos eixos do pai.
  - Dobradiças: um número em graus. "canela.*" (joelho): positivo leva a canela para trás, faixa 2..150.
    "antebraco.*" (cotovelo): positivo fecha o cotovelo (no repouso, o antebraço vai para a frente), faixa 3..148.
  - Lado direito: escreva os ângulos como se fosse o lado esquerdo; o espelhamento é feito aqui.
  - Ossos: quadril, coluna, peito, pescoco, cabeca, clavicula.L/R, braco.L/R, antebraco.L/R, mao.L/R,
    coxa.L/R, canela.L/R, pe.L/R. O osso "quadril" gira o corpo inteiro; `pos_quadril` é a posição do início dele.
"""
from __future__ import annotations
import numpy as np
from scipy.spatial.transform import Rotation as Rot

from .solver import Solver, DEG


def manual(S: Solver, pos_quadril, ossos: dict):
    """Devolve (x, n): o vetor de pose e quantos números foram escritos."""
    x = np.zeros(S.nvar)
    x[:3] = pos_quadril
    n = 3
    for nome in S.names:
        i = S.idx[nome]
        v = ossos.get(nome, 0 if S.hinge[i] else [])
        if S.hinge[i]:
            x[S.slices[i]] = v * DEG; n += 1 if nome in ossos else 0
        else:
            R = Rot.identity()
            for eixo, g in v:
                if nome.endswith(".R") and eixo in "yz":
                    g = -g
                R = Rot.from_euler(eixo, g, degrees=True) * R
                n += 1
            x[S.slices[i]] = R.as_rotvec()
    return x, n
