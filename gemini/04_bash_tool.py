"""Gemini API – ein generisches Bash-Tool (mit Schutzmaßnahmen).

Statt vieler spezieller Tools bekommt das Modell EIN Tool: `run_bash`.
Damit kann es (fast) alles – genau deshalb ist es gefährlich:
  - destruktive Befehle (rm -rf ...)
  - Zugriff auf Secrets (z. B. `env` zeigt GEMINI_API_KEY)
  - Prompt Injection: präparierte Eingaben bringen das Modell zu ungewollten Befehlen

Schutzmaßnahmen in diesem Beispiel:
  1. Bestätigung: jeder Befehl wird angezeigt und nur nach "y" ausgeführt
  2. Minimale Umgebung: Secrets werden NICHT an die Shell weitergegeben
  3. Timeout + gekürzte Ausgabe
  4. Festes Arbeitsverzeichnis (Repo-Root)

Voraussetzung: Umgebungsvariable GEMINI_API_KEY ist gesetzt.
Start:  .venv/bin/python gemini/04_bash_tool.py ["Deine Frage"]
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors, types

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 503, 504}

WORKDIR = Path(__file__).resolve().parent.parent  # Repo-Root
TIMEOUT_S = 10
MAX_OUTPUT = 4000


# --- Das Bash-Tool ----------------------------------------------------------

def run_bash(command: str) -> dict:
    """Führt einen Shell-Befehl aus – nur nach Bestätigung durch den Benutzer."""
    # Schutz 1: Bestätigung
    print(f"\n⚠️  Modell möchte ausführen:\n    $ {command}")
    try:
        answer = input("    Ausführen? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    if answer != "y":
        print("    ✗ abgelehnt")
        return {"error": "vom Benutzer abgelehnt"}

    # Schutz 2: minimale Umgebung – GEMINI_API_KEY & Co. werden nicht vererbt
    safe_env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
        "HOME": str(Path.home()),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    }

    try:
        # Schutz 3 + 4: Timeout und festes Arbeitsverzeichnis
        proc = subprocess.run(
            ["/bin/bash", "-c", command],
            cwd=WORKDIR, env=safe_env,
            capture_output=True, text=True, timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout nach {TIMEOUT_S} s"}

    output = (proc.stdout + proc.stderr)[:MAX_OUTPUT]  # Schutz 3: Ausgabe kürzen
    print(f"    ✓ exit code {proc.returncode}")
    return {"exit_code": proc.returncode, "output": output}


run_bash_decl = types.FunctionDeclaration(
    name="run_bash",
    description="Führt einen Bash-Befehl im Projektordner aus und liefert Ausgabe und Exit-Code.",
    parameters=types.Schema(
        type="OBJECT",
        properties={"command": types.Schema(type="STRING", description="Der Bash-Befehl")},
        required=["command"],
    ),
)

TOOLS = {"run_bash": run_bash}

SYSTEM_PROMPT = (
    "Du bist ein hilfreicher Assistent mit Zugriff auf eine Bash-Shell (macOS/Linux) "
    "im Projektordner. Verwende kurze, einfache Befehle. Lies nur – lösche oder "
    "verändere keine Dateien. Antworte auf Deutsch."
)


# --- API-Aufruf mit Wiederholung ---------------------------------------------

def generate(client, contents, config):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return client.models.generate_content(model=MODEL, contents=contents, config=config)
        except errors.APIError as e:
            if e.code not in RETRY_STATUS or attempt == MAX_ATTEMPTS:
                sys.exit(f"Fehler {e.code}: {e.message}")
            wait = 2 ** attempt
            print(f"  (Versuch {attempt}/{MAX_ATTEMPTS}: {e.code} – warte {wait} s)", file=sys.stderr)
            time.sleep(wait)


# --- Hauptablauf -------------------------------------------------------------

def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Fehler: GEMINI_API_KEY ist nicht gesetzt.")

    question = (sys.argv[1] if len(sys.argv) > 1
                else "Wie viele Python-Dateien gibt es im Ordner gemini und wie heißen sie?")
    print(f"Frage: {question}")

    client = genai.Client()
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=[run_bash_decl])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=question)])]

    for _ in range(8):
        response = generate(client, contents, config)
        if not response.function_calls:
            print(f"\nAntwort: {response.text}")
            return

        contents.append(response.candidates[0].content)
        parts = []
        for call in response.function_calls:
            result = TOOLS[call.name](**dict(call.args or {}))
            parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
        contents.append(types.Content(role="user", parts=parts))

    sys.exit("Abbruch: zu viele Tool-Runden.")


if __name__ == "__main__":
    main()
