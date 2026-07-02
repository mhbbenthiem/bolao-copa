# Bolão da Copa do Mundo 2026 — Sistema em Python

Sistema simples e gratuito para gerenciar o bolão da empresa: as pessoas
registram palpites em um app web, e a classificação é calculada
automaticamente com base nos resultados reais da Copa.

## Como funciona

- **Frontend**: app Streamlit com 3 páginas (Palpites, Classificação, Admin)
- **Banco de dados**: Google Sheets (grátis, persistente, acessível de qualquer lugar)
- **Placares oficiais**: API football-data.org (grátis)
- **Hospedagem**: Streamlit Community Cloud (grátis)

## Passo a passo para configurar

### 1. Criar a planilha no Google Sheets

Crie uma planilha nova com **duas abas**:

**Aba "Jogos"** — cabeçalho na linha 1:
```
JogoID | Data | Hora | Time1 | Time2 | Grupo | PlacarReal1 | PlacarReal2 | Status
```

**Aba "Palpites"** — cabeçalho na linha 1:
```
Nome | JogoID | Placar1 | Placar2 | AtualizadoEm
```

Copie o ID da planilha a partir da URL:
`https://docs.google.com/spreadsheets/d/**ESTE-É-O-ID**/edit`

### 2. Criar a Service Account do Google (para o app acessar o Sheets)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com/)
2. Crie um projeto novo (gratuito)
3. Ative a **Google Sheets API** e a **Google Drive API**
4. Vá em "Credenciais" → "Criar credenciais" → "Conta de serviço"
5. Crie uma chave para essa conta no formato **JSON** e faça o download
6. **Importante**: abra a planilha do passo 1, clique em "Compartilhar" e
   adicione o e-mail da service account (algo como
   `nome@projeto.iam.gserviceaccount.com`) com permissão de **Editor**

### 3. Criar conta gratuita na football-data.org

1. Acesse [football-data.org/client/register](https://www.football-data.org/client/register)
2. Copie sua API key gratuita (o plano free já inclui a Copa do Mundo)

### 4. Configurar os secrets do app

Copie `.streamlit/secrets.toml.exemplo` para `.streamlit/secrets.toml` e
preencha com:
- O ID da planilha (passo 1)
- Os dados do JSON da service account (passo 2)
- Sua API key da football-data.org (passo 3)
- Uma senha de administrador de sua escolha

### 5. Rodar localmente para testar

```bash
pip install -r requirements.txt
streamlit run app.py
```

### 6. Publicar gratuitamente (Streamlit Community Cloud)

1. Suba este projeto para um repositório no GitHub (**sem** o arquivo
   `secrets.toml` real — apenas o `.exemplo`)
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta GitHub
3. Selecione o repositório e o arquivo `app.py`
4. Em "Settings → Secrets", cole o conteúdo do seu `secrets.toml` real
5. Publique — você receberá um link público (ex: `bolao-copa.streamlit.app`)
   que funciona em qualquer navegador, PC ou celular

## Sobre a regra de "editar até o jogo começar"

O app compara automaticamente a data/hora de cada jogo com o horário atual.
Jogos que já começaram aparecem travados (🔒) e não podem mais ser editados
— isso é verificado no momento em que a página carrega, sem necessidade de
travar manualmente cada jogo.

## Sobre a página Admin

A página Admin busca os jogos/placares atualizados na API e mostra uma
pré-visualização. Na primeira versão, a escrita final na planilha (aba
"Jogos") pode ser feita manualmente copiando os dados, ou você pode me
pedir para automatizar esse último passo também (gravação automática via
`gspread`, função `atualizar_placares_reais` já preparada em
`utils/sheets.py`).

## Pontuação

- **10 pontos**: acertou o placar exato
- **5 pontos**: acertou apenas o resultado (vencedor ou empate)
- **0 pontos**: errou o resultado

Essa regra está isolada em `utils/scoring.py` — fácil de ajustar se vocês
quiserem mudar os valores.
