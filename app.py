from __future__ import annotations

import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

import requests
from flask import Flask, jsonify, render_template, request
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

CAMARA_BASE = "https://dadosabertos.camara.leg.br/api/v2"
HTTP = requests.Session()
HTTP.headers.update({
    "Accept": "application/json",
    "User-Agent": "FichaPublica-MVP/0.3 (projeto de transparencia civica)"
})
HTTP.mount("https://", HTTPAdapter(
    max_retries=Retry(total=2, backoff_factor=0.35, status_forcelist=(429, 500, 502, 503, 504)),
    pool_connections=8,
    pool_maxsize=8,
))

CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "900"))
_cache: dict[str, tuple[float, Any]] = {}


def cached(key: str):
    item = _cache.get(key)
    if not item:
        return None
    created, value = item
    if time.time() - created > CACHE_TTL:
        _cache.pop(key, None)
        return None
    return value


def set_cache(key: str, value: Any):
    _cache[key] = (time.time(), value)


def camara_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{CAMARA_BASE}{path}"
    response = HTTP.get(url, params=params or {}, timeout=20)
    response.raise_for_status()
    return response.json()


def fetch_all_deputados() -> list[dict[str, Any]]:
    key = "deputados:all"
    hit = cached(key)
    if hit is not None:
        return hit

    deputados: list[dict[str, Any]] = []
    for pagina in range(1, 10):
        payload = camara_get(
            "/deputados",
            {
                "pagina": pagina,
                "itens": 100,
                "ordem": "ASC",
                "ordenarPor": "nome",
            },
        )
        page = payload.get("dados", [])
        deputados.extend(page)
        if len(page) < 100:
            break

    # Protege contra eventuais duplicidades sem esconder mudanças de partido no detalhe.
    unique: dict[int, dict[str, Any]] = {}
    for dep in deputados:
        dep_id = dep.get("id")
        if dep_id is not None:
            unique[int(dep_id)] = dep

    result = sorted(unique.values(), key=lambda d: (d.get("nome") or "").casefold())
    set_cache(key, result)
    return result


def fetch_paginated(path: str, params: dict[str, Any], max_pages: int = 30) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pagina in range(1, max_pages + 1):
        p = dict(params)
        p.update({"pagina": pagina, "itens": 100})
        payload = camara_get(path, p)
        page = payload.get("dados", [])
        rows.extend(page)
        if len(page) < 100:
            break
    return rows


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "Ficha Pública", "version": "0.3"})


@app.get("/api/deputados")
def api_deputados():
    try:
        deputados = fetch_all_deputados()
        q = (request.args.get("q") or "").strip().casefold()
        uf = (request.args.get("uf") or "").strip().upper()
        partido = (request.args.get("partido") or "").strip().upper()

        filtered = deputados
        if q:
            filtered = [
                d for d in filtered
                if q in " ".join([
                    str(d.get("nome") or ""),
                    str(d.get("siglaPartido") or ""),
                    str(d.get("siglaUf") or ""),
                ]).casefold()
            ]
        if uf:
            filtered = [d for d in filtered if (d.get("siglaUf") or "").upper() == uf]
        if partido:
            filtered = [d for d in filtered if (d.get("siglaPartido") or "").upper() == partido]

        parties = sorted({d.get("siglaPartido") for d in deputados if d.get("siglaPartido")})
        ufs = sorted({d.get("siglaUf") for d in deputados if d.get("siglaUf")})

        return jsonify({
            "dados": filtered,
            "meta": {
                "totalAtual": len(deputados),
                "totalFiltrado": len(filtered),
                "partidos": parties,
                "ufs": ufs,
                "fonte": "Câmara dos Deputados — Dados Abertos",
                "urlFonte": f"{CAMARA_BASE}/deputados",
                "cacheSegundos": CACHE_TTL,
            },
        })
    except requests.RequestException as exc:
        return jsonify({
            "erro": "Não foi possível consultar a Câmara dos Deputados agora.",
            "detalhe": str(exc),
        }), 502


