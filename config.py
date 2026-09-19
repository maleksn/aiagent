import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    api_key: str | None = os.environ.get("GEMINI_API_KEY")
    default_model: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    default_working_directory: str = os.environ.get("WORKING_DIRECTORY", "./calculator")
    max_chars: int = int(os.environ.get("MAX_CHARS", "10000"))
    max_iterations: int = int(os.environ.get("MAX_ITERATIONS", "20"))
    subprocess_timeout_seconds: int = int(os.environ.get("SUBPROCESS_TIMEOUT", "30"))
    temperature: float = float(os.environ.get("TEMPERATURE", "0.0"))


config = Config()

# Backwards compatibility constants
MAX_CHARS = config.max_chars
DEFAULT_WORKING_DIRECTORY = config.default_working_directory

