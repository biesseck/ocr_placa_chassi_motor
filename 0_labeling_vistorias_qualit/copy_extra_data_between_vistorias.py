from __future__ import annotations
import argparse
import os
import re
import glob
import json
import shutil
from pathlib import Path

__version__ = "0.2.0"

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync missing keys, format image URLs, and copy missing images from v1 to v2.")
    parser.add_argument("--v1", type=str, required=True, help="Path to dataset_v1 directory")
    parser.add_argument("--v2", type=str, required=True, help="Path to dataset_v2 directory")
    return parser.parse_args(argv)

def load_json(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def save_json(obj: dict, path: str | Path, indent: int = 4) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=indent)
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    
    path_v1 = Path(args.v1)
    path_v2 = Path(args.v2)
    
    if not path_v1.is_dir():
        print(f"Error: v1 directory does not exist: {path_v1}")
        return 1
    if not path_v2.is_dir():
        print(f"Error: v2 directory does not exist: {path_v2}")
        return 1

    # Find all <inspection> subdirectories inside v1
    v1_subdirs = [d for d in path_v1.iterdir() if d.is_dir()]
    v1_subdirs.sort(key=lambda d: natural_sort_key(d.name))
    
    print(f"Found {len(v1_subdirs)} inspection folders in v1.")
    
    synced_count = 0
    
    for idx_v1_ins_dir, v1_ins_dir in enumerate(v1_subdirs):
        # v1_ins_dir = Path(str(v1_ins_dir).replace("\\","/").replace("[","*"))
        inspection_name = v1_ins_dir.name
        print("-------------------")
        print(f"{idx_v1_ins_dir}/{len(v1_subdirs)} Processing: {inspection_name}")
        v2_ins_dir = path_v2 / inspection_name
        # v2_ins_dir = Path(str(v2_ins_dir).replace("\\","/").replace("[","*"))
        
        # Check if the exact same inspection folder exists in v2
        if not v2_ins_dir.is_dir():
            print(f"    Skipping: {inspection_name} does not exist in v2.")
            continue
            
        # Locate json files in both folders
        v1_jsons = glob.glob(os.path.join(v1_ins_dir, "dados_vistoria*.json"))
        v2_jsons = glob.glob(os.path.join(v2_ins_dir, "dados_vistoria*.json"))
        
        if not v1_jsons:
            print(f"    Skipping {inspection_name}: JSON file missing in v1")
            continue
        if not v2_jsons:
            print(f"    Skipping {inspection_name}: JSON file missing in v2")
            continue
            
        v1_json_path = Path(v1_jsons[0])
        v2_json_path = Path(v2_jsons[0])
        print(f"    Found JSON: v1: {v1_json_path.name}")
        print(f"    Found JSON: v2: {v2_json_path.name}")
        # sys.exit(0)
        
        try:
            v1_data = load_json(v1_json_path)
            v2_data = load_json(v2_json_path)
        except Exception as e:
            print(f"    Error reading JSONs in {inspection_name}: {e}")
            continue
            
        modified = False
        
        for key, val in v1_data.items():
            # Rule 1: Ignore blank key and values
            if key == "" or val == "":
                continue

            # Rule 2: Only copy missing keys
            if key not in v2_data:
                # Rule 3: Check if value looks like a URL or image path
                if isinstance(val, str) and (val.startswith("http://") or val.startswith("https://") or "/" in val or "\\" in val):
                    filename = val.replace('\\', '/').split('/')[-1]
                    
                    # Target value to keep in v2 json is just the filename
                    v2_data[key] = filename
                    modified = True
                    
                    # Handle image copy
                    v1_img_path = v1_ins_dir / "imgs" / filename
                    v2_img_dir = v2_ins_dir / "imgs"
                    v2_img_path = v2_img_dir / filename
                    
                    if v1_img_path.is_file():
                        # v2_img_dir.mkdir(parents=True, exist_ok=True)
                        assert v2_img_dir.is_dir(), f"    Expected directory: {v2_img_dir}"
                        if not v2_img_path.is_file():
                            shutil.copy2(v1_img_path, v2_img_path)
                            print(f"    [{inspection_name}] Copied image: {filename}")
                            sys.exit(0)
                    else:
                        print(f"    Warning [{inspection_name}]: Image {filename} referenced in v1 but file not found.")
                else:
                    # Regular text value copy
                    v2_data[key] = val
                    modified = True
            
            else:
                if isinstance(val, str) and (val.startswith("http://") or val.startswith("https://") or "/" in val or "\\" in val):
                    filename = val.replace('\\', '/').split('/')[-1]

                    v1_img_path = v1_ins_dir / "imgs" / filename
                    v2_img_dir = v2_ins_dir / "imgs"
                    v2_img_path = v2_img_dir / filename

                    if v1_img_path.is_file() and not v2_img_path.is_file():
                        shutil.copy2(v1_img_path, v2_img_path)
                        print(f"    [{inspection_name}] Key exists, but image was missing. Copied image: {filename}")
                        # sys.exit(0)
                        # modified = True                    

        
        if modified:
            save_json(v2_data, v2_json_path)
            print(f"    Updated JSON keys for inspection: {inspection_name}")
            synced_count += 1

    print(f"\nFinished synchronization. Successfully updated {synced_count} dataset directories.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())