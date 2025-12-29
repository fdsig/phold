import requests
import os
from typing import Optional, List, Dict, Any

class AlphaFoldFetcher:
    """
    A class to fetch protein model files and metadata from the AlphaFold Protein Structure Database.
    API Documentation: https://alphafold.ebi.ac.uk/api-docs
    """
    
    BASE_URL = "https://alphafold.ebi.ac.uk/api/prediction"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    def get_metadata(self, uniprot_id: str) -> List[Dict[str, Any]]:
        """
        Fetches metadata for a given UniProt ID.
        """
        url = f"{self.BASE_URL}/{uniprot_id}"
        response = self.session.get(url, timeout=self.timeout)
        
        if response.status_code == 404:
            raise ValueError(f"UniProt ID '{uniprot_id}' not found in AlphaFold DB.")
        
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError(f"No prediction data found for UniProt ID '{uniprot_id}'.")
            
        return data

    def download_model(self, uniprot_id: str, output_dir: str = ".", file_format: str = "pdb") -> str:
        """
        Downloads the protein model file for a given UniProt ID.
        
        Args:
            uniprot_id: The UniProt accession (e.g., 'P12345').
            output_dir: Directory to save the file.
            file_format: 'pdb' or 'cif'.
            
        Returns:
            The path to the downloaded file.
        """
        file_format = file_format.lower()
        if file_format not in ["pdb", "cif"]:
            raise ValueError("file_format must be either 'pdb' or 'cif'.")

        # 1. Get metadata to find the download URL
        metadata = self.get_metadata(uniprot_id)
        
        # Usually there is only one entry for a single UniProt ID, but we take the first one
        prediction = metadata[0]
        
        url_key = "pdbUrl" if file_format == "pdb" else "cifUrl"
        download_url = prediction.get(url_key)
        
        if not download_url:
            raise ValueError(f"Download URL for format '{file_format}' not found for {uniprot_id}.")

        # 2. Download the file
        response = self.session.get(download_url, timeout=self.timeout)
        response.raise_for_status()

        # 3. Save the file
        filename = f"{uniprot_id}.{file_format}"
        file_path = os.path.join(output_dir, filename)
        
        os.makedirs(output_dir, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(response.content)
            
        return file_path

if __name__ == "__main__":
    # Example usage for Drosophila melanogaster
    fetcher = AlphaFoldFetcher()
    
    # Common Drosophila melanogaster UniProt IDs:
    # P10379: Engrailed
    # P02833: Antennapedia
    # P00334: Alcohol dehydrogenase
    drosophila_proteins = ["P10379", "P02833", "P00334"]
    
    output_directory = "drosophila_models"
    
    for uniprot_id in drosophila_proteins:
        try:
            print(f"\n--- Fetching model for Drosophila protein: {uniprot_id} ---")
            
            # Download PDB
            pdb_path = fetcher.download_model(uniprot_id, output_dir=output_directory, file_format="pdb")
            print(f"PDB saved to: {pdb_path}")
            
            # Download CIF
            cif_path = fetcher.download_model(uniprot_id, output_dir=output_directory, file_format="cif")
            print(f"CIF saved to: {cif_path}")
            
        except Exception as e:
            print(f"Error fetching {uniprot_id}: {e}")

