"""Gemini API – Hello World.

Voraussetzung: Umgebungsvariable GEMINI_API_KEY ist gesetzt.
Start:  .venv/bin/python gemini/01_hello.py
"""

import os
import sys
import time

from google import genai
from google.genai import errors


#gemini-2.5-flash-lite
#gemini-flash-latest
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 503, 504}  # vorübergehende Fehler


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Fehler: GEMINI_API_KEY ist nicht gesetzt.")

    # Der Client liest GEMINI_API_KEY automatisch aus der Umgebung.
    client = genai.Client()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents="Sag 'Hallo Welt' und erkläre in einem Satz, wer du bist.",
            )
            print(response.text)
            return
        except errors.APIError as e:
            if e.code not in RETRY_STATUS or attempt == MAX_ATTEMPTS:
                sys.exit(f"Fehler {e.code}: {e.message}")
            wait = 2 ** attempt  # 2 s, 4 s
            print(f"Versuch {attempt}/{MAX_ATTEMPTS}: {e.code} – neuer Versuch in {wait} s …",
                  file=sys.stderr)
            time.sleep(wait)


if __name__ == "__main__":
    main()
