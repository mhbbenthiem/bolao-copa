"""
Regras de pontuação do bolão:
  - 10 pontos: acertou o placar exato
  - 5 pontos: acertou apenas o resultado (vencedor ou empate), placar diferente
  - 0 pontos: errou o resultado
"""

import pandas as pd


def calcular_pontos_palpite(placar1_previsto, placar2_previsto, placar1_real, placar2_real) -> int:
    """Calcula os pontos de um único palpite, dado o resultado real do jogo."""
    if placar1_real is None or placar2_real is None or pd.isna(placar1_real) or pd.isna(placar2_real):
        return None  # jogo ainda não aconteceu / sem resultado

    placar1_previsto, placar2_previsto = int(placar1_previsto), int(placar2_previsto)
    placar1_real, placar2_real = int(placar1_real), int(placar2_real)

    if placar1_previsto == placar1_real and placar2_previsto == placar2_real:
        return 10

    resultado_previsto = _resultado(placar1_previsto, placar2_previsto)
    resultado_real = _resultado(placar1_real, placar2_real)

    if resultado_previsto == resultado_real:
        return 5

    return 0


def _resultado(g1: int, g2: int) -> str:
    if g1 > g2:
        return "time1"
    if g2 > g1:
        return "time2"
    return "empate"


def montar_classificacao(df_palpites: pd.DataFrame, df_jogos: pd.DataFrame) -> pd.DataFrame:
    if df_palpites.empty or df_jogos.empty:
        return pd.DataFrame(columns=["Nome", "Pontos", "JogosPontuados"])

    df = df_palpites.merge(df_jogos, on="JogoID", how="left", suffixes=("", "_jogo"))

    df["Pontos"] = df.apply(
        lambda r: calcular_pontos_palpite(
            r["Placar1"], r["Placar2"], r.get("PlacarReal1"), r.get("PlacarReal2")
        ),
        axis=1,
    )

    classificacao = (
        df.dropna(subset=["Pontos"])
        .groupby("Nome")
        .agg(Pontos=("Pontos", "sum"), JogosPontuados=("Pontos", "count"))
        .reset_index()
        .sort_values("Pontos", ascending=False)
        .reset_index(drop=True)
    )
    classificacao.index += 1
    return classificacao

def detalhe_por_pessoa(df_palpites: pd.DataFrame, df_jogos: pd.DataFrame, nome: str) -> pd.DataFrame:
    df = df_palpites[df_palpites["Nome"].str.strip().str.lower() == nome.strip().lower()]
    df = df.merge(df_jogos, on="JogoID", how="left", suffixes=("", "_jogo"))
    df["Pontos"] = df.apply(
        lambda r: calcular_pontos_palpite(
            r["Placar1"], r["Placar2"], r.get("PlacarReal1"), r.get("PlacarReal2")
        ),
        axis=1,
    )
    return df