@app.get("/api/deputados/<int:dep_id>")
def api_deputado(dep_id: int):
    key = f"deputado:{dep_id}"
    hit = cached(key)
    if hit is not None:
        return jsonify(hit)
    try:
        payload = camara_get(f"/deputados/{dep_id}")
        result = {
            "dados": payload.get("dados", {}),
            "meta": {
                "fonte": "Câmara dos Deputados — Dados Abertos",
                "urlFonte": f"{CAMARA_BASE}/deputados/{dep_id}",
            },
        }
        set_cache(key, result)
        return jsonify(result)
    except requests.RequestException as exc:
        return jsonify({"erro": "Falha ao consultar o perfil do deputado.", "detalhe": str(exc)}), 502


@app.get("/api/deputados/<int:dep_id>/despesas")
def api_despesas(dep_id: int):
    ano = request.args.get("ano", type=int) or 2026
    key = f"despesas:{dep_id}:{ano}"
    hit = cached(key)
    if hit is not None:
        return jsonify(hit)

    try:
        rows = fetch_paginated(
            f"/deputados/{dep_id}/despesas",
            {
                "ano": ano,
                "ordem": "ASC",
                "ordenarPor": "dataDocumento",
            },
            max_pages=25,
        )

        por_tipo: defaultdict[str, float] = defaultdict(float)
        total = 0.0
        for row in rows:
            raw = row.get("valorLiquido")
            if not isinstance(raw, (int, float)):
                raw = row.get("valorDocumento")
            value = float(raw or 0)
            total += value
            por_tipo[row.get("tipoDespesa") or "Outros"] += value

        categorias = [
            {"tipo": tipo, "valor": round(valor, 2)}
            for tipo, valor in sorted(por_tipo.items(), key=lambda kv: kv[1], reverse=True)
        ]

        result = {
            "dados": {
                "ano": ano,
                "total": round(total, 2),
                "quantidadeLancamentos": len(rows),
                "categorias": categorias,
            },
            "meta": {
                "fonte": "Câmara dos Deputados — Cota para o Exercício da Atividade Parlamentar",
                "urlFonte": f"{CAMARA_BASE}/deputados/{dep_id}/despesas?ano={ano}",
            },
        }
        set_cache(key, result)
        return jsonify(result)
    except requests.RequestException as exc:
        return jsonify({"erro": "Falha ao consultar despesas.", "detalhe": str(exc)}), 502


@app.get("/api/deputados/<int:dep_id>/carreira")
def api_carreira(dep_id: int):
    key = f"carreira:{dep_id}"
    hit = cached(key)
    if hit is not None:
        return jsonify(hit)
    try:
        historico = camara_get(f"/deputados/{dep_id}/historico").get("dados", [])
        mandatos = camara_get(f"/deputados/{dep_id}/mandatosExternos").get("dados", [])
        result = {
            "dados": {"historicoCamara": historico, "mandatosExternos": mandatos},
            "meta": {
                "fonte": "Câmara dos Deputados — Dados Abertos",
                "urlHistorico": f"{CAMARA_BASE}/deputados/{dep_id}/historico",
                "urlMandatos": f"{CAMARA_BASE}/deputados/{dep_id}/mandatosExternos",
            },
        }
        set_cache(key, result)
        return jsonify(result)
    except requests.RequestException as exc:
        return jsonify({"erro": "Falha ao consultar histórico político.", "detalhe": str(exc)}), 502


def fetch_votacoes_recentes(dias: int = 120, limite: int = 36) -> list[dict[str, Any]]:
    """Retorna uma amostra recente; o histórico completo requer os arquivos anuais."""
    dias = max(7, min(dias, 120))
    limite = max(1, min(limite, 60))
    fim = date.today()
    inicio = fim - timedelta(days=dias)
    key = f"votacoes:{inicio}:{fim}:{limite}"
    hit = cached(key)
    if hit is not None:
        return hit
    rows = camara_get("/votacoes", {
        "dataInicio": inicio.isoformat(),
        "dataFim": fim.isoformat(),
        "pagina": 1,
        "itens": limite,
        "ordem": "DESC",
        "ordenarPor": "dataHoraRegistro",
    }).get("dados", [])
    set_cache(key, rows)
    return rows


