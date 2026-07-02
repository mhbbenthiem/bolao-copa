"""
Conexão com Google Sheets, usado como "banco de dados" do bolão.

Estrutura esperada da planilha (2 abas):

Aba "Jogos":
  JogoID | Data | Hora | Time1 | Time2 | Grupo | PlacarReal1 | PlacarReal2 | Status

Aba "Palpites":
  Nome | JogoID | Placar1 | Placar2 | AtualizadoEm
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


@st.cache_resource
def conectar_planilha():
    """
    Conecta na planilha do Google Sheets usando uma Service Account.
    As credenciais e o ID da planilha vêm de st.secrets (configurado no
    arquivo .streamlit/secrets.toml ou nos "Secrets" do Streamlit Cloud).
    """
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    planilha = client.open_by_key(st.secrets["SPREADSHEET_ID"])
    return planilha


def carregar_jogos() -> pd.DataFrame:
    """Lê a aba 'Jogos' e devolve como DataFrame."""
    planilha = conectar_planilha()
    aba = planilha.worksheet("Jogos")
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)
    if df.empty:
        return df
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    return df


def carregar_palpites() -> pd.DataFrame:
    """Lê a aba 'Palpites' e devolve como DataFrame."""
    planilha = conectar_planilha()
    aba = planilha.worksheet("Palpites")
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)
    return df


def salvar_palpite(nome: str, jogo_id: str, placar1: int, placar2: int):
    """
    Salva ou atualiza (upsert) o palpite de uma pessoa para um jogo específico.
    Se já existir uma linha para (nome, jogo_id), ela é atualizada.
    Caso contrário, uma nova linha é criada.

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
        if str(r.get("Nome", "")).strip().lower() == nome.strip().lower() and str(
            r.get("JogoID", "")
        ) == str(jogo_id):
            linha_existente = i + 2
            break

    nova_linha = [nome, jogo_id, placar1, placar2, agora]

    if linha_existente:
        aba.update(f"A{linha_existente}:E{linha_existente}", [nova_linha])
    else:
        aba.append_row(nova_linha)


def atualizar_placares_reais(jogo_id: str, placar1: int, placar2: int, status: str = "Finalizado"):
    """
    Atualiza o placar real de um jogo na aba 'Jogos' (chamado depois de
    buscar os resultados na API oficial da Copa).
    """
    planilha = conectar_planilha()
    aba = planilha.worksheet("Jogos")
    registros = aba.get_all_records()

    for i, r in enumerate(registros):
        if str(r.get("JogoID", "")) == str(jogo_id):
            linha = i + 2
            aba.update(f"G{linha}:I{linha}", [[placar1, placar2, status]])
            break
def carregar_pontuacao_inicial() -> pd.DataFrame:
    """
    Lê a aba 'PontuacaoInicial'.

    Estrutura esperada:
        Nome | Pontos
    """

    planilha = conectar_planilha()

    try:
        aba = planilha.worksheet("PontuacaoInicial")
    except gspread.WorksheetNotFound:
        return pd.DataFrame(columns=["Nome", "Pontos"])

    dados = aba.get_all_records()

    df = pd.DataFrame(dados)

    if df.empty:
        return pd.DataFrame(columns=["Nome", "Pontos"])

    df["Pontos"] = pd.to_numeric(df["Pontos"], errors="coerce").fillna(0)

    return df