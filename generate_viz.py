import os
import re

def extract_sequence_from_pdb(pdb_content):
    # Mapping of 3-letter to 1-letter codes
    aa_map = {
        'ALA':'A', 'ARG':'R', 'ASN':'N', 'ASP':'D', 'CYS':'C', 'GLN':'Q', 'GLU':'E', 'GLY':'G', 'HIS':'H',
        'ILE':'I', 'LEU':'L', 'LYS':'K', 'MET':'M', 'PHE':'F', 'PRO':'P', 'SER':'S', 'THR':'T', 'TRP':'W',
        'TYR':'Y', 'VAL':'V'
    }
    
    seq = []
    # Find SEQRES lines
    for line in pdb_content.splitlines():
        if line.startswith("SEQRES"):
            parts = line.split()
            for p in parts[4:]:
                if p in aa_map:
                    seq.append(aa_map[p])
    
    # If no SEQRES, try to extract from ATOM lines (fallback)
    if not seq:
        res_nums = set()
        for line in pdb_content.splitlines():
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                res_name = line[17:20].strip()
                res_seq = line[22:26].strip()
                if res_seq not in res_nums:
                    seq.append(aa_map.get(res_name, '?'))
                    res_nums.add(res_seq)
                    
    return "".join(seq)

def generate_sophisticated_viz(pdb_path, output_html):
    if not os.path.exists(pdb_path):
        print(f"Error: {pdb_path} not found.")
        return

    with open(pdb_path, 'r') as f:
        pdb_content = f.read()

    protein_id = os.path.basename(pdb_path).replace('.pdb', '')
    sequence = extract_sequence_from_pdb(pdb_content)
    
    # Format sequence for top bar (groups of 10 with indices)
    seq_html = ""
    for i in range(0, len(sequence), 10):
        group = sequence[i:i+10]
        seq_html += f'<span class="seq-index">{i+1}</span>'
        seq_html += f'<span class="seq-group">{group}</span>'

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AlphaFold Structure - {protein_id}</title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {{
            --sidebar-width: 320px;
            --header-height: 60px;
            --bg-gray: #f5f5f5;
            --border-color: #e0e0e0;
            --primary-blue: #0053D6;
        }}
        body, html {{ 
            margin: 0; padding: 0; height: 100%; width: 100%;
            font-family: 'Inter', -apple-system, sans-serif;
            overflow: hidden; background: #fff;
        }}
        
        /* Layout Grid */
        .app-container {{
            display: grid;
            grid-template-areas: 
                "sequence sequence"
                "viewer sidebar";
            grid-template-columns: 1fr var(--sidebar-width);
            grid-template-rows: auto 1fr;
            height: 100vh;
        }}

        /* Top Sequence Bar */
        .sequence-bar {{
            grid-area: sequence;
            background: #fff;
            border-bottom: 1px solid var(--border-color);
            padding: 8px 20px;
            font-family: monospace;
            font-size: 12px;
            overflow-x: auto;
            white-space: nowrap;
            display: flex;
            align-items: flex-end;
            gap: 15px;
            color: #666;
        }}
        .seq-item {{ display: flex; flex-direction: column; align-items: flex-start; }}
        .seq-index {{ font-size: 10px; color: #999; margin-bottom: 2px; }}
        .seq-group {{ letter-spacing: 2px; font-weight: bold; color: #333; }}

        /* Main Viewer Area */
        .viewer-container {{
            grid-area: viewer;
            position: relative;
            background: #fff;
        }}
        #viewer {{ width: 100%; height: 100%; }}

        /* Sidebar Structure Tools */
        .sidebar {{
            grid-area: sidebar;
            background: #efefef;
            border-left: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }}
        .sidebar-header {{
            padding: 15px;
            background: #e0e0e0;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
        }}
        .sidebar-section {{
            margin-bottom: 1px;
            background: #fff;
        }}
        .section-title {{
            padding: 10px 15px;
            background: #f8f8f8;
            font-size: 13px;
            font-weight: 600;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
        }}
        .section-content {{
            padding: 15px;
            font-size: 13px;
        }}

        /* Buttons and UI elements */
        .btn-group {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px;
            margin-top: 10px;
        }}
        button {{
            padding: 8px;
            border: 1px solid var(--border-color);
            background: #fff;
            cursor: pointer;
            font-size: 12px;
            border-radius: 4px;
        }}
        button:hover {{ background: #f0f0f0; }}
        button.active {{ 
            background: var(--primary-blue); 
            color: white; 
            border-color: var(--primary-blue);
        }}

        /* Confidence Legend */
        .confidence-list {{
            list-style: none;
            padding: 0;
            margin: 10px 0;
        }}
        .conf-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            font-size: 12px;
        }}
        .dot {{ width: 12px; height: 12px; border-radius: 50%; }}

        /* Viewer Controls Overlay */
        .viewer-controls {{
            position: absolute;
            right: 20px;
            top: 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 10;
        }}
        .control-btn {{
            width: 36px;
            height: 36px;
            background: #fff;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sequence-bar">
            {seq_html}
        </div>

        <div class="viewer-container">
            <div id="viewer"></div>
            <div class="viewer-controls">
                <div class="control-btn" title="Rotate"><i class="fa-solid fa-rotate"></i></div>
                <div class="control-btn" title="Zoom"><i class="fa-solid fa-magnifying-glass-plus"></i></div>
                <div class="control-btn" title="Center"><i class="fa-solid fa-crosshairs"></i></div>
            </div>
        </div>

        <div class="sidebar">
            <div class="sidebar-header">
                <span>Structure Tools</span>
                <i class="fa-solid fa-wrench"></i>
            </div>

            <div class="sidebar-section">
                <div class="section-title">
                    <i class="fa-solid fa-cube"></i> Structure
                </div>
                <div class="section-content">
                    <div style="color: var(--primary-blue); font-weight: bold; margin-bottom: 10px;">
                        AF-{protein_id}-F1
                    </div>
                    <div style="font-size: 11px; color: #666;">Type: Model</div>
                </div>
            </div>

            <div class="sidebar-section">
                <div class="section-title">
                    <i class="fa-solid fa-tags"></i> Annotations
                </div>
                <div class="section-content">
                    <div class="conf-item">
                        <span>Validation</span>
                        <i class="fa-solid fa-eye" style="margin-left: auto; color: #999;"></i>
                    </div>
                </div>
            </div>

            <div class="sidebar-section">
                <div class="section-title">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> Quick Styles
                </div>
                <div class="section-content">
                    <div style="margin-bottom: 5px; color: #666; font-size: 11px;">Apply Representation</div>
                    <div class="btn-group">
                        <button id="style-cartoon" class="active">Cartoon</button>
                        <button id="style-sphere">Spacefill</button>
                        <button id="style-stick">Stick</button>
                        <button id="style-surface">Surface</button>
                    </div>
                </div>
            </div>

            <div class="sidebar-section">
                <div class="section-title">
                    <i class="fa-solid fa-layer-group"></i> Confidence (pLDDT)
                </div>
                <div class="section-content">
                    <div class="confidence-list">
                        <div class="conf-item"><div class="dot" style="background: #0053D6;"></div> Very high (>90)</div>
                        <div class="conf-item"><div class="dot" style="background: #65CBF3;"></div> Confident (70-90)</div>
                        <div class="conf-item"><div class="dot" style="background: #FFDB13;"></div> Low (50-70)</div>
                        <div class="conf-item"><div class="dot" style="background: #FF7D45;"></div> Very low (<50)</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            const element = document.querySelector('#viewer');
            const viewer = $3Dmol.createViewer(element, {{ backgroundColor: 'white' }});
            const pdbData = `{pdb_content.replace('`', '\\`').replace('${', '\\${')}`;

            viewer.addModel(pdbData, "pdb");
            
            function applyStyle(styleType) {{
                viewer.removeAllSurfaces();
                viewer.setStyle({{}}, {{}}); // clear
                
                const afColors = {{
                    colorfunc: function(atom) {{
                        if (atom.b > 90) return '#0053D6';
                        if (atom.b > 70) return '#65CBF3';
                        if (atom.b > 50) return '#FFDB13';
                        return '#FF7D45';
                    }}
                }};

                if (styleType === 'cartoon') {{
                    viewer.setStyle({{}}, {{ cartoon: afColors }});
                }} else if (styleType === 'sphere') {{
                    viewer.setStyle({{}}, {{ sphere: afColors }});
                }} else if (styleType === 'stick') {{
                    viewer.setStyle({{}}, {{ stick: afColors }});
                }} else if (styleType === 'surface') {{
                    viewer.setStyle({{}}, {{ cartoon: afColors }});
                    viewer.addSurface($3Dmol.SurfaceType.VDW, {{
                        opacity: 0.7,
                        colorfunc: afColors.colorfunc
                    }});
                }}
                viewer.render();
            }}

            // Initial style
            applyStyle('cartoon');
            viewer.zoomTo();
            viewer.render();

            // Style listeners
            document.getElementById('style-cartoon').onclick = (e) => {{
                setActive(e.target); applyStyle('cartoon');
            }};
            document.getElementById('style-sphere').onclick = (e) => {{
                setActive(e.target); applyStyle('sphere');
            }};
            document.getElementById('style-stick').onclick = (e) => {{
                setActive(e.target); applyStyle('stick');
            }};
            document.getElementById('style-surface').onclick = (e) => {{
                setActive(e.target); applyStyle('surface');
            }};

            function setActive(btn) {{
                document.querySelectorAll('.btn-group button').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            }}
        }});
    </script>
</body>
</html>
    """
    
    with open(output_html, 'w') as f:
        f.write(html_template)
    print(f"Sophisticated visualization saved to: {output_html}")

if __name__ == "__main__":
    generate_sophisticated_viz('drosophila_models/P02833.pdb', 'sophisticated_P02833.html')
