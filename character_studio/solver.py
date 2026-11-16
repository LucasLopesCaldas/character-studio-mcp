"""Solucionador de poses de corpo inteiro por restrições.

A pose é um problema de mínimos quadrados: achar a posição do quadril e as rotações
de todas as articulações que cumprem as restrições pedidas (apoios, alvos, direções,
olhar) respeitando limites articulares, sem o corpo se atravessar, em equilíbrio e
com o menor "desconforto". Quem usa só declara restrições; nunca mexe em ângulos.

Eixos: X = esquerda da personagem, Y = costas, Z = cima (ela olha para -Y).
Rotações locais são vetores de rotação relativos ao repouso (pose T), no referencial do pai.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from scipy.optimize import least_squares

from .skeleton import Skeleton

DEG = np.pi / 180.0


def rodrigues(v):
    """Vetores de rotação (n,3) -> matrizes (n,3,3)."""
    v = np.atleast_2d(v)
    th = np.linalg.norm(v, axis=1)
    k = v / np.maximum(th, 1e-12)[:, None]
    K = np.zeros((len(v), 3, 3))
    K[:, 0, 1], K[:, 0, 2] = -k[:, 2], k[:, 1]
    K[:, 1, 0], K[:, 1, 2] = k[:, 2], -k[:, 0]
    K[:, 2, 0], K[:, 2, 1] = -k[:, 1], k[:, 0]
    s, c = np.sin(th)[:, None, None], np.cos(th)[:, None, None]
    return np.eye(3)[None] + s * K + (1 - c) * (K @ K)


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


# ------------------------------------------------------------------ modelo articular
# Definido para o lado esquerdo; o direito espelha (componentes Y e Z do vetor de rotação trocam de sinal).
#   tipo "bola": 3 graus de liberdade; "dobradica": 1 grau em torno de `eixo`.
#   conforto: rotação preferida; peso: quanto custa sair dela.
#   caixa: limites (graus) por componente do vetor de rotação; cone: (direção central, abertura máx.) para o osso;
#   torcao: limites (graus) da rotação em torno do próprio osso.
JOINTS = {
    "quadril":   dict(tipo="bola", conforto=(0, 0, 0), peso=3.0),
    "coluna":    dict(tipo="bola", conforto=(0, 0, 0), peso=2.5, caixa=((-15, 32), (-18, 18), (-22, 22))),
    "pescoco":   dict(tipo="bola", conforto=(0, 0, 0), peso=1.2, caixa=((-20, 28), (-12, 12), (-30, 30))),
    "cabeca":    dict(tipo="bola", conforto=(0, 0, 0), peso=0.8, caixa=((-25, 30), (-15, 15), (-40, 40))),
    "clavicula": dict(tipo="bola", conforto=(0, 0, 0), peso=3.0, caixa=((-3, 3), (-18, 10), (-15, 15))),
    "braco":     dict(tipo="bola", conforto=(0, 74, 0), peso=0.30, cone=((0.45, -0.45, -0.77), 120), torcao=(-85, 85)),
    "antebraco": dict(tipo="dobradica", eixo=(0, 0, -1), faixa=(3, 148), conforto=18, peso=0.25),
    "mao":       dict(tipo="bola", conforto=(0, 0, 0), peso=0.2, caixa=((-80, 80), (-55, 55), (-25, 25))),
    "coxa":      dict(tipo="bola", conforto=(0, 0, 0), peso=0.18, cone=((0, -0.5, -0.87), 105), torcao=(-35, 35)),
    "canela":    dict(tipo="dobradica", eixo=(1, 0, 0), faixa=(2, 150), conforto=4, peso=0.25),
    "pe":        dict(tipo="bola", conforto=(0, 0, 0), peso=0.6, caixa=((-40, 35), (-15, 15), (-20, 20))),
}
MIRROR = np.array([1.0, -1.0, -1.0])
# raio da cápsula de colisão de cada osso e fração da massa do corpo, por papel
RADIUS = {"quadril": 0.062, "coluna": 0.062, "pescoco": 0.028, "cabeca": 0.088, "clavicula": 0.03,
          "braco": 0.026, "antebraco": 0.023, "mao": 0.022, "coxa": 0.045, "canela": 0.036, "pe": 0.028}
MASS = {"quadril": 0.14, "coluna": 0.16, "pescoco": 0.02, "cabeca": 0.12, "clavicula": 0.01,
        "braco": 0.03, "antebraco": 0.02, "mao": 0.008, "coxa": 0.10, "canela": 0.05, "pe": 0.015}


# ------------------------------------------------------------------ restrições

@dataclass
class Alvo:
    """Um ponto do corpo num ponto do espaço. parte: 'mao.L', 'pe.R', 'quadril', 'cabeca'..."""
    parte: str
    ponto: tuple
    peso: float = 30.0
    eixos: str = "xyz"


@dataclass
class Direcao:
    """Um osso apontando numa direção (ex.: 'braco.L' para cima)."""
    osso: str
    direcao: tuple
    peso: float = 8.0


@dataclass
class Palma:
    """A palma da mão virada para uma direção."""
    mao: str
    normal: tuple
    peso: float = 4.0


@dataclass
class Olhar:
    """Olhar para um ponto. `cabeca` = fração do giro feita pela cabeça (o resto fica com os olhos)."""
    ponto: tuple
    peso: float = 6.0
    cabeca: float = 0.6


@dataclass
class Toque:
    """Uma parte encosta na superfície de outro osso (ex.: mão na coxa, mão no queixo).

    onde = fração ao longo do osso (0 = início, 1 = fim); lado = direção, no referencial de
    repouso da personagem, do ponto da superfície em relação ao eixo do osso (ex.: (0,-1,0) = frente).
    """
    parte: str
    osso: str
    onde: float = 0.5
    lado: tuple = (0, -1, 0)
    peso: float = 25.0


@dataclass
class Dobra:
    """Quanto um cotovelo ou joelho está dobrado: 0 = esticado, 1 = todo dobrado."""
    osso: str
    quanto: float
    peso: float = 6.0


@dataclass
class Tronco:
    """Inclinação do tronco em graus: frente (+), lado esquerdo (+), giro à esquerda (+)."""
    frente: float = 0.0
    lado: float = 0.0
    giro: float = 0.0
    peso: float = 5.0


@dataclass
class ApoioChao:
    """Pé chapado no chão. ponto=(x, y) fixa onde; sem ponto, o solucionador escolhe."""
    pe: str
    ponto: tuple | None = None
    altura: float = 0.0
    peso: float = 40.0


@dataclass
class ApoioAssento:
    """Quadril apoiado num assento de dada altura; centro=(x, y) e frente = para onde ela olha."""
    altura: float
    centro: tuple = (0.0, 0.0)
    profundidade: float = 0.40
    peso: float = 40.0


@dataclass
class Fixar:
    """Prende a rotação de um osso (graus, vetor de rotação local). Usado por correções e varreduras."""
    osso: str
    rotacao: tuple
    peso: float = 60.0


@dataclass
class Relatorio:
    erros: dict = field(default_factory=dict)
    avisos: list = field(default_factory=list)
    custo: float = 0.0

    def __str__(self):
        linhas = [f"  {k}: {v}" for k, v in self.erros.items()] + [f"  AVISO: {a}" for a in self.avisos]
        return "\n".join(linhas)


@dataclass
class PoseState:
    names: list
    head: np.ndarray    # (n,3) início de cada osso
    tail: np.ndarray    # (n,3) fim de cada osso
    D: np.ndarray       # (n,3,3) rotação global em relação ao repouso
    local: np.ndarray   # (n,3) vetor de rotação local

    def posed_skeleton(self, sk: Skeleton) -> Skeleton:
        out = Skeleton()
        for i, n in enumerate(self.names):
            b = sk.bones[n]
            out.add(n, b.parent, self.head[i], self.tail[i], b.role, b.side)
        return out


class Solver:
    def __init__(self, sk: Skeleton):
        self.sk = sk
        self.names = [n for n in sk.bones if sk.bones[n].role != "raiz"]
        self.idx = {n: i for i, n in enumerate(self.names)}
        n = len(self.names)
        B = [sk.bones[x] for x in self.names]
        self.H = max(b.tail[2] for b in B)
        self.parent = np.array([self.idx.get(b.parent, -1) for b in B])
        self.rest_head = np.array([b.head for b in B])
        self.rest_vec = np.array([b.tail - b.head for b in B])
        self.rest_dir = self.rest_vec / np.linalg.norm(self.rest_vec, axis=1, keepdims=True)
        self.offset = np.array([B[i].head - (B[self.parent[i]].head if self.parent[i] >= 0 else 0) for i in range(n)])
        self.sign = np.array([MIRROR if b.side == "R" else np.ones(3) for b in B])
        self.spec = [JOINTS[b.role] for b in B]
        # layout das variáveis: [posição do quadril (3)] + por osso (3 ou 1)
        self.slices, k = [], 3
        for s in self.spec:
            d = 3 if s["tipo"] == "bola" else 1
            self.slices.append(slice(k, k + d)); k += d
        self.nvar = k
        self.hinge = np.array([s["tipo"] == "dobradica" for s in self.spec])
        self.axis = np.array([np.array(s.get("eixo", (0, 0, 0)), float) * self.sign[i] for i, s in enumerate(self.spec)])
        self.comfort = np.zeros((n, 3)); self.cw = np.zeros(n)
        for i, s in enumerate(self.spec):
            self.cw[i] = s["peso"]
            self.comfort[i] = (self.axis[i] * s["conforto"] if self.hinge[i] else np.array(s["conforto"], float) * self.sign[i]) * DEG
        self.radius = np.array([RADIUS[b.role] for b in B]) * self.H
        self.mass = np.array([MASS[b.role] for b in B])
        self._collision_pairs()

    # -------------------------------------------------------------- cinemática
    def x0(self):
        """Pose inicial: a de conforto (em pé, braços soltos)."""
        x = np.zeros(self.nvar)
        x[:3] = self.rest_head[self.idx["quadril"]]
        for i, s in enumerate(self.spec):
            x[self.slices[i]] = s["conforto"] * DEG if self.hinge[i] else self.comfort[i]
        return x

    def locals_(self, x):
        v = np.zeros((len(self.names), 3))
        for i, sl in enumerate(self.slices):
            v[i] = self.axis[i] * x[sl][0] if self.hinge[i] else x[sl]
        return v

    def fk(self, x) -> PoseState:
        v = self.locals_(x)
        R = rodrigues(v)
        n = len(self.names)
        D = np.empty((n, 3, 3)); head = np.empty((n, 3))
        for i in range(n):
            p = self.parent[i]
            if p < 0:
                D[i] = R[i]; head[i] = x[:3]
            else:
                D[i] = D[p] @ R[i]
                head[i] = head[p] + D[p] @ self.offset[i]
        tail = head + np.einsum("nij,nj->ni", D, self.rest_vec)
        return PoseState(self.names, head, tail, D, v)

    # -------------------------------------------------------------- colisão
    def _collision_pairs(self):
        role = [self.sk.bones[n].role for n in self.names]
        limbs = [i for i, r in enumerate(role) if r in ("antebraco", "mao", "canela", "pe", "braco", "coxa")]
        pairs = []
        for a in limbs:
            for b in range(len(self.names)):
                if a == b or self.parent[a] == b or self.parent[b] == a:
                    continue
                if self.parent[a] == self.parent[b] and role[a] not in ("coxa",):
                    continue
                if role[b] == "clavicula" or (role[a] in ("braco",) and role[b] in ("coluna", "pescoco", "cabeca")
                                              and self.rest_head[b][2] > 0.6 * self.H and role[b] != "cabeca"):
                    continue
                if role[a] == "coxa" and role[b] in ("quadril", "coluna") and self.rest_head[b][2] < 0.62 * self.H:
                    continue
                if role[a] == "braco" and self.sk.bones[self.names[b]].role == "coluna":
                    continue
                if b in limbs and b < a:
                    continue
                pairs.append((a, b))
        self.pa = np.array([p[0] for p in pairs]); self.pb = np.array([p[1] for p in pairs])
        self.ts = np.array([0.15, 0.5, 0.85, 1.0])

    def collision(self, st: PoseState):
        """Penetração (m) entre cápsulas de ossos não vizinhos, amostrando pontos do osso A contra o segmento B."""
        a0, a1 = st.head[self.pa], st.tail[self.pa]
        b0, b1 = st.head[self.pb], st.tail[self.pb]
        out = []
        ba = b1 - b0
        bb = np.einsum("ij,ij->i", ba, ba)
        for t in self.ts:
            p = a0 + (a1 - a0) * t
            h = np.clip(np.einsum("ij,ij->i", p - b0, ba) / bb, 0, 1)
            d = np.linalg.norm(p - (b0 + ba * h[:, None]), axis=1)
            out.append(np.maximum(0.0, self.radius[self.pa] + self.radius[self.pb] - d))
        return np.concatenate(out)

    # -------------------------------------------------------------- pontos do corpo
    def point(self, st: PoseState, parte: str):
        i = self.idx[parte]
        role = self.sk.bones[parte].role
        if role == "mao" or role == "cabeca":
            return (st.head[i] + st.tail[i]) / 2
        return st.head[i]

    def com(self, st: PoseState):
        c = (st.head + st.tail) / 2
        return (c * self.mass[:, None]).sum(0) / self.mass.sum()

    # -------------------------------------------------------------- resíduos
    def _limits(self, st: PoseState):
        r = []
        for i, s in enumerate(self.spec):
            v = st.local[i]
            if "caixa" in s:
                vv = v * self.sign[i] / DEG
                for c, (lo, hi) in zip(vv, s["caixa"]):
                    r.append(max(0.0, c - hi) * DEG + min(0.0, c - lo) * DEG)
            if "cone" in s:
                ax = unit(np.array(s["cone"][0]) * np.array([1 if self.sign[i][1] > 0 else -1, 1, 1]))
                d = rodrigues(v)[0] @ self.rest_dir[i]
                ang = np.arccos(np.clip(d @ ax, -1, 1))
                r.append(max(0.0, ang - s["cone"][1] * DEG))
            if "torcao" in s:
                th = np.linalg.norm(v)
                a = self.rest_dir[i]
                tw = 2 * np.arctan2(np.sin(th / 2) * (v @ a) / max(th, 1e-12), np.cos(th / 2))
                tw *= (1 if self.sign[i][1] > 0 else -1)
                lo, hi = s["torcao"]
                r.append(max(0.0, tw - hi * DEG) + min(0.0, tw - lo * DEG))
        return np.array(r)

    def _constraint_residuals(self, st: PoseState, cons, parts=None):
        res = []
        for c in cons:
            if isinstance(c, Alvo):
                e = self.point(st, c.parte) - np.asarray(c.ponto, float)
                e = e[["xyz".index(a) for a in c.eixos]]
            elif isinstance(c, Direcao):
                i = self.idx[c.osso]
                e = unit(st.tail[i] - st.head[i]) - unit(c.direcao)
            elif isinstance(c, Palma):
                i = self.idx[c.mao]
                e = st.D[i] @ np.array([0, 0, -1.0]) - unit(c.normal)
            elif isinstance(c, Olhar):
                i = self.idx["cabeca"]
                centro = (st.head[i] + st.tail[i]) / 2
                p = self.idx["peito"]
                alvo = unit(np.asarray(c.ponto, float) - centro)
                neutro = st.D[p] @ np.array([0, -1.0, 0])
                e = st.D[i] @ np.array([0, -1.0, 0]) - unit(neutro * (1 - c.cabeca) + alvo * c.cabeca)
            elif isinstance(c, Toque):
                i = self.idx[c.osso]
                sup = st.head[i] + (st.tail[i] - st.head[i]) * c.onde + st.D[i] @ unit(c.lado) * (self.radius[i] + self.radius[self.idx[c.parte]])
                e = self.point(st, c.parte) - sup
            elif isinstance(c, Dobra):
                i = self.idx[c.osso]
                lo, hi = self.spec[i]["faixa"]
                ang = np.linalg.norm(st.local[i]) / DEG
                e = np.array([(ang - (lo + (hi - lo) * c.quanto)) * DEG])
            elif isinstance(c, Tronco):
                i = self.idx["peito"]; q = self.idx["quadril"]
                rel = st.D[q].T @ st.D[i]
                alvo = rodrigues(np.array([0, 0, c.giro * DEG]))[0] @ rodrigues(np.array([c.frente * DEG, c.lado * DEG, 0]))[0]
                e = (rel - alvo).ravel() * 0.6
            elif isinstance(c, ApoioChao):
                i = self.idx[c.pe]
                az = self.rest_head[i][2] + c.altura
                e = [st.head[i][2] - az, st.tail[i][2] - (self.rest_head[i][2] + self.rest_vec[i][2] + c.altura),
                     (st.D[i] @ np.array([1.0, 0, 0]))[2] * 0.1]
                if c.ponto is not None:
                    e += [st.head[i][0] - c.ponto[0], st.head[i][1] - c.ponto[1]]
                e = np.array(e)
            elif isinstance(c, ApoioAssento):
                q = self.idx["quadril"]
                rq = self.radius[q] * 1.25
                e = [st.head[q][2] - (c.altura + rq), st.head[q][0] - c.centro[0], st.head[q][1] - c.centro[1]]
                for s in ("L", "R"):          # coxas apoiadas: joelho na altura do assento
                    k = self.idx[f"canela.{s}"]
                    e.append((st.head[k][2] - (c.altura + self.radius[self.idx[f'coxa.{s}']])) * 0.5)
                up = st.D[q] @ np.array([0, 0, 1.0])       # quadril aprumado e de frente (mole)
                e += [up[0] * 0.25, up[1] * 0.25, (st.D[q] @ np.array([1.0, 0, 0]))[1] * 0.25]
                e = np.array(e)
            elif isinstance(c, Fixar):
                i = self.idx[c.osso]
                e = st.local[i] - np.array(c.rotacao, float) * DEG
            else:
                raise TypeError(f"restrição desconhecida: {c!r}")
            if parts is not None:
                parts.append((c, np.asarray(e, float)))
            res.append(np.asarray(e, float) * c.peso)
        return np.concatenate(res) if res else np.zeros(0)

    def _balance(self, st, cons):
        feet = [c for c in cons if isinstance(c, ApoioChao)]
        if not feet or any(isinstance(c, ApoioAssento) for c in cons):
            return np.zeros(0)
        pts = []
        for c in feet:
            i = self.idx[c.pe]
            pts += [st.head[i][:2], st.tail[i][:2]]
        centro = np.mean(pts, axis=0)
        d = self.com(st)[:2] - centro
        n = np.linalg.norm(d)
        folga = 0.02 * self.H
        return d / max(n, 1e-9) * max(0.0, n - folga) * 25.0

    def residuals(self, x, cons):
        st = self.fk(x)
        comfort = ((st.local - self.comfort) * self.cw[:, None] * 0.12).ravel()
        return np.concatenate([
            self._constraint_residuals(st, cons),
            self._limits(st) * 20.0,
            self.collision(st) * 60.0,
            self._balance(st, cons),
            (x[:3] - self._anchor) * 0.05,     # âncora fraca: sem restrição, o quadril não sai do lugar
            comfort,
        ])

    # -------------------------------------------------------------- resolver
    def solve(self, cons, inicial=None, chute=None):
        """Resolve a pose. `inicial` = vetor de uma pose anterior (continuidade na animação);
        `chute` = {osso: rotação em graus} para partir de uma pose aproximada (usado pelas receitas)."""
        x = self.x0() if inicial is None else np.array(inicial, float)
        for osso, rot in (chute or {}).items():
            if osso == "quadril_pos":
                x[:3] = rot; continue
            i = self.idx[osso]
            x[self.slices[i]] = (np.atleast_1d(rot) * DEG if self.hinge[i] else np.array(rot, float) * DEG * self.sign[i])
        lo = np.full(self.nvar, -np.inf); hi = np.full(self.nvar, np.inf)
        for i, s in enumerate(self.spec):
            if self.hinge[i]:
                lo[self.slices[i]] = s["faixa"][0] * DEG; hi[self.slices[i]] = s["faixa"][1] * DEG
            else:
                lo[self.slices[i]] = -np.pi; hi[self.slices[i]] = np.pi
        x = np.clip(x, lo + 1e-6, hi - 1e-6)
        self._anchor = x[:3].copy()
        sol = least_squares(self.residuals, x, args=(cons,), bounds=(lo, hi), method="trf",
                            x_scale="jac", max_nfev=120, xtol=1e-7, ftol=1e-7)
        st = self.fk(sol.x)
        return sol.x, st, self.report(st, cons, sol.cost)

    def report(self, st, cons, cost=0.0) -> Relatorio:
        rep = Relatorio(custo=float(cost))
        parts = []
        self._constraint_residuals(st, cons, parts)
        for c, e in parts:
            nome = type(c).__name__ + "(" + str(getattr(c, "parte", getattr(c, "osso", getattr(c, "pe", getattr(c, "mao", ""))))) + ")"
            if isinstance(c, (Alvo, Toque, ApoioChao, ApoioAssento)):
                err = float(np.abs(e).max())
                rep.erros[nome] = f"{err * 100:.1f} cm"
                if err > 0.03:
                    rep.avisos.append(f"{nome} não foi cumprida (erro de {err * 100:.0f} cm)")
            else:
                err = float(np.linalg.norm(e))
                rep.erros[nome] = f"{err / DEG:.0f} graus" if not isinstance(c, Tronco) else f"{err:.2f}"
                if isinstance(c, (Direcao, Olhar, Palma)) and err > 0.35:
                    rep.avisos.append(f"{nome} só foi cumprida em parte (desvio de {err / DEG:.0f} graus)")
        lim = self._limits(st)
        if len(lim) and np.abs(lim).max() > 5 * DEG:
            rep.avisos.append(f"articulação {np.abs(lim).max() / DEG:.0f} graus além do limite")
        col = self.collision(st)
        if len(col) and col.max() > 0.015:
            k = int(np.argmax(col)) % len(self.pa)
            rep.avisos.append(f"{self.names[self.pa[k]]} atravessa {self.names[self.pb[k]]} em {col.max() * 100:.1f} cm")
        return rep
