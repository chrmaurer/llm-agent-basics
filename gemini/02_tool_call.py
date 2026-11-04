"""Gemini API – Beispiel für einen eigenen (Dummy-)Tool-Call.

Ablauf:
  1. Wir beschreiben dem Modell ein Tool (Name, Zweck, Parameter).
  2. Das Modell entscheidet selbst, ob es das Tool aufrufen will,
     und liefert dann Name + Argumente zurück – es führt nichts aus!
  3. Unser Code führt die Funktion aus und schickt das Ergebnis zurück.
  4. Das Modell formuliert damit die endgültige Antwort.

Voraussetzung: Umgebungsvariable GEMINI_API_KEY ist gesetzt.
Start:  .venv/bin/python gemini/02_tool_call.py ["Deine Frage"]
"""

import os
import sys
import time

from google import genai
from google.genai import errors, types

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_ATTEMPTS = 3
RETRY_STATUS = {429, 500, 503, 504}


# --- 1. Das eigene Tool (Dummy) -------------------------------------------

def get_weather(city: str, unit: str = "celsius") -> dict:
    """Dummy: liefert erfundene Wetterdaten statt eine echte API zu fragen."""
    fake_data = {
        "wien": 12,
        "berlin": 9,
        "rom": 19,
    }
    temp_c = fake_data.get(city.lower(), 15)
    temp = temp_c if unit == "celsius" else round(temp_c * 9 / 5 + 32)
    return {"city": city, "temperature": temp, "unit": unit, "condition": "bewölkt"}


# Beschreibung für das Modell (JSON-Schema der Parameter)
get_weather_decl = types.FunctionDeclaration(
    name="get_weather",
    description="Liefert das aktuelle Wetter für eine Stadt.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "city": types.Schema(type="STRING", description="Name der Stadt, z. B. Wien"),
            "unit": types.Schema(
                type="STRING",
                enum=["celsius", "fahrenheit"],
                description="Temperatureinheit",
            ),
        },
        required=["city"],
    ),
)

# Zuordnung Tool-Name -> Python-Funktion
TOOLS = {"get_weather": get_weather}


# --- Hilfsfunktion: API-Aufruf mit Wiederholung bei Überlast ---------------

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


# --- 2.–4. Der Tool-Call-Ablauf --------------------------------------------

def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Fehler: GEMINI_API_KEY ist nicht gesetzt.")

    question = sys.argv[1] if len(sys.argv) > 1 else "Wie ist das Wetter in Wien und in Rom?"
    print(f"Frage: {question}\n")

    client = genai.Client()
    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[get_weather_decl])],
        # Automatik aus, damit wir jeden Schritt selbst sehen und ausführen
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=question)])]

    # Schleife: solange das Modell Tools aufrufen will, führen wir sie aus
    for _ in range(5):
        response = generate(client, contents, config)

        if not response.function_calls:
            print(f"Antwort: {response.text}")
            return

        # Antwort des Modells (inkl. Tool-Call-Wunsch) in den Verlauf übernehmen
        contents.append(response.candidates[0].content)

        result_parts = []
        for call in response.function_calls:
            args = dict(call.args or {})
            print(f"→ Modell ruft Tool auf: {call.name}({args})")
            result = TOOLS[call.name](**args)
            print(f"← Ergebnis unseres Codes: {result}\n")
            result_parts.append(
                types.Part.from_function_response(name=call.name, response={"result": result})
            )

        # Tool-Ergebnisse zurück an das Modell
        contents.append(types.Content(role="user", parts=result_parts))

    sys.exit("Abbruch: zu viele Tool-Runden.")


if __name__ == "__main__":
    main()
