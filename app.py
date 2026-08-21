from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

CAMARA_BASE = "https://dadosabertos.camara.leg.br/api/v2"
HTTP = requests.Session()
HTTP.headers.update({
    "Accept": "application/json",
    "User-Agent": "FichaPublica-MVP/0.2 (projeto de transparencia civica)"
})

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
    return jsonify({"ok": True, "service": "Ficha Pública", "version": "0.2"})


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


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1")
