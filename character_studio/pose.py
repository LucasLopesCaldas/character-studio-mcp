"""Construtor de poses: a interface curta que o Claude usa.

Tudo é dito no vocabulário do corpo, sem ângulos de osso e sem coordenadas soltas:
  - direções por palavras: "frente", "tras", "cima", "baixo", "fora", "dentro", "esquerda", "direita",
    combináveis e com pesos: "frente baixo*0.5";
  - distâncias em alturas do corpo (0.10 = 10% da altura da personagem);
  - pontos ancorados no corpo: ("peito", "frente*0.17 baixo*0.03").
`descrever()` devolve a pose resultante nas mesmas palavras, para conferir sem renderizar.
"""
from __future__ import annotations
import numpy as np

from .solver import (Solver, Alvo, Direcao, Palma, Olhar, Dobra, Tronco, Toque, ApoioChao, ApoioAssento,
                     Fixar, unit, DEG)

EIXOS = {"frente": (0, -1, 0), "tras": (0, 1, 0), "cima": (0, 0, 1), "baixo": (0, 0, -1),
         "esquerda": (1, 0, 0), "direita": (-1, 0, 0)}


def vetor(texto, lado="L"):
    """'frente baixo*0.5' -> vetor (não normalizado). 'fora'/'dentro' dependem do lado do membro."""
    if not isinstance(texto, str):
        return np.asarray(texto, float)
    v = np.zeros(3)
    for termo in texto.replace(",", " ").split():
        nome, _, peso = termo.partition("*")
        w = float(peso) if peso else 1.0
        if nome in ("fora", "dentro"):
            s = (1 if lado == "L" else -1) * (1 if nome == "fora" else -1)
            v += np.array([s, 0, 0]) * w
        else:
            v += np.array(EIXOS[nome]) * w
    return v


def palavras(v, lado="C", casas=2):
    """Vetor -> 'frente*0.80 baixo*0.60' (o inverso de `vetor`)."""
    v = np.asarray(v, float)
    out = []
    for comp, pos, neg in ((-v[1], "frente", "tras"), (v[2], "cima", "baixo")):
        if abs(comp) >= 0.5 * 10 ** -casas:
            out.append(f"{pos if comp > 0 else neg}*{abs(comp):.{casas}f}")
    x = v[0]
    if abs(x) >= 0.5 * 10 ** -casas:
        if lado == "C":
            out.append(f"{'esquerda' if x > 0 else 'direita'}*{abs(x):.{casas}f}")
        else:
            fora = x > 0 if lado == "L" else x < 0
            out.append(f"{'fora' if fora else 'dentro'}*{abs(x):.{casas}f}")
    return " ".join(out) or "0"


def _lado(nome):
    return nome.split(":")[0].rsplit(".", 1)[-1] if "." in nome else "C"


