import os

import geopandas as gpd
import logfire
import pprint
# import pandas as pd

# import streamlit as st
from colorama import Fore
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

# Set up Streamlit page -
# ! FOR NOW JUST FOR VISULIZATION OF DATA !
# st.set_page_config(page_title="AI Test", layout="wide")
# st.title("AI Test")

# Load environment variables from .env file
load_dotenv()

# Setup logfire
logfire.configure()

# Prepare ollama model
model = OllamaModel(
    "qwen3:8b",
    provider=OllamaProvider(base_url=os.getenv("OLLAMA_URL")),
)


class Listed_off(BaseModel):
    """A Pydantic model representing a listed-off entity."""

    results: list[str]


class AnswerType(BaseModel):
    """a Pydantic model representing a answer from list"""

    answer: str


gdf = gpd.read_file("data/maps/geoBoundaries-POL-ADM2.geojson")
list_of_all_sectors = gdf["shapeName"].tolist()
pprint.pprint(
    Fore.GREEN + "Lista wszystkich sektorów: \n" + Fore.BLUE + str(list_of_all_sectors)
)
# Add it to the agent's dependencies so it can use it in its reasoning
deps = Listed_off(results=list_of_all_sectors)


# map_file = st.file_uploader(
#     "Upload a GeoJSON map file", type=[".json", ".geojson"], accept_multiple_files=False
# )

# csv_file = st.file_uploader(
#     "Upload a CSV file with data", type=[".csv"], accept_multiple_files=False
# )


pick_all_of_agent = Agent(
    model=model,
    deps_type=Listed_off,
    output_type=AnswerType,
    retries=3,
    system_prompt="""
                    Jesteś narzędziem do wyszukiwania najlepszego odpowiednika nazwy sektora w liście sektorów przekazanej w dependencies.

                    Twoim zadaniem jest zwrócenie dokładnego indeksu w formie stringa nazwy sektora z przekazanej listy albo string brak, jeśli nie istnieje odpowiedni odpowiednik.

                    Przy dopasowywaniu uwzględnij następujące zasady (w podanej kolejności):

                    Dokładne dopasowanie - jeśli nazwa użytkownika występuje na liście, zwróć ją.
                    Ignorowanie różnic w zapisie, takich jak:
                    - wielkość liter,
                    - polskie znaki,
                    - myślniki, spacje i znaki specjalne,
                    - odmiana gramatyczna (np. "powiatu" → "powiat"),
                    - liczba pojedyncza i mnoga.
                    - Literówki - popraw oczywiste błędy w pisowni.
                    - Synonimy i tłumaczenia - rozpoznawaj nazwy w innych językach oraz ich odpowiedniki, np.:
                    county → powiat,
                    - district, province, municipality itp., jeśli w danym kontekście oznaczają sektor z listy.
                    - Dodatkowe lub zbędne słowa - ignoruj wyrazy, które nie zmieniają znaczenia, np.:
                    - "County Wrocław",
                    - "Powiat Wrocław",
                    - "Wrocław County",
                    - "District of Wrocław".
                    - Nazwy historyczne lub przestarzałe - jeśli sektor został zastąpiony lub połączony z innym, zwróć jego aktualny odpowiednik znajdujący się na liście.
                    - Najbliższy jednoznaczny odpowiednik - jeśli istnieje tylko jeden oczywiście pasujący sektor, zwróć go.
                    - Jeśli istnieje kilka równie prawdopodobnych odpowiedników lub nie można jednoznacznie wskazać właściwego sektora, zwróć brak. Nie zgaduj.
                    Ważne!
                    Korzystaj wyłącznie z sektorów znajdujących się w przekazanej liście.
                    Nigdy nie twórz nowych nazw.
                    Nie dodawaj żadnych wyjaśnień ani komentarzy.
                    Odpowiedź musi być wyłącznie jednym stringiem:
                    indeksem poprawnej nazwy z listy w formie string,
                    lub dokładnie brak.
    """,
)

# TODO Ideas for working this up:
# TODO 1. Test the Agent. Maybe he doesn't really remeber all the stuff he gets inside the list (maybe it's too big?)
# TODO 1.1. Maybe it need something else first to thin out the list.
# TODO 1.2. Maybe dived list into multiple smaller ones.
# TODO 2. Extra agent to controll the first one?
# TODO 3. New tools for it to work this out.
# TODO 4. Check if the ollama model really works good with polish language.
# ! Well of course it ain't that easy ;)


# if map_file is not None:
#     gdf = gpd.read_file(map_file)
#     st.write(gdf)
#     # Add it to the agent's dependencies so it can use it in its reasoning
#     deps = MapData(gdf=gdf)

# if csv_file is not None:
#     df = pd.read_csv(csv_file, sep=None, engine="python")
#     st.write(df)


user_query = input(Fore.CYAN + "Jaki sektor znaleźć\n" + Fore.YELLOW)

response = pick_all_of_agent.run_sync(user_query, deps=deps)

logfire.notice("Output from LLM: {result}", result=str(response.output))
logfire.info("Result type: {result}", result=type(response.output))

print(Fore.GREEN + "Sektor z listy: " + Fore.BLUE + str(response.output))
print(deps[(int(response.output))])
