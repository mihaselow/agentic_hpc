# Implementation Plan: HPC-Architect-Bot

This plan outlines the steps to build the Python-based "HPC-Architect-Bot" framework for generating "Architecturally Certified" Slurm scripts and solver journals.

## Phase 1: Project Setup & Dependencies
- [ ] Initialize the project structure. Ensure `knowledge/manuals`, `knowledge/hardware`, and `knowledge/templates` directories exist.
- [ ] Create `requirements.txt` specifying Python 3.10+ compatibility, Streamlit, Pydantic, the `ai4free` integration library (or dependencies required to interact with it), and any libraries needed for document parsing (e.g., `PyPDF2` or `pdfplumber` for PDFs).

## Phase 2: Configuration & Data Management (`config_manager.py`)
- [ ] Implement `config_manager.py` to handle data ingestion and configurations.
- [ ] Create Pydantic models for the Hardware Catalog and Solver Configurations.
- [ ] Implement a function to read and parse a CSV-based Hardware Catalog into the Pydantic models.
- [ ] Implement a function to ingest the "Knowledge Base" (read all `.pdf`, `.txt`, and `.md` files in the `knowledge/` directories) to construct the "Source of Truth" context for the LLM.

## Phase 3: LLM Integration (`llm_engine.py`)
- [ ] Implement `llm_engine.py` using the `ai4free` API.
- [ ] Create a robust function for making API calls, including an implementation of **exponential backoff** to handle rate limits or API instability.
- [ ] Design the system prompt mechanism that injects the ingested "Source of Truth" from the knowledge base into the LLM context.

## Phase 4: Core Logic Engine
- [ ] Create a `Router` class to detect the requested solver (defaulting to Fluent).
- [ ] Implement the `ScriptGenerator` class with the following capabilities:
    - Receive user inputs: Project Path, Mesh Scale (cells), Physics Type, Hardware constraints.
    - Calculate required resources using the rule: **1 core per 100k cells**.
    - Cross-reference calculated requirements against the Hardware Catalog.
    - **Validation Constraint:** If `requested_cores > hardware_max_cores`, trigger a warning and suggest a multi-node configuration.
    - Generate the Slurm Script (`.sh`).
        - **Affinity Constraint:** Ensure `--exclusive` and `--cpu-bind=cores` are always included.
    - Generate the Solver Journal (`.jou`).
        - **Cleanup Constraint:** Ensure the journal explicitly ends with an `exit` command.

## Phase 5: Streamlit Frontend (`app.py`)
- [ ] Develop `app.py` using Streamlit.
- [ ] Configure the UI for a "Dark Mode" aesthetic.
- [ ] Implement input sections:
    - Text fields: "Project Path", "Mesh Scale (e.g., 10M cells)", "Physics Type (Steady/Transient)".
    - Selectors: Dropdown for "Solver Type" (Default: Fluent) and "Partition" (drawn from Hardware Catalog).
- [ ] Implement the interaction logic: send inputs to the `ScriptGenerator` (and subsequently the LLM engine).
- [ ] Design the Output view: A split-screen layout displaying the generated Slurm Script on the left and the Solver Journal on the right.
- [ ] Add a "Download Bundle" button allowing the user to save both generated files.

## Phase 6: Sample Data & Initial Testing
- [ ] Create a sample `hardware_catalog.csv` in `knowledge/hardware/`.
- [ ] Create a sample `fluent_manual_snippet.txt` in `knowledge/manuals/`.
- [ ] Perform end-to-end testing to verify resource calculation, script generation constraints, UI responsiveness, and LLM integration.
