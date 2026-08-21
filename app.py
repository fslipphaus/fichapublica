from __future__ import annotations

import os
from collections import defaultdict
from datetime import date

from flask import Flask, jsonify, render_template, request

from services.camara import API_BASE, CamaraClient, CamaraError
from services.contradicoes import demonstracao


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
camara = CamaraClient()


def api_error(exc: Exception, status: int = 502):
    return jsonify({"erro": str(exc), "fonte": "Câmara dos Deputados", "tenteNovamente": True}), status


@app.errorhandler(CamaraError)
def handle_camara_error(exc: CamaraError):
    return api_error(exc)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/deputados/<int:deputado_id>")
def ficha(deputado_id: int):
    try:
        payload = camara.deputado(deputado_id)
        deputado = payload.get("dados", {})
    except CamaraError as exc:
        return render_template("erro.html", mensagem=str(exc)), 502
    return render_template("deputado.html", deputado=deputado, api_base=API_BASE)


@app.get("/api/saude")
def saude():
    return jsonify({"status": "ok", "versao": "0.3.0", "data": date.today().isoformat()})


@app.get("/api/deputados")
def api_deputados():
    return jsonify(camara.deputados(
        nome=request.args.get("nome", "").strip(),
        partido=request.args.get("partido", "").strip().upper(),
        uf=request.args.get("uf", "").strip().upper(),
        pagina=request.args.get("pagina", 1, type=int) or 1,
    ))


@app.get("/api/deputados/<int:deputado_id>")
def api_deputado(deputado_id: int):
    return jsonify(camara.deputado(deputado_id))


@app.get("/api/deputados/<int:deputado_id>/despesas")
def api_despesas(deputado_id: int):
    ano = request.args.get("ano", date.today().year, type=int)
    dados = camara.despesas(deputado_id, ano).get("dados", [])
    categorias = defaultdict(float)
    total = 0.0
    for despesa in dados:
        valor = float(despesa.get("valorLiquido") or 0)
        total += valor
        categorias[despesa.get("tipoDespesa") or "Outros"] += valor
    ranking = sorted(
        ({"categoria": nome, "valor": valor} for nome, valor in categorias.items()),
        key=lambda item: item["valor"], reverse=True,
    )
    return jsonify({"dados": dados, "resumo": {"ano": ano, "total": total, "categorias": ranking[:8]}})


@app.get("/api/votacoes")
def api_votacoes():
    inicio = request.args.get("dataInicio", "")
    fim = request.args.get("dataFim", "")
    if not inicio or not fim:
        return jsonify({"erro": "dataInicio e dataFim são obrigatórios (AAAA-MM-DD)."}), 400
    return jsonify(camara.votacoes(inicio, fim, request.args.get("pagina", 1, type=int) or 1,
                                   request.args.get("itens", 30, type=int) or 30))


@app.get("/api/votacoes/<path:votacao_id>")
def api_votacao(votacao_id: str):
    return jsonify(camara.votacao(votacao_id))


@app.get("/api/votacoes/<path:votacao_id>/votos")
def api_votos(votacao_id: str):
    return jsonify(camara.votos(votacao_id))


@app.get("/api/deputados/<int:deputado_id>/votacoes")
def api_votos_deputado(deputado_id: int):
    return jsonify(camara.votos_recentes_deputado(
        deputado_id,
        limite=request.args.get("limite", 8, type=int) or 8,
        dias=request.args.get("dias", type=int),
    ))


@app.get("/api/deputados/<int:deputado_id>/posicoes")
def api_posicoes(deputado_id: int):
    return jsonify({
        "dados": [], "meta": {"deputadoId": deputado_id, "automatizado": False},
        "aviso": "Ainda não há fonte pública estruturada integrada para declarações. Nenhuma posição foi atribuída automaticamente.",
    })


@app.get("/api/deputados/<int:deputado_id>/contradicoes")
def api_contradicoes(deputado_id: int):
    incluir_demo = request.args.get("demonstracao", "0") == "1"
    body = {
        "dados": [], "meta": {"deputadoId": deputado_id, "automatizado": False, "publicavel": False},
        "aviso": "Nenhuma contradição real foi atribuída. Casos futuros exigirão fontes, contexto e revisão humana.",
    }
    if incluir_demo:
        body["demonstracao"] = demonstracao()
    return jsonify(body)


@app.get("/api/deputados/<int:deputado_id>/justica")
def api_justica(deputado_id: int):
    return jsonify({
        "dados": [], "meta": {"deputadoId": deputado_id, "automatizado": False},
        "aviso": "Justiça e inelegibilidade não são automatizadas nesta versão. Aguardando integração oficial com TSE/Justiça.",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")

