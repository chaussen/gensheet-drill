"""
conftest.py — loaded by pytest before any test file is imported.
Ensures .env is present in the environment before module-level constants
(like AI_PROVIDER in ai_service.py) are evaluated.
"""
from pathlib import Path
from dotenv import load_dotenv

# Load from project root .env first, then cwd as fallback
load_dotenv(Path(__file__).parent.parent.parent / ".env")
load_dotenv()
