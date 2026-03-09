import os
import csv
from typing import List, Optional
from pydantic import BaseModel
import PyPDF2

class HardwareNode(BaseModel):
    partition_name: str
    nodes_available: int
    cores_per_node: int
    memory_gb: int

class HardwareCatalog(BaseModel):
    nodes: List[HardwareNode]

class SolverConfig(BaseModel):
    name: str
    version: Optional[str] = None
    default_executable: str

def load_hardware_catalog(csv_path: str) -> HardwareCatalog:
    """Loads hardware catalog from a CSV file into Pydantic models."""
    nodes = []
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                nodes.append(HardwareNode(
                    partition_name=row['partition_name'],
                    nodes_available=int(row['nodes_available']),
                    cores_per_node=int(row['cores_per_node']),
                    memory_gb=int(row['memory_gb'])
                ))
    else:
        print(f"Warning: Hardware catalog not found at {csv_path}")
    return HardwareCatalog(nodes=nodes)

def ingest_knowledge_base(base_dir: str = "knowledge") -> str:
    """
    Reads all .pdf, .txt, and .md files in the knowledge/manuals, knowledge/hardware,
    and knowledge/templates directories and concatenates their content to form
    the Source of Truth context for the LLM.
    """
    context = []
    target_dirs = [
        os.path.join(base_dir, "manuals"),
        os.path.join(base_dir, "hardware"),
        os.path.join(base_dir, "templates")
    ]

    for d in target_dirs:
        if not os.path.exists(d):
            continue
        for filename in os.listdir(d):
            filepath = os.path.join(d, filename)
            if not os.path.isfile(filepath):
                continue
            
            ext = os.path.splitext(filename)[1].lower()
            try:
                if ext in ['.txt', '.md']:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        context.append(f"--- Document: {filename} ---
{content}
")
                elif ext == '.pdf':
                    with open(filepath, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = []
                        for page in reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text.append(extracted)
                        content = "
".join(text)
                        context.append(f"--- Document: {filename} ---
{content}
")
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                
    return "
".join(context)
