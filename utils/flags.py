"""
Converte o nome de um time/seleção em uma imagem de bandeira (via flagcdn.com).

Funciona tanto com nomes em inglês (como vêm da football-data.org, ex:
"Brazil", "Germany") quanto em português (ex: "Brasil", "Alemanha"), então
funciona independente de como os nomes estão escritos na planilha.

Usamos imagens (flagcdn.com) em vez de emoji porque emoji de bandeira
depende da fonte do sistema operacional — no Windows, por exemplo, a
maioria dos navegadores não tem essas fontes e mostra só a sigla do país
(ex: "BR") em vez do desenho da bandeira. Com imagem, funciona igual em
qualquer aparelho.

Se o nome não for reconhecido (ex: placeholders de fase eliminatória como
"Vencedor Grupo A", ou time ainda vazio), retorna uma bolinha de futebol ⚽
no lugar da bandeira.
"""

import unicodedata
import pandas as pd

# nome normalizado (minúsculo, sem acento) -> código usado pelo flagcdn.com
# (é o código ISO 3166-1 alpha-2 em minúsculo; para países do Reino Unido,
# o flagcdn também aceita os códigos de subdivisão gb-eng/gb-sct/gb-wls/gb-nir)
_PAISES_CODIGO = {
    # --- nomes em inglês (como a football-data.org costuma retornar) ---
    "brazil": "br", "argentina": "ar", "germany": "de", "spain": "es",
    "france": "fr", "england": "gb-eng", "portugal": "pt",
    "netherlands": "nl", "belgium": "be", "croatia": "hr",
    "uruguay": "uy", "colombia": "co", "mexico": "mx", "usa": "us",
    "united states": "us", "canada": "ca", "japan": "jp",
    "south korea": "kr", "korea republic": "kr", "morocco": "ma",
    "senegal": "sn", "ghana": "gh", "cameroon": "cm", "tunisia": "tn",
    "egypt": "eg", "nigeria": "ng", "algeria": "dz",
    "saudi arabia": "sa", "iran": "ir", "ir iran": "ir", "qatar": "qa",
    "australia": "au", "ecuador": "ec", "chile": "cl", "peru": "pe",
    "paraguay": "py", "bolivia": "bo", "venezuela": "ve",
    "costa rica": "cr", "panama": "pa", "jamaica": "jm", "poland": "pl",
    "serbia": "rs", "switzerland": "ch", "denmark": "dk", "sweden": "se",
    "norway": "no", "wales": "gb-wls", "scotland": "gb-sct",
    "northern ireland": "gb-nir", "republic of ireland": "ie",
    "ireland": "ie", "italy": "it", "austria": "at",
    "czech republic": "cz", "czechia": "cz", "slovakia": "sk",
    "slovenia": "si", "hungary": "hu", "romania": "ro", "ukraine": "ua",
    "turkey": "tr", "turkiye": "tr", "greece": "gr", "finland": "fi",
    "iceland": "is", "new zealand": "nz", "china": "cn", "china pr": "cn",
    "india": "in", "south africa": "za", "ivory coast": "ci",
    "cote d'ivoire": "ci", "côte d'ivoire": "ci", "mali": "ml",
    "dr congo": "cd", "congo dr": "cd", "united arab emirates": "ae",
    "iraq": "iq", "jordan": "jo", "uzbekistan": "uz", "curacao": "cw",
    "curaçao": "cw", "haiti": "ht", "honduras": "hn", "suriname": "sr",
    "cape verde": "cv", "new caledonia": "nc",
    "bosnia and herzegovina": "ba", "russia": "ru",

    # --- nomes em português ---
    "brasil": "br", "alemanha": "de", "espanha": "es", "franca": "fr",
    "frança": "fr", "inglaterra": "gb-eng", "holanda": "nl",
    "paises baixos": "nl", "países baixos": "nl", "belgica": "be",
    "bélgica": "be", "croacia": "hr", "croácia": "hr", "uruguai": "uy",
    "colombia": "co", "colômbia": "co", "mexico": "mx", "méxico": "mx",
    "estados unidos": "us", "canada": "ca", "canadá": "ca",
    "japao": "jp", "japão": "jp", "coreia do sul": "kr",
    "coréia do sul": "kr", "marrocos": "ma", "gana": "gh",
    "camaroes": "cm", "camarões": "cm", "tunisia": "tn", "tunísia": "tn",
    "egito": "eg", "nigeria": "ng", "nigéria": "ng", "argelia": "dz",
    "argélia": "dz", "arabia saudita": "sa", "arábia saudita": "sa",
    "ira": "ir", "irã": "ir", "catar": "qa", "australia": "au",
    "austrália": "au", "equador": "ec", "chile": "cl", "peru": "pe",
    "paraguai": "py", "bolivia": "bo", "bolívia": "bo",
    "venezuela": "ve", "costa rica": "cr", "panama": "pa",
    "panamá": "pa", "jamaica": "jm", "polonia": "pl", "polônia": "pl",
    "servia": "rs", "sérvia": "rs", "suica": "ch", "suíça": "ch",
    "dinamarca": "dk", "suecia": "se", "suécia": "se", "noruega": "no",
    "pais de gales": "gb-wls", "país de gales": "gb-wls",
    "escocia": "gb-sct", "escócia": "gb-sct", "irlanda": "ie",
    "italia": "it", "itália": "it", "austria": "at", "áustria": "at",
    "republica tcheca": "cz", "república tcheca": "cz",
    "eslovaquia": "sk", "eslováquia": "sk", "eslovenia": "si",
    "eslovênia": "si", "hungria": "hu", "romenia": "ro",
    "romênia": "ro", "ucrania": "ua", "ucrânia": "ua", "turquia": "tr",
    "grecia": "gr", "grécia": "gr", "finlandia": "fi", "finlândia": "fi",
    "islandia": "is", "islândia": "is", "nova zelandia": "nz",
    "nova zelândia": "nz", "india": "in", "índia": "in",
    "africa do sul": "za", "áfrica do sul": "za",
    "costa do marfim": "ci", "republica democratica do congo": "cd",
    "república democrática do congo": "cd",
    "emirados arabes unidos": "ae", "emirados árabes unidos": "ae",
    "iraque": "iq", "jordania": "jo", "jordânia": "jo",
    "uzbequistao": "uz", "uzbequistão": "uz", "cabo verde": "cv",
    "nova caledonia": "nc", "nova caledônia": "nc",
    "bosnia": "ba", "bósnia": "ba", "russia": "ru", "rússia": "ru",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().lower()


# pares (largura, altura) válidos no flagcdn.com (proporção 4:3 fixa) —
# usar qualquer outro valor (ex: w44) retorna 404
_TAMANHOS_VALIDOS = [
    (16, 12), (20, 15), (24, 18), (28, 21), (32, 24), (36, 27), (40, 30),
    (48, 36), (56, 42), (60, 45), (64, 48), (72, 54), (80, 60), (84, 63),
    (96, 72), (108, 81), (112, 84), (120, 90), (128, 96), (144, 108),
    (160, 120), (192, 144), (224, 168), (256, 192),
]


def _preset_mais_proximo(altura_desejada: int):
    return min(_TAMANHOS_VALIDOS, key=lambda par: abs(par[1] - altura_desejada))


def bandeira_url(nome_time, largura: int = 24, altura: int = 18) -> str | None:
    """
    Retorna a URL da imagem da bandeira (flagcdn.com) para o nome do
    time/seleção informado, no tamanho WxH indicado (deve ser um dos
    tamanhos fixos aceitos pelo flagcdn — ver _TAMANHOS_VALIDOS), ou None
    se o time não for reconhecido.
    """
    if nome_time is None or (isinstance(nome_time, float) and pd.isna(nome_time)):
        return None

    texto = str(nome_time).strip()
    if not texto:
        return None

    codigo = _PAISES_CODIGO.get(_normalizar(texto))
    if not codigo:
        return None

    return f"https://flagcdn.com/{largura}x{altura}/{codigo}.png"


def bandeira_html(nome_time, altura_px: int = 18) -> str:
    """
    Retorna um <img> pronto para uso em st.markdown(unsafe_allow_html=True)
    com a bandeira do time, incluindo srcset para telas retina (2x/3x),
    igual ao padrão recomendado pelo próprio flagcdn.com. Se não reconhecer
    o time, retorna o emoji ⚽ como alternativa (não depende de fonte, é
    suportado em todo lugar).
    """
    largura, altura = _preset_mais_proximo(altura_px)

    url_1x = bandeira_url(nome_time, largura, altura)
    if not url_1x:
        return "⚽"

    candidatos_2x = (largura * 2, altura * 2)
    candidatos_3x = (largura * 3, altura * 3)

    partes_srcset = []
    if candidatos_2x in _TAMANHOS_VALIDOS:
        partes_srcset.append(f"{bandeira_url(nome_time, *candidatos_2x)} 2x")
    if candidatos_3x in _TAMANHOS_VALIDOS:
        partes_srcset.append(f"{bandeira_url(nome_time, *candidatos_3x)} 3x")

    srcset_attr = f' srcset="{", ".join(partes_srcset)}"' if partes_srcset else ""

    return (
        f'<img src="{url_1x}"{srcset_attr} width="{largura}" height="{altura}" alt="" '
        f'style="vertical-align:middle;border-radius:3px;'
        f'box-shadow:0 0 0 1px rgba(255,255,255,.15);margin-right:2px;" />'
    )