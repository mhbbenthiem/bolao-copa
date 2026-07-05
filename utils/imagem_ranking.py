"""
Gera uma imagem (PNG) com a classificação geral inteira, no mesmo estilo
visual do app (fundo escuro, cards arredondados, medalhas pro top 3,
barra de pontuação). Serve pra participantes compartilharem o ranking
completo sem precisar tirar print da tela — que muitas vezes não cabe
tudo de uma vez, principalmente no celular.
"""

import io

import matplotlib
matplotlib.use("Agg")  # backend sem interface, só pra gerar a imagem
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle

from utils.sheets import agora_brasil

_COR_FUNDO = "#0b255b"
_COR_CARD = "#111827"
_COR_CARD_TOP = "#1a1f33"
_COR_TEXTO = "#FFFFFF"
_COR_SUBTEXTO = "#8FA0C2"
_COR_SCORE = "#1977e1"
_COR_SCORE_TOP = "#FFD700"
_COR_BARRA = "#1977e1"
_COR_BARRA_TOP = "#FFD700"
_COR_BORDA_PADRAO = "#ffffff22"
_MEDALHAS_COR = {1: "#FFD700", 2: "#C9C9C9", 3: "#CD7F32"}


def gerar_imagem_classificacao(classificacao) -> bytes:
    """
    Recebe o DataFrame de classificação (colunas Nome, Pontos, ...) já
    ordenado (posição 1 = primeira linha) e retorna os bytes de uma
    imagem PNG pronta para download.
    """
    n = len(classificacao)

    largura = 900
    altura_header = 110
    altura_linha = 92
    altura_rodape = 40
    altura = altura_header + n * altura_linha + altura_rodape

    fig = plt.figure(figsize=(largura / 100, altura / 100), dpi=100)
    fig.patch.set_facecolor(_COR_FUNDO)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, largura)
    ax.set_ylim(0, altura)
    ax.invert_yaxis()  # y=0 no topo, crescendo pra baixo (como pixels)
    ax.axis("off")

    margem_lateral = 40

    # ------- cabeçalho -------
    ax.add_patch(Rectangle((margem_lateral, 38), 6, 42, facecolor=_COR_SCORE_TOP, linewidth=0))
    ax.text(
        margem_lateral + 22, 55, "Classificação Geral",
        fontsize=25, ha="left", va="center", color=_COR_TEXTO, fontweight="bold",
    )
    ax.text(
        margem_lateral + 22, 88, "Bolão Copa do Mundo 2026",
        fontsize=12, ha="left", va="center", color=_COR_SUBTEXTO,
    )

    pontos_max = classificacao["Pontos"].max() or 1
    largura_card = largura - margem_lateral * 2

    y = altura_header
    for posicao, (_, pessoa) in enumerate(classificacao.iterrows(), start=1):
        top3 = posicao <= 3
        cor_card = _COR_CARD_TOP if top3 else _COR_CARD
        cor_score = _COR_SCORE_TOP if top3 else _COR_SCORE
        cor_barra = _COR_BARRA_TOP if top3 else _COR_BARRA
        cor_borda = _MEDALHAS_COR.get(posicao, _COR_BORDA_PADRAO)

        altura_card = altura_linha - 14

        card = FancyBboxPatch(
            (margem_lateral, y), largura_card, altura_card,
            boxstyle="round,pad=0,rounding_size=14",
            linewidth=1.3 if top3 else 0.7,
            edgecolor=cor_borda,
            facecolor=cor_card,
        )
        ax.add_patch(card)

        centro_y = y + altura_card * 0.38

        if top3:
            circulo = Circle(
                (margem_lateral + 34, centro_y), 16,
                facecolor=_MEDALHAS_COR[posicao], edgecolor="none",
            )
            ax.add_patch(circulo)
            ax.text(
                margem_lateral + 34, centro_y, str(posicao),
                fontsize=13, ha="center", va="center",
                color="#111827", fontweight="bold",
            )
        else:
            ax.text(
                margem_lateral + 34, centro_y, f"{posicao}º",
                fontsize=14, ha="center", va="center",
                color=_COR_SUBTEXTO, fontweight="bold",
            )

        ax.text(
            margem_lateral + 66, centro_y, str(pessoa["Nome"]),
            fontsize=16, ha="left", va="center",
            color=_COR_TEXTO, fontweight="bold",
        )

        ax.text(
            margem_lateral + largura_card - 20, centro_y, f"{int(pessoa['Pontos'])} pts",
            fontsize=15, ha="right", va="center",
            color=cor_score, fontweight="bold",
        )

        # barra de pontuação relativa ao líder
        y_barra = y + altura_card * 0.74
        largura_barra_total = largura_card - 40

        ax.add_patch(FancyBboxPatch(
            (margem_lateral + 20, y_barra), largura_barra_total, 6,
            boxstyle="round,pad=0,rounding_size=3",
            linewidth=0, facecolor="#ffffff1a",
        ))

        percentual = max(0.0, min(1.0, pessoa["Pontos"] / pontos_max)) if pontos_max else 0.0
        if percentual > 0:
            ax.add_patch(FancyBboxPatch(
                (margem_lateral + 20, y_barra), largura_barra_total * percentual, 6,
                boxstyle="round,pad=0,rounding_size=3",
                linewidth=0, facecolor=cor_barra,
            ))

        y += altura_linha

    # ------- rodapé -------
    ax.text(
        largura - margem_lateral, altura - altura_rodape / 2,
        f"Gerado em {agora_brasil().strftime('%d/%m/%Y %H:%M')}",
        fontsize=10, ha="right", va="center", color=_COR_SUBTEXTO,
    )

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=_COR_FUNDO)
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()