from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Charge les instructions d'un agent depuis un fichier Markdown."""
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8").strip()