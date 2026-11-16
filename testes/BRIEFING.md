# Teste às cegas 2: três poses por intenção, dois corpos, uma tentativa

Você recebe só a **intenção** de cada pose e os **critérios** com que ela será medida. Quanto dobrar cada articulação,
onde pôr o quadril e como equilibrar o corpo é decisão sua.

## Personagens
```python
from character_studio.skeleton import corpo
from character_studio.solver import Solver
S = Solver(corpo("padrao"))     # H = 1,60 m
S = Solver(corpo("baixinho"))   # H = 1,15 m, cabeçudo, pernas curtas, braços longos
```
`H = S.H` é a altura. Eixos: X = esquerda da personagem, Y = costas, Z = cima (ela olha para -Y); chão em z = 0.
Em repouso (pose T) ela está em pé na origem. Pode ler as medidas de repouso de cada corpo (`S.rest_head`,
`S.rest_vec`, `S.radius`, `S.sk.bones`). "Ponto da mão" = meio do osso `mao.*`; "ponta do pé" = fim do osso `pe.*`;
"tornozelo" = início do osso `pe.*`; "frente do peito/cabeça" = eixo -Y do osso girado.

As três poses valem para os **dois corpos**. Cada critério vale 1 ponto; além deles, toda pose é medida em
**validade**: nenhuma articulação além do limite (tolerância 2°; limites em `solver.JOINTS`) e nenhum par de ossos
se atravessando mais de 1 cm (cápsulas de `Solver.collision`).

## Pose 1 — `celular`: sentada, olhando o celular na mão direita
Assento: tampo horizontal na altura A = `character_studio.poses.altura_assento_ideal(S)` (0,376 m no padrão;
0,2185 m no baixinho), centrado em x = 0, y = 0. Sentada, o início do osso quadril fica a 0,0775·H acima do tampo.
1. Quadril no assento: início do osso quadril a até 1 cm de z = A + 0,0775·H e a até 3 cm de x = 0, y = 0.
2. Pé esquerdo chapado no chão: tornozelo e ponta do pé a até 1 cm da altura que têm em repouso.
3. Pé direito chapado no chão: idem.
4. Mão direita segurando o celular à frente do peito: o ponto da mão, no referencial do osso peito (a partir do
   início dele), fica entre 0,10·H e 0,25·H à frente, entre 0,10·H abaixo e 0,10·H acima, e entre 0,10·H à direita
   e 0,05·H à esquerda. Mede-se a distância para fora dessa caixa (tolerância 1 cm).
5. Palma direita voltada para cima e para o rosto: ângulo entre a normal da palma e a direção "cima + 0,8·trás" ≤ 35°.
   (Em repouso a palma aponta para baixo, -Z do osso da mão.)
6. Mão esquerda pousada em cima da coxa esquerda: distância do ponto da mão ao eixo da coxa (trecho de 30% a 90%
   do comprimento) igual a raio da coxa + raio da mão, com tolerância de 2 cm, e a mão acima da coxa.
7. Cabeça voltada para o celular: ângulo entre a frente da cabeça e a direção do centro da cabeça até a mão direita ≤ 30°.
8. Tronco aprumado: eixo vertical do peito a até 12° da vertical.

## Pose 2 — `chute`: chutando uma bola parada no chão, instante do contato
Bola: raio r = 0,068·H, centro em (-0,06·H, -0,31·H, r).
1. Pé esquerdo de apoio chapado no chão, no lugar de repouso: tornozelo a até 2 cm da posição de repouso e ponta do
   pé a até 1 cm da altura de repouso.
2. Ponta do pé direito encostada na bola por trás: distância da ponta do pé à superfície da bola ≤ 2 cm, com a
   ponta atrás do centro da bola (y maior) e abaixo de 1,2·r.
3. Perna direita quase esticada: joelho direito dobrado ≤ 40°.
4. Equilibrada num pé só: projeção do centro de massa (`Solver.com`) a até 0,03·H do segmento tornozelo–ponta do pé esquerdo.
5. Tronco inclinado para trás: peito entre 5° e 20° para trás em relação à vertical.
6. Braço esquerdo aberto para o lado/frente: ponto da mão esquerda a mais de 0,15·H para a esquerda do início do
   osso peito (referencial do peito) e não atrás dele.
7. Braço direito para trás: ponto da mão direita atrás do início do osso peito (referencial do peito).
8. Cabeça voltada para a bola: ângulo ≤ 35°.

## Pose 3 — `agachada`: agachada, pegando um objeto no chão com a mão direita
Objeto: ponto em (-0,05·H, -0,25·H, 0,04·H).
1. Pé esquerdo chapado no chão no lugar de repouso (mesma medida do critério 1 da pose 2).
2. Pé direito chapado no chão no lugar de repouso (idem).
3. Mão direita no objeto: ponto da mão a até 3 cm do objeto.
4. Mão esquerda apoiada no joelho esquerdo: ponto da mão a até raio da coxa + raio da mão + 2 cm do joelho
   (início do osso canela.L).
5. Equilibrada: projeção do centro de massa a até 0,03·H do apoio (os dois segmentos tornozelo–ponta e o segmento
   que liga o meio dos dois pés).
6. Cabeça voltada para o objeto: ângulo ≤ 35°.

## Entrega
Um único arquivo Python (o nome está nas instruções da sua sessão) com:

```python
def construir(S, corpo_nome):
    """corpo_nome é "padrao" ou "baixinho". Devolve {"celular": x, "chute": x, "agachada": x};
    cada x é o vetor de pose (np.ndarray de tamanho S.nvar)."""
```

Regras: uma tentativa por pose e por corpo, sem retoque depois de ver qualquer resultado. Sem imagens, sem render
(não instale o bpy). Dependências: `pip install numpy scipy`.
