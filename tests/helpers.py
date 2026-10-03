import json
from pathlib import Path

LANGUAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "game" / "language"


def load_language(code="en"):
    with open(LANGUAGE_DIR / f"{code}.json", encoding="utf-8") as file:
        return json.load(file)


class ZeroRng:
    def randint(self, low, high):
        return 0
