import streamlit as st

def ranking_card(row, posicao):

    html = f"""<div class="ranking-card">
<div class="ranking-position">{posicao}º</div>
<div class="ranking-name">{row["Nome"]}</div>
<div class="ranking-score">{row["Pontos"]} pts</div>
</div>"""

    st.markdown(html, unsafe_allow_html=True)