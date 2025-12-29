import os
import requests
import weave
import time
from typing import Annotated, List, Dict, Any
from weave import Content
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

# Initialize weave project
weave.init('protein-folding-viz')

class AlphaFoldFetcher:
    API_BASE = "https://alphafold.ebi.ac.uk/api"
    PREDICTION_URL = f"{API_BASE}/prediction"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    @weave.op
    def get_uniprot_ids_for_organism(self, taxonomy_id: str = "7227") -> List[str]:
        print(f"Fetching UniProt IDs for taxonomy ID {taxonomy_id}...")
        uniprot_url = "https://rest.uniprot.org/uniprotkb/search"
        params = {
            "query": f"taxonomy_id:{taxonomy_id}",
            "fields": "accession",
            "format": "json",
            "size": 50
        }
        response = self.session.get(uniprot_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return [result['primaryAccession'] for result in data.get('results', [])]

    @weave.op
    def download_model(self, uniprot_id: str, output_dir: str = "models") -> str:
        url = f"{self.PREDICTION_URL}/{uniprot_id}"
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code == 404: return None
        response.raise_for_status()
        data = response.json()
        if not data: return None
        
        pdb_url = data[0].get("pdbUrl")
        response = self.session.get(pdb_url, timeout=self.timeout)
        response.raise_for_status()

        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{uniprot_id}.pdb")
        with open(file_path, "wb") as f:
            f.write(response.content)
        return file_path

def extract_sequence_from_pdb(pdb_content):
    aa_map = {'ALA':'A', 'ARG':'R', 'ASN':'N', 'ASP':'D', 'CYS':'C', 'GLN':'Q', 'GLU':'E', 'GLY':'G', 'HIS':'H', 'ILE':'I', 'LEU':'L', 'LYS':'K', 'MET':'M', 'PHE':'F', 'PRO':'P', 'SER':'S', 'THR':'T', 'TRP':'W', 'TYR':'Y', 'VAL':'V'}
    seq = []
    for line in pdb_content.splitlines():
        if line.startswith("SEQRES"):
            parts = line.split()
            for p in parts[4:]:
                if p in aa_map: seq.append(aa_map[p])
    if not seq:
        res_nums = set()
        for line in pdb_content.splitlines():
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                res_name, res_seq = line[17:20].strip(), line[22:26].strip()
                if res_seq not in res_nums:
                    seq.append(aa_map.get(res_name, '?'))
                    res_nums.add(res_seq)
    return "".join(seq)

def generate_base_html(uniprot_id: str, pdb_content: str, style: str) -> str:
    sequence = extract_sequence_from_pdb(pdb_content)
    seq_html = "".join([
        f'''<div class="res-node" onclick="focusResidue({i+1})" title="{sequence[i]}{i+1}">
            <span class="res-idx">{i+1 if (i+1)%10==1 else ""}</span>
            <span class="res-aa">{sequence[i]}</span>
        </div>''' for i in range(len(sequence))
    ])

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {{ --sidebar-width: 280px; --primary-blue: #0053D6; }}
        body, html {{ margin: 0; padding: 0; height: 100%; width: 100%; font-family: sans-serif; overflow: hidden; background: #fff; }}
        .app {{ display: grid; grid-template-areas: "header header" "view side"; grid-template-columns: 1fr var(--sidebar-width); grid-template-rows: auto 1fr; height: 100vh; }}
        .header-bar {{ grid-area: header; background: white; border-bottom: 1px solid #ddd; padding: 10px 20px; }}
        .seq-bar {{ display: flex; overflow-x: auto; padding-bottom: 5px; scrollbar-width: thin; }}
        .res-node {{ display: flex; flex-direction: column; align-items: center; cursor: pointer; padding: 2px; min-width: 12px; }}
        .res-node:hover {{ background: #eef; }}
        .res-idx {{ font-size: 9px; color: #999; height: 12px; }}
        .res-aa {{ font-family: monospace; font-weight: bold; font-size: 12px; }}
        .view-container {{ grid-area: view; position: relative; }}
        #viewer {{ width: 100%; height: 100%; }}
        .sidebar {{ grid-area: side; background: #f8f9fa; border-left: 1px solid #ddd; padding: 15px; display: flex; flex-direction: column; gap: 10px; }}
        .card {{ background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 12px; font-size: 13px; }}
        .card-title {{ font-weight: bold; margin-bottom: 8px; color: #495057; }}
        .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }}
        .btn {{ width: 100%; padding: 8px; border: 1px solid #ced4da; background: #fff; cursor: pointer; border-radius: 4px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="app">
        <div class="header-bar">
            <div style="font-weight:bold; color:var(--primary-blue); margin-bottom:5px;">{uniprot_id} - {style.capitalize()} View</div>
            <div class="seq-bar">{seq_html}</div>
        </div>
        <div class="view-container"><div id="viewer"></div></div>
        <div class="sidebar">
            <div class="card">
                <div class="card-title">Active Representation</div>
                <div style="color:var(--primary-blue); font-weight:bold;">{style.capitalize()}</div>
            </div>
            <div class="card">
                <div class="card-title">Background</div>
                <button class="btn" onclick="toggleBG()">Toggle Background</button>
            </div>
            <div class="card">
                <div class="card-title">Confidence (pLDDT)</div>
                <div style="font-size:12px;">
                    <div style="margin-bottom:4px;"><span class="dot" style="background:#0053D6"></span>Very high (>90)</div>
                    <div style="margin-bottom:4px;"><span class="dot" style="background:#65CBF3"></span>Confident (70-90)</div>
                    <div style="margin-bottom:4px;"><span class="dot" style="background:#FFDB13"></span>Low (50-70)</div>
                    <div><span class="dot" style="background:#FF7D45"></span>Very low (<50)</div>
                </div>
            </div>
        </div>
    </div>
    <script>
        let v;
        let isBlack = false;
        const af = {{ colorfunc: a => a.b > 90 ? '#0053D6' : a.b > 70 ? '#65CBF3' : a.b > 50 ? '#FFDB13' : '#FF7D45' }};
        
        function toggleBG() {{
            isBlack = !isBlack;
            v.setBackgroundColor(isBlack ? 'black' : 'white');
            v.render();
        }}

        function focusResidue(idx) {{
            v.zoomTo({{resi: idx}}, 1000);
            v.setStyle({{resi: idx}}, {{cartoon: {{color: 'magenta'}}, stick: {{radius: 0.5}}}});
            v.render();
        }}

        document.addEventListener("DOMContentLoaded", () => {{
            v = $3Dmol.createViewer(document.querySelector('#viewer'), {{ backgroundColor: 'white' }});
            v.addModel(`{pdb_content.replace('`', '\\`').replace('${', '\\${')}`, "pdb");
            
            const s = '{style}';
            if(s==='cartoon') v.setStyle({{}}, {{cartoon: af}});
            else if(s==='sphere') v.setStyle({{}}, {{sphere: af}});
            else if(s==='stick') v.setStyle({{}}, {{stick: af}});
            else if(s==='surface') {{ v.setStyle({{}}, {{cartoon: af}}); v.addSurface($3Dmol.SurfaceType.VDW, {{opacity:0.7, colorfunc:af.colorfunc}}); }}
            
            v.zoomTo(); v.render();
        }});
    </script>
</body>
</html>
    """
    return html_content

@weave.op
def cartoon(uniprot_id: str, pdb_content: str) -> Annotated[str, Content[Literal['html']]]:
    return generate_base_html(uniprot_id, pdb_content, 'cartoon')

@weave.op
def spacefill(uniprot_id: str, pdb_content: str) -> Annotated[str, Content[Literal['html']]]:
    return generate_base_html(uniprot_id, pdb_content, 'sphere')

@weave.op
def stick(uniprot_id: str, pdb_content: str) -> Annotated[str, Content[Literal['html']]]:
    return generate_base_html(uniprot_id, pdb_content, 'stick')

@weave.op
def surface(uniprot_id: str, pdb_content: str) -> Annotated[str, Content[Literal['html']]]:
    return generate_base_html(uniprot_id, pdb_content, 'surface')

@weave.op
def process_protein(uniprot_id: str) -> Dict[str, Any]:
    fetcher = AlphaFoldFetcher()
    print(f"Processing {uniprot_id}...")
    try:
        pdb_path = fetcher.download_model(uniprot_id)
        if not pdb_path: return {}
        with open(pdb_path, 'r') as f:
            content = f.read()
            
        return {
            "cartoon": cartoon(uniprot_id, content),
            "spacefill": spacefill(uniprot_id, content),
            "stick": stick(uniprot_id, content),
            "surface": surface(uniprot_id, content)
        }
    except Exception as e:
        print(f"Skipping {uniprot_id}: {e}")
        return {}

if __name__ == "__main__":
    proteins = ["P10379", "P02833", "P00334"]
    for pid in proteins: process_protein(pid)
