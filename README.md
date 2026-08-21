# Ficha Pública v0.3

MVP em Flask para consultar deputados federais e votos nominais reais recentes usando a API oficial de Dados Abertos da Câmara dos Deputados.

> Princípio editorial: **não confie na gente; confira a fonte.**

## O que há nesta versão

- Diretório de deputados com busca por nome, partido e UF.
- Ficha individual com cadastro e foto oficiais.
- Consulta de despesas e resumo por categoria.
- Endpoints de votações, detalhes e votos nominais.
- Cruzamento de votações recentes para localizar votos de um deputado.
- Estrutura JSON para declarações, posições, atos e fontes.
- Motor inicial, determinístico e explicável, de candidatos a contradição.
- Exemplo de contradição totalmente fictício, separado dos dados reais e marcado como **não publicável**.
- Justiça e inelegibilidade deliberadamente vazias e não automatizadas.
- Cache em memória e limites adequados a uma instância gratuita do Render.

## Fontes e limites

A fonte factual integrada é `https://dadosabertos.camara.leg.br/api/v2`.

A Câmara expõe `GET /votacoes`, `GET /votacoes/{id}` e `GET /votacoes/{id}/votos`, mas não oferece na API REST um filtro direto para “todos os votos de um deputado”. Por isso, `/api/deputados/{id}/votacoes`:

1. busca uma janela de votações recentes;
2. consulta em paralelo os votos nominais de cada uma;
3. seleciona os registros do deputado;
4. aplica cache por 15 minutos.

Isso é uma amostra recente, não o histórico completo. Votações simbólicas normalmente não têm votos individuais; deputados ausentes também não aparecem em `/votos`. A própria Câmara alerta que a associação entre votação e proposição pode ser imperfeita, especialmente em destaques e proposições acessórias. A interface explicita essas limitações.

Para escala e histórico completo, a próxima versão deve importar diariamente os arquivos anuais `votacoes`, `votacoesVotos`, `votacoesProposicoes` e `votacoesObjetos` para um banco persistente.

## Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/saude` | Saúde e versão |
| GET | `/api/deputados?nome=&partido=&uf=&pagina=` | Busca de deputados |
| GET | `/api/deputados/{id}` | Cadastro oficial |
| GET | `/api/deputados/{id}/despesas?ano=` | Despesas e resumo |
| GET | `/api/votacoes?dataInicio=&dataFim=&pagina=&itens=` | Votações no período |
| GET | `/api/votacoes/{id}` | Detalhe de uma votação |
| GET | `/api/votacoes/{id}/votos` | Votos nominais da votação |
| GET | `/api/deputados/{id}/votacoes?limite=&dias=` | Votos recentes do deputado |
| GET | `/api/deputados/{id}/posicoes` | Estrutura futura; retorna vazio |
| GET | `/api/deputados/{id}/contradicoes` | Casos reais; retorna vazio |
| GET | `/api/deputados/{id}/contradicoes?demonstracao=1` | Inclui exemplo fictício marcado |
| GET | `/api/deputados/{id}/justica` | Não automatizado; retorna vazio |

IDs de votação podem conter hífen; o backend aceita o identificador completo.

## Modelo de posições e contradições

O contrato inicial está em `data/posicoes.schema.json`. Uma posição exige pessoa, tema, natureza do ato, orientação, data e estado da fonte. O motor só gera um candidato quando encontra:

- o mesmo `tema_id`;
- posições opostas (`favoravel` × `contra`);
- dois registros explicitamente fornecidos.

A saída é sempre `requer_revisao_humana`. Não há classificação por IA, inferência de tema ou publicação automática nesta versão. Antes de publicar um caso real, será necessário verificar o texto efetivamente votado, o contexto temporal, mudanças no projeto, justificativas do parlamentar e as fontes primárias.

## Justiça e inelegibilidade

Não são inferidas a partir de notícias, nomes ou buscas genéricas. O endpoint retorna lista vazia até haver integração confiável com TSE e sistemas oficiais da Justiça, além de regras de atualização e revisão. Um campo vazio significa **não integrado**, nunca “sem processos” ou “elegível”.

## Execução local

Requer Python 3.11 ou superior.

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

Os testes não dependem da internet: validam saúde, rotas sensíveis, marcação do conteúdo demonstrativo e regras básicas do motor.

## Publicação no GitHub e Render

1. Extraia o ZIP e envie o conteúdo da pasta para um repositório GitHub.
2. No Render, escolha **New → Blueprint** e conecte o repositório.
3. O Render lerá `render.yaml`.
4. Confirme que aparece `plan: free` / instância gratuita antes de concluir.
5. Aguarde o health check em `/api/saude`.

O serviço inicia com `gunicorn app:app`. Nenhum banco ou segredo é necessário nesta versão.

### Variáveis de ambiente

- `CACHE_TTL_SECONDS=900`: duração do cache local.
- `VOTACOES_LOOKBACK_DAYS=120`: janela padrão de busca.
- `VOTACOES_SCAN_LIMIT=36`: máximo de votações inspecionadas por ficha.
- `PORT`: definida automaticamente pelo Render.

## Estrutura

```text
app.py                         rotas Flask e API
services/camara.py             cliente da Câmara e cruzamento de votos
services/cache.py              cache TTL em memória
services/contradicoes.py       motor inicial + demonstração fictícia
data/posicoes.schema.json      contrato dos dados editoriais
templates/                     páginas HTML
static/css/style.css           identidade visual responsiva
tests/test_app.py              testes automatizados
render.yaml                    Blueprint Render no plano free
```

## Roadmap recomendado

1. Banco PostgreSQL e importação incremental dos arquivos anuais da Câmara.
2. Associação auditável entre votação, proposição principal, destaques e temas.
3. Pipeline de declarações com captura de trecho, URL, data e cópia da fonte.
4. Fila de revisão humana e histórico de decisões editoriais.
5. Integração TSE/Justiça antes de preencher elegibilidade ou processos.
6. Senado e candidaturas presidenciais somente após estabilizar os contratos de fonte.

## Aviso editorial

“Possível contradição” é uma hipótese de análise, não uma afirmação sobre intenção, honestidade ou legalidade. Dados demonstrativos nunca devem ser misturados a perfis reais. Todo dado factual deve manter link para a fonte e data de atualização.

