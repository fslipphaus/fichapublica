# Ficha Pública — MVP v0.2

A v0.2 substitui os deputados fictícios por **dados consultados em tempo real na API oficial de Dados Abertos da Câmara dos Deputados**.

## O que já funciona

- Diretório atual de deputados federais, paginado no backend.
- Busca por nome, partido e UF.
- Filtros por partido e UF.
- Foto oficial, nome eleitoral, partido, UF e ID da Câmara.
- Perfil detalhado do deputado.
- Cadastro pessoal disponível na Câmara.
- Despesas parlamentares de 2026, totalizadas e agrupadas por categoria.
- Histórico parlamentar e mandatos externos retornados pela Câmara.
- Links para os endpoints oficiais em cada ficha.
- Cache de 15 minutos para evitar chamadas desnecessárias à API.
- Interface responsiva.
- Página de metodologia.

## O que propositalmente AINDA NÃO é automático

- Contradições.
- Promessas.
- Processos judiciais.
- Histórico de inelegibilidade.
- Patrimônio do TSE.
- Votações relevantes por parlamentar.
- Senadores.
- Presidência 2026.

Essas informações permanecem marcadas como próximas integrações. A aplicação não inventa dados para preencher espaços vazios.

## Rodar localmente

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Abra:

http://localhost:5000

## Publicar no Render

Este pacote inclui `render.yaml`.

1. Suba os arquivos para um repositório GitHub.
2. No Render, crie um **Blueprint** a partir do repositório.
3. O Render detectará `render.yaml`.
4. O comando de produção será `gunicorn app:app`.

## Arquitetura atual

Browser
→ Flask (`/api/...`)
→ Dados Abertos da Câmara
→ cache em memória
→ resposta JSON
→ interface Ficha Pública

O proxy Flask evita depender diretamente de CORS no navegador e nos dá um ponto central para cache, logs, validação e futuras integrações com IA.

## Próxima etapa sugerida — v0.3

1. Integrar votações nominais.
2. Construir a tabela `statement` / `position` para falas públicas.
3. Criar detector de possíveis contradições.
4. Integrar TSE para situação eleitoral, patrimônio e candidaturas.
5. Criar revisão editorial para registros sensíveis.
