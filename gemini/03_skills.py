"""Gemini API – Skills nachgebaut mit Tool-Calls.

Idee (wie bei Claude-Skills):
  - Jeder Skill ist eine Markdown-Datei in skills/ mit Frontmatter
    (name + description) und ausführlichen Anweisungen.
  - Das Modell sieht anfangs NUR Name + Kurzbeschreibung aller Skills.
  - Braucht es einen Skill, ruft es das Tool `load_skill(name)` auf
    und bekommt erst dann die vollständigen Anweisungen.
  - Skills können ihrerseits weitere Tools nutzen (hier: get_weather).

Voraussetzung: Umgebungsvariable GEMINI_API_KEY ist gesetzt.
Start:  .venv/bin/python gemini/03_skills.py ["Deine Anfrage"]
"""

import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors, types

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
SKILLS_DIR = Path(__file__).parent / "skills"
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 503, 504}


# --- Skills laden -----------------------------------------------------------

def parse_skill(path: Path) -> dict:
    """Liest Frontmatter (name, description) und Inhalt einer Skill-Datei."""
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        _, header, body = text.split("---", 2)
        for line in header.strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return {"name": meta.get("name", path.stem), "description": meta.get("description", ""),
            "body": body.strip()}


SKILLS = {s["name"]: s for s in map(parse_skill, sorted(SKILLS_DIR.glob("*.md")))}


# --- Tools ------------------------------------------------------------------

def load_skill(name: str) -> dict:
    """Gibt die vollständigen Anweisungen eines Skills zurück."""
    skill = SKILLS.get(name)
    if not skill:
        return {"error": f"Unbekannter Skill '{name}'. Verfügbar: {list(SKILLS)}"}
    return {"name": name, "instructions": skill["body"]}


def get_weather(city: str, unit: str = "celsius") -> dict:
    """Dummy: liefert erfundene Wetterdaten."""
    temp_c = {"wien": 12, "berlin": 9, "rom": 19}.get(city.lower(), 15)
    temp = temp_c if unit == "celsius" else round(temp_c * 9 / 5 + 32)
    return {"city": city, "temperature": temp, "unit": unit, "condition": "bewölkt"}


TOOLS = {"load_skill": load_skill, "get_weather": get_weather}

TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="load_skill",
        description="Lädt die vollständigen Anweisungen eines Skills. "
                    "Vor der Bearbeitung einer passenden Aufgabe aufrufen.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"name": types.Schema(type="STRING", enum=list(SKILLS))},
            required=["name"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_weather",
        description="Liefert das aktuelle Wetter für eine Stadt.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "city": types.Schema(type="STRING"),
                "unit": types.Schema(type="STRING", enum=["celsius", "fahrenheit"]),
            },
            required=["city"],
        ),
    ),
]


def system_prompt() -> str:
    """Nur Name + Beschreibung jedes Skills – nicht der volle Inhalt."""
    catalog = "\n".join(f"- {s['name']}: {s['description']}" for s in SKILLS.values())
    return (
        "Du bist ein hilfreicher Assistent. Dir stehen folgende Skills zur Verfügung:\n"
        f"{catalog}\n\n"
        "Wenn eine Anfrage zu einem Skill passt, rufe ZUERST load_skill auf und "
        "befolge dann dessen Anweisungen genau. Passt kein Skill, antworte normal."
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

    request = sys.argv[1] if len(sys.argv) > 1 else "Mach mir einen Wetterbericht für Wien und Berlin."
    print(f"Skills: {', '.join(SKILLS)}")
    print(f"Anfrage: {request}\n")

    client = genai.Client()
    config = types.GenerateContentConfig(
        system_instruction=system_prompt(),
        tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=request)])]

    for _ in range(8):
        response = generate(client, contents, config)
        if not response.function_calls:
            print(f"Antwort:\n{response.text}")
            return

        contents.append(response.candidates[0].content)
        parts = []
        for call in response.function_calls:
            args = dict(call.args or {})
            label = "📘 Skill geladen" if call.name == "load_skill" else "🔧 Tool"
            print(f"{label}: {call.name}({args})")
            result = TOOLS[call.name](**args)
            parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
        print()
        contents.append(types.Content(role="user", parts=parts))

    sys.exit("Abbruch: zu viele Tool-Runden.")


if __name__ == "__main__":
    main()
