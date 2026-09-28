import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_index_view():
    response = client.get("/")
    assert response.status_code == 200
    assert "pinpoint" in response.text.lower()



def test_get_catalog():
    response = client.get("/api/game/catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_game_flow():
    create_res = client.post("/api/game/new", json={"language": "spa", "synset_id": "tree.n.01"})
    assert create_res.status_code == 201
    session_data = create_res.json()
    session_id = session_data["session_id"]
    assert len(session_data["revealed_clues"]) == 1

    wrong_guess_res = client.post("/api/game/guess", json={"session_id": session_id, "guess": "computadora"})
    assert wrong_guess_res.status_code == 200
    wrong_data = wrong_guess_res.json()
    assert wrong_data["is_correct"] is False
    assert len(wrong_data["revealed_clues"]) == 2

    reveal_res = client.post("/api/game/reveal", json={"session_id": session_id})
    assert reveal_res.status_code == 200
    reveal_data = reveal_res.json()
    assert len(reveal_data["revealed_clues"]) == 3

    correct_guess_res = client.post("/api/game/guess", json={"session_id": session_id, "guess": "los árboles"})
    assert correct_guess_res.status_code == 200
    correct_data = correct_guess_res.json()
    assert correct_data["is_correct"] is True
    assert correct_data["is_game_over"] is True
    assert correct_data["score"] > 0
