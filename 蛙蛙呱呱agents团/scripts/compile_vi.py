# scripts/compile_vi.py
import yaml
from pathlib import Path

def compile_design_tokens():
    '''将企业 VI YAML 编译为报告通用的 CSS 变量库'''
    token_path = Path("D:/一人公司/agents/styles/color-system/brand-tokens.yaml")
    css_out_path = Path("D:/一人公司/agents/styles/color-system/corporate-vi.css")
    
    if not token_path.exists():
        return
        
    with open(token_path, "r", encoding="utf-8") as f:
        tokens = yaml.safe_load(f)
        
    css_content = ":root {\n"
    for key, value in tokens.get("colors", {}).items():
        css_content += f"    --color-{key}: {value};\n"
    for key, value in tokens.get("fonts", {}).items():
        css_content += f"    --font-{key}: {value};\n"
    css_content += "}\n"
    
    with open(css_out_path, "w", encoding="utf-8") as f:
        f.write(css_content)
    print(f"[VI System] CSS 变量已编译至: {css_out_path}")

if __name__ == "__main__":
    compile_design_tokens()
