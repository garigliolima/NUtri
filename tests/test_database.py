import json
import os
import pytest

os.environ.setdefault("DB_PATH", ":memory:")

from database import init_db, upsert_user, save_bioimpedancia, get_bioimpedancia


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    import database
    monkeypatch.setattr(database, "DB_PATH", db_file)
    init_db()
    upsert_user(123, first_name="Teste", username="teste")
    yield


def test_save_and_get_bioimpedancia():
    data = {
        "gordura_pct": 22.5,
        "massa_magra_kg": 58.3,
        "massa_gorda_kg": 17.2,
        "agua_corporal_pct": 55.1,
        "gordura_visceral": 8,
        "tmb_medida": 1820,
        "idade_metabolica": 34,
        "outros": {"massa_ossea_kg": 2.8},
    }
    save_bioimpedancia(123, data)
    result = get_bioimpedancia(123)
    assert result["gordura_pct"] == 22.5
    assert result["massa_magra_kg"] == 58.3
    assert result["outros"]["massa_ossea_kg"] == 2.8


def test_get_bioimpedancia_sem_dados():
    result = get_bioimpedancia(123)
    assert result == {}


def test_save_bioimpedancia_sobrescreve():
    save_bioimpedancia(123, {"gordura_pct": 20.0, "outros": {}})
    save_bioimpedancia(123, {"gordura_pct": 25.0, "outros": {}})
    result = get_bioimpedancia(123)
    assert result["gordura_pct"] == 25.0
