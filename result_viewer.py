import streamlit as st
from ansys.dpf import core as dpf
from ansys.dpf.core import examples
from ansys.dpf.core.plotter import DpfPlotter
import tempfile, os, uuid, numpy as np

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Ansys Result Viewer", page_icon=":bar_chart:")
st.title("Ansys Result Viewer")

# --- App Info ---
with st.expander("About This Tool"):
    st.markdown("""
        **Ansys Result Viewer**: An intuitive tool to convert Ansys simulation data into interactive visualizations.

        **Key Features**:
        - Interactive 3D HTML plots for displacement and stress
        - Customizable visual range and mesh edges
        - Upload your files or use built-in examples
        - Share visualizations via HTML download
                
        **Author**: **Manh Tuan Nguyen**
        <div class="social-buttons" style="display: flex; gap: 20px; align-items: center;">
        <a href="https://www.linkedin.com/in/manh-tuan-nguyen19/" target="_blank">
            <img src="https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg" width="30">
        </a>
        </div>
    """,unsafe_allow_html=True)

# --- Sidebar: Upload & Settings ---
st.sidebar.header("Settings")

uploaded_file = st.sidebar.file_uploader(
    "Upload Ansys result file (.rst)",
    type=["rst"]
)

example_choice = st.sidebar.selectbox(
    "Or choose an example:",
    ["None", "Static RST", "Simple Bar", "Crankshaft", "Transient RST"]
)

result_type = st.sidebar.radio("Result Type:", ("Displacement", "Stress (Von Mises)"))
show_edges = st.sidebar.checkbox("Show Mesh Edges", value=True)

# --- Session State Defaults ---
for key, val in {
    'html_content': None,
    'plot_filename': "plot.html",
    'processing_key': str(uuid.uuid4()),
    'data_range': {'Displacement': (0.0, 1.0), 'Stress (Von Mises)': (0.0, 1.0)}
}.items():
    st.session_state.setdefault(key, val)

# --- Utility: Load DataSources ---
def load_data_source():
    if uploaded_file:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(uploaded_file.getbuffer())
        return dpf.DataSources(tmp.name), uploaded_file.name
    elif example_choice != "None":
        example_map = {
            "Static RST": examples.find_static_rst,
            "Simple Bar": examples.find_simple_bar,
            "Crankshaft": examples.download_crankshaft,
            "Transient RST": examples.download_transient_result
        }
        example_file = example_map[example_choice]()
        return dpf.DataSources(example_file), f"{example_choice}.rst"
    return None, ""

# --- Utility: Compute Range ---
def get_data_range(ds, rtype):
    try:
        if rtype == "Displacement":
            op = dpf.operators.result.displacement()
        else:
            op = dpf.operators.result.stress_von_mises()
            op.inputs.requested_location.connect('Nodal')
        op.inputs.data_sources.connect(ds)
        norm = dpf.operators.math.norm_fc(op)
        minmax = dpf.operators.min_max.min_max_fc(norm)
        return float(minmax.outputs.field_min().data), float(minmax.outputs.field_max().data)
    except:
        return 0.0, 1.0

# --- Utility: Plot ---
def generate_plot(ds, model_name, rtype, show_edges, vmin, vmax):
    model = dpf.Model(ds)
    op = dpf.operators.result.displacement() if rtype == "Displacement" else dpf.operators.result.stress_von_mises()
    if rtype == "Stress (Von Mises)":
        op.inputs.requested_location.connect("Nodal")
    op.inputs.data_sources.connect(ds)
    field = op.eval()[0]
    plotter = DpfPlotter()
    plotter.add_field(field=field, meshed_region=model.metadata.meshed_region, show_edges=show_edges, clim=(vmin, vmax))

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        plotter._internal_plotter._plotter.export_html(f.name)
        html = open(f.name, encoding="utf-8").read()
    os.remove(f.name)
    return html, f"{model_name.replace('.', '_')}_{rtype.replace(' ', '_')}.html"

# --- Processing ---
ds, model_name = load_data_source()
if ds:
    vmin, vmax = get_data_range(ds, result_type)
    vmin_input = st.sidebar.number_input("Legend Min", value=vmin)
    vmax_input = st.sidebar.number_input("Legend Max", value=vmax)

    html, fname = generate_plot(ds, model_name, result_type, show_edges, vmin_input, vmax_input)
    if html:
        st.components.v1.html(html, height=600, scrolling=True)
        st.download_button("Download Plot as HTML", data=html, file_name=fname, mime="text/html")
else:
    st.info("Please upload a file or select an example.")
