"""
Bolão da Copa do Mundo — App principal (Streamlit)

Como rodar localmente:
    pip install -r requirements.txt
    streamlit run app.py

Antes de rodar, configure .streamlit/secrets.toml (veja secrets.toml.exemplo)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from utils.sheets import jogos_pendentes, sincronizar_jogos_com_api, carregar_jogos, carregar_palpites, salvar_palpite, carregar_pontuacao_inicial
from utils.scoring import montar_classificacao, detalhe_por_pessoa
from utils.api_copa import buscar_jogos_football_data
from pathlib import Path
from components.navbar import navbar
from components.game_card import game_card
from components.ranking_card import ranking_card



st.set_page_config(
    page_title="Bolão Copa 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

css = Path("style.css").read_text(encoding="utf-8")

st.markdown(
    f"<style>{css}</style>",
    unsafe_allow_html=True,
)
pagina = navbar()



if st.button("Atualizar jogos"):
    sincronizar_jogos_com_api()
    st.success("Jogos atualizados!")
# ---------------------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------------------


st.sidebar.markdown("---")
st.sidebar.caption("Bolão da Copa do Mundo 2026 · dados atualizados via API oficial")


# ---------------------------------------------------------------------------
# Utilitário: exportar DataFrame para Excel (download)
# ---------------------------------------------------------------------------
def exportar_excel(df: pd.DataFrame, nome_arquivo: str):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=True, sheet_name="Classificação")
    buffer.seek(0)
    st.download_button(
        label="⬇️ Exportar para Excel",
        data=buffer,
        file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ---------------------------------------------------------------------------
# Página: Meus Palpites
# ---------------------------------------------------------------------------
if pagina == "📝 Meus Palpites":
    st.title("📝 Registrar / Editar Palpites")

    col1, col2 = st.columns(2)
    nome_da_url = st.query_params.get("nome", "")
    nome = st.text_input(
        "Seu nome",
        value=nome_da_url,
        key="nome_usuario"
    )
        

    if not nome:
        st.info("Digite seu nome para ver e registrar seus palpites.")
        st.stop()

    if nome != nome_da_url:
        st.query_params["nome"] = nome
        st.info(
            "💡 Dica: salve este link (ou adicione à tela inicial do celular) "
            "para não precisar digitar seu nome de novo da próxima vez."
        )
        st.code(f"?nome={nome}", language=None)

    df_jogos = jogos_pendentes(nome)
    df_palpites = carregar_palpites()

    if df_jogos.empty:
        st.warning("Nenhum jogo carregado ainda. Peça ao organizador para atualizar na aba Admin.")
        st.stop()

    agora = pd.Timestamp.now(tz=df_jogos["Data"].dt.tz) if df_jogos["Data"].dt.tz else pd.Timestamp.now()

    meus_palpites = (
        df_palpites[df_palpites["Nome"].str.strip().str.lower() == nome.strip().lower()]
        if not df_palpites.empty
        else pd.DataFrame()
    )

    st.caption("Jogos com o cadeado 🔒 já começaram e não podem mais ser editados.")

    for _, jogo in df_jogos.sort_values("Data").iterrows():
        game_card(jogo, nome, meus_palpites)


# ---------------------------------------------------------------------------
# Página: Classificação
# ---------------------------------------------------------------------------
elif pagina == "🏆 Classificação":
    st.title("🏆 Classificação Geral")

    df_jogos = carregar_jogos()
    df_palpites = carregar_palpites()
    pontuacao_inicial = carregar_pontuacao_inicial()
    classificacao = montar_classificacao(df_palpites, df_jogos, pontuacao_inicial)
    
    


    if classificacao.empty:
        st.info("Ainda não há pontos calculados (nenhum jogo finalizado ou nenhum palpite registrado).")
    else:
        for posicao, (_, pessoa) in enumerate(classificacao.iterrows(), start=1):
            ranking_card(pessoa, posicao)
        exportar_excel(classificacao, "classificacao_bolao_copa.xlsx")

    st.markdown("---")
    st.subheader("🔍 Ver detalhes de uma pessoa")
    nome_busca = st.text_input("Nome da pessoa")
    if nome_busca:
        detalhe = detalhe_por_pessoa(df_palpites, df_jogos, nome_busca)
        if detalhe.empty:
            st.warning("Nenhum palpite encontrado para esse nome.")
        else:
            colunas = ["Time1", "Time2", "Placar1", "Placar2", "PlacarReal1", "PlacarReal2", "Pontos"]
            st.dataframe(detalhe[colunas], use_container_width=True)


# ---------------------------------------------------------------------------
# Página: Admin (atualizar jogos/placares via API)
# ---------------------------------------------------------------------------
elif pagina == "⚙️ Admin":
    st.title("⚙️ Administração")
    st.caption("Use esta página para atualizar jogos e placares a partir da API oficial da Copa.")

    senha = st.text_input("Senha de administrador", type="password")
    if senha != st.secrets.get("ADMIN_PASSWORD", ""):
        st.warning("Digite a senha de administrador para continuar.")
        st.stop()

    if st.button("🔄 Atualizar jogos e placares agora"):
        with st.spinner("Buscando dados na API..."):
            try:
                df_api = buscar_jogos_football_data()
                st.session_state["df_api_preview"] = df_api
                st.success(f"{len(df_api)} jogos encontrados. Confira abaixo antes de aplicar.")
            except Exception as e:
                st.error(f"Erro ao buscar dados na API: {e}")

    if "df_api_preview" in st.session_state:
        st.dataframe(st.session_state["df_api_preview"], use_container_width=True)
        st.info(
            "Próximo passo: escreva esses dados na aba 'Jogos' da planilha "
            "(pode ser feito manualmente colando os dados, ou automatizando "
            "com gspread — ver função `atualizar_placares_reais` em utils/sheets.py)."
        )
