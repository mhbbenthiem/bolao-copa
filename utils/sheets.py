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
# Fuso de Brasília. Fixo em UTC-3 porque o Brasil não usa mais horário de
# verão desde 2019 — se isso mudar, atualizar aqui.
FUSO_BRASIL = timezone(timedelta(hours=-3))


def converter_data_brasil(data_iso: str):
    if not data_iso:
        return None

    # converte string ISO (UTC) para datetime "consciente" do fuso
    dt_utc = datetime.fromisoformat(data_iso.replace("Z", "+00:00"))

    # converte corretamente para o horário de Brasília (mantém o instante
    # real, só troca o fuso/rótulo — usar "- timedelta(hours=3)" aqui seria
    # errado, pois desloca o relógio SEM trocar o fuso, fazendo a
    # comparação de "jogo já começou" ficar 3h adiantada)
    dt_br = dt_utc.astimezone(FUSO_BRASIL)

    return dt_br


def agora_brasil():
    """Horário atual no fuso de Brasília, no mesmo formato usado pela coluna 'Data'."""
    return datetime.now(FUSO_BRASIL)
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
    """
    Salva ou atualiza (upsert) o palpite de uma pessoa para um jogo específico.
    Se já existir uma linha para (nome, jogo_id), ela é atualizada. Caso
    contrário, uma nova linha é criada.
    Observação: a identificação é feita só pelo nome (sem e-mail). Se duas
    pessoas tiverem exatamente o mesmo nome, oriente-as a usar nome completo
    (ex: "João Silva" em vez de só "João") para evitar que os palpites se
    misturem.
    """
    planilha = conectar_planilha()
    aba = planilha.worksheet("Palpites")
    registros = aba.get_all_records()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    linha_existente = None
    for i, r in enumerate(registros):
        if (
            str(r.get("Nome", "")).strip().lower() == nome.strip().lower()
            and str(r.get("JogoID", "")) == str(jogo_id)
        ):
            linha_existente = i + 2
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
def jogos_pendentes(nome_usuario: str = None):
    """
    Retorna os jogos que ainda fazem sentido aparecer na tela de palpites:
    exclui apenas os jogos já FINALIZADOS. Jogos que a pessoa já palpitou
    continuam aparecendo (para permitir edição enquanto não começarem).
    """
    df_jogos = carregar_jogos()

    if df_jogos.empty:
        return df_jogos

    return df_jogos[
        df_jogos["Status"].fillna("").astype(str).str.upper() != "FINISHED"
    ]

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
# LISTA DE NOMES (para dropdown)
# =========================
def listar_nomes_participantes(df_palpites: pd.DataFrame = None) -> list:
    """
    Retorna a lista de nomes conhecidos, juntando quem está na aba
    'PontuacaoInicial' com quem já registrou algum palpite (união dos dois),
    para não deixar ninguém de fora da lista suspensa.
    """
    pontuacao_inicial = carregar_pontuacao_inicial()
    nomes = set()

    if not pontuacao_inicial.empty:
        nomes.update(pontuacao_inicial["Nome"].dropna().astype(str).str.strip())

    if df_palpites is None:
        df_palpites = carregar_palpites()

    if not df_palpites.empty:
        nomes.update(df_palpites["Nome"].dropna().astype(str).str.strip())

    return sorted(nomes, key=lambda n: n.lower())


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