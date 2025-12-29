import weave
from typing import Annotated, Dict, Any, List, Literal
from weave import Content

AA_MAP = {
    'A': 'Alanine', 'R': 'Arginine', 'N': 'Asparagine', 'D': 'Aspartic Acid',
    'C': 'Cysteine', 'Q': 'Glutamine', 'E': 'Glutamic Acid', 'G': 'Glycine',
    'H': 'Histidine', 'I': 'Isoleucine', 'L': 'Leucine', 'K': 'Lysine',
    'M': 'Methionine', 'F': 'Phenylalanine', 'P': 'Proline', 'S': 'Serine',
    'T': 'Threonine', 'W': 'Tryptophan', 'Y': 'Tyrosine', 'V': 'Valine'
}

class Protean:
    def __init__(self, uniprot_id: str, pdb_content: str):
        self.uniprot_id = uniprot_id
        self.pdb_content = pdb_content
        self.sequence = self._extract_sequence()

    def _extract_sequence(self):
        seq = []
        aa_3to1 = {'ALA':'A', 'ARG':'R', 'ASN':'N', 'ASP':'D', 'CYS':'C', 'GLN':'Q', 'GLU':'E', 'GLY':'G', 'HIS':'H', 'ILE':'I', 'LEU':'L', 'LYS':'K', 'MET':'M', 'PHE':'F', 'PRO':'P', 'SER':'S', 'THR':'T', 'TRP':'W', 'TYR':'Y', 'VAL':'V'}
        for line in self.pdb_content.splitlines():
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                res_name = line[17:20].strip()
                seq.append(aa_3to1.get(res_name, '?'))
        return "".join(seq)

    def _generate_isolated_html(self, resi: int, style: str, aa_name: str, aa_code: str) -> str:
        title = f"{aa_name} ({aa_code}{resi}) - {style.capitalize()}"
        
        # Style logic: isolate the residue and apply representation
        isolate_js = f"v.setStyle({{not: {{resi: {resi}}}}}, {{}}); const target = {{resi: {resi}}};"
        
        af_colors = "{colorfunc: a => a.b > 90 ? '#0053D6' : a.b > 70 ? '#65CBF3' : a.b > 50 ? '#FFDB13' : '#FF7D45'}"
        
        style_js = ""
        if style == 'cartoon': style_js = f"v.setStyle(target, {{cartoon: {af_colors}}});"
        elif style == 'sphere': style_js = f"v.setStyle(target, {{sphere: {af_colors}}});"
        elif style == 'stick': style_js = f"v.setStyle(target, {{stick: {{colorscheme: 'amino acid'}}}});"
        elif style == 'surface': style_js = f"v.setStyle(target, {{cartoon: {af_colors}}}); v.addSurface($3Dmol.SurfaceType.VDW, {{opacity:0.7, colorfunc: (a) => a.b > 90 ? '#0053D6' : a.b > 70 ? '#65CBF3' : a.b > 50 ? '#FFDB13' : '#FF7D45'}}, target);"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        body {{ margin: 0; font-family: sans-serif; background: #fff; overflow: hidden; }}
        #viewer {{ width: 100%; height: 400px; }}
        #header {{ padding: 8px; background: #0053D6; color: white; font-size: 12px; font-weight: bold; text-align: center; }}
    </style>
</head>
<body>
    <div id="header">{title}</div>
    <div id="viewer"></div>
    <script>
        document.addEventListener("DOMContentLoaded", () => {{
            const v = $3Dmol.createViewer(document.querySelector('#viewer'), {{ backgroundColor: 'white' }});
            v.addModel(`{self.pdb_content.replace('`', '\\`').replace('${', '\\${')}`, "pdb");
            {isolate_js}
            {style_js}
            v.zoomTo(target);
            v.render();
        }});
    </script>
</body>
</html>
        """
        return html

    @weave.op
    def render_aa_instance(self, aa_code: str, resi: int) -> Dict[str, Annotated[str, Content[Literal['html']]]]:
        name = AA_MAP.get(aa_code, "Unknown")
        return {
            "cartoon": self._generate_isolated_html(resi, 'cartoon', name, aa_code),
            "spacefill": self._generate_isolated_html(resi, 'sphere', name, aa_code),
            "stick": self._generate_isolated_html(resi, 'stick', name, aa_code),
            "surface": self._generate_isolated_html(resi, 'surface', name, aa_code)
        }

    
    @weave.op
    def _render_all_of_type(self, aa_code: str):
        indices = [i + 1 for i, aa in enumerate(self.sequence) if aa == aa_code]
        print(f"  -> Rendering {len(indices)} {AA_MAP[aa_code]} residues...")
        results = {}
        # Limit to first 5 instances to keep dashboard responsive
        for idx in indices[:5]:
            results[f"{aa_code}{idx}"] = self.render_aa_instance(aa_code, idx)
        return results

    # --- Methods for all 20 Amino Acids ---
    @weave.op
    def alanine(self): return self._render_all_of_type('A')
    @weave.op
    def arginine(self): return self._render_all_of_type('R')
    @weave.op
    def asparagine(self): return self._render_all_of_type('N')
    @weave.op
    def aspartic_acid(self): return self._render_all_of_type('D')
    @weave.op
    def cysteine(self): return self._render_all_of_type('C')
    @weave.op
    def glutamine(self): return self._render_all_of_type('Q')
    @weave.op
    def glutamic_acid(self): return self._render_all_of_type('E')
    @weave.op
    def glycine(self): return self._render_all_of_type('G')
    @weave.op
    def histidine(self): return self._render_all_of_type('H')
    @weave.op
    def isoleucine(self): return self._render_all_of_type('I')
    @weave.op
    def leucine(self): return self._render_all_of_type('L')
    @weave.op
    def lysine(self): return self._render_all_of_type('K')
    @weave.op
    def methionine(self): return self._render_all_of_type('M')
    @weave.op
    def phenylalanine(self): return self._render_all_of_type('F')
    @weave.op
    def proline(self): return self._render_all_of_type('P')
    @weave.op
    def serine(self): return self._render_all_of_type('S')
    @weave.op
    def threonine(self): return self._render_all_of_type('T')
    @weave.op
    def tryptophan(self): return self._render_all_of_type('W')
    @weave.op
    def tyrosine(self): return self._render_all_of_type('Y')
    @weave.op
    def valine(self): return self._render_all_of_type('V')

    @weave.op
    def process_all_components(self):
        """Dispatches calls to all 20 amino acid methods."""
        print(f"Processing all amino acid components for {self.uniprot_id}...")
        self.alanine()
        self.arginine()
        self.asparagine()
        self.aspartic_acid()
        self.cysteine()
        self.glutamine()
        self.glutamic_acid()
        self.glycine()
        self.histidine()
        self.isoleucine()
        self.leucine()
        self.lysine()
        self.methionine()
        self.phenylalanine()
        self.proline()
        self.serine()
        self.threonine()
        self.tryptophan()
        self.tyrosine()
        self.valine()
        return f"Completed analysis for {self.uniprot_id}"
