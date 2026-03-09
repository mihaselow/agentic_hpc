import math
from typing import Tuple, Optional, Dict
from pydantic import BaseModel
from config_manager import HardwareCatalog, HardwareNode
from llm_engine import LLMEngine

class GenerationResult(BaseModel):
    slurm_script: str
    solver_journal: str
    warning: Optional[str] = None
    cores_allocated: int
    nodes_allocated: int

class Router:
    @staticmethod
    def detect_solver(solver_name: str) -> str:
        """Detects and standardizes the requested solver name."""
        name = solver_name.strip().lower()
        if "fluent" in name:
            return "fluent"
        # Default to fluent if unknown
        return "fluent"

class ScriptGenerator:
    def __init__(self, llm_engine: LLMEngine, context: str):
        self.llm_engine = llm_engine
        self.context = context

    def generate(
        self,
        project_path: str,
        mesh_scale_cells: int,
        physics_type: str,
        hardware_catalog: HardwareCatalog,
        partition_name: str,
        solver_name: str = "Fluent"
    ) -> GenerationResult:
        
        solver = Router.detect_solver(solver_name)
        
        # 1. Calculate required cores (1 core per 100k cells)
        cores_needed = math.ceil(mesh_scale_cells / 100000)
        if cores_needed < 1:
            cores_needed = 1

        # 2. Cross-reference against Hardware Catalog
        partition = next(
            (p for p in hardware_catalog.nodes if p.partition_name == partition_name), 
            None
        )
        
        warning_msg = None
        nodes_needed = 1
        cores_per_node_allocated = cores_needed
        
        if partition:
            if cores_needed > partition.cores_per_node:
                nodes_needed = math.ceil(cores_needed / partition.cores_per_node)
                cores_per_node_allocated = partition.cores_per_node
                warning_msg = (
                    f"Warning: Requested cores ({cores_needed}) exceeds partition's max cores "
                    f"per node ({partition.cores_per_node}). Suggesting multi-node configuration "
                    f"using {nodes_needed} nodes."
                )
            else:
                cores_per_node_allocated = cores_needed
        else:
            warning_msg = f"Warning: Partition '{partition_name}' not found in hardware catalog. Proceeding with requested cores."

        total_cores = nodes_needed * cores_per_node_allocated

        # 3. Generate Slurm Script (Enforcing Architectural Constraints)
        # Constraint: must include --exclusive and --cpu-bind=cores
        slurm_script = self._generate_slurm_script(
            project_path=project_path,
            partition_name=partition_name,
            nodes=nodes_needed,
            cores_per_node=cores_per_node_allocated,
            total_cores=total_cores,
            solver=solver
        )

        # 4. Generate Solver Journal via LLM
        # We ask the LLM to generate the journal based on the physics type and knowledge base
        llm_prompt = (
            f"Generate an Ansys {solver.capitalize()} solver journal (.jou) for a "
            f"'{physics_type}' simulation.
"
            f"The mesh has {mesh_scale_cells} cells.
"
            f"Only output the raw journal commands. Do not include markdown formatting or explanations."
        )
        
        try:
            solver_journal = self.llm_engine.generate(llm_prompt, self.context)
        except Exception as e:
            solver_journal = f"; Error generating journal via LLM: {e}
; Fallback journal template
file/read-case data.cas.h5"
            
        # Clean up LLM output (remove potential markdown blocks)
        solver_journal = solver_journal.replace("```journal", "").replace("```", "").strip()

        # Constraint: Every journal must end with an explicit exit command
        if not solver_journal.strip().endswith("exit"):
            if not solver_journal.endswith("
"):
                solver_journal += "
"
            solver_journal += "exit
"

        return GenerationResult(
            slurm_script=slurm_script,
            solver_journal=solver_journal,
            warning=warning_msg,
            cores_allocated=total_cores,
            nodes_allocated=nodes_needed
        )

    def _generate_slurm_script(
        self, 
        project_path: str, 
        partition_name: str, 
        nodes: int, 
        cores_per_node: int, 
        total_cores: int,
        solver: str
    ) -> str:
        script = [
            "#!/bin/bash",
            f"#SBATCH --job-name={solver}_job",
            f"#SBATCH --partition={partition_name}",
            f"#SBATCH --nodes={nodes}",
            f"#SBATCH --ntasks-per-node={cores_per_node}",
            "#SBATCH --exclusive",          # Architectural Constraint
            "#SBATCH --cpu-bind=cores",     # Architectural Constraint
            f"#SBATCH --output={project_path}/job_%j.out",
            f"#SBATCH --error={project_path}/job_%j.err",
            "",
            f"cd {project_path}",
            ""
        ]
        
        if solver == "fluent":
            script.append(
                f"fluent 3ddp -g -t{total_cores} -i solver_journal.jou > fluent_output.log 2>&1"
            )
        else:
            script.append(f"# Command to run {solver} goes here")
            
        return "
".join(script)
