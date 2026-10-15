"""
Módulo de Gerenciamento de Configuração e Chaves de API para a Sonar.
Armazena e valida credenciais localmente com segurança.
"""

import os
from pathlib import Path
from dotenv import load_dotenv, set_key

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Carrega variáveis existentes
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


def get_gemini_api_key() -> str:
    """Retorna a chave do Google Gemini configurada."""
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_default_model() -> str:
    """Retorna o modelo Gemini padrão selecionado."""
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()


def save_api_config(gemini_api_key: str, model_name: str = "gemini-2.5-flash") -> bool:
    """Salva a chave e modelo no arquivo .env local."""
    try:
        if not ENV_PATH.exists():
            ENV_PATH.touch(mode=0o600, exist_ok=True)

        set_key(str(ENV_PATH), "GEMINI_API_KEY", gemini_api_key.strip())
        set_key(str(ENV_PATH), "GEMINI_MODEL", model_name.strip())

        # Atualiza variáveis em memória
        os.environ["GEMINI_API_KEY"] = gemini_api_key.strip()
        os.environ["GEMINI_MODEL"] = model_name.strip()
        return True
    except Exception as e:
        print(f"Erro ao salvar .env: {e}")
        return False


def test_gemini_connection(api_key: str, model_name: str = "gemini-2.5-flash") -> dict:
    """
    Testa a conectividade com a API do Google Gemini.
    Retorna status de sucesso ou mensagem de erro explicativa.
    """
    if not api_key:
        return {
            "success": False,
            "message": "Nenhuma chave de API foi fornecida. Por favor insira sua chave do Google Gemini."
        }

    try:
        from google import genai
        client = genai.Client(api_key=api_key.strip())

        # Teste leve para validar autorização
        # Tentamos com o modelo especificado, e se for legado ou falhar, tentamos modelos alternativos
        models_to_try = [model_name, "gemini-2.5-flash", "gemini-1.5-flash", "gemini-3.8-flash"]
        # Remove duplicatas mantendo a ordem
        seen = set()
        clean_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

        last_error = None
        for m in clean_models:
            try:
                # Testa usando client.models.generate_content
                response = client.models.generate_content(
                    model=m,
                    contents="Responda apenas com a palavra: OK"
                )
                if response and response.text:
                    return {
                        "success": True,
                        "message": f"Conexão com a Google Gemini API validada com sucesso! (Modelo ativo: {m})",
                        "model": m
                    }
            except Exception as ex:
                last_error = ex
                continue

        return {
            "success": False,
            "message": f"Falha ao validar a chave de API: {str(last_error)}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Erro inesperado ao conectar com a API: {str(e)}"
        }
