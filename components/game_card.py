import streamlit as st
from utils.sheets import salvar_palpite

def game_card(jogo, nome, meus_palpites):

    with st.container(key=f"card_{jogo['JogoID']}"):

        st.markdown(
            f"<div class='game-header'>{jogo['Data'].strftime('%d/%m %H:%M')}</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([3, 1, 3])

        with c1:
            st.markdown(f"<div class='team'>{jogo['Time1']}</div>", unsafe_allow_html=True)
            p1 = st.number_input(
                "Placar Time 1",
                label_visibility="collapsed",
                key=f"p1_{jogo['JogoID']}",
                min_value=0,
                max_value=20,
            )

        with c2:
            st.markdown("<div class='vs'>x</div>", unsafe_allow_html=True)

        with c3:
            st.markdown(f"<div class='team'>{jogo['Time2']}</div>", unsafe_allow_html=True)
            p2 = st.number_input(
                "Placar Time 2",
                label_visibility="collapsed",
                key=f"p2_{jogo['JogoID']}",
                min_value=0,
                max_value=20,
            )

        if st.button("Salvar Palpite", key=f"save_{jogo['JogoID']}", use_container_width=True):
            salvar_palpite(nome, jogo["JogoID"], p1, p2)
            st.toast("Palpite salvo!")