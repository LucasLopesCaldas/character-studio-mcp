# Teste às cegas: três poses, uma tentativa cada

Personagem: `sk = humanoid(); S = Solver(sk); H = S.H` (H = altura, 1,60 m). Todas as medidas abaixo estão em
frações de H. Eixos: X = esquerda da personagem, Y = costas, Z = cima (ela olha para -Y). "Fora" = para longe do
corpo, do lado do próprio membro. O ponto de uma mão é o meio do osso `mao.*`; "ponta do pé" é o fim do osso `pe.*`.
Direções como "frente*0.7 baixo*0.25" são vetores (não normalizados): 0,7 para a frente e 0,25 para baixo.

## Pose 1 — `celular`: sentada, segurando o celular
- Sentada num assento de altura `character_studio.poses.altura_assento_ideal(S)` (0,376 m), centrado em x=0, y=0.
  O início do osso quadril fica a 0,0775·H acima do assento. Os dois pés chapados no chão. Tronco aprumado.
- Mão direita em: início do osso peito + 0,17·H para a frente, 0,03·H para baixo e 0,03·H para a direita
  (no referencial do peito).
- Palma da mão direita voltada para "cima tras*0.8".
- Mão esquerda encostada em cima da coxa esquerda, a 60% do comprimento da coxa (a partir do quadril).
- Cabeça olhando para a mão direita, fazendo cerca de 60% do giro necessário (o resto seria dos olhos).

## Pose 2 — `chute_contato`: chutando a bola, instante do contato
- Bola de raio r = 0,068·H no chão, centro em (-0,06·H, -0,31·H, r).
- Só o pé esquerdo no chão, chapado, com o tornozelo na posição de repouso (x = +0,053·H, y = 0). Joelho esquerdo a ~23°.
- Ponta do pé direito em (x da bola, y da bola + 0,85·r, 0,8·r). Pé direito apontando "frente baixo*0.45". Joelho direito a ~17°.
- Peito inclinado 12° para TRÁS e girado 12° para a ESQUERDA (em relação à vertical e à frente).
- Braço esquerdo (osso braco.L) apontando "fora frente*0.7 baixo*0.25", cotovelo a ~32°.
- Braço direito (osso braco.R) apontando "fora*0.7 tras*0.7 baixo*0.6", cotovelo a ~39°.
- Cabeça olhando para a bola (60% do giro).
- Equilibrada: centro de massa sobre o pé de apoio.

## Pose 3 — `chute_armado`: perna armada para trás antes do chute (corrida, não precisa de equilíbrio)
- Bola de raio r = 0,068·H no chão, centro em (-0,05·H, -0,30·H, r).
- Só o pé esquerdo no chão, chapado, com o tornozelo em (x = +0,05·H, y = -0,20·H). Joelho esquerdo a ~24°.
- Início do osso quadril em (0, 0, 0,46·H).
- Coxa direita apontando "tras*0.6 baixo". Joelho direito a ~94°.
- Peito inclinado 18° para a FRENTE e girado 20° para a DIREITA.
- Braço esquerdo apontando "cima fora*0.8 tras*0.2", cotovelo a ~18°.
- Braço direito apontando "tras*0.8 baixo*0.7 fora*0.2", cotovelo a ~75°.
- Cabeça olhando para a bola (60% do giro).

## Entrega
Um único arquivo Python (o nome está nas instruções da sua sessão) com:

```python
def construir(S):
    """Devolve {"celular": x, "chute_contato": x, "chute_armado": x}; cada x é o vetor de pose (np.ndarray de tamanho S.nvar)."""
```

Regras: uma tentativa por pose, sem retoque depois de ver qualquer resultado. Sem imagens, sem render (não instale o bpy).
Dependências: `pip install numpy scipy`.
