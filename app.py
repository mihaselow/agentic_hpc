import streamlit as st
import os
from config_manager import load_hardware_catalog, ingest_knowledge_base
from llm_engine import LLMEngine
from core_logic import ScriptGenerator, Router

# Constants
HARDWARE_CATALOG_PATH = "knowledge/hardware/hardware_catalog.csv"

# Configure Streamlit page for a professional, "Dark Mode" aesthetic
st.set_page_config(
    page_title="HPC-Architect-Bot",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State for LLM and Knowledge Base
if 'llm_engine' not in st.session_state:
    st.session_state.llm_engine = LLMEngine()
if 'knowledge_context' not in st.session_state:
    with st.spinner("Ingesting Knowledge Base..."):
        st.session_state.knowledge_context = ingest_knowledge_base()
if 'hardware_catalog' not in st.session_state:
    st.session_state.hardware_catalog = load_hardware_catalog(HARDWARE_CATALOG_PATH)

# Ensure hardware catalog is loaded before proceeding
if not st.session_state.hardware_catalog.nodes:
    st.error(f"Hardware catalog not found or empty at {HARDWARE_CATALOG_PATH}. Please provide a valid CSV.")
    st.stop()

st.title("HPC-Architect-Bot 🚀")
st.markdown("Generate *Architecturally Certified* Slurm scripts and solver journals based on engineering intent.")

# Initialize ScriptGenerator
generator = ScriptGenerator(st.session_state.llm_engine, st.session_state.knowledge_context)

# Sidebar - Configuration
with st.sidebar:
    st.header("Project Configuration")
    project_path = st.text_input("Project Path", value="/scratch/user/fluent_project")
    mesh_scale_cells = st.number_input(
        "Mesh Scale (Cells)", 
        min_value=100_000, 
        value=10_000_000, 
        step=1_000_000,
        help="Used to calculate core count (1 core per 100k cells)."
    )
    physics_type = st.selectbox(
        "Physics Type", 
        ["Steady State", "Transient", "Multiphase", "Combustion"]
    )
    
    solver_type = st.selectbox(
        "Solver Type",
        ["Fluent", "CFX", "Mechanical"] # Defaulting to Fluent is handled by core logic
    )
    
    # Dynamically populate partition names from the loaded catalog
    partition_options = [node.partition_name for node in st.session_state.hardware_catalog.nodes]
    partition = st.selectbox("Partition", partition_options)
    
    generate_btn = st.button("Generate Bundle", type="primary", use_container_width=True)

# Main Content Area
if generate_btn:
    with st.spinner("Generating Architecturally Certified Scripts..."):
        # Generate the scripts using the core logic engine
        result = generator.generate(
            project_path=project_path,
            mesh_scale_cells=mesh_scale_cells,
            physics_type=physics_type,
            hardware_catalog=st.session_state.hardware_catalog,
            partition_name=partition,
            solver_name=solver_type
        )
        
        # Display validation warnings if any
        if result.warning:
            st.warning(result.warning)
            
        st.success(f"Generated successfully! Allocated {result.cores_allocated} cores across {result.nodes_allocated} node(s).")
        
        # Split-screen view for the generated scripts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Slurm Script (`submit.sh`)")
            st.code(result.slurm_script, language="bash")
            st.download_button(
                label="Download Slurm Script",
                data=result.slurm_script,
                file_name="submit.sh",
                mime="text/x-shellscript"
            )
            
        with col2:
            st.subheader(f"Solver Journal (`{solver_type.lower()}_journal.jou`)")
            st.code(result.solver_journal, language="lisp") # Using lisp for simple journal highlighting
            st.download_button(
                label="Download Solver Journal",
                data=result.solver_journal,
                file_name=f"{solver_type.lower()}_journal.jou",
                mime="text/plain"
            )
else:
    st.info("Fill out the configuration on the sidebar and click 'Generate Bundle'.")
