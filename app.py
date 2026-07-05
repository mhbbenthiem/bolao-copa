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
from utils.sheets import jogos_pendentes, sincronizar_jogos_com_api, carregar_jogos, carregar_palpites, salvar_palpite, carregar_pontuacao_inicial, listar_nomes_participantes, agora_brasil
from utils.scoring import montar_classificacao, detalhe_por_pessoa, montar_conferencia, filtrar_jogos_para_conferencia, montar_placares_por_jogo
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

    nomes_disponiveis = listar_nomes_participantes()
    OPCAO_VAZIA = "Selecione seu nome..."
    OPCAO_OUTRO = "➕ Outro (não estou na lista)"
    opcoes = [OPCAO_VAZIA] + nomes_disponiveis + [OPCAO_OUTRO]

    if nome_da_url and nome_da_url in nomes_disponiveis:
        indice_padrao = opcoes.index(nome_da_url)
    else:
        indice_padrao = 0

    escolha = st.selectbox("Seu nome", opcoes, index=indice_padrao, key="escolha_nome")

    if escolha == OPCAO_OUTRO:
        nome = st.text_input(
            "Digite seu nome completo",
            value=nome_da_url if nome_da_url not in nomes_disponiveis else "",
            key="nome_usuario_manual",
        )
    elif escolha == OPCAO_VAZIA:
        nome = ""
    else:
        nome = escolha

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

    agora = agora_brasil()

    meus_palpites = (
        df_palpites[df_palpites["Nome"].str.strip().str.lower() == nome.strip().lower()]
        if not df_palpites.empty
        else pd.DataFrame()
    )

    st.caption("Jogos com o cadeado 🔒 já começaram e não podem mais ser editados.")

    for _, jogo in df_jogos.sort_values("Data").iterrows():
        game_card(jogo, nome, meus_palpites, agora)


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
# Página: Visão Geral (conferência — todo mundo preencheu todos os jogos?)
# ---------------------------------------------------------------------------
elif pagina == "📊 Visão Geral":
    st.title("📊 Visão Geral")
    st.caption("Confira quem já preencheu todos os palpites e quem ainda está devendo.")

    df_jogos = carregar_jogos()
    df_palpites = carregar_palpites()
    nomes = listar_nomes_participantes(df_palpites)

    if df_jogos.empty:
        st.warning("Nenhum jogo carregado ainda. Peça ao organizador para atualizar na aba Admin.")
        st.stop()

    df_jogos_conferencia = filtrar_jogos_para_conferencia(df_jogos)

    if df_jogos_conferencia.empty:
        st.info("Não há jogos futuros com times já definidos para conferir no momento.")
        st.stop()

    if not nomes:
        st.info("Ainda não há ninguém na lista (nem em 'PontuacaoInicial', nem em 'Palpites').")
        st.stop()

    conferencia = montar_conferencia(df_palpites, df_jogos_conferencia, nomes)

    completos = int((conferencia["Faltando"] == 0).sum())
    incompletos = len(conferencia) - completos

    aba_pessoa, aba_jogo = st.tabs(["👥 Por pessoa", "⚽ Por jogo"])

    with aba_pessoa:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total de jogos", int(conferencia["TotalJogos"].iloc[0]))
        m2.metric("✅ Completaram tudo", completos)
        m3.metric("⚠️ Ainda faltando", incompletos)

        st.markdown("---")

        ordenado = conferencia.sort_values(["Faltando", "Nome"], ascending=[False, True])

        for _, pessoa in ordenado.iterrows():
            completo = pessoa["Faltando"] == 0
            rotulo = f"{'✅' if completo else '⚠️'} {pessoa['Nome']} — {pessoa['Preenchidos']}/{pessoa['TotalJogos']} jogos preenchidos"

            with st.expander(rotulo, expanded=not completo):
                if completo:
                    st.success("Todos os jogos preenchidos! 🎉")
                else:
                    st.write(f"Faltam **{pessoa['Faltando']}** jogo(s):")
                    for jogo in pessoa["JogosFaltantes"]:
                        st.write(f"- {jogo}")

    with aba_jogo:
        placares_por_jogo = montar_placares_por_jogo(df_palpites, df_jogos_conferencia)

        for _, jogo in df_jogos_conferencia.sort_values("Data").iterrows():
            jogo_id = str(jogo["JogoID"])
            palpites_do_jogo = placares_por_jogo.get(jogo_id, [])

            data_str = (
                jogo["Data"].strftime("%d/%m %H:%M") if pd.notna(jogo["Data"]) else "data a definir"
            )
            rotulo = (
                f"{jogo['Time1']} x {jogo['Time2']} — {data_str} "
                f"({len(palpites_do_jogo)}/{len(nomes)} já palpitaram)"
            )

            with st.expander(rotulo):
                if not palpites_do_jogo:
                    st.info("Ninguém palpitou este jogo ainda.")
                else:
                    for p in palpites_do_jogo:
                        st.write(f"- **{p['Nome']}**: {p['Placar1']} x {p['Placar2']}")


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