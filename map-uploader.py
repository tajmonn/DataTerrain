import streamlit as st
import geopandas as gpd
import plotly.express as px

from io import BytesIO

# -- PAGE CONFIG -------------------------
st.set_page_config(page_title="Upload and edit the map", layout="wide", page_icon="🗺️")

# -- CONFIG ------------------------------
GEO_NAME_COL = "shapeName"
GEO_DROP_COLS = ["shapeISO", "shapeGroup", "shapeType", "shapeID"]

# Coordinate system
CRS_MAP = 4326  # WGS84 - required by Plotly


# -- SESSION STATE -----------------------
if "edited_gdf" not in st.session_state:
    st.session_state.edited_gdf = None
if "last_file_id" not in st.session_state:
    st.session_state.last_file_id = None
if "change_detected" not in st.session_state:
    st.session_state.change_detected = False
if "editor_key" not in st.session_state:
    st.session_state.editor_key = 0


# -- DATA LOADING -----------------------
def add_affix(data: gpd.GeoDataFrame, affix: str, front: bool):
    if front:
        data.loc[data["include"], "areaName"] = affix + data["areaName"].astype(str)
    else:
        data.loc[data["include"], "areaName"] = data["areaName"].astype(str) + affix
    return data


def remove_text(data: gpd.GeoDataFrame, text_to_remove: str):
    mask = data["include"]
    data.loc[mask, "areaName"] = data.loc[mask, "areaName"].replace(
        text_to_remove, "", regex=True
    )
    return data


def gdf_change_button():
    st.session_state.change_detected = True


def remove_not_included(data: gpd.GeoDataFrame):
    removed_unchecked = (data[data["include"]]).drop(columns=["include"])
    return removed_unchecked


def download_edited_map(data: gpd.GeoDataFrame):
    removed_unchecked = remove_not_included(data)
    removed_unchecked = removed_unchecked.to_json()
    buffer = BytesIO()
    buffer.write(removed_unchecked.encode("utf-8"))
    buffer.seek(0)

    return buffer


# -- MAIN -------------------------------
with st.container(
    horizontal=False,
    horizontal_alignment="center",
    vertical_alignment="center",
    width="stretch",
):
    with st.container(
        horizontal=False,
        horizontal_alignment="center",
        vertical_alignment="center",
        width="content",
    ):
        file = st.file_uploader(
            label="Upload the map file",
            type=[".json", ".geojson"],
            accept_multiple_files=False,
        )

        # Only reload if it's a genuinely new file
        if file:
            file_id = (file.name, file.size)
            if file_id != st.session_state.last_file_id:
                gdf = gpd.read_file(file)
                gdf = gdf.drop(columns=GEO_DROP_COLS, errors="ignore")
                gdf = gdf.rename(columns={"shapeName": "areaName"})
                st.session_state.edited_gdf = gdf.assign(include=True)
                st.session_state.last_file_id = file_id

        # Show editor as long as session state has data, not only when file is present
        if st.session_state.edited_gdf is not None:
            with st.container(
                horizontal=True,
                horizontal_alignment="center",
                vertical_alignment="center",
                width="stretch",
            ):
                with st.container(
                    horizontal=True,
                    horizontal_alignment="center",
                    vertical_alignment="center",
                    width="content",
                ):
                    with st.container(
                        horizontal=False,
                        horizontal_alignment="center",
                        vertical_alignment="center",
                        width="stretch",
                    ):
                        changed_edited_gdf = st.data_editor(
                            st.session_state.edited_gdf,
                            width="content",
                            hide_index=True,
                            column_config={
                                "include": st.column_config.CheckboxColumn(
                                    width=90,
                                    help="Select the areas you want to include in the map",
                                ),
                                "areaName": st.column_config.TextColumn(width="large"),
                            },
                            column_order=["include", "areaName"],
                            on_change=gdf_change_button,
                            key=f"data_editor_{st.session_state.editor_key}",
                        )

                        if st.session_state.change_detected:
                            with st.container(
                                horizontal=True,
                                horizontal_alignment="center",
                                vertical_alignment="center",
                                width="stretch",
                            ):
                                st.warning(
                                    "save changes before using add/delete functions on the left or generating the map"
                                )
                            with st.container(
                                horizontal=True,
                                horizontal_alignment="center",
                                vertical_alignment="center",
                                width="stretch",
                            ):
                                if st.button("save changes"):
                                    st.session_state.edited_gdf = changed_edited_gdf
                                    st.session_state["edited_gdf"]["geometry"] = (
                                        gpd.GeoSeries.from_wkt(
                                            st.session_state["edited_gdf"]["geometry"]
                                        )
                                    )
                                    st.session_state.change_detected = False
                                    st.rerun()
                                elif st.button("cancel"):
                                    st.session_state.change_detected = False
                                    st.session_state.editor_key += 1
                                    st.rerun()

                with st.container(
                    horizontal=False,
                    horizontal_alignment="center",
                    vertical_alignment="center",
                    width="content",
                ):
                    with st.container(
                        horizontal=False,
                        horizontal_alignment="center",
                        vertical_alignment="center",
                    ):
                        st.write(
                            "Please mind spaces in affixes!",
                        )

                        affix = st.text_input(
                            label="Add an affix to all areaNames and press where to add it:",
                            placeholder="Add something in front or back of every areaName",
                        )
                        with st.container(
                            horizontal=True,
                            horizontal_alignment="center",
                            vertical_alignment="center",
                        ):
                            if st.button("Front", type="secondary"):
                                if st.session_state.change_detected:
                                    st.error("Save or cancel the changes first")
                                elif not affix:
                                    st.error(
                                        "Type affix before selecting where to add it :)"
                                    )
                                else:
                                    st.session_state.edited_gdf = add_affix(
                                        data=st.session_state.edited_gdf,
                                        affix=affix,
                                        front=True,
                                    )
                                    st.rerun()

                            if st.button("Back", type="secondary"):
                                if st.session_state.change_detected:
                                    st.error("Save or cancel the changes first")
                                elif not affix:
                                    st.error(
                                        "Type affix before selecting where to add it :)"
                                    )
                                else:
                                    st.session_state.edited_gdf = add_affix(
                                        data=st.session_state.edited_gdf,
                                        affix=affix,
                                        front=False,
                                    )
                                    st.rerun()

                    with st.container(
                        horizontal=False,
                        horizontal_alignment="center",
                        vertical_alignment="center",
                    ):
                        remove_part = st.text_input(
                            label="Remove text from every areaName",
                            placeholder="Remove repeating part from each areaName",
                        )
                        with st.container(
                            horizontal=True,
                            horizontal_alignment="center",
                            vertical_alignment="center",
                            width="stretch",
                        ):
                            if st.button("Remove", type="secondary"):
                                if st.session_state.change_detected:
                                    st.error("Save or cancel the changes first")
                                elif not remove_part:
                                    st.error(
                                        "You have to type what you wanna remove before removing it :)"
                                    )
                                else:
                                    st.session_state.edited_gdf = remove_text(
                                        data=st.session_state.edited_gdf,
                                        text_to_remove=remove_part,
                                    )
                                    st.rerun()

        print("\n\n\n\n")
        with st.container(
            horizontal=False,
            horizontal_alignment="center",
            vertical_alignment="center",
        ):
            try:
                print("a")
                new_name = st.text_input(
                    label="Name for new - edited geojson",
                    value=file.name.split(".")[0] + "_edited",
                )
                print("b")
                if st.session_state.change_detected:
                    print("c")
                    st.warning("Save or cancel the changes to download new file")
                    print("d")
                else:
                    print("f")
                    downloadable_file = download_edited_map(st.session_state.edited_gdf)
                    download_new_geojson = st.download_button(
                        label="Download new GeoJSON",
                        data=downloadable_file,
                        file_name=new_name + ".geojson",
                        mime="appliation/geo+json",
                    )
                    print("g")
            except AttributeError:
                print("h")
                new_name = None

        with st.container(
            horizontal=False,
            horizontal_alignment="center",
            vertical_alignment="center",
        ):
            if st.button("Preview map"):
                gdf_map = remove_not_included(st.session_state["edited_gdf"])
                gdf_map = gpd.GeoDataFrame(gdf_map, geometry="geometry", crs=CRS_MAP)

                bounds = gdf_map.total_bounds
                lon_center = (bounds[0] + bounds[2]) / 2
                lat_center = (bounds[1] + bounds[3]) / 2

                # st.write(type(gdf_map))
                fig = px.choropleth_map(
                    gdf_map,
                    geojson=gdf_map.__geo_interface__,
                    locations=gdf_map.index,
                    center={"lat": lat_center, "lon": lon_center},
                    opacity=1,
                )

                fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
                st.plotly_chart(fig, width="stretch")
