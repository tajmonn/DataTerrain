"""
Dopasowywanie nazw jednostek administracyjnych z dwóch źródeł (geojson + CSV)
w dwóch etapach:

    1. Fuzzy matching (rapidfuzz)  -> szybkie, darmowe, deterministyczne.
       Rozwiązuje różnice w wielkości liter, polskich znakach, literówkach,
       dopiskach typu "powiat", "woj." itp.

    2. LLM (lokalny model przez Ollama) -> tylko dla nazw, których fuzzy
       matching nie rozwiązał z wystarczającą pewnością. Model dostaje
       JEDNĄ nazwę na raz + pełną listę kandydatów w system prompcie i musi
       zwrócić wynik zgodny ze strukturą (NativeOutput), a jego odpowiedź
       jest dodatkowo walidowana względem realnej listy kandydatów, żeby
       ewentualna halucynacja nie przeszła dalej jako "dopasowanie".

Wymagane pakiety:
    pip install geopandas pandas rapidfuzz unidecode pydantic-ai colorama python-dotenv logfire

Wymaga uruchomionego lokalnie (lub zdalnie) serwera Ollama z załadowanym
modelem (domyślnie qwen3:8b) oraz zmiennej środowiskowej OLLAMA_URL
(np. http://localhost:11434/v1) w pliku .env.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import geopandas as gpd
import pandas as pd
from colorama import Fore
from colorama import init as colorama_init
from dotenv import load_dotenv
from rapidfuzz import fuzz, process
from unidecode import unidecode

import logfire
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.output import NativeOutput
from pydantic_ai.providers.ollama import OllamaProvider

colorama_init(autoreset=True)
load_dotenv()
logfire.configure()

# --------------------------------------------------------------------------
# Konfiguracja
# --------------------------------------------------------------------------
GEOJSON_PATH = "data/maps/geoBoundaries-POL-ADM2.geojson"
GEOJSON_NAME_COLUMN = "shapeName"

CSV_PATH = "data/datasets/wyniki_gl_na_kandydatow_po_powiatach_utf8.csv"
CSV_NAME_COLUMN = "Powiat"

OUTPUT_PATH = "data/matches/name_matches.csv"

FUZZY_THRESHOLD = 90  # poniżej tego progu (0-100) nazwa trafia do LLM
OLLAMA_MODEL_NAME = "SpeakLeash/bielik-11b-v3.0-instruct:Q8_0"

# Przedrostki/dopiski, które często różnią się między źródłami danych
COMMON_PREFIXES = ["powiat", "gmina", "wojewodztwo", "woj.", "miasto", "m."]


# --------------------------------------------------------------------------
# Etap 0: normalizacja nazw (przygotowanie pod fuzzy matching)
# --------------------------------------------------------------------------
def normalize(name: str) -> str:
    """Sprowadza nazwę do wspólnej postaci: bez polskich znaków, małe litery,
    bez typowych przedrostków administracyjnych, bez nadmiarowych spacji."""
    text = unidecode(str(name)).lower().strip()
    for prefix in COMMON_PREFIXES:
        text = re.sub(rf"^{re.escape(prefix)}\.?\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# --------------------------------------------------------------------------
# Wspólny typ wyniku
# --------------------------------------------------------------------------
@dataclass
class MatchResult:
    source_name: str
    matched_name: str | None
    score: float  # -1 dla dopasowań z LLM (nie ma tam liczbowego score)
    method: str  # "fuzzy" | "llm" | "none"
    reasoning: str = ""  # uzasadnienie modelu - puste dla dopasowań fuzzy


# --------------------------------------------------------------------------
# Etap 1: fuzzy matching
# --------------------------------------------------------------------------
def fuzzy_match_all(
    source_names: list[str], target_names: list[str], threshold: float
) -> tuple[list[MatchResult], list[str]]:
    """Dopasowuje każdą nazwę z source_names do najlepiej pasującej nazwy
    z target_names. Zwraca (dopasowania powyżej progu, nazwy nierozwiązane)."""
    normalized_targets = {normalize(t): t for t in target_names}
    target_norm_list = list(normalized_targets.keys())

    matches: list[MatchResult] = []
    unmatched: list[str] = []

    for name in source_names:
        result = process.extractOne(
            normalize(name), target_norm_list, scorer=fuzz.WRatio
        )
        if result is not None:
            matched_norm, score, _ = result
            if score >= threshold:
                matches.append(
                    MatchResult(
                        source_name=name,
                        matched_name=normalized_targets[matched_norm],
                        score=score,
                        method="fuzzy",
                    )
                )
                continue
        unmatched.append(name)

    return matches, unmatched


# --------------------------------------------------------------------------
# Etap 2: LLM tylko dla trudnych przypadków
# --------------------------------------------------------------------------
class NameMatch(BaseModel):
    """Wynik dopasowania jednej nazwy przez model.

    Kolejność pól ma znaczenie: `reasoning` jest wypełniane przed
    `matched_name`/`found`, więc przy generowaniu zgodnym ze schematem
    (grammar-constrained decoding) model musi najpierw "przemyśleć" sprawę,
    zanim poda ostateczną odpowiedź. To prosty sposób na poprawę jakości
    odpowiedzi małych modeli bez pełnego promptowania chain-of-thought."""

    reasoning: str  # krótkie uzasadnienie decyzji, po polsku, 1-2 zdania
    matched_name: str  # ma być dokładnie jedną z nazw z listy kandydatów (albo puste)
    found: bool  # False, jeśli żadna nazwa nie pasuje / to nie jest jednostka administracyjna


def build_llm_agent(candidate_names: list[str]) -> Agent:
    """Buduje agenta dopasowującego POJEDYNCZĄ nazwę do listy kandydatów.

    Lista kandydatów jest wpisana wprost do system promptu (nie jako deps) -
    dla małych modeli lokalnych to dużo bardziej niezawodne niż poleganie na
    tym, że model "sam sobie przypomni" dane z RunContext. Jeśli lista
    kandydatów jest bardzo duża (np. ~2500 gmin), warto ją wcześniej zawęzić
    (np. po dopasowanym już powiecie nadrzędnym) zamiast wrzucać całość.
    """
    model = OllamaModel(
        OLLAMA_MODEL_NAME,
        provider=OllamaProvider(
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
        ),
    )

    candidates_block = "\n".join(f"- {c}" for c in candidate_names)

    return Agent(
        model=model,
        output_type=NativeOutput(NameMatch),
        retries=3,
        system_prompt=(
            "Jesteś narzędziem dopasowującym nazwy polskich jednostek administracyjnych.\n"
            "Dostajesz od użytkownika JEDNĄ nazwę. Twoim zadaniem jest znalezienie "
            "najlepiej pasującej nazwy z poniższej listy kandydatów:\n\n"
            f"{candidates_block}\n\n"
            "Postępuj według poniższych kroków, w tej kolejności:\n\n"
            "1. Sprawdź, czy podana nazwa to w ogóle jednostka administracyjna "
            "(powiat/gmina/województwo). Jeżeli to coś innego - np. 'zagranica', "
            "'statki', 'głosowanie korespondencyjne', nazwa komisji wyborczej, "
            "błąd w danych, wartość pusta lub dowolna inna rzecz, która NIE JEST "
            "nazwą jednostki administracyjnej - natychmiast ustaw found=False "
            "i matched_name na pusty tekst. W polu reasoning krótko napisz, "
            "dlaczego to nie jest jednostka administracyjna. Nie próbuj na siłę "
            "dopasowywać takiej wartości do żadnej nazwy z listy.\n\n"
            "2. Jeśli to jest jednostka administracyjna, poszukaj dokładnego lub "
            "bardzo bliskiego odpowiednika na liście kandydatów. Różnice mogą "
            "wynikać z literówek, odmiennej pisowni, dodatkowych słów "
            "(np. 'powiat', 'województwo'), wielkości liter lub kolejności wyrazów.\n\n"
            "3. Jeśli nie ma bliskiego odpowiednika, rozważ, czy podana nazwa nie "
            "jest przestarzała, historyczna, albo czy dana jednostka nie została "
            "z czasem zniesiona, przemianowana lub wchłonięta przez inną, większą "
            "jednostkę z listy kandydatów (np. mała gmina włączona do sąsiedniego "
            "miasta, powiat zlikwidowany i podzielony między sąsiednie powiaty, "
            "zmiana nazwy miejscowości). Skorzystaj z własnej wiedzy o historii "
            "polskiego podziału administracyjnego. Jeśli znajdziesz w ten sposób "
            "sensownego następcę, zwróć go jako matched_name i w reasoning krótko "
            "wyjaśnij tę zmianę (np. 'jednostka zniesiona w [rok], włączona do X').\n\n"
            "4. Jeśli mimo to nie jesteś w stanie wskazać żadnego rozsądnego "
            "odpowiednika - nie zgaduj na siłę. Ustaw found=False, matched_name "
            "na pusty tekst, a w reasoning napisz dlaczego.\n\n"
            "Zawsze najpierw wypełnij pole reasoning, dopiero potem matched_name "
            "i found. Gdy found=True, matched_name musi być DOKŁADNIE jedną "
            "nazwą z listy kandydatów powyżej, bez żadnych zmian w pisowni."
        ),
    )


def llm_match_unmatched(
    unmatched: list[str], target_names: list[str]
) -> list[MatchResult]:
    """Dla każdej niedopasowanej nazwy pyta lokalny model o dopasowanie i
    weryfikuje odpowiedź względem realnej listy kandydatów."""
    agent = build_llm_agent(target_names)
    valid_names = set(target_names)
    results: list[MatchResult] = []

    for name in unmatched:
        response = agent.run_sync(name)
        output: NameMatch = response.output

        logfire.info(
            "LLM match attempt: {name} -> {matched} (found={found}) reasoning={reasoning}",
            name=name,
            matched=output.matched_name,
            found=output.found,
            reasoning=output.reasoning,
        )

        if output.found and output.matched_name in valid_names:
            results.append(
                MatchResult(
                    source_name=name,
                    matched_name=output.matched_name,
                    score=-1,
                    method="llm",
                    reasoning=output.reasoning,
                )
            )
        else:
            results.append(
                MatchResult(
                    source_name=name,
                    matched_name=None,
                    score=-1,
                    method="none",
                    reasoning=output.reasoning,
                )
            )

    return results


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    print(Fore.GREEN + "Wczytywanie danych...")

    gdf = gpd.read_file(GEOJSON_PATH)
    target_names = gdf[GEOJSON_NAME_COLUMN].tolist()

    df = pd.read_csv(CSV_PATH, sep=None, engine="python")
    source_names = df[CSV_NAME_COLUMN].tolist()

    print(
        Fore.GREEN
        + f"Geojson: {len(target_names)} jednostek, CSV: {len(source_names)} jednostek."
    )

    # Etap 1 - fuzzy matching (darmowy, szybki, deterministyczny)
    fuzzy_matches, unmatched = fuzzy_match_all(
        source_names, target_names, FUZZY_THRESHOLD
    )
    print(
        Fore.BLUE
        + f"Fuzzy matching dopasował {len(fuzzy_matches)}/{len(source_names)}. "
        f"Pozostało do LLM: {len(unmatched)}."
    )

    # Etap 2 - LLM tylko dla reszty
    llm_matches: list[MatchResult] = []
    if unmatched:
        print(
            Fore.YELLOW
            + f"Wysyłam {len(unmatched)} nazw do lokalnego modelu ({OLLAMA_MODEL_NAME})..."
        )
        llm_matches = llm_match_unmatched(unmatched, target_names)

    all_matches = fuzzy_matches + llm_matches
    still_unmatched = [m for m in all_matches if m.matched_name is None]

    print(
        Fore.GREEN
        + f"\nWynik: {len(all_matches) - len(still_unmatched)} dopasowanych, "
        f"{len(still_unmatched)} bez dopasowania (do ręcznej weryfikacji)."
    )

    result_df = pd.DataFrame(
        [
            {
                "source_name": m.source_name,
                "matched_name": m.matched_name,
                "score": m.score,
                "method": m.method,
                "reasoning": m.reasoning,
            }
            for m in all_matches
        ]
    )
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    result_df.to_csv(OUTPUT_PATH, index=False)
    print(Fore.GREEN + f"Zapisano wynik do {OUTPUT_PATH}")

    if still_unmatched:
        print(Fore.RED + "\nBrak dopasowania dla:")
        for m in still_unmatched:
            reason = f" ({m.reasoning})" if m.reasoning else ""
            print(Fore.RED + f"  - {m.source_name}{reason}")


if __name__ == "__main__":
    main()