def fetch_votos_votacao(votacao_id: str) -> list[dict[str, Any]]:
    key = f"votos:{votacao_id}"
    hit = cached(key)
    if hit is not None:
        return hit
    rows = camara_get(f"/votacoes/{quote(votacao_id, safe='-')}/votos").get("dados", [])
    set_cache(key, rows)
    return rows


@app.get("/api/votacoes")
def api_votacoes():
    data_inicio = (request.args.get("dataInicio") or "").strip()
    data_fim = (request.args.get("dataFim") or "").strip()
    if not data_inicio or not data_fim:
        return jsonify({"erro": "Informe dataInicio e dataFim no formato AAAA-MM-DD."}), 400
    try:
        payload = camara_get("/votacoes", {
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "pagina": request.args.get("pagina", type=int) or 1,
            "itens": min(request.args.get("itens", type=int) or 30, 100),
            "ordem": "DESC",
            "ordenarPor": "dataHoraRegistro",
        })
        return jsonify({
            "dados": payload.get("dados", []),
            "links": payload.get("links", []),
            "meta": {"fonte": "Câmara dos Deputados — Votações", "urlFonte": f"{CAMARA_BASE}/votacoes"},
        })
    except requests.RequestException as exc:
        return jsonify({"erro": "Falha ao consultar votações.", "detalhe": str(exc)}), 502


@app.get("/api/votacoes/<path:votacao_id>")
def api_votacao(votacao_id: str):
    try:
        payload = camara_get(f"/votacoes/{quote(votacao_id, safe='-')}")
        return jsonify({
            "dados": payload.get("dados", {}),
            "meta": {"fonte": "Câmara dos Deputados — Votação", "urlFonte": f"{CAMARA_BASE}/votacoes/{quote(votacao_id, safe='-')}"},
        })
    except requests.RequestException as exc:
        return jsonify({"erro": "Falha ao consultar a votação.", "detalhe": str(exc)}), 502


@app.get("/api/votacoes/<path:votacao_id>/votos")
def api_votos(votacao_id: str):
    try:
        rows = fetch_votos_votacao(votacao_id)
        return jsonify({
            "dados": rows,
            "meta": {"fonte": "Câmara dos Deputados — Votos nominais", "urlFonte": f"{CAMARA_BASE}/votacoes/{quote(votacao_id, safe='-')}/votos"},
        })
    except requests.RequestException as exc:
        return jsonify({"erro": "Falha ao consultar os votos nominais.", "detalhe": str(exc)}), 502


@app.get("/api/deputados/<int:dep_id>/votacoes")
def api_votacoes_deputado(dep_id: int):
    limite = max(1, min(request.args.get("limite", type=int) or 8, 20))
    dias = request.args.get("dias", type=int) or int(os.getenv("VOTACOES_LOOKBACK_DAYS", "120"))
    scan_limit = int(os.getenv("VOTACOES_SCAN_LIMIT", "36"))
    key = f"votacoes-deputado:{dep_id}:{limite}:{dias}:{scan_limit}"
    hit = cached(key)
    if hit is not None:
        return jsonify(hit)
    try:
        votacoes = fetch_votacoes_recentes(dias, scan_limit)

        def localizar(votacao: dict[str, Any]):
            try:
                for registro in fetch_votos_votacao(str(votacao.get("id"))):
                    deputado = registro.get("deputado_") or registro.get("deputado") or {}
                    if str(deputado.get("id")) == str(dep_id):
                        return {
                            "id": votacao.get("id"),
                            "data": votacao.get("data") or str(votacao.get("dataHoraRegistro") or "")[:10],
                            "descricao": votacao.get("descricao") or "Votação nominal",
                            "descricaoUltimaAberturaVotacao": votacao.get("descricaoUltimaAberturaVotacao"),
                            "resultado": votacao.get("descricaoResultado"),
                            "aprovacao": votacao.get("aprovacao"),
                            "voto": registro.get("tipoVoto") or registro.get("voto") or "—",
                            "urlFonte": f"{CAMARA_BASE}/votacoes/{quote(str(votacao.get('id')), safe='-')}/votos",
                        }
            except requests.RequestException:
                return None
            return None

        encontrados = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(localizar, votacao) for votacao in votacoes]
            for future in as_completed(futures):
                item = future.result()
                if item:
                    encontrados.append(item)
        encontrados.sort(key=lambda item: item.get("data") or "", reverse=True)
        result = {
            "dados": encontrados[:limite],
            "meta": {
                "fonte": "Câmara dos Deputados — Votos nominais",
                "deputadoId": dep_id,
                "votacoesAnalisadas": len(votacoes),
                "janelaDias": max(7, min(dias, 120)),
                "nota": "Ausência nesta amostra não significa ausência à sessão; somente votos individualmente registrados aparecem.",
            },
        }
        set_cache(key, result)
        return jsonify(result)
    except requests.RequestException as exc:
        return jsonify({"erro": "Falha ao cruzar as votações do deputado.", "detalhe": str(exc)}), 502


