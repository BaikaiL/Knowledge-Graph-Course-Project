import os
from dotenv import load_dotenv



_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ENV_PATH = os.path.join(_BASE_DIR, ".env")

if os.path.exists(_ENV_PATH):
    if load_dotenv is None:
        raise RuntimeError("python-dotenv is required to load .env")
    load_dotenv(_ENV_PATH)


def _get_env(name, default=None):
    value = os.getenv(name)
    return value if value not in (None, "") else default


NEO4J_HOST = _get_env("NEO4J_HOST", "localhost")
NEO4J_PORT = _get_env("NEO4J_PORT", "7687")
NEO4J_URI = _get_env("NEO4J_URI", f"bolt://{NEO4J_HOST}:{NEO4J_PORT}")
NEO4J_USER = _get_env("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = _get_env("NEO4J_PASSWORD", "88888888")

DASHSCOPE_API_KEY = _get_env("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = _get_env(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
