import streamlit as st

def navbar():
    paginas = ["📝 Meus Palpites", "🏆 Classificação", "📊 Visão Geral", "⚙️ Admin"]

    if "pagina" not in st.session_state:
        st.session_state["pagina"] = paginas[0]

    cols = st.columns(len(paginas))
    for i, nome in enumerate(paginas):
        if cols[i].button(nome, use_container_width=True):
            st.session_state["pagina"] = nome

    return st.session_state["pagina"]