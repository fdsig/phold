import os
import requests
import weave
from typing import Annotated, List, Dict, Any
from weave import Content
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from protean import Protean

# Initialize weave project
weave.init('protein-folding-viz')

class AlphaFoldFetcher:
    API_BASE = "https://alphafold.ebi.ac.uk/api"
    PREDICTION_URL = f"{API_BASE}/prediction"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    @weave.op
    def fetch_pdb_content(self, uniprot_id: str) -> str:
        """Fetches the PDB file content from AlphaFold DB."""
        url = f"{self.PREDICTION_URL}/{uniprot_id}"
        print(f"Fetching metadata for {uniprot_id}...")
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 404:
                print(f"Error: {uniprot_id} not found in AlphaFold DB.")
                return None
            response.raise_for_status()
            data = response.json()
            if not data: return None
            
            pdb_url = data[0].get("pdbUrl")
            if not pdb_url: return None

            print(f"Downloading PDB for {uniprot_id}...")
            pdb_response = self.session.get(pdb_url, timeout=self.timeout)
            pdb_response.raise_for_status()
            return pdb_response.text
        except Exception as e:
            print(f"Fetch failed for {uniprot_id}: {e}")
            return None

@weave.op
def process_protein_workflow(uniprot_id: str):
    """
    Main workflow: Fetch -> Instantiate Protean -> Process all 20 AA methods.
    """
    fetcher = AlphaFoldFetcher()
    pdb_content = fetcher.fetch_pdb_content(uniprot_id)
    
    if not pdb_content:
        return f"Skipped {uniprot_id}: No structural data available."
    
    # Create the protein object from the separate protean.py class
    protein = Protean(uniprot_id, pdb_content)
    
    # Run the comprehensive amino acid analysis
    # This will trigger 20 child traces (alanine, arginine, etc.)
    return protein.process_all_components()

if __name__ == "__main__":
    # Test with Engrailed (P10379) - a core Drosophila protein
    # and vegD (Q9V3G5) if available.
    test_proteins = ["P10379", "Q9V3G5"]
    
    for pid in test_proteins:
        print(f"\n--- Starting Analysis for {pid} ---")
        process_protein_workflow(pid)
