# Ficha Pública — MVP v0.3

Esta versão foi construída **diretamente sobre a v0.2**, preservando sua arquitetura Flask, interface azul, navegação por hash, diretório, ficha, despesas, histórico e metodologia. A novidade principal é a integração inicial de votos nominais reais da Câmara e a base auditável para posições e possíveis contradições.

## O que continua igual à v0.2

- Aplicação Flask simples (`app.py`) com frontend em `static/app.js`.
- Mesma identidade visual e estrutura responsiva.
- Diretório dos deputados federais, busca e filtros.
- Perfil, foto, partido, UF, cadastro oficial, despesas e carreira.
- Cache em memória e links para os endpoints oficiais.
- Justiça e inelegibilidade sem preenchimento automático.

## O que entrou na v0.3

- Consulta de votações da Câmara por período.
- Detalhes de uma votação e seus votos nominais.
- Cruzamento de uma amostra de votações recentes para localizar votos de cada deputado.
- Painel de votações reais recentes na ficha existente.
- Menu, cartões e abas da ficha com links funcionais e URLs compartilháveis.
- Estrutura JSON para declaração, voto/ato, tema, posição e estado da fonte.
- Motor inicial, determinístico e explicável, de candidatos a contradição.
- Exemplo fictício separado e marcado como **não publicável**.
- Health check e Blueprint do Render explicitamente no plano gratuito.

## Fonte oficial e limitações

A integração factual usa `https://dadosabertos.camara.leg.br/api/v2`.

A API oferece `/votacoes` e `/votacoes/{id}/votos`, mas não um endpoint direto de “todos os votos de um deputado”. A ficha busca uma janela de votações recentes, consulta em paralelo os registros nominais, seleciona os registros do deputado e mantém o resultado em cache.

É uma **amostra recente**, não um histórico completo. Votações simbólicas normalmente não têm votos individuais, e ausência na lista não significa ausência à sessão. Para escala e histórico completo, uma versão futura deverá importar os arquivos anuais `votacoes`, `votacoesVotos`, `votacoesProposicoes` e `votacoesObjetos` para um banco persistente.

## Endpoints

| Endpoint | Função |
|---|---|
| `GET /api/health` | Saúde e versão |
| `GET /api/deputados` | Diretório completo |
| `GET /api/deputados/{id}` | Cadastro oficial |
| `GET /api/deputados/{id}/despesas?ano=2026` | Despesas agregadas |
| `GET /api/deputados/{id}/carreira` | Histórico e mandatos externos |
| `GET /api/votacoes?dataInicio=AAAA-MM-DD&dataFim=AAAA-MM-DD` | Votações no período |
| `GET /api/votacoes/{id}` | Detalhe da votação |
| `GET /api/votacoes/{id}/votos` | Votos nominais oficiais |
| `GET /api/deputados/{id}/votacoes?limite=8&dias=120` | Votos recentes do deputado |
| `GET /api/deputados/{id}/posicoes` | Estrutura futura; lista vazia |
| `GET /api/deputados/{id}/contradicoes` | Casos reais; lista vazia |
| `GET /api/deputados/{id}/contradicoes?demonstracao=1` | Exemplo fictício marcado |
| `GET /api/deputados/{id}/justica` | Não automatizado; lista vazia |

## Navegação da ficha

As abas agora são links reais. Uma seção pode ser aberta ou compartilhada diretamente:

- `#deputado/204534/visao-geral`
- `#deputado/204534/votacoes`
- `#deputado/204534/despesas`
- `#deputado/204534/historico`
- `#deputado/204534/contradicoes`
- `#deputado/204534/justica`
- `#deputado/204534/eleicoes`

Quando uma fonte oficial não está disponível naquele acesso, a interface mostra uma mensagem em vez de criar um link vazio para `#`.

## Posições e contradições

O contrato inicial está em `data/posicoes.schema.json`. O motor compara somente dados explicitamente fornecidos e só cria um candidato quando encontra o mesmo tema com posições opostas (`favoravel` × `contra`). Toda saída exige revisão humana e é não publicável por padrão.

A demonstração local não usa nome de pessoa real, não possui fonte e aparece em campo separado. Nenhuma declaração ou contradição é atribuída automaticamente a um deputado nesta versão.

## Justiça e inelegibilidade

Continuam deliberadamente não automatizadas até uma integração confiável com TSE e fontes oficiais da Justiça. Campo vazio significa **não integrado**, e nunca “sem processos” ou “elegível”.

## Rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abra `http://localhost:5000`.

## Testes

```bash
pip install pytest
pytest -q
```

## Publicar no GitHub e Render

1. Extraia o ZIP e envie o conteúdo da pasta para um repositório GitHub.
2. No Render, use **New → Blueprint** e conecte o repositório.
3. Confirme a instância **Free — $0/month** antes de concluir.
4. O Blueprint executará `gunicorn app:app` e verificará `/api/health`.

O `render.yaml` contém explicitamente `plan: free`.

## Variáveis

- `CACHE_TTL_SECONDS=900`: cache local.
- `VOTACOES_LOOKBACK_DAYS=120`: janela recente.
- `VOTACOES_SCAN_LIMIT=36`: votações inspecionadas por ficha.
- `PORT`: definida pelo Render.

## Arquitetura preservada

```text
Browser / SPA existente
        ↓
Flask (app.py)
        ↓
Dados Abertos da Câmara
        ↓
cache em memória
        ↓
ficha e painéis existentes
```

## Roadmap

1. Importação incremental dos arquivos anuais em PostgreSQL.
2. Associação auditável entre votação, proposição, destaques e temas.
3. Pipeline de declarações com URL, trecho, data e cópia da fonte.
4. Fila de revisão editorial humana.
5. Integração TSE/Justiça antes de preencher elegibilidade ou processos.
