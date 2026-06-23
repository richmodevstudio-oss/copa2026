"""Previsor de resultados da Copa do Mundo 2026.

Pacote com o núcleo do algoritmo descrito no PRD:

- ``scoring``    -> função de pontuação do bolão (Seção 3)
- ``strength``   -> cálculo de força iterativo O/D (Seção 4.2)
- ``prediction`` -> gols esperados e matriz de placares via Poisson (Seção 4.3)
- ``optimizer``  -> palpite que maximiza os pontos esperados (Seção 4.4)
- ``data_source``-> coleta de dados (API pública / dados sintéticos)
- ``pipeline``   -> orquestra as quatro etapas
"""

from .models import Match, TeamRatings

__all__ = ["Match", "TeamRatings"]
