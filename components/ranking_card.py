import streamlit as st

_MEDALHAS = {1: "🥇", 2: "🥈", 3: "🥉"}


def ranking_card(row, posicao, pontos_max=None):
    """
    Card de uma posição no ranking. Top 3 recebem medalha e destaque visual;
    todas as posições mostram uma barrinha com a pontuação relativa à
    pessoa líder (pontos_max), pra dar uma referência visual rápida.
    """
    pontos = row["Pontos"]
    referencia = pontos_max if pontos_max else (pontos or 1)
    percentual = max(0, min(100, (pontos / referencia) * 100)) if referencia else 0

    medalha = _MEDALHAS.get(posicao)
    classe_extra = "ranking-top" if medalha else ""

    marcador_html = (
        f'<div class="ranking-medalha">{medalha}</div>'
        if medalha
        else f'<div class="ranking-posicao">{posicao}º</div>'
    )

    html = f"""<div class="ranking-card {classe_extra}">
    <div class="ranking-top-row">
        <div class="ranking-left">
            {marcador_html}
            <div class="ranking-name">{row["Nome"]}</div>
        </div>
        <div class="ranking-score">{int(pontos)} pts</div>
    </div>
    <div class="ranking-bar-bg">
        <div class="ranking-bar-fill" style="width:{percentual:.0f}%"></div>
    </div>
</div>"""

    st.markdown(html, unsafe_allow_html=True)