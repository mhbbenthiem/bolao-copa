import streamlit as st
import gspread
import requests
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# =========================
# CONEXÃO
# =========================

@st.cache_resource
def conectar_planilha():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["SPREADSHEET_ID"])


# =========================
# LEITURA
# =========================
def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
def converter_data_brasil(data_iso: str):
    if not data_iso:
        return None

    # converte string ISO para datetime UTC
    dt_utc = datetime.fromisoformat(data_iso.replace("Z", "+00:00"))

    # converte para horário do Brasil (UTC-3)
    dt_br = dt_utc - timedelta(hours=3)

    return dt_br
@st.cache_data(ttl=30)  # reaproveita o resultado por 30 segundos
def carregar_jogos():
    planilha = conectar_planilha()
    aba = planilha.worksheet("Jogos")

    df = pd.DataFrame(aba.get_all_records())

    if df.empty:
        return df

    df["Data"] = df["Data"].apply(converter_data_brasil)
    return df

@st.cache_data(ttl=30)  # reaproveita o resultado por 30 segundos
def carregar_palpites():
    planilha = conectar_planilha()
    aba = planilha.worksheet("Palpites")
    return pd.DataFrame(aba.get_all_records())
def salvar_palpite(nome: str, jogo_id: str, placar1: int, placar2: int): 
    """ Salva ou atualiza (upsert) o palpite de uma pessoa para um jogo específico. Se já existir uma linha para (nome, jogo_id), ela é atualizada. Caso contrário, uma nova linha é criada. Observação: a identificação é feita só pelo nome (sem e-mail). Se duas pessoas tiverem exatamente o mesmo nome, oriente-as a usar nome completo (ex: "João Silva" em vez de só "João") para evitar que os palpites se misturem. """ 
    planilha = conectar_planilha() 
    aba = planilha.worksheet("Palpites") 
    registros = aba.get_all_records() 
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
    linha_existente = None 
    for i, r in enumerate(registros): 
        if str(r.get("Nome", "")).strip().lower() == nome.strip().lower() and str( r.get("JogoID", "") ) == str(jogo_id): linha_existente = i + 2 
        break 
    nova_linha = [nome, jogo_id, placar1, placar2, agora] 
    if linha_existente: 
        aba.update(f"A{linha_existente}:E{linha_existente}", [nova_linha]) 
    else: 
        aba.append_row(nova_linha)
        carregar_palpites.clear()

# =========================
# ATUALIZAR PLACAR REAL
# =========================

def valido(valor):
    return valor is not None and valor != ""
@st.cache_data(ttl=30)  # reaproveita o resultado por 30 segundos
def sincronizar_jogos_com_api():
    dados = buscar_resultados_api()

    planilha = conectar_planilha()
    aba = planilha.worksheet("Jogos")

    registros = aba.get_all_records()

    mapa_linhas = {
        str(r["JogoID"]): i + 2
        for i, r in enumerate(registros)
        if str(r.get("JogoID", "")) != ""
    }

    for jogo in dados.get("matches", []):

        jogo_id = str(jogo.get("id"))
        status = jogo.get("status")

        score = jogo.get("score", {})
        full = score.get("fullTime", {})

        placar1 = full.get("home")
        placar2 = full.get("away")

        # 🔥 FILTRO ROBUSTO
        if (
            jogo_id in mapa_linhas and
            valido(placar1) and
            valido(placar2) and
            status in ["FINISHED", "FULL_TIME"]
        ):
            linha = mapa_linhas[jogo_id]

            aba.update(
                f"G{linha}:I{linha}",
                [[int(placar1), int(placar2), status]]
            )
    carregar_jogos.clear()

@st.cache_data(ttl=30)  # reaproveita o resultado por 30 segundos
def jogos_pendentes(nome_usuario: str):
    df_jogos = carregar_jogos()
    df_palpites = carregar_palpites()

    if df_jogos.empty:
        return df_jogos

    # 1) Remove jogos já finalizados
    df_jogos = df_jogos[
        df_jogos["Status"].fillna("").astype(str).str.upper() != "FINISHED"
    ]

    # 2) Se não houver palpites, retorna só os não finalizados
    if df_palpites.empty:
        return df_jogos

    nome = nome_usuario.strip().lower()

    df_user = df_palpites[
        df_palpites["Nome"].str.strip().str.lower() == nome
    ]

    jogos_ja_respondidos = set(df_user["JogoID"].astype(str))

    # 3) Remove jogos já respondidos
    df_filtrado = df_jogos[
        ~df_jogos["JogoID"].astype(str).isin(jogos_ja_respondidos)
    ]

    return df_filtrado
# =========================
# API FOOTBALL
# =========================
@st.cache_data(ttl=30)  # reaproveita o resultado por 30 segundos
def buscar_resultados_api():
    url = "https://api.football-data.org/v4/matches"

    headers = {
        "X-Auth-Token": st.secrets["FOOTBALL_DATA_API_KEY"]
    }

    response = requests.get(url, headers=headers)
    return response.json()


# =========================
# SINCRONIZAÇÃO AUTOMÁTICA
# =========================
@st.cache_data(ttl=30)  # reaproveita o resultado por 30 segundos
def sincronizar_jogos_com_api():
    dados = buscar_resultados_api()

    planilha = conectar_planilha()
    aba = planilha.worksheet("Jogos")

    registros = aba.get_all_records()

    mapa_linhas = {
        str(r["JogoID"]): i + 2
        for i, r in enumerate(registros)
        if str(r["JogoID"]) != ""
    }

    for jogo in dados.get("matches", []):

        jogo_id = str(jogo.get("id"))
        status = jogo.get("status")

        score = jogo.get("score", {})
        full = score.get("fullTime", {})

        placar1 = full.get("home")
        placar2 = full.get("away")

        # 🔥 só atualiza se tiver resultado válido
        if (
            jogo_id in mapa_linhas and
            placar1 is not None and
            placar2 is not None and
            status in ["FINISHED", "FULL_TIME"]
        ):
            linha = mapa_linhas[jogo_id]

            aba.update(
                f"G{linha}:I{linha}",
                [[placar1, placar2, status]]
            )


# =========================
# PONTUAÇÃO INICIAL
# =========================
@st.cache_data(ttl=30)  # reaproveita o resultado por 30 segundos
def carregar_pontuacao_inicial():
    planilha = conectar_planilha()

    try:
        aba = planilha.worksheet("PontuacaoInicial")
    except gspread.WorksheetNotFound:
        return pd.DataFrame(columns=["Nome", "Pontos"])

    df = pd.DataFrame(aba.get_all_records())

    if df.empty:
        return pd.DataFrame(columns=["Nome", "Pontos"])

    df["Pontos"] = pd.to_numeric(df["Pontos"], errors="coerce").fillna(0)
    return df