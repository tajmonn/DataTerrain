import streamlit as st
import geopandas as gpd

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


def download_edited_map():
    pass


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
                        )
                        if st.session_state.change_detected:
                            st.warning(
                                "save changes before using add/delete functions on the left or generating the map"
                            )
                            if st.button("save changes"):
                                st.session_state.edited_gdf = changed_edited_gdf
                                st.session_state.change_detected = False
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
                            label="Add an affix to all areaNames and press where to add it:",  # TODO add check if was changed the editable data thingy
                            placeholder="Add something in front or back of every areaName",
                        )
                        with st.container(
                            horizontal=True,
                            horizontal_alignment="center",
                            vertical_alignment="center",
                        ):
                            if st.button("Front", type="secondary"):
                                if not affix:
                                    st.error(
                                        "Type affix before selecting where to add it :)"
                                    )
                                else:
                                    st.session_state.edited_gdf = add_affix(
                                        data=st.session_state.edited_gdf,
                                        affix=affix,
                                        front=True,
                                    )
                                    # data_editor already rendered above with old data,
                                    # so force a rerun to make it reflect the update
                                    st.rerun()
                            if st.button("Back", type="secondary"):
                                if not affix:
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
                        if st.button("Remove", type="secondary"):
                            if not remove_part:
                                st.error(
                                    "You have to type what you wanna remove before removing it :)"
                                )
                            else:
                                st.session_state.edited_gdf = remove_text(
                                    data=st.session_state.edited_gdf,
                                    text_to_remove=remove_part,
                                )
                                st.rerun()

        with st.container(
            horizontal=False,
            horizontal_alignment="center",
            vertical_alignment="center",
        ):
            try:
                new_name = st.text_input(
                    label="Name for new - edited geojson",
                    value=file.name.split(".")[0] + "_edited",
                )
                download_edited = st.button(
                    "Download new geojson", on_click=download_edited_map
                )
            except AttributeError:
                new_name = None
