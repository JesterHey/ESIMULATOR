import json
import os
from pathlib import Path

def convert_json_to_guide(json_path: Path, output_path: Path):
    """
    Converts a *_bind_masks.json file to the guide.txt format.

    Args:
        json_path: Path to the input JSON file.
        output_path: Path to the output guide.txt format file.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing {json_path}: {e}")
        return

    output_lines = []
    binds = data.get("binds", [])

    for bind in binds:
        dest = bind.get("dest", "unknown_dest")
        
        # If workset_order is empty, the line should just be the dest and '0'
        if not bind.get("workset_order"):
            output_lines.append(f"{dest}, 0")
            continue

        ast_nodes = bind.get("ast", {}).get("nodes", {})
        workset_order = bind.get("workset_order", [])
        # 使用 intrinsic_mask 而不是 workset_mask
        # intrinsic_mask 只看操作符本身是否线性，不考虑子节点
        workset_mask = bind.get("workset_intrinsic_mask", [])

        operator_names = []
        for node_id in workset_order:
            node = ast_nodes.get(str(node_id))
            if node and 'value' in node:
                operator_names.append(node['value'])
            else:
                operator_names.append("OP_NOT_FOUND")
        
        # Convert mask values to strings
        mask_str = " ".join(map(str, workset_mask))

        line_parts = [dest] + operator_names + [mask_str]
        output_lines.append(", ".join(line_parts))

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(output_lines))
        print(f"Successfully converted {json_path} to {output_path}")
    except IOError as e:
        print(f"Error writing to {output_path}: {e}")

def main():
    """
    Main function to find and convert all relevant JSON files.
    """
    project_root = Path(__file__).parent
    results_dir = project_root / "results"
    
    if not results_dir.is_dir():
        print(f"Error: Results directory not found at {results_dir}")
        return

    json_files_to_convert = list(results_dir.glob("**/*_bind_masks.json"))

    if not json_files_to_convert:
        print("No '*_bind_masks.json' files found to convert.")
        return

    print(f"Found {len(json_files_to_convert)} files to convert.")

    for json_file in json_files_to_convert:
        # e.g. results/alu_result/alu_dfg_bind_masks.json -> results/alu_result/guide.txt
        output_file = json_file.parent / "guide.txt"
        convert_json_to_guide(json_file, output_file)

if __name__ == "__main__":
    main()
