import streamlit as st
import pandas as pd
from utils.sheets import salvar_palpite
from utils.flags import bandeira_html


def game_card(jogo, nome, meus_palpites, agora=None):

    # Verifica se a pessoa já tem um palpite salvo para este jogo
    meu_palpite = None
    if meus_palpites is not None and not meus_palpites.empty:
        linhas = meus_palpites[meus_palpites["JogoID"].astype(str) == str(jogo["JogoID"])]
        if not linhas.empty:
            meu_palpite = linhas.iloc[0]

    tem_palpite = meu_palpite is not None

    # Jogo travado = já começou (não pode mais editar)
    travado = False
    if agora is not None and pd.notna(jogo["Data"]):
        travado = jogo["Data"] <= agora

    # Chave do container varia com o estado, para poder estilizar via CSS
    # (a base "card_" continua batendo com o seletor genérico já existente)
    if travado:
        estado = "travado"
    elif tem_palpite:
        estado = "palpitado"
    else:
        estado = "pendente"

    with st.container(key=f"card_{estado}_{jogo['JogoID']}"):

        st.markdown(
            f"<div class='game-header'>{jogo['Data'].strftime('%d/%m %H:%M')}</div>",
            unsafe_allow_html=True,
        )

        if tem_palpite or travado:
            selos = ""
            if tem_palpite:
                selos += "<span class='badge-palpitado'>✅ Palpitado!</span>"
            if travado:
                selos += "<span class='badge-travado'>🔒 Palpites encerrados</span>"
            st.markdown(f"<div class='badges'>{selos}</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns([3, 1, 3])

        valor_p1 = int(meu_palpite["Placar1"]) if tem_palpite else 0
        valor_p2 = int(meu_palpite["Placar2"]) if tem_palpite else 0

        with c1:
            st.markdown(
                f"<div class='team'>{bandeira_html(jogo['Time1'])} {jogo['Time1']}</div>",
                unsafe_allow_html=True,
            )
            p1 = st.number_input(
                "Placar Time 1",
                label_visibility="collapsed",
                key=f"p1_{jogo['JogoID']}",
                min_value=0,
                max_value=20,
                value=valor_p1,
                disabled=travado,
            )

        with c2:
            st.markdown("<div class='vs'>x</div>", unsafe_allow_html=True)

        with c3:
            st.markdown(
                f"<div class='team'>{bandeira_html(jogo['Time2'])} {jogo['Time2']}</div>",
                unsafe_allow_html=True,
            )
            p2 = st.number_input(
                "Placar Time 2",
                label_visibility="collapsed",
                key=f"p2_{jogo['JogoID']}",
                min_value=0,
                max_value=20,
                value=valor_p2,
                disabled=travado,
            )

        if travado:
            st.caption("Os palpites deste jogo foram encerrados.")
        else:
            rotulo_botao = "🔁 Atualizar Palpite" if tem_palpite else "Salvar Palpite"
            if st.button(rotulo_botao, key=f"save_{jogo['JogoID']}", use_container_width=True):
                salvar_palpite(nome, jogo["JogoID"], p1, p2)
                st.toast("Palpite atualizado!" if tem_palpite else "Palpite salvo!")
                st.rerun()