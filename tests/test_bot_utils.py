import sys
import os
from unittest.mock import Mock, patch

# Garante que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock das variáveis de ambiente antes de importar bot
os.environ.setdefault("TELEGRAM_TOKEN", "fake_token")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake_key")
os.environ.setdefault("DB_PATH", ":memory:")

# Mock anthropic client para evitar problemas de inicialização
with patch("anthropic.Anthropic"):
    from bot import _detectar_bioimpedancia


def test_detectar_bioimpedancia_por_palavra_chave():
    assert _detectar_bioimpedancia("minha bioimpedância chegou") is True
    assert _detectar_bioimpedancia("tenho 22% gordura e massa magra 58kg") is True
    assert _detectar_bioimpedancia("minha tmb: 1820 kcal") is True
    assert _detectar_bioimpedancia("arquivo inbody 270") is True
    assert _detectar_bioimpedancia("quero emagrecer") is False
    assert _detectar_bioimpedancia("me gera um plano") is False


def test_detectar_bioimpedancia_case_insensitive():
    assert _detectar_bioimpedancia("BIOIMPEDÂNCIA") is True
    assert _detectar_bioimpedancia("Massa Magra 60kg") is True
    assert _detectar_bioimpedancia("InBody 570") is True


def test_build_system_with_bioimpedancia():
    from bot import _build_system_with_profile
    profile = {
        "nome": "Ana",
        "peso": "75kg",
        "altura": "1,65m",
        "idade": "30 anos",
        "objetivo": "emagrecer",
        "nivel_atividade": "moderado",
    }
    bio = {
        "gordura_pct": 30.0,
        "massa_magra_kg": 52.5,
        "massa_gorda_kg": 22.5,
        "tmb_medida": 1650,
        "gordura_visceral": 10,
        "agua_corporal_pct": 48.0,
        "idade_metabolica": 38,
        "outros": {},
    }
    result = _build_system_with_profile(profile, bioimpedancia=bio)
    assert "BIOIMPEDÂNCIA DO USUÁRIO" in result
    assert "30.0%" in result
    assert "52.5 kg" in result
    assert "1650 kcal" in result
    assert "massa magra real" in result


def test_build_system_sem_bioimpedancia():
    from bot import _build_system_with_profile
    profile = {"nome": "Ana", "peso": "75kg"}
    result = _build_system_with_profile(profile)
    assert "BIOIMPEDÂNCIA" not in result


def test_is_affirmative():
    from bot import _is_affirmative
    assert _is_affirmative("sim") is True
    assert _is_affirmative("SIM") is True
    assert _is_affirmative("s") is True
    assert _is_affirmative("quero") is True
    assert _is_affirmative("pode") is True
    assert _is_affirmative("vai") is True
    assert _is_affirmative("gera") is True
    assert _is_affirmative("ok") is True
    assert _is_affirmative("yes") is True
    assert _is_affirmative("não") is False
    assert _is_affirmative("nao") is False
    assert _is_affirmative("n") is False
    assert _is_affirmative("depois") is False
