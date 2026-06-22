import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_stl as ststl

# Set up Streamlit page
st.set_page_config(page_title="Tester", layout="wide")
st.title("Interactive Map")


# Load and merge the data
@st.cache_data
def load_and_merge_data(geojson_path, csv_path):

    try:
        gdf = gpd.read_file(geojson_path)

        # Drop the unnecessary columns immediately to save memory
        columns_to_drop = ["shapeISO", "shapeGroup", "shapeType", "shapeID"]
        # Using errors='ignore' ensures it won't crash if one of these columns is missing
        gdf = gdf.drop(columns=columns_to_drop, errors="ignore")

        gdf["shapeName"] = gdf["shapeName"].str.removeprefix("powiat ")

        # Plotly requires a coordinate reference system (CRS) in WGS84-EPSG:4326 (latitude/longitude)
        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)

        df = pd.read_csv(
            csv_path,
            sep=";",
            usecols=["Powiat", "Liczba kart ważnych", "Liczba głosów nieważnych"],
            encoding="utf-8",
        )

        df["Procent głosów nieważnych"] = (
            100
            * df["Liczba głosów nieważnych"]
            / (df["Liczba kart ważnych"] + df["Liczba głosów nieważnych"])
        )

        merged_gdf = gdf.merge(df, left_on="shapeName", right_on="Powiat", how="left")
        merged_gdf = merged_gdf.drop(columns=["shapeName"])
        return merged_gdf, "Procent głosów nieważnych"

    except Exception as e:
        st.error(f"Error loading GeoJSON: {e}")
        return None, None


# --- Configuration ---
GEOJSON_FILE = "data/maps/geoBoundaries-POL-ADM2_simplified_smaller.json"
CSV_FILE = "data/datasets/wyniki_gl_na_kandydatow_po_powiatach_utf8.csv"

# Execute loading routine
gdf, color_column = load_and_merge_data(GEOJSON_FILE, CSV_FILE)

if gdf is not None:
    # Dynamically find the geographical center of Poland to position the camera correctly
    bounds = gdf.total_bounds
    lon_center = (bounds[0] + bounds[2]) / 2
    lat_center = (bounds[1] + bounds[3]) / 2

    # Create the interactive map
    fig = px.choropleth_map(
        gdf,
        geojson=gdf.__geo_interface__,
        locations=gdf.index,
        color=color_column,  # Colors binded to color_column
        color_continuous_scale="blues",
        zoom=5.5,
        center={"lat": lat_center, "lon": lon_center},
        opacity=1,
        hover_name="Powiat",
    )

    # Maximize visual real-estate by eliminating chart margins
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    # Render directly to the Streamlit app
    st.plotly_chart(fig, width="stretch")

    # Preview of the final dataframe (geometry omitted)
    if st.checkbox("Show Cleaned Data Table"):
        st.dataframe(gdf.drop(columns="geometry"))

    # TODO - Add checkboxes for powiats - so you can choose how many you wanna print?
    # TODO - Add STL handling
    # TODO - Check if simplifing map deleted any powiats
    # TODO - Soft-code all of this
