"""
Regras de pontuação do bolão:
  - 10 pontos: acertou o placar exato
  - 5 pontos: acertou apenas o resultado (vencedor ou empate), placar diferente
  - 0 pontos: errou o resultado
"""

import pandas as pd


def filtrar_jogos_para_conferencia(df_jogos: pd.DataFrame) -> pd.DataFrame:
    """
    Remove da conferência (tela "Visão Geral"):
      - jogos com data anterior a hoje (já aconteceram, não faz sentido cobrar palpite);
      - jogos cujos dois times ainda não foram definidos (ex: fases eliminatórias
        aguardando classificados — time vazio, ou textos como "TBD", "A definir",
        "Vencedor Grupo A", "1º Grupo B" etc.).
    """
    if df_jogos.empty:
        return df_jogos

    df = df_jogos.copy()

    if df["Data"].dt.tz is not None:
        hoje = pd.Timestamp.now(tz=df["Data"].dt.tz).normalize()
    else:
        hoje = pd.Timestamp.now().normalize()

    df = df[df["Data"].notna() & (df["Data"] >= hoje)]

    marcadores_indefinido = [
        "tbd", "a definir", "indefinido", "vencedor", "perdedor",
        "definido", "classificado", "1º", "2º", "3º", "melhor",
    ]

    def time_definido(valor) -> bool:
        if pd.isna(valor):
            return False
        texto = str(valor).strip().lower()
        if texto == "":
            return False
        return not any(marcador in texto for marcador in marcadores_indefinido)

    df = df[df["Time1"].apply(time_definido) & df["Time2"].apply(time_definido)]

    return df


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

def montar_conferencia(df_palpites: pd.DataFrame, df_jogos: pd.DataFrame, nomes: list) -> pd.DataFrame:
    """
    Para cada nome da lista, verifica quantos jogos já têm palpite registrado
    e quais jogos ainda estão faltando. Útil para conferir, antes da Copa
    começar, se todo mundo já preencheu tudo.
    """
    if df_jogos.empty:
        return pd.DataFrame(columns=["Nome", "TotalJogos", "Preenchidos", "Faltando", "JogosFaltantes"])

    total_jogos = len(df_jogos)

    if df_palpites.empty:
        jogos_por_nome = {}
    else:
        jogos_por_nome = (
            df_palpites.assign(NomeNorm=df_palpites["Nome"].str.strip().str.lower())
            .groupby("NomeNorm")["JogoID"]
            .apply(lambda s: set(s.astype(str)))
            .to_dict()
        )

    linhas = []
    for nome in nomes:
        nome_norm = nome.strip().lower()
        respondidos = jogos_por_nome.get(nome_norm, set())

        faltantes = df_jogos[~df_jogos["JogoID"].astype(str).isin(respondidos)]

        descricao_faltantes = [
            "{} x {} ({})".format(
                j["Time1"],
                j["Time2"],
                j["Data"].strftime("%d/%m %H:%M") if pd.notna(j.get("Data")) else "data a definir",
            )
            for _, j in faltantes.iterrows()
        ]

        linhas.append(
            {
                "Nome": nome,
                "TotalJogos": total_jogos,
                "Preenchidos": total_jogos - len(faltantes),
                "Faltando": len(faltantes),
                "JogosFaltantes": descricao_faltantes,
            }
        )

    return pd.DataFrame(linhas)


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