"""Motor inicial e explicável de candidatos a contradição.

Nesta versão, ele só opera sobre dados fornecidos explicitamente. O exemplo local é
didático, não descreve pessoa real e nunca deve ser publicado como constatação.
"""

from __future__ import annotations

from typing import Any


OPPOSTOS = {("favoravel", "contra"), ("contra", "favoravel")}


def detectar(posicoes: list[dict[str, Any]], atos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidatos = []
    for posicao in posicoes:
        for ato in atos:
            mesmo_tema = posicao.get("tema_id") and posicao.get("tema_id") == ato.get("tema_id")
            opostos = (posicao.get("posicao"), ato.get("posicao")) in OPPOSTOS
            if mesmo_tema and opostos:
                candidatos.append({
                    "tipo": "possivel_contradicao",
                    "tema_id": posicao["tema_id"],
                    "declaracao": posicao,
                    "ato": ato,
                    "confianca_metodologica": 0.55,
                    "status": "requer_revisao_humana",
                    "alerta": "Correspondência temática automática; contexto, texto votado e justificativa ainda precisam ser verificados.",
                })
    return candidatos


DEMONSTRACAO = {
    "demo": True,
    "publicavel": False,
    "rotulo": "EXEMPLO DEMONSTRATIVO — NÃO É DADO SOBRE O DEPUTADO",
    "posicoes": [{
        "id": "demo-declaracao-1", "pessoa_id": None, "tema_id": "demo-tema-x",
        "tipo": "declaracao", "posicao": "contra", "texto": "Exemplo: sou contra a medida X.",
        "data": "2025-01-10", "fonte_url": None, "fonte_status": "placeholder_sem_fonte",
    }],
    "atos": [{
        "id": "demo-voto-1", "pessoa_id": None, "tema_id": "demo-tema-x",
        "tipo": "voto", "posicao": "favoravel", "texto": "Exemplo: voto SIM em medida relacionada a X.",
        "data": "2025-06-20", "fonte_url": None, "fonte_status": "placeholder_sem_fonte",
    }],
}


def demonstracao() -> dict[str, Any]:
    return {**DEMONSTRACAO, "resultado": detectar(DEMONSTRACAO["posicoes"], DEMONSTRACAO["atos"])}

