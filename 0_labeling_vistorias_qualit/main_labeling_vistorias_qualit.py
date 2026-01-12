#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
import os
from pathlib import Path
import json
from PIL import Image
    

__version__ = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, required=True,  default="D:/Datasets/veiculos_vistoria_laudo_chassi_v1_DADOS_BRUTOS/qualit/vistorias_qualit/vistorias_download")
    parser.add_argument("-o", "--output", type=str, required=True, default="D:/Datasets/veiculos_vistoria_laudo_chassi_v2_LABELED/qualit_LABELED/vistorias_qualit_LABELED/vistorias_download_LABELED")
    return parser.parse_args(argv)


def load_json(path: str) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(obj: dict, path: str, indent: int = 4) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=indent)
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)


def load_all_subdirs(input_folder: str) -> list[str]:
    subdirs = [os.path.join(input_folder, name).replace('\\','/') for name in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, name))]
    return subdirs




def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not os.path.isdir(args.input):
        print(f"Error: input file '{args.input}' does not exist", file=sys.stderr)
        return 2
    os.makedirs(args.output, exist_ok=True)

    
    print(f"Scanning input folder: {args.input}")
    all_vistorias_subdirs = load_all_subdirs(args.input)
    print(f"    Found {len(all_vistorias_subdirs)} vistorias in input folder")


    # Main loop
    for idx_vistoria_subdir, vistoria_subdir in enumerate(all_vistorias_subdirs):
        print(f"{idx_vistoria_subdir}/{len(all_vistorias_subdirs)}: Processing vistoria subdir: {vistoria_subdir}")

        json_path = os.path.join(vistoria_subdir, "dados_vistoria.json").replace('\\','/')
        print(f"    Loading JSON data from: {json_path}")
        dados_vistoria_orig = load_json(json_path)
        dados_vistoria_corrected = {}
        for idx_key_vistoria, key_vistoria in enumerate(dados_vistoria_orig.keys()):
            if key_vistoria:
                if key_vistoria.startswith("URL "):
                    dados_vistoria_corrected[key_vistoria] = dados_vistoria_orig[key_vistoria].split('/')[-1]
                else:
                    dados_vistoria_corrected[key_vistoria] = dados_vistoria_orig[key_vistoria]

        images_folder = os.path.join(vistoria_subdir, "imgs").replace('\\','/')
        imgs_vistoria = {}
        print(f"    Loading images of vistoria:")
        for idx_key_vistoria, key_vistoria in enumerate(dados_vistoria_corrected.keys()):
            if key_vistoria.startswith("URL "):
                img_filename = dados_vistoria_corrected[key_vistoria]
                print(f"        {key_vistoria}: {img_filename}")
                img_path = os.path.join(images_folder, img_filename).replace('\\','/')
                if os.path.isfile(img_path):
                    imgs_vistoria[dados_vistoria_corrected[key_vistoria]] = Image.open(img_path)
                else:
                    raise FileNotFoundError(f"Image file not found: {img_path}")

        # TODO: For each folder, show a GUI tool to choose license plate and chassi image
        

        print("-----------")
        # sys.exit(0)


    print("\nFinished processing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
