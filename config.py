import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _normalize_model(model: str) -> str:
    aliases = {
        "google/gemini-2.0-flash-001": "google/gemini-2.5-flash",
        "gemini-2.5-flash": "google/gemini-2.5-flash",
        "gemini-2.0-flash": "google/gemini-2.5-flash",
    }
    return aliases.get(model, model)


@dataclass(frozen=True)
class Config:
    api_key: str | None = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    default_model: str = _normalize_model(
        os.environ.get("OPENROUTER_MODEL")
        or "google/gemini-2.5-flash"
    )
    openrouter_base_url: str = os.environ.get(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )

    default_working_directory: str = os.environ.get("WORKING_DIRECTORY", "./calculator")
    max_tokens: int = int(os.environ.get("MAX_TOKENS", "4096"))
    max_chars: int = int(os.environ.get("MAX_CHARS", "10000"))
    max_iterations: int = int(os.environ.get("MAX_ITERATIONS", "20"))
    subprocess_timeout_seconds: int = int(os.environ.get("SUBPROCESS_TIMEOUT", "30"))
    temperature: float = float(os.environ.get("TEMPERATURE", "0.0"))


config = Config()

# Backwards compatibility constants
MAX_CHARS = config.max_chars
DEFAULT_WORKING_DIRECTORY = config.default_working_directory

