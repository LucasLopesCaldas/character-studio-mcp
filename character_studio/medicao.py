"""Réguas para medir uma pose contra uma lista de intenções (restrições), venha ela de onde vier."""
from __future__ import annotations
import numpy as np
from scipy.spatial.transform import Rotation as Rot

from .solver import (Alvo, Toque, ApoioChao, ApoioAssento, Direcao, Olhar, Palma, Dobra, Tronco, SemEquilibrio,
                     rodrigues, DEG)


def medir(S, st, cons):
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
