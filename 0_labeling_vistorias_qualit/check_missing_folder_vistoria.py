import argparse
import os
from pathlib import Path
import shutil


def parse_arguments():
    parser = argparse.ArgumentParser(description="Find missing first-level folders between two directories.")
    parser.add_argument("--path1", required=True, help="The source directory (the 'complete' list).")
    parser.add_argument("--path2", required=True, help="The target directory to check against.")
    parser.add_argument("--output-path", help="Optional: Full path for the output .txt file.")
    parser.add_argument("--copy-missing-folders", action="store_true", help="Copy missing folders from path1 to path2 (optional).")
    args = parser.parse_args()
    return args


def find_missing_folders(path1, path2, output_path):
    p1 = Path(path1)
    p2 = Path(path2)
    
    assert p1.exists(), f"Error: The path '{path1}' does not exist."
    assert p2.exists(), f"Error: The path '{path2}' does not exist."

    print(f"Loading folders names from path1: '{path1}'...")
    folders1 = {f.name for f in p1.iterdir() if f.is_dir()}
    print(f"    Found {len(folders1)} folders")
    print(f"Loading folders names from path2: '{path2}'...")
    folders2 = {f.name for f in p2.iterdir() if f.is_dir()}
    print(f"    Found {len(folders2)} folders")
    print(f"Checking for missing folders")
    missing = sorted(list(folders1 - folders2))
    print(f"    Found {len(missing)} missing folders")

    if len(missing) > 0:
        if output_path:
            out_file = Path(output_path)
        else:
            out_file = p2 / "missing_folders.txt"

        try:
            print(f"Saving results to: '{out_file}'...")
            with open(out_file, 'w', encoding='utf-8') as f:
                for folder in missing:
                    f.write(f"{folder}\n")
            print(f"    Done")
        except Exception as e:
            print(f"An error occurred while writing the file: {e}")

        if args.copy_missing_folders:
            print(f"Copying missing folders from '{path1}' to '{path2}'...")
            for idx_folder, folder in enumerate(missing):
                src = p1 / folder
                dst = p2 / folder
                try:
                    # os.system(f'cp -r "{src}" "{dst}"')
                    shutil.copytree(src, dst)
                    print(f"{idx_folder}/{len(missing)}    Copied: {folder}")
                except Exception as e:
                    print(f"An error occurred while copying '{folder}': {e}")
            print("    Done copying missing folders.")
    else:
        print("No missing folders found.")


if __name__ == "__main__":
    args = parse_arguments()
    find_missing_folders(args.path1, args.path2, args.output_path)