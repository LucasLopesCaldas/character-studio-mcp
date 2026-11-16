"""Esqueleto paramétrico em pose T.

Metros, Z para cima, personagem olhando para -Y, lado esquerdo em +X.
Cada osso tem um papel (role) e um lado, para que o solucionador de poses
trabalhe por papéis e não por nomes fixos.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Bone:
    name: str
    parent: str | None
    head: np.ndarray
    tail: np.ndarray
    role: str            # raiz, quadril, coluna, pescoco, cabeca, clavicula, braco, antebraco, mao, coxa, canela, pe
    side: str = "C"      # C (centro), L (esquerda, +X), R (direita, -X)

    @property
    def length(self) -> float:
        return float(np.linalg.norm(self.tail - self.head))


@dataclass
class Proportions:
    """Proporções como frações da altura total (padrão: estilo massinha, cabeça ~1/5)."""
    height: float = 1.60
    head: float = 0.20          # altura da cabeça
    neck: float = 0.04
    hip_height: float = 0.50    # altura da articulação do quadril
    hip_width: float = 0.053    # meia distância entre os quadris
    shoulder_width: float = 0.094  # meia largura dos ombros
    upper_arm: float = 0.150
    forearm: float = 0.138
    hand: float = 0.056
    thigh: float = 0.220
    ankle_height: float = 0.053
    foot: float = 0.085


@dataclass
class Skeleton:
    bones: dict[str, Bone] = field(default_factory=dict)

    def add(self, name, parent, head, tail, role, side="C"):
        self.bones[name] = Bone(name, parent, np.asarray(head, float), np.asarray(tail, float), role, side)

    def by_role(self, role, side=None):
        return [b for b in self.bones.values() if b.role == role and (side is None or b.side == side)]

    def children(self, name):
        return [b for b in self.bones.values() if b.parent == name]


def humanoid(p: Proportions | None = None) -> Skeleton:
    """Bípede humanoide em pose T (braços na horizontal, pernas retas)."""
    p = p or Proportions()
    H = p.height
    sk = Skeleton()

    hip_z = p.hip_height * H
    top = H
    head_base = top - p.head * H
    neck_base = head_base - p.neck * H
    pelvis_z = hip_z + 0.025 * H
    torso = neck_base - pelvis_z
    spine_z = pelvis_z + 0.22 * torso
    chest_z = pelvis_z + 0.56 * torso
    shoulder_z = neck_base - 0.022 * H

    sk.add("raiz", None, (0, 0, 0), (0, 0.06 * H, 0), "raiz")
    sk.add("quadril", "raiz", (0, 0, pelvis_z), (0, 0, spine_z), "quadril")
    sk.add("coluna", "quadril", (0, 0, spine_z), (0, 0, chest_z), "coluna")
    sk.add("peito", "coluna", (0, 0, chest_z), (0, 0, neck_base), "coluna")
    sk.add("pescoco", "peito", (0, 0, neck_base), (0, 0, head_base), "pescoco")
    sk.add("cabeca", "pescoco", (0, 0, head_base), (0, 0, top), "cabeca")

    for side, s in (("L", 1.0), ("R", -1.0)):
        sx = p.shoulder_width * H
        x_el = sx + p.upper_arm * H
        x_wr = x_el + p.forearm * H
        x_tip = x_wr + p.hand * H
        sk.add(f"clavicula.{side}", "peito", (s * 0.015 * H, 0, shoulder_z), (s * sx, 0, shoulder_z), "clavicula", side)
        sk.add(f"braco.{side}", f"clavicula.{side}", (s * sx, 0, shoulder_z), (s * x_el, 0, shoulder_z), "braco", side)
        sk.add(f"antebraco.{side}", f"braco.{side}", (s * x_el, 0, shoulder_z), (s * x_wr, 0, shoulder_z), "antebraco", side)
        sk.add(f"mao.{side}", f"antebraco.{side}", (s * x_wr, 0, shoulder_z), (s * x_tip, 0, shoulder_z), "mao", side)

        hx = p.hip_width * H
        knee_z = hip_z - p.thigh * H
        ankle_z = p.ankle_height * H
        sk.add(f"coxa.{side}", "quadril", (s * hx, 0, hip_z), (s * hx, 0, knee_z), "coxa", side)
        sk.add(f"canela.{side}", f"coxa.{side}", (s * hx, 0, knee_z), (s * hx, 0, ankle_z), "canela", side)
        sk.add(f"pe.{side}", f"canela.{side}", (s * hx, 0, ankle_z), (s * hx, -p.foot * H, 0.012 * H), "pe", side)
    return sk


CORPOS = {
    "padrao": Proportions(),
    # cabeçudo, pernas curtas, braços longos
    "baixinho": Proportions(height=1.15, head=0.30, hip_height=0.40, thigh=0.165, upper_arm=0.17, forearm=0.16,
                            shoulder_width=0.11, hip_width=0.07),
}


def corpo(nome: str = "padrao") -> Skeleton:
    """Esqueleto de um corpo pré-definido: 'padrao' ou 'baixinho'."""
    return humanoid(CORPOS[nome])
