# Import relevant libraries.
import streamlit as st
from fast_neighborhood_profiles import main as fnp_main
import streamlit_dataframe_editor as sde
import pandas as pd
import polars as pl


# Define session state key prefixes.
ST_KEY_PREFIX = "delete_cells.py__"
ST_KEY_PREFIX_PHENOTYPE = "phenotype.py__"


# Obtain the selected indices from the scatter plot.
def get_selected_indices():
    selection = st.session_state[ST_KEY_PREFIX + f"scatter_plot__do_not_persist"]
    if "selection" in selection and "points" in selection["selection"] and selection["selection"]["points"]:
        points_list = selection["selection"]["points"]
        indices = [point["customdata"][4] for point in points_list]  # Note this means that if the "input_index" column is added to the plot data when calling main.plot_image_from_frame(), it must be the very first custom_column, i.e., at position 4 (0-based indexing) since there are four required columns in front of it.
        st.session_state[ST_KEY_PREFIX + "selected_indices"] = indices
    else:
        st.session_state[ST_KEY_PREFIX + "selected_indices"] = []


# Main function.
def main():

    # Ensure the phenotyped lazyframe is ready for usage.
    if not ("LAZYFRAMES" in st.session_state and "phenotyped" in st.session_state["LAZYFRAMES"]):
        st.warning("Please perform phenotyping (at left).")
        return

    # Get the main lazyframe from session state.
    lf_phenotyped = st.session_state["LAZYFRAMES"]["phenotyped"]["lf"]

    # Grab values we'll need downstream.
    unique_image_ids = st.session_state[ST_KEY_PREFIX_PHENOTYPE + "unique_image_ids"]
    selected_indices = []
    if ST_KEY_PREFIX + "selected_indices" in st.session_state and st.session_state[ST_KEY_PREFIX + "selected_indices"]:
        selected_indices = st.session_state[ST_KEY_PREFIX + "selected_indices"]
    image_colname = "Image ID_(standardized)"
    xcol = "Centroid X (µm)_(standardized)"
    ycol = "Centroid Y (µm)_(standardized)"
    color_col = "label"
    key = ST_KEY_PREFIX + "de_selections"
    if key not in st.session_state:
        st.session_state[key] = sde.DataframeEditor(df_name=ST_KEY_PREFIX + "df_selections", default_df_contents=pd.DataFrame(columns=["label", "number_of_cells", "input_indices", "color"]))
    phenotype_color_map = st.session_state[ST_KEY_PREFIX_PHENOTYPE + "phenotype_color_map"]
    missing_label_value = "Other"

    st.header(":one: Select cells to delete")
    st.write("Create \"deletion groups\" by selecting groups of cells and adding them to the selections table below.")

    with st.container(horizontal=True, vertical_alignment="bottom"):
        selected_image_to_plot = st.selectbox("Select image to plot:", options=unique_image_ids, key=ST_KEY_PREFIX + "selected_image_to_plot")
        st.button("Previous", on_click=lambda: st.session_state.update({ST_KEY_PREFIX + "selected_image_to_plot": unique_image_ids[max(0, unique_image_ids.index(st.session_state[ST_KEY_PREFIX + "selected_image_to_plot"]) - 1)]}), disabled=(st.session_state[ST_KEY_PREFIX + "selected_image_to_plot"] == unique_image_ids[0]), key=ST_KEY_PREFIX + "previous_button__do_not_persist")
        st.button("Next", on_click=lambda: st.session_state.update({ST_KEY_PREFIX + "selected_image_to_plot": unique_image_ids[min(len(unique_image_ids) - 1, unique_image_ids.index(st.session_state[ST_KEY_PREFIX + "selected_image_to_plot"]) + 1)]}), disabled=(st.session_state[ST_KEY_PREFIX + "selected_image_to_plot"] == unique_image_ids[-1]), key=ST_KEY_PREFIX + "next_button__do_not_persist")

    # Allow user to plot rectangles faithful to the object sizes, if possible.
    st.session_state.setdefault(ST_KEY_PREFIX + "plot_faithful_object_sizes", False)
    plot_faithful_object_sizes = st.checkbox("Plot faithful object sizes (if available)", key=ST_KEY_PREFIX + "plot_faithful_object_sizes")

    # Allow the user to select marker size.
    st.session_state.setdefault(ST_KEY_PREFIX + "marker_size", 5)
    marker_size = st.slider("Marker size:", min_value=2, max_value=10, key=ST_KEY_PREFIX + "marker_size", disabled=plot_faithful_object_sizes)

    # Write the number of selected points.
    with st.container(horizontal=True):
        st.write(f"Number of selected points: {len(selected_indices):_}")
        st.button("Clear selection", on_click=lambda: st.session_state.update({ST_KEY_PREFIX + "selected_indices": []}), key=ST_KEY_PREFIX + "clear_selection_button__do_not_persist")

    # Plot the scatter plot with selectable points.
    frame_with_faithful_columns = st.session_state["LAZYFRAMES"]["unified_input_file"]["lf"] if plot_faithful_object_sizes else None
    fig = fnp_main.plot_image_from_frame(lf_phenotyped, image_colname=image_colname, xcol=xcol, ycol=ycol, color_col=color_col, selected_images=[selected_image_to_plot], marker_size=marker_size, custom_columns=["input_index"], color_map=phenotype_color_map, sort_index_col="input_index", plot_faithful_object_sizes=plot_faithful_object_sizes, frame_with_faithful_columns=frame_with_faithful_columns)
    fig.update_layout(uirevision="static")  # this doesn't seem to be honored; investigate in the future... actually, maybe it is?
    st.plotly_chart(fig, on_select=get_selected_indices, selection_mode=("points", "box", "lasso"), key=ST_KEY_PREFIX + "scatter_plot__do_not_persist")

    # If there are selected points...
    if selected_indices:

        # Allow user to choose a label for the selected cells.
        key = ST_KEY_PREFIX + "selected_label"
        st.session_state.setdefault(key, "")
        selected_label = st.text_input("Enter label for selected cells (can edit later)", key=key)

        # Allow user to pick color of selected cells.
        key = ST_KEY_PREFIX + "selected_color"
        st.session_state.setdefault(key, "#FF0000")  # FF0000 is red
        selected_color = st.color_picker("Select color for selected cells (can edit later)", key=key)

        # Allow user to add the selected cells to a selections dataframe.
        if st.button("Add selected cells to selections table"):
            df = st.session_state[ST_KEY_PREFIX + "de_selections"].reconstruct_edited_dataframe()
            new_row = {
                "label": selected_label if selected_label else f"Selection {len(df) + 1}",
                "number_of_cells": len(selected_indices),
                "input_indices": selected_indices,
                "color": selected_color,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state[ST_KEY_PREFIX + "de_selections"].update_editor_contents(new_df_contents=df)

    # Plot the editable and selectable tables side-by-side.
    st.session_state[ST_KEY_PREFIX + "de_selections"].dataframe_editor(reset_data_editor_button_text='Reset deletion groups', disabled=["number_of_cells", "input_indices"])

    st.header(":two: Register all deletion groups for deletion")

    # Add option for user to modify how to keep duplicate cell assignments when registering deletion groups.
    key = ST_KEY_PREFIX + "keep_strategy"
    st.session_state.setdefault(key, "any")
    keep_strategy = st.radio("Select keep strategy for resolving multiple labels for a given cell when registering deletion groups:", options=['first', 'last', 'any', 'none'], key=key, help='"none" drops duplicates; "any" is non-deterministic but fast.', horizontal=True)
    
    # Allow user to register the selected deletion groups.
    if st.button("Register selected deletion groups"):
        df = st.session_state[ST_KEY_PREFIX + "de_selections"].reconstruct_edited_dataframe()
        if len(df) > 0:
            params = dict(updates_pd=df, keep=keep_strategy, missing_label_value=missing_label_value, updates_index_column="input_indices", main_index_column="input_index", new_label_column="deletion_group")
            lf_with_deletion_groups = fnp_main.add_new_label_column(lf=lf_phenotyped, **params)
            st.session_state["LAZYFRAMES"]["deletion_groups"] = {
                "lf": lf_with_deletion_groups,
                "function_metadata": {"module_name": "fast_neighborhood_profiles.main", "qualpath": "add_new_label_column"},
                "input_dataset": {"type": "lf", "keys": ("phenotyped",)},
                "params": params,
            }
            color_map = dict(zip(df["label"], df["color"]))
            color_map[missing_label_value] = "#808080"
            st.session_state[ST_KEY_PREFIX + "deletion_group_color_map"] = color_map
            st.success("Deletion groups registered successfully.")
        else:
            if "deletion_groups" in st.session_state["LAZYFRAMES"]:
                del st.session_state["LAZYFRAMES"]["deletion_groups"]
            if ST_KEY_PREFIX + "deletion_group_color_map" in st.session_state:
                del st.session_state[ST_KEY_PREFIX + "deletion_group_color_map"]
            st.success("No deletion groups to register; existing deletion groups (if any) have been cleared.")

    # Ensure the deletion groups lazyframe is ready for usage.
    if "deletion_groups" not in st.session_state["LAZYFRAMES"]:
        st.warning("Please register deletion groups above.")
        return

    # Get the main lazyframe from session state.
    lf_with_deletion_groups = st.session_state["LAZYFRAMES"]["deletion_groups"]["lf"]

    st.header(":three: Visually confirm cells to be deleted")

    # Allow user to select which image to visualize.
    with st.container(horizontal=True, vertical_alignment="bottom"):
        selected_image_to_plot_for_deletion_groups = st.selectbox("Select image to plot:", options=unique_image_ids, key=ST_KEY_PREFIX + "selected_image_to_plot_for_deletion_groups")
        st.button("Previous", on_click=lambda: st.session_state.update({ST_KEY_PREFIX + "selected_image_to_plot_for_deletion_groups": unique_image_ids[max(0, unique_image_ids.index(st.session_state[ST_KEY_PREFIX + "selected_image_to_plot_for_deletion_groups"]) - 1)]}), disabled=(st.session_state[ST_KEY_PREFIX + "selected_image_to_plot_for_deletion_groups"] == unique_image_ids[0]), key=ST_KEY_PREFIX + "previous_button_deletion_groups__do_not_persist")
        st.button("Next", on_click=lambda: st.session_state.update({ST_KEY_PREFIX + "selected_image_to_plot_for_deletion_groups": unique_image_ids[min(len(unique_image_ids) - 1, unique_image_ids.index(st.session_state[ST_KEY_PREFIX + "selected_image_to_plot_for_deletion_groups"]) + 1)]}), disabled=(st.session_state[ST_KEY_PREFIX + "selected_image_to_plot_for_deletion_groups"] == unique_image_ids[-1]), key=ST_KEY_PREFIX + "next_button_deletion_groups__do_not_persist")

    # Allow the user to select whether to exclude the deleted cells from the plot.
    st.session_state.setdefault(ST_KEY_PREFIX + "exclude_deleted_cells_from_deletion_groups_plot", True)
    exclude_deleted_cells_from_deletion_groups_plot = st.checkbox("Exclude deleted cells from plot", key=ST_KEY_PREFIX + "exclude_deleted_cells_from_deletion_groups_plot")
    if exclude_deleted_cells_from_deletion_groups_plot:
        lf_to_plot = lf_with_deletion_groups.filter(pl.col("deletion_group").eq(missing_label_value))
    else:
        lf_to_plot = lf_with_deletion_groups

    # Allow the user to select whether to color by phenotype or deletion groups.
    st.session_state.setdefault(ST_KEY_PREFIX + "color_deletion_groups_by", "Phenotype")
    color_deletion_groups_by = st.radio("Color deletion group plot by:", options=["Phenotype", "Deletion group"], key=ST_KEY_PREFIX + "color_deletion_groups_by", horizontal=True)

    # Allow user to plot rectangles faithful to the object sizes, if possible.
    st.session_state.setdefault(ST_KEY_PREFIX + "plot_faithful_object_sizes_for_deletion_groups", False)
    plot_faithful_object_sizes_for_deletion_groups = st.checkbox("Plot faithful object sizes (if available)", key=ST_KEY_PREFIX + "plot_faithful_object_sizes_for_deletion_groups")

    # Allow the user to select marker size.
    st.session_state.setdefault(ST_KEY_PREFIX + "marker_size_real_space_for_deletion_groups", 5)
    marker_size_real_space_for_deletion_groups = st.slider("Marker size:", min_value=2, max_value=10, key=ST_KEY_PREFIX + "marker_size_real_space_for_deletion_groups", disabled=plot_faithful_object_sizes_for_deletion_groups)

    # Plot the scatter plot.
    color_col_mapping = {"Phenotype": "label", "Deletion group": "deletion_group"}
    color_map_mapping = {"Phenotype": phenotype_color_map, "Deletion group": st.session_state[ST_KEY_PREFIX + "deletion_group_color_map"]}
    frame_with_faithful_columns = st.session_state["LAZYFRAMES"]["unified_input_file"]["lf"] if plot_faithful_object_sizes_for_deletion_groups else None
    fig = fnp_main.plot_image_from_frame(lf_to_plot, image_colname=image_colname, xcol=xcol, ycol=ycol, color_col=color_col_mapping[color_deletion_groups_by], selected_images=[selected_image_to_plot_for_deletion_groups], marker_size=marker_size_real_space_for_deletion_groups, custom_columns=["input_index"], color_map=color_map_mapping[color_deletion_groups_by], plot_faithful_object_sizes=plot_faithful_object_sizes_for_deletion_groups, frame_with_faithful_columns=frame_with_faithful_columns, sort_index_col="input_index")
    fig.update_layout(uirevision="static")  # this doesn't seem to be honored; investigate in the future
    st.plotly_chart(fig)

    st.header(":four: Create filtered unified datafile")

    # Allow user to modify the name of a new unified datafile to write out.
    st.session_state.setdefault(ST_KEY_PREFIX + "output_unified_datafile_name", st.session_state["LAZYFRAMES"]["unified_input_file"]["params"]["object_filename"].removeprefix("mawa-unified_datafile-").removesuffix(".csv.zip").removesuffix(".csv.gz"))
    output_unified_datafile_name = st.text_input("Enter name for modified unified datafile (without any prefixes or suffixes, just like the example):", key=ST_KEY_PREFIX + "output_unified_datafile_name")

    # Allow user to write out the modified unified datafile with the deletion groups deleted.
    if st.button("Write modified unified datafile with deletion groups deleted"):
        fnp_main.push_filtered_lazyframe_to_object_store(st.session_state["LAZYFRAMES"]["unified_input_file"]["lf"], st.session_state[ST_KEY_PREFIX + "de_selections"].reconstruct_edited_dataframe(), output_unified_datafile_name)
        st.success(f"Modified unified datafile written to object store. Now start from the \"Load unified input file\" page at left and load this modified datafile (you may have to refresh the file listing there).")


# Run the main function if this script is executed.
if __name__ == "__main__":
    main()
