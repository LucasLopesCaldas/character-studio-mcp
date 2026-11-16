"""Receitas de pose: atalhos que só declaram restrições para o solucionador."""
from __future__ import annotations
from .solver import Solver, ApoioChao, ApoioAssento


def em_pe(S: Solver):
    """Em pé, pés no chão na largura do quadril."""
    cons = []
    for lado in ("L", "R"):
        h = S.rest_head[S.idx[f"pe.{lado}"]]
        cons.append(ApoioChao(f"pe.{lado}", ponto=(h[0], h[1])))
    return cons, {}


def altura_assento_ideal(S: Solver) -> float:
    """Altura de assento em que os pés tocam o chão com o joelho perto de 90 graus."""
    k = S.rest_head[S.idx["canela.L"]][2]
    return float(k - S.radius[S.idx["coxa.L"]])


def sentar(S: Solver, altura: float | None = None, centro=(0.0, 0.0)):
    """Sentada num assento. Os pés vão ao chão se alcançarem (restrição mole)."""
    altura = altura_assento_ideal(S) if altura is None else altura
    cons = [ApoioAssento(altura, centro)]
    for lado in ("L", "R"):
        cons.append(ApoioChao(f"pe.{lado}", peso=6.0))
    chute = {"quadril_pos": (centro[0], centro[1], altura + 0.1 * S.H),
             "coxa.L": (-85, 0, 0), "coxa.R": (-85, 0, 0), "canela.L": 85, "canela.R": 85}
    return cons, chute
