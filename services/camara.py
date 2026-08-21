"""Cliente e agregações da API oficial Dados Abertos da Câmara."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.cache import TTLCache


API_BASE = "https://dadosabertos.camara.leg.br/api/v2"


class CamaraError(RuntimeError):
    pass


class CamaraClient:
    def __init__(self) -> None:
        ttl = int(os.getenv("CACHE_TTL_SECONDS", "900"))
        self.cache = TTLCache(ttl)
        self.session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.35, status_forcelist=(429, 500, 502, 503, 504))
        self.session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8))
        self.session.headers.update({"Accept": "application/json", "User-Agent": "FichaPublica/0.3"})

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        clean = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        key = f"{path}:{sorted(clean.items())}"

        def fetch() -> dict[str, Any]:
            try:
                response = self.session.get(f"{API_BASE}{path}", params=clean, timeout=(4, 14))
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                raise CamaraError(f"A fonte oficial da Câmara está indisponível no momento: {exc}") from exc

        return self.cache.get_or_set(key, fetch)

    def deputados(self, nome: str = "", partido: str = "", uf: str = "", pagina: int = 1) -> dict[str, Any]:
        return self._get("/deputados", {
            "nome": nome, "siglaPartido": partido, "siglaUf": uf,
            "pagina": pagina, "itens": 24, "ordem": "ASC", "ordenarPor": "nome",
        })

    def deputado(self, deputado_id: int) -> dict[str, Any]:
        return self._get(f"/deputados/{deputado_id}")

    def despesas(self, deputado_id: int, ano: int | None = None) -> dict[str, Any]:
        return self._get(f"/deputados/{deputado_id}/despesas", {
            "ano": ano or date.today().year, "itens": 100, "ordem": "DESC", "ordenarPor": "dataDocumento",
        })

    def votacoes(self, data_inicio: str, data_fim: str, pagina: int = 1, itens: int = 30) -> dict[str, Any]:
        return self._get("/votacoes", {
            "dataInicio": data_inicio, "dataFim": data_fim, "pagina": pagina,
            "itens": min(itens, 100), "ordem": "DESC", "ordenarPor": "dataHoraRegistro",
        })

    def votacao(self, votacao_id: str) -> dict[str, Any]:
        return self._get(f"/votacoes/{quote(votacao_id, safe='-')}")

    def votos(self, votacao_id: str) -> dict[str, Any]:
        return self._get(f"/votacoes/{quote(votacao_id, safe='-')}/votos")

    def votos_recentes_deputado(
        self, deputado_id: int, limite: int = 8, dias: int | None = None, scan_limit: int | None = None
    ) -> dict[str, Any]:
        """Cruza votações recentes e votos nominais, pois a API não filtra votos por deputado."""
        limite = max(1, min(limite, 20))
        dias = dias or int(os.getenv("VOTACOES_LOOKBACK_DAYS", "120"))
        scan_limit = scan_limit or int(os.getenv("VOTACOES_SCAN_LIMIT", "36"))
        fim = date.today()
        # O endpoint rejeita janelas muito extensas; o histórico completo deve vir
        # dos arquivos anuais, conforme documentado no README.
        dias = max(7, min(dias, 120))
        inicio = fim - timedelta(days=dias)
        lista = self.votacoes(inicio.isoformat(), fim.isoformat(), itens=min(scan_limit, 100)).get("dados", [])
        lista = lista[:scan_limit]

        encontrados: list[dict[str, Any]] = []

        def procurar(votacao: dict[str, Any]) -> dict[str, Any] | None:
            try:
                votos = self.votos(str(votacao.get("id"))).get("dados", [])
            except CamaraError:
                return None
            for registro in votos:
                deputado = registro.get("deputado_") or registro.get("deputado") or {}
                if str(deputado.get("id")) == str(deputado_id):
                    return {
                        "id": votacao.get("id"),
                        "data": votacao.get("data") or str(votacao.get("dataHoraRegistro", ""))[:10],
                        "descricao": votacao.get("descricao") or "Votação nominal",
                        "descricaoUltimaAberturaVotacao": votacao.get("descricaoUltimaAberturaVotacao"),
                        "aprovacao": votacao.get("aprovacao"),
                        "resultado": votacao.get("descricaoResultado"),
                        "voto": registro.get("tipoVoto") or registro.get("voto"),
                        "deputado": deputado,
                        "fonte": f"{API_BASE}/votacoes/{quote(str(votacao.get('id')), safe='-')}/votos",
                    }
            return None

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(procurar, item) for item in lista]
            for future in as_completed(futures):
                found = future.result()
                if found:
                    encontrados.append(found)

        encontrados.sort(key=lambda item: item.get("data") or "", reverse=True)
        return {
            "dados": encontrados[:limite],
            "meta": {
                "deputadoId": deputado_id, "votacoesAnalisadas": len(lista),
                "janelaDias": dias, "limite": limite,
                "nota": "Ausência nesta lista não significa ausência em plenário; só votos nominais registrados aparecem.",
            },
        }
