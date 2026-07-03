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


def montar_classificacao(
    df_palpites: pd.DataFrame,
    df_jogos: pd.DataFrame,
    df_pontuacao_inicial: pd.DataFrame | None = None,
) -> pd.DataFrame:

    # pontos vindos dos palpites (pode ser vazio)
    if df_palpites.empty or df_jogos.empty:
        pontos_palpites = pd.DataFrame(columns=["Nome", "Pontos", "JogosPontuados"])
    else:
        df = df_palpites.merge(df_jogos, on="JogoID", how="left", suffixes=("", "_jogo"))

        df["Pontos"] = df.apply(
            lambda r: calcular_pontos_palpite(
                r["Placar1"], r["Placar2"], r.get("PlacarReal1"), r.get("PlacarReal2")
            ),
            axis=1,
        )

        pontos_palpites = (
            df.dropna(subset=["Pontos"])
            .groupby("Nome")
            .agg(Pontos=("Pontos", "sum"), JogosPontuados=("Pontos", "count"))
            .reset_index()
        )

    # pontuação inicial (pode ser vazia)
    if df_pontuacao_inicial is None or df_pontuacao_inicial.empty:
        pontuacao_inicial = pd.DataFrame(columns=["Nome", "Pontos"])
    else:
        pontuacao_inicial = df_pontuacao_inicial[["Nome", "Pontos"]].copy()

    # junta tudo (outer, pra não perder ninguém dos dois lados)
    classificacao = pontos_palpites.merge(
        pontuacao_inicial,
        on="Nome",
        how="outer",
        suffixes=("_palpites", "_inicial"),
    )

    classificacao["Pontos_palpites"] = classificacao["Pontos_palpites"].fillna(0)
    classificacao["Pontos_inicial"] = classificacao["Pontos_inicial"].fillna(0)
    classificacao["JogosPontuados"] = classificacao["JogosPontuados"].fillna(0).astype(int)

    classificacao["Pontos"] = (
        classificacao["Pontos_palpites"] + classificacao["Pontos_inicial"]
    )

    classificacao = (
        classificacao[["Nome", "Pontos", "JogosPontuados"]]
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
