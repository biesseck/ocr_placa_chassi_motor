from __future__ import annotations
import sys
import os
import argparse
import re
import shutil


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, required=True,  help="Path to the input folder")
    return parser.parse_args(argv)


def natural_sort_key(path):
    s = str(path)
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def load_all_subdirs(input_folder: str) -> list[str]:
    subdirs = [os.path.join(input_folder, name).replace('\\','/') for name in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, name))]
    subdirs.sort(key=natural_sort_key)
    return subdirs


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not os.path.isdir(args.input):
        print(f"Error: input folder '{args.input}' does not exist", file=sys.stderr)
        return 2
    
    all_current_subdirs = load_all_subdirs(args.input)
    # print("all_current_subdirs:", all_current_subdirs)

    for idx_curr_subdir, curr_subdir in enumerate(all_current_subdirs):
        curr_subdir_base_name = os.path.basename(curr_subdir)
        # print("curr_subdir_base_name:", curr_subdir_base_name)
        curr_subdir_base_name_split = curr_subdir_base_name.split('_')
        curr_status = '_'.join(curr_subdir_base_name_split[:-4])
        curr_date1  = curr_subdir_base_name_split[-4]
        curr_time1  = curr_subdir_base_name_split[-3]
        curr_date2  = curr_subdir_base_name_split[-2]
        curr_time2  = curr_subdir_base_name_split[-1]
        
        if len(curr_date1.split('-')[2]) == 4 and len(curr_date2.split('-')[2]) == 4:
            new_date1 = curr_date1.split('-')[2] + '-' + curr_date1.split('-')[1] + '-' + curr_date1.split('-')[0]
            new_date2 = curr_date2.split('-')[2] + '-' + curr_date2.split('-')[1] + '-' + curr_date2.split('-')[0]

            new_subdir_base_name = f"{curr_status}_{new_date1}_{curr_time1}_{new_date2}_{curr_time2}"
            
            new_subdir = os.path.join(os.path.dirname(curr_subdir), new_subdir_base_name).replace('\\','/')
            print(f"{idx_curr_subdir}/{len(all_current_subdirs)} -", "Renaming", curr_subdir_base_name, "->", new_subdir_base_name)
            shutil.move(curr_subdir, new_subdir)
        else:
            print(f"{idx_curr_subdir}/{len(all_current_subdirs)} -", "Skipping", curr_subdir_base_name, "- already in correct format")

        # sys.exit(0)

    print("\nFinished!\n")
    

if __name__ == "__main__":
    main()