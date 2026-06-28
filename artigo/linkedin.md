# Quem é o favorito da Copa de 2026, segundo os números?

*Um exercício de análise de dados — não uma previsão.* (dados de 28/06/2026 — fim da fase de grupos)

Montei um modelo estatístico simples para a Copa do Mundo de 2026 e resolvi
testá-lo de verdade antes de olhar para o futuro. Agora que a **fase de grupos
terminou**, dá para fechar a conta sobre os 72 jogos do primeiro turno. O
resultado virou um pequeno artigo — e aqui vai o resumo.

## A ideia, em uma frase

A partir da **forma recente** de cada seleção (últimos 90 dias), estimo uma
**força de ataque e de defesa** para cada uma e uso a **distribuição de Poisson**
para transformar isso em probabilidade de cada resultado. É a abordagem clássica
para placares de futebol (Maher, 1982).

## Antes de prever, verificar

Em vez de só apresentar números bonitos, fiz um **backtest honesto**: voltei ao
primeiro jogo da Copa e avancei jogo a jogo, sempre prevendo cada partida
**apenas com os dados anteriores a ela** (sem espiar o futuro).

➡️ Sobre toda a fase de grupos, o modelo acertou o vencedor em **78,8%** dos
jogos decididos (41 de 52).

Um detalhe importante de transparência: os **empates** ficaram de fora dessa
conta. Ao escolher o resultado mais provável, o método quase nunca aponta o
empate — e, como o que interessa adiante é o mata-mata (onde não há empate: a
decisão vai aos pênaltis), a métrica certa é o acerto do **vencedor** nos jogos
que tiveram vencedor.

## E o título?

Com a fase de grupos encerrada, o chaveamento dos 16 avos já está **definido
pelos resultados reais**. Encadeando as probabilidades de vitória rodada a rodada
até a final, chega-se à probabilidade de cada seleção ser campeã. As doze
maiores hoje:

| # | Seleção | Probabilidade de título |
|---|---|---|
| 1 | 🇦🇷 Argentina | 19,1% |
| 2 | 🇲🇽 México | 12,8% |
| 3 | 🇧🇪 Bélgica | 10,9% |
| 4 | 🇲🇦 Marrocos | 9,7% |
| 5 | 🇧🇷 **Brasil** | **9,1%** |
| 6 | 🇩🇪 Alemanha | 5,2% |
| 7 | 🇫🇷 França | 3,9% |
| 8 | 🇵🇹 Portugal | 3,7% |
| 9 | 🇨🇮 Costa do Marfim | 3,3% |
| 10 | 🇪🇸 Espanha | 3,1% |
| 11 | 🇨🇴 Colômbia | 2,5% |
| 12 | 🇦🇺 Austrália | 2,3% |

A **Argentina** lidera com folga; o **Brasil** aparece em **5º, com 9,1%**.

## O recado mais importante

Isto **não é uma previsão**. É uma fotografia do cenário atual sob as hipóteses
do modelo — a cada rodada os números mudam. A graça está menos em "cravar o
campeão" e mais em **medir o quanto um modelo simples acerta** e deixar tudo
aberto e reproduzível.

Feito em Python (NumPy/SciPy/Matplotlib), com o auxílio do Claude Code. Metodologia
completa, verificação e tabelas no artigo; código aberto no repositório.

📄 **Artigo completo:** https://richmo.com.br/downloads/forca-probabilidades-copa-2026.pdf
💻 **Repositório:** https://github.com/richmodevstudio-oss/copa2026

*#DataScience #Estatística #CopaDoMundo2026 #Python #Futebol*