class Pose:
    def __init__(self, solver: Solver):
        self.S = solver
        self.H = solver.H
        self.cons: list = []
        self.chute: dict = {}
        self._apoios: list = []
        self._no_ar = False
        self.x = None; self.st = None; self.rel = None

    # ------------------------------------------------------------ apoios
    def pes_no_chao(self, *pes, em=None):
        """Pés chapados no chão. Sem argumentos = os dois. em={'pe.L': (x, y)} fixa onde (em alturas do corpo)."""
        for pe in (pes or ("pe.L", "pe.R")):
            h = self.S.rest_head[self.S.idx[pe]]
            pt = (em or {}).get(pe)
            pt = (h[0], h[1]) if pt is None else (pt[0] * self.H, pt[1] * self.H)
            self.cons.append(ApoioChao(pe, ponto=pt)); self._apoios.append(pe)
        return self

    def sentar(self, altura=None, centro=(0.0, 0.0)):
        """Sentada num assento (altura em metros; padrão = a ideal para o corpo). Pés vão ao chão se alcançarem."""
        from . import poses
        c, ch = poses.sentar(self.S, altura, centro)
        self.cons += c; self.chute.update(ch); self._apoios.append("assento")
        return self

    def no_ar(self, altura_quadril=0.6):
        """Sem apoio (salto). altura_quadril em alturas do corpo."""
        self._no_ar = True
        self.cons.append(Alvo("quadril", (0, 0, altura_quadril * self.H), eixos="z"))
        return self

    # ------------------------------------------------------------ corpo
    def tronco(self, frente=0.0, lado=0.0, giro=0.0, peso=8.0):
        """Inclinação do peito em graus, em relação à vertical: frente (+) / trás (-), lado esquerdo (+), giro à esquerda (+)."""
        self.cons.append(Tronco(frente, lado, giro, peso)); return self

    def apontar(self, osso, direcao, dobra=None, peso=8.0):
        """Um osso aponta numa direção ('braco.L', 'frente fora*0.5'). `dobra` (0 a 1) vale para o cotovelo/joelho seguinte."""
        self.cons.append(Direcao(osso, tuple(vetor(direcao, _lado(osso))), peso))
        if dobra is not None:
            filho = {"braco": "antebraco", "coxa": "canela"}[osso.split(".")[0]] + "." + _lado(osso)
            self.dobra(filho, dobra)
        return self

    def dobra(self, osso, quanto, peso=6.0):
        """Cotovelo ('antebraco.L') ou joelho ('canela.R'): 0 = esticado, 1 = todo dobrado."""
        self.cons.append(Dobra(osso, quanto, peso)); return self

    def ponto(self, onde):
        """Resolve um ponto: (x, y, z) em metros no mundo, ou ('osso', 'frente*0.2 cima*0.1') ancorado no corpo."""
        if isinstance(onde, tuple) and len(onde) == 2 and isinstance(onde[0], str):
            ref, desl = onde
            return tuple(vetor(desl, _lado(ref)) * self.H), ref
        return tuple(np.asarray(onde, float)), None

    def colocar(self, parte, onde, peso=30.0):
        """Uma parte ('mao.R', 'pe.R:ponta', 'quadril') num ponto do mundo ou ancorado no corpo."""
        pt, ref = self.ponto(onde)
        self.cons.append(Alvo(parte, pt, peso, ref=ref)); return self

    def palma(self, mao, direcao, peso=2.0):
        self.cons.append(Palma(mao, tuple(vetor(direcao, _lado(mao))), peso)); return self

    def tocar(self, parte, osso, onde=0.5, lado="frente", peso=25.0):
        """Uma parte encosta na superfície de um osso (mão na coxa, mão no queixo)."""
        self.cons.append(Toque(parte, osso, onde, tuple(vetor(lado, _lado(osso))), peso)); return self

    def olhar(self, onde, cabeca=0.6):
        """Olha para um ponto do mundo (x, y, z). `cabeca` = quanto do giro a cabeça faz."""
        self.cons.append(Olhar(tuple(np.asarray(onde, float)), cabeca=cabeca)); return self

    def fixar(self, osso, rotacao):
        self.cons.append(Fixar(osso, rotacao)); return self

    # ------------------------------------------------------------ resolver
    def resolver(self, inicial=None):
        if not self._apoios and not self._no_ar:
            self.pes_no_chao()
        if not any(isinstance(c, Tronco) for c in self.cons):
            self.cons.append(Tronco(0, 0, 0, peso=2.5))     # postura aprumada por padrão (mole)
        melhor = None
        chutes = [self.chute] if inicial is not None else [self.chute, {**self.chute, **self._chute_das_direcoes()}]
        for ch in chutes:
            x, st, rel = self.S.solve(self.cons, inicial=inicial, chute=ch)
            if melhor is None or rel.custo < melhor[2].custo:
                melhor = (x, st, rel)
        self.x, self.st, self.rel = melhor
        return self

    def _chute_das_direcoes(self):
        """Segundo ponto de partida: já gira braços e coxas para perto das direções pedidas (evita mínimos locais)."""
        ch = {}
        for c in self.cons:
            if isinstance(c, Direcao) and c.osso.split(".")[0] in ("braco", "coxa"):
                i = self.S.idx[c.osso]
                a, b = self.S.rest_dir[i], unit(c.direcao)
                eixo = np.cross(a, b); n = np.linalg.norm(eixo)
                if n > 1e-6:
                    rv = eixo / n * np.arctan2(n, a @ b) / DEG
                    ch[c.osso] = tuple(rv * self.S.sign[i])
        return ch

    # ------------------------------------------------------------ descrever
    def descrever(self) -> str:
        S, st, H = self.S, self.st, self.H
        i = S.idx
        L = []
        up = st.D[i["peito"]] @ np.array([0, 0, 1.0]); fw = st.D[i["peito"]] @ np.array([0, -1.0, 0])
        L.append(f"tronco: frente {np.arctan2(-up[1], up[2]) / DEG:+.0f}°, lado {np.arctan2(up[0], up[2]) / DEG:+.0f}°, "
                 f"giro {np.arctan2(fw[0], -fw[1]) / DEG:+.0f}°")
        q = st.head[i["quadril"]]
        L.append(f"quadril: altura {q[2] / H:.2f}, deslocado {palavras(np.array([q[0], q[1], 0]) / H)}")
        hf = st.D[i["cabeca"]] @ np.array([0, -1.0, 0])
        L.append(f"cabeça olhando: {palavras(hf)}")
        for s in ("L", "R"):
            n = "esq" if s == "L" else "dir"
            b = unit(st.tail[i[f"braco.{s}"]] - st.head[i[f"braco.{s}"]])
            cot = np.linalg.norm(st.local[i[f"antebraco.{s}"]]) / DEG
            mao = (S.point(st, f"mao.{s}") - st.head[i["peito"]]) / H
            palma = st.D[i[f"mao.{s}"]] @ np.array([0, 0, -1.0])
            L.append(f"braço {n}: aponta {palavras(b, s)}; cotovelo {cot:.0f}°; mão em relação ao peito: {palavras(mao, s)}; "
                     f"palma {palavras(palma, s, 1)}")
        for s in ("L", "R"):
            n = "esq" if s == "L" else "dir"
            c = unit(st.tail[i[f"coxa.{s}"]] - st.head[i[f"coxa.{s}"]])
            jo = np.linalg.norm(st.local[i[f"canela.{s}"]]) / DEG
            tz = st.head[i[f"pe.{s}"]][2] - S.rest_head[i[f"pe.{s}"]][2]
            p = st.head[i[f"pe.{s}"]] / H
            L.append(f"perna {n}: coxa aponta {palavras(c, s)}; joelho {jo:.0f}°; tornozelo em {palavras(np.array([p[0], p[1], 0]), 'C')}, "
                     f"{'no chão' if abs(tz) < 0.01 * H else f'{tz / H:.2f} acima do chão'}")
        if self._apoios and "assento" not in self._apoios:
            pts = []
            for pe in self._apoios:
                pts += [st.head[i[pe]][:2], st.tail[i[pe]][:2]]
            d = (S.com(st)[:2] - np.mean(pts, axis=0)) / H
            fora = np.linalg.norm(d) > 0.06
            L.append(f"equilíbrio: centro de massa {palavras(np.array([d[0], d[1], 0]))} do centro do apoio"
                     + (" (DESEQUILIBRADA)" if fora else " (ok)"))
        L += [f"restrição {k}: erro {v}" for k, v in self.rel.erros.items() if not v.startswith(("0.0 cm", "0 graus", "0.00"))]
        L += [f"AVISO: {a}" for a in self.rel.avisos]
        return "\n".join(L)
