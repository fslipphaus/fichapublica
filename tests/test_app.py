from unittest.mock import patch

from app import app, detectar_contradicoes


def test_health_v03():
    response = app.test_client().get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["version"] == "0.3"


def test_justica_continua_nao_automatizada():
    body = app.test_client().get("/api/deputados/123/justica").get_json()
    assert body["dados"] == []
    assert body["meta"]["automatizado"] is False


def test_demonstracao_nao_publicavel():
    body = app.test_client().get("/api/deputados/123/contradicoes?demonstracao=1").get_json()
    assert body["dados"] == []
    assert body["demonstracao"]["demo"] is True
    assert body["demonstracao"]["publicavel"] is False


def test_motor_exige_mesmo_tema_e_oposicao():
    posicoes = [{"temaId": "a", "posicao": "contra"}]
    atos = [{"temaId": "b", "posicao": "favoravel"}]
    assert detectar_contradicoes(posicoes, atos) == []


@patch("app.fetch_votacoes_recentes")
@patch("app.fetch_votos_votacao")
def test_cruzamento_de_voto_nominal(mock_votos, mock_votacoes):
    mock_votacoes.return_value = [{"id": "1-2", "data": "2026-08-12", "descricao": "Teste"}]
    mock_votos.return_value = [{"tipoVoto": "Sim", "deputado_": {"id": 123}}]
    body = app.test_client().get("/api/deputados/123/votacoes").get_json()
    assert body["dados"][0]["voto"] == "Sim"
    assert body["meta"]["deputadoId"] == 123