DEMO_POSICOES = [{
    "id": "demo-declaracao-1", "pessoaId": None, "temaId": "tema-demonstrativo-x",
    "tipo": "declaracao", "posicao": "contra", "data": "2025-01-10",
    "texto": "Exemplo fictício: sou contra a medida X.",
    "fonteUrl": None, "fonteStatus": "placeholder_sem_fonte", "demo": True,
}]
DEMO_ATOS = [{
    "id": "demo-voto-1", "pessoaId": None, "temaId": "tema-demonstrativo-x",
    "tipo": "voto", "posicao": "favoravel", "data": "2025-06-20",
    "texto": "Exemplo fictício: voto SIM em medida relacionada a X.",
    "fonteUrl": None, "fonteStatus": "placeholder_sem_fonte", "demo": True,
}]


def detectar_contradicoes(posicoes: list[dict[str, Any]], atos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    opostos = {("favoravel", "contra"), ("contra", "favoravel")}
    return [{
        "tipo": "possivel_contradicao",
        "temaId": posicao["temaId"],
        "declaracao": posicao,
        "ato": ato,
        "confiancaMetodologica": 0.55,
        "status": "requer_revisao_humana",
        "publicavel": False,
        "alerta": "Contexto, texto votado e justificativa ainda precisam ser verificados.",
    } for posicao in posicoes for ato in atos
      if posicao.get("temaId") == ato.get("temaId")
      and (posicao.get("posicao"), ato.get("posicao")) in opostos]


@app.get("/api/deputados/<int:dep_id>/posicoes")
def api_posicoes(dep_id: int):
    return jsonify({
        "dados": [],
        "meta": {"deputadoId": dep_id, "automatizado": False},
        "aviso": "Nenhuma declaração foi atribuída automaticamente. A integração de uma fonte pública estruturada ainda está pendente.",
    })


@app.get("/api/deputados/<int:dep_id>/contradicoes")
def api_contradicoes(dep_id: int):
    result: dict[str, Any] = {
        "dados": [],
        "meta": {"deputadoId": dep_id, "automatizado": False, "publicavel": False},
        "aviso": "Nenhuma contradição real foi atribuída a este deputado.",
    }
    if request.args.get("demonstracao") == "1":
        result["demonstracao"] = {
            "demo": True,
            "publicavel": False,
            "rotulo": "EXEMPLO DEMONSTRATIVO — NÃO É DADO SOBRE O DEPUTADO",
            "posicoes": DEMO_POSICOES,
            "atos": DEMO_ATOS,
            "resultado": detectar_contradicoes(DEMO_POSICOES, DEMO_ATOS),
        }
    return jsonify(result)


@app.get("/api/deputados/<int:dep_id>/justica")
def api_justica(dep_id: int):
    return jsonify({
        "dados": [],
        "meta": {"deputadoId": dep_id, "automatizado": False},
        "aviso": "Justiça e inelegibilidade não são automatizadas até a integração oficial com TSE/Justiça.",
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
