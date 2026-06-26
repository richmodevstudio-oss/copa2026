# Quem é o favorito da Copa de 2026, segundo os números?

*Um exercício de análise de dados — não uma previsão.* (dados de 25/06/2026)

Montei um modelo estatístico simples para a Copa do Mundo de 2026 e resolvi
testá-lo de verdade antes de olhar para o futuro. O resultado virou um pequeno
artigo — e aqui vai o resumo.

## A ideia, em uma frase

A partir da **forma recente** de cada seleção (últimos 90 dias), estimo uma
**força de ataque e de defesa** para cada uma e uso a **distribuição de Poisson**
para transformar isso em probabilidade de cada resultado. É a abordagem clássica
para placares de futebol (Maher, 1982).

## Antes de prever, verificar

Em vez de só apresentar números bonitos, fiz um **backtest honesto**: voltei ao
primeiro jogo da Copa e avancei jogo a jogo, sempre prevendo cada partida
**apenas com os dados anteriores a ela** (sem espiar o futuro).

➡️ O modelo acertou o vencedor em **81,0%** dos jogos decididos (34 de 42).

Um detalhe importante de transparência: os **empates** ficaram de fora dessa
conta. Ao escolher o resultado mais provável, o método quase nunca aponta o
empate — e, como o que interessa adiante é o mata-mata (onde não há empate: a
decisão vai aos pênaltis), a métrica certa é o acerto do **vencedor** nos jogos
que tiveram vencedor.

## E o título?

Completando a fase de grupos com o cenário mais provável e encadeando as
probabilidades de vitória rodada a rodada até a final, chega-se à probabilidade
de cada seleção ser campeã. As cinco maiores hoje:

| Seleção | Probabilidade de título |
|---|---|
| 🇦🇷 Argentina | 17,5% |
| 🇲🇽 México | 10,1% |
| 🇧🇷 **Brasil** | **8,4%** (3º) |
| 🇧🇪 Bélgica | 8,2% |
| 🇨🇮 Costa do Marfim | 7,2% |

A **Argentina** lidera; o **Brasil** aparece em **3º, com 8,4%**.

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
