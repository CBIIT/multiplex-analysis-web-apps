# Import relevant libraries.
import streamlit as st
import polars as pl
import framework.utils as framework_utils
from fast_neighborhood_profiles import main as fnp_main

# Define constant.
ST_KEY_PREFIX = "load_unified_input_file.py__"  # Not actually used as of 1/5/26 at 2:20pm, but defined for consistency.


# Get the list of objects in the bucket.
@st.cache_data()
def get_objects_list(upload_location):
    return fnp_main.get_objects_list(upload_location)


# Store information about possible upload locations.
@st.cache_data()
def get_location_settings():
    return fnp_main.get_location_settings()


@st.cache_data(show_spinner="Sampling dataset...", show_time=True)
def sample_lf(_lf):
    return _lf.collect(engine="streaming").sample(100).sort(pl.col("input_index"))


# Define the main function.
def main():

    # Show the current contents of the selected upload location using a selectable dataframe.
    with st.columns(2)[0]:

        # Create two tabs.
        tab_options = ["From unified input file", "From raw intensities phenotyper"]
        tabs = st.tabs(tab_options)

        # In the first tab, load data from a unified input file.
        with tabs[0]:

            # Display the available unified input files.
            upload_location = "Available input files"
            objects_list = get_objects_list(upload_location)
            unified_datafile_mapping = {fullname.removeprefix("mawa-unified_datafile-").removesuffix(".csv.zip").removesuffix(".csv.gz"): fullname for fullname in objects_list if fullname.startswith("mawa-unified_datafile-") and fullname.endswith((".csv.zip", ".csv.gz"))}
            objects_list = unified_datafile_mapping.keys()
            column_heading = "Unified input file"
            key = "current_contents_table__do_not_persist"
            if objects_list:
                df = pl.DataFrame({column_heading: objects_list})
                st.dataframe(df, on_select="rerun", key=key, selection_mode="single-row")
                st.write(f"{len(objects_list)} unified input file(s) found.")
            else:
                st.write("No unified input files found.")
            st.button("Refresh file list", on_click=get_objects_list.clear)

            # If some files are selected...
            if key in st.session_state:
                rows = st.session_state[key]["selection"]["rows"]
                if rows:
                    
                    # Get a list of the selected shortnames (short versions of the filenames).
                    selected_filenames = df[rows][column_heading].to_list()

                    # Load the lazyframe from the selected row.
                    if st.button(f":warning: Load unified input file", help="We recommend that you press the \"🧹 Reset app\" button on the left sidebar before loading a new file in order to start cleanly. If so, and if it's important, please back up the app session first at the \"Manage sessions\" page at left. The primary point of that is to free of memory from pages *outside* the high-performance workflow. Separately, pressing this button will delete downstream data *inside* the high-performance workflow as well, which makes sense because we are opening a new dataset here. So, please ensure any results in the high-performance workflow are sufficiently backed up before proceeding."):
                        object_filename = unified_datafile_mapping[selected_filenames[0]]
                        file_format = "parquet"
                        db_schema = get_location_settings()[upload_location]["db_schema"]
                        bucket_name = get_location_settings()[upload_location]["bucket_name"]
                        params = dict(file_format=file_format, db_schema=db_schema, bucket_name=bucket_name, object_filename=object_filename)
                        with st.spinner("Loading file..."):
                            lf = fnp_main.load_unified_input_file_data(**params, topdir=framework_utils.session_dir())
                        st.session_state["LAZYFRAMES"] = {}  # Clear existing lazyframes.
                        st.session_state["LAZYFRAMES"]["unified_input_file"] = {
                            "lf": lf,
                            "function_metadata": {"module_name": "fast_neighborhood_profiles.main", "qualpath": "load_unified_input_file_data"},
                            "input_dataset": None,
                            "params": params,
                        }
                        st.session_state[ST_KEY_PREFIX + "data_loading_method"] = tab_options[0]
                        fnp_main.clear_data_in_memory(st.session_state, st_key_prefixes=["phenotype.py__", "delete_cells.py__", "run_spatial_umap.py__", "assign_neighborhood_types.py__", "plot_neighborhood_types.py__"], function_caches=[sample_lf])

        # In the second tab, load data from raw intensities phenotyper.
        with tabs[1]:
            if "mg__df" in st.session_state:
                if st.button("Load data from raw intensities phenotyper"):
                    params = dict(handle="unified_input_file", file_format="parquet", index_column_name="input_index")
                    with st.spinner("Loading data..."):
                        lf = fnp_main.load_phenotyped_raw_intensities_data(st.session_state["mg__df"], **params, topdir=framework_utils.session_dir())
                    st.session_state["LAZYFRAMES"] = {}  # Clear existing lazyframes.
                    st.session_state["LAZYFRAMES"]["unified_input_file"] = {
                        "lf": lf,
                        "function_metadata": {"module_name": "fast_neighborhood_profiles.main", "qualpath": "load_phenotyped_raw_intensities_data"},
                        "input_dataset": {"type": "pandas_df", "keys": ("mg__df",)},
                        "params": params,
                        }
                    st.session_state[ST_KEY_PREFIX + "data_loading_method"] = tab_options[1]
                    fnp_main.clear_data_in_memory(st.session_state, st_key_prefixes=["phenotype.py__", "delete_cells.py__", "run_spatial_umap.py__", "assign_neighborhood_types.py__", "plot_neighborhood_types.py__"], function_caches=[sample_lf])
            else:
                st.info("You need to run the \"Using Raw Intensities\" page in the \"Phenotyping\" page at left first.")

    # If there's lazyframe information in the session state...
    if not ("LAZYFRAMES" in st.session_state and "unified_input_file" in st.session_state["LAZYFRAMES"]):
        st.info("Please load a unified input file (whether above or from a session archive) to see its details here.")
        return

    # Get information about the lazyframe from the metadata in the session state.
    params = st.session_state["LAZYFRAMES"]["unified_input_file"]["params"]
    file_format = params["file_format"]
    db_schema = params["db_schema"] if "db_schema" in params else "N/A"
    bucket_name = params["bucket_name"] if "bucket_name" in params else "N/A"
    object_filename = params["object_filename"] if "object_filename" in params else "N/A"

    # Get the lazyframe from the session state now.
    lf = st.session_state["LAZYFRAMES"]["unified_input_file"]["lf"]

    # At this point the lazyframe must be working, so display information about it.
    information = f'''
    Properties:

    :small_orange_diamond: Data loading method: `{st.session_state[ST_KEY_PREFIX + "data_loading_method"]}`  
    :small_orange_diamond: File format: `{file_format}`  
    :small_orange_diamond: database.schema: `{db_schema}`  
    :small_orange_diamond: Bucket name: `{bucket_name}`  
    :small_orange_diamond: Object filename: `{object_filename}`  
    :small_orange_diamond: Number of rows: `{lf.select(pl.len()).collect(engine="streaming").item():_}`  
    :small_orange_diamond: Number of columns: `{len(lf.collect_schema())}`  
    '''
    st.markdown(information)

    # Show a sample of 100 rows from the lazyframe.
    st.write(sample_lf(lf))
    st.button("Resample dataset", on_click=sample_lf.clear)


# Run the main function if this script is executed.
if __name__ == "__main__":
    main()
