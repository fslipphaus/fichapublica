from unittest.mock import patch

from app import app
from services.contradicoes import detectar, demonstracao


def test_saude():
    client = app.test_client()
    response = client.get("/api/saude")
    assert response.status_code == 200
    assert response.get_json()["versao"] == "0.3.0"


def test_justica_nao_automatizada():
    response = app.test_client().get("/api/deputados/123/justica")
    body = response.get_json()
    assert body["dados"] == []
    assert body["meta"]["automatizado"] is False


def test_contradicao_demo_marcada():
    body = demonstracao()
    assert body["demo"] is True
    assert body["publicavel"] is False
    assert body["resultado"][0]["status"] == "requer_revisao_humana"


def test_motor_nao_cruza_temas_diferentes():
    posicoes = [{"tema_id": "a", "posicao": "contra"}]
    atos = [{"tema_id": "b", "posicao": "favoravel"}]
    assert detectar(posicoes, atos) == []


@patch("app.camara.deputados")
def test_proxy_deputados(mock_deputados):
    mock_deputados.return_value = {"dados": [{"id": 1, "nome": "Teste"}]}
    response = app.test_client().get("/api/deputados?nome=Teste&uf=sp")
    assert response.status_code == 200
    mock_deputados.assert_called_once_with(nome="Teste", partido="", uf="SP", pagina=1)

