"""Teste às cegas, condição SEM solucionador: ângulos escritos à mão (trigonometria feita no raciocínio)."""
from character_studio.manual import manual


def construir(S):
    # ---------------- Pose 1: sentada com o celular
    celular = manual(S, (0.0, 0.0, 0.5), {
        "coxa.L": [("x", -88)], "canela.L": 88,
        "coxa.R": [("x", -88)], "canela.R": 88,
        # mão direita (escrita como esquerda): cotovelo junto ao corpo, antebraço para a frente
        "braco.R": [("x", -67.3), ("y", 82.0), ("z", -90.0)],
        "antebraco.R": 95.5,
        "mao.R": [("x", -77.7)],
        # mão esquerda pousada na coxa
        "braco.L": [("x", 45.2), ("y", 75.3), ("z", 7.5)],
        "antebraco.L": 86.2,
        "mao.L": [("x", 79.4)],
        "pescoco": [("x", 15)],
        "cabeca": [("x", 35.3), ("z", -4.5), ("x", -15)],
    })[0]

    # ---------------- Pose 2: chute, instante do contato
    chute_contato = manual(S, (0.07, -0.055, 0.8404), {
        "quadril": [("y", 14)],
        "coluna": [("y", -7)],
        "peito": [("x", -12), ("z", 12), ("y", -7)],
        "coxa.L": [("x", -7.2), ("y", -9.3)], "canela.L": 23,
        "pe.L": [("x", -15.9), ("y", -4.6), ("z", 1.3)],
        "coxa.R": [("x", -26.0), ("y", 7.7)], "canela.R": 17,
        "pe.R": [("x", 7.5), ("y", 6.2), ("z", 1.0)],
        "braco.L": [("y", 11.6), ("z", -47), ("x", 12)], "antebraco.L": 32,
        "braco.R": [("y", 31.2), ("z", 57), ("x", 12)], "antebraco.R": 39,
        "pescoco": [("x", 12), ("z", -12), ("x", 12)],
        "cabeca": [("x", 26)],
    })[0]

    # ---------------- Pose 3: perna armada antes do chute
    chute_armado = manual(S, (0.0, 0.0, 0.736), {
        "quadril": [("x", 10), ("y", -5)],
        "coluna": [("x", 9), ("z", -10), ("y", 5), ("x", -10)],
        "peito": [("x", 18), ("z", -10), ("x", -9)],
        "coxa.L": [("x", -50.1), ("y", 5.6), ("z", -1.0)], "canela.L": 24,
        "pe.L": [("x", 16.1), ("y", -0.7)],
        "coxa.R": [("x", 31.0), ("y", -5), ("x", -10)], "canela.R": 94,
        "pe.R": [("x", -30)],
        "braco.L": [("y", -50.5), ("z", 34.0), ("x", -18)], "antebraco.L": 18,
        "braco.R": [("y", 40.3), ("z", 56.0), ("x", -18)], "antebraco.R": 75,
        "pescoco": [("x", 34.6), ("z", 4.5), ("x", -18)],
        "cabeca": [("x", 18)],
    })[0]

    return {"celular": celular, "chute_contato": chute_contato, "chute_armado": chute_armado}
