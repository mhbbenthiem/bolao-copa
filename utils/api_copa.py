"""
Busca dados oficiais da Copa do Mundo (jogos, datas, placares) via
football-data.org (plano gratuito, precisa de uma API key gratuita em
https://www.football-data.org/client/register).

Alternativa 100% sem cadastro (mas atualizada manualmente por voluntários):
https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json
-> ver função buscar_jogos_openfootball() como fallback.
"""

import requests
import streamlit as st
import pandas as pd

FOOTBALL_DATA_URL = "https://api.football-data.org/v4/competitions/WC/matches"
OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
)


def buscar_jogos_football_data() -> pd.DataFrame:
    """
    Busca todos os jogos da Copa do Mundo via football-data.org.
    Requer API key gratuita configurada em st.secrets["FOOTBALL_DATA_API_KEY"].
    """
    headers = {"X-Auth-Token": st.secrets["FOOTBALL_DATA_API_KEY"]}
    resp = requests.get(FOOTBALL_DATA_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    dados = resp.json()

    jogos = []
    for m in dados.get("matches", []):
        placar = m.get("score", {}).get("fullTime", {})
        jogos.append(
            {
                "JogoID": m["id"],
                "Data": m["utcDate"],
                "Time1": m["homeTeam"]["name"],
                "Time2": m["awayTeam"]["name"],
                "Grupo": m.get("group"),
                "PlacarReal1": placar.get("home"),
                "PlacarReal2": placar.get("away"),
                "Status": m.get("status"),  # SCHEDULED, IN_PLAY, FINISHED...
            }
        )
    return pd.DataFrame(jogos)


def buscar_jogos_openfootball() -> pd.DataFrame:
    """
    Alternativa sem API key. Bom para prototipar rápido ou como fallback
    se a API principal estiver fora do ar.
    """
    dados = requests.get(OPENFOOTBALL_URL, timeout=15).json()

    jogos = []
    for i, m in enumerate(dados.get("matches", [])):
        score = m.get("score", {}).get("ft")
        jogos.append(
            {
                "JogoID": f"OF-{i}",
                "Data": m["date"],
                "Time1": m["team1"],
                "Time2": m["team2"],
                "Grupo": m.get("group"),
                "PlacarReal1": score[0] if score else None,
                "PlacarReal2": score[1] if score else None,
                "Status": "FINISHED" if score else "SCHEDULED",
            }
        )
    return pd.DataFrame(jogos)
