from __future__ import annotations
import sys
import os
import argparse
import re
import shutil
from pathlib import Path
from typing import Dict, Any
import json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, required=True,  help="Path to the input folder")
    return parser.parse_args(argv)


def natural_sort_key(path):
    s = str(path)
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(data: Dict[str, Any], path: str, indent: int = 4) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not os.path.isfile(args.input):
        print(f"Error: input file '{args.input}' does not exist", file=sys.stderr)
        return 2
    if not args.input.lower().endswith('.json'):
        print(f"Error: input file '{args.input}' is not a JSON file", file=sys.stderr)
        return 2

    dict_curr_links_vistorias_qualit = read_json(args.input)
    # print("dict_curr_links_vistorias_qualit:", dict_curr_links_vistorias_qualit)
    dict_corrected_links_vistorias_qualit = {}

    num_vistorias = len(dict_curr_links_vistorias_qualit)
    print(f"Number of vistorias in the current JSON: {num_vistorias}")
    
    for idx_vistoria, vistoria_key in enumerate(list(dict_curr_links_vistorias_qualit.keys())):
        # print("vistoria_key:", vistoria_key)
        vistoria_key_split = vistoria_key.split('_')
        curr_date1  = vistoria_key_split[-4]
        curr_time1  = vistoria_key_split[-3]
        curr_date2  = vistoria_key_split[-2]
        curr_time2  = vistoria_key_split[-1]
        
        if len(curr_date1.split('-')[2]) == 4 and len(curr_date2.split('-')[2]) == 4:
            new_date1 = curr_date1.split('-')[2] + '-' + curr_date1.split('-')[1] + '-' + curr_date1.split('-')[0]
            new_date2 = curr_date2.split('-')[2] + '-' + curr_date2.split('-')[1] + '-' + curr_date2.split('-')[0]

            new_vistoria_key = f"{new_date1}_{curr_time1}_{new_date2}_{curr_time2}"
            print(f"{idx_vistoria}/{num_vistorias} -", "Renaming", vistoria_key, "->", new_vistoria_key)
            dict_corrected_links_vistorias_qualit[new_vistoria_key] = dict_curr_links_vistorias_qualit[vistoria_key]
        else:
            print(f"{idx_vistoria}/{num_vistorias} -", "Skipping", vistoria_key, "- already in correct format")

        # sys.exit(0)
    
    output_json_path = f"{Path(args.input).parent}/{Path(args.input).stem}_CORRECTED.json"
    write_json(dict_corrected_links_vistorias_qualit, output_json_path, indent=4)
    print(f"\nCorrected JSON saved to: {output_json_path}")
    print("\nFinished!\n")
    

if __name__ == "__main__":
    main()