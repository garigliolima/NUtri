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
