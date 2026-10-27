import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()                           # wczytuje zmienne z pliku .env

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
API_KEY = os.getenv("GEMINI_API_KEY")
MAX_KROKOW = 25
KATALOG = Path(sys.argv[1]).resolve()   # katalog projektu, na którym pracuje agent

SYSTEM_PROMPT = f"""Jesteś agentem programistycznym. Pracujesz w katalogu {KATALOG}.
Zasady:
- Zanim coś zmienisz, przeczytaj odpowiednie pliki.
- Zmieniaj tylko to, co potrzebne do zadania.
- Po każdej zmianie uruchom testy komendą: python -m pytest -q
- Skończ dopiero, gdy wszystkie testy przechodzą. Na koniec napisz krótko, co zmieniłeś."""

if MODEL is None :
    raise ValueError("GEMINI_MODEL is not set")

if API_KEY is None:
    raise ValueError("GEMINI_API_KEY is not set")

client = genai.Client(
    api_key=API_KEY,
    http_options=types.HttpOptions(
        timeout=60_000,  # ms
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
)

# ---------- NARZĘDZIA: opis dla modelu ----------
DEKLARACJE = [
    {
        "name": "list_files",
        "description": "Wypisuje wszystkie pliki w projekcie (ścieżki względne).",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "read_file",
        "description": "Zwraca zawartość pliku. Podaj ścieżkę względną, np. 'src/app.py'.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Podmienia fragment pliku. old_str musi wystąpić w pliku DOKŁADNIE raz "
            "(skopiuj go dosłownie, z wcięciami). new_str to nowy tekst."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_str": {"type": "string"},
                "new_str": {"type": "string"},
                "line": {
                    "type": "integer",
                    "description": "Numer linii, gdy old_str występuje w pliku kilka razy.",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Ustaw na true, aby zmienić WSZYSTKIE wystąpienia old_str. Domyślnie false.",
                },
            },
            "required": ["path", "old_str", "new_str"],
        },
    },
    {
        "name": "run_command",
        "description": "Uruchamia komendę w terminalu w katalogu projektu i zwraca wynik.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]

CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[types.Tool(function_declarations=DEKLARACJE)],
    temperature=0,
)


def bezpieczna_sciezka(path):
    pelna = (KATALOG / path).resolve()
    if (not pelna.exists() and not pelna.is_relative_to(KATALOG)):
        raise ValueError(f"Nieprawidłowa ścieżka: {path}")
    return pelna

def list_files():
    pliki = [str(p.relative_to(KATALOG)) for p in KATALOG.rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts]
    return "\n".join(sorted(pliki))

def read_file(path):
    linie = bezpieczna_sciezka(path).read_text().splitlines()
    return "\n".join(f"{i:4}| {linia}" for i, linia in enumerate(linie, start=1))

def edit_file(path, old_str, new_str, line=None):
    plik = bezpieczna_sciezka(path)
    tresc = plik.read_text()
    pozycje = []
    start = tresc.find(old_str)
    while start != -1:                                   # znajdź wszystkie wystąpienia
        pozycje.append(start)
        start = tresc.find(old_str, start + 1)

    if not pozycje:
        return "BŁĄD: nie znaleziono old_str. Przeczytaj plik ponownie."
    if len(pozycje) > 1:
        numery = [tresc.count("\n", 0, p) + 1 for p in pozycje]   # numer linii każdego wystąpienia
        if line not in numery:
            return f"BŁĄD: old_str występuje w liniach {numery}. Podaj parametr line z jedną z nich."
        pozycje = [pozycje[numery.index(line)]]

    p = pozycje[0]
    plik.write_text(tresc[:p] + new_str + tresc[p + len(old_str):])
    return "OK, plik zmieniony."

def run_command(command):
    print(f"\n⚠️  Agent chce uruchomić: {command}")
    if input("   Zgoda? [t/N] ").strip().lower() != "t":
        return "Użytkownik odmówił uruchomienia tej komendy."
    wynik = subprocess.run(command, shell=True, cwd=KATALOG,
                           capture_output=True, text=True, timeout=60)
    return (wynik.stdout + wynik.stderr)[-5000:] or "(brak wyniku)"


def wykonaj_narzedzie(nazwa, argumenty):
    try:
        if nazwa == "list_files":
            return list_files()
        if nazwa == "read_file":
            return read_file(**argumenty)
        if nazwa == "edit_file":
            return edit_file(**argumenty)
        if nazwa == "run_command":
            return run_command(**argumenty)
        return f"Nieznane narzędzie: {nazwa}"
    except Exception as e:                      # błąd wraca do modelu, a nie wywala programu
        return f"BŁĄD: {e}"


def uruchom_agenta(zadanie):
    historia = [types.Content(role="user", parts=[types.Part(text=zadanie)])]

    for krok in range(1, MAX_KROKOW + 1):
        odpowiedz = client.models.generate_content(model=MODEL, contents=historia, config=CONFIG)
        tresc = odpowiedz.candidates[0].content if odpowiedz.candidates else None
        if tresc is None or not tresc.parts:
            print("\n⛔ Model zwrócił pustą odpowiedź.")
            return
        historia.append(tresc)                  # cała odpowiedź modelu, razem z podpisami myślenia

        for part in tresc.parts:
            if part.text and not part.thought:
                print(f"\n🤖 {part.text}")

        wywolania = [part.function_call for part in tresc.parts if part.function_call]
        if not wywolania:
            print(f"\n✅ Agent skończył po {krok} krokach.")
            return

        wyniki = []
        for wywolanie in wywolania:
            argumenty = dict(wywolanie.args or {})
            print(f"\n🔧 [{krok}] {wywolanie.name}({json.dumps(argumenty, ensure_ascii=False)[:150]})")
            wynik = wykonaj_narzedzie(wywolanie.name, argumenty)
            print(f"   → {wynik[:300]}")
            wyniki.append(types.Part(function_response=types.FunctionResponse(
                id=wywolanie.id, name=wywolanie.name, response={"result": wynik},
            )))
        historia.append(types.Content(role="user", parts=wyniki))

    print(f"\n⛔ Przekroczono limit {MAX_KROKOW} kroków.")


if __name__ == "__main__":
    uruchom_agenta(" ".join(sys.argv[2:]) or "Testy w tym projekcie nie przechodzą. Znajdź przyczynę i napraw kod.")
