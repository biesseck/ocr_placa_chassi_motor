#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import sys
import os
import numpy as np
from pathlib import Path
import json
import cv2
from PIL import Image, ImageDraw, ImageTk
from datetime import datetime
import shutil
import glob
from ultralytics import YOLO
import torch
    

__version__ = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="labeling", choices=["labeling", "check"], help="Mode of operation.")
    parser.add_argument('--model', type=str, default='license-plate-finetune-v1l.pt', help='Path to the YOLO model')
    return parser.parse_args(argv)


def make_default_global_config(path_config_global = "config_global.json") -> None:
    default_config = {
        "input":                "",
        "output":               "",
        "start_labeling_index": 0,
        "labeled_folders":      []
    }
    save_json(default_config, path_config_global)


def app_dir():
    if getattr(sys, "frozen", False):    # If running as a PyInstaller-built exe
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))    # If running as a normal .py
    

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


def natural_sort_key(path):
    s = str(path)
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def load_all_subdirs(input_folder: str) -> list[str]:
    subdirs = [os.path.join(input_folder, name).replace('\\','/') for name in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, name))]
    subdirs.sort(key=natural_sort_key)
    return subdirs


def select_folder(title="Select a folder"):
    root = tk.Tk()
    root.withdraw()          # hide the main window
    root.attributes("-topmost", True)  # bring dialog to front (optional)
    folder = filedialog.askdirectory(title=title)
    root.destroy()
    return folder


def resize_with_scale(image, target_size=640):
    h, w = image.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    resized_image = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
    return resized_image, scale




def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print(f"Loading license plate detection model '{args.model}'")
    model = YOLO(args.model)
    print("    Done")

    # path_config_global = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_global.json").replace('\\','/')
    path_config_global = os.path.join(app_dir(), "config_global.json").replace('\\','/')
    if not os.path.isfile(path_config_global):
        print(f"Creating default global config file at: {path_config_global}")
        make_default_global_config(path_config_global)
    print(f"Loading default global config file: {path_config_global}")
    dict_global_config = load_json(path_config_global)

    if not os.path.isdir(dict_global_config["input"]):
        print(f"Selecting input folder...")
        dict_global_config["input"] = select_folder("Select INPUT folder")
        print(f"    Selected input folder: \'{dict_global_config['input']}\'")
        if not os.path.isdir(dict_global_config["input"]):
            print("    No input folder selected. Exiting program.")
            return 0
        save_json(dict_global_config, path_config_global)
    if not os.path.isdir(dict_global_config["output"]):
        dict_global_config["output"] = '/'.join(dict_global_config["input"].split('/')[:-3])
        dict_global_config["output"] = dict_global_config["output"].replace('v1','v2').replace('DADOS_BRUTOS','LABELED')
        dict_global_config["output"] = os.path.join(dict_global_config["output"], '/'.join([folder for folder in dict_global_config["input"].split('/')[-3:]]))
        dict_global_config["output"] = dict_global_config["output"].replace('\\','/')
        os.makedirs(dict_global_config["output"], exist_ok=True)
        save_json(dict_global_config, path_config_global)


    print(f"Scanning input folder: {dict_global_config['input']}")
    all_vistorias_subdirs = load_all_subdirs(dict_global_config["input"])
    print(f"    Found {len(all_vistorias_subdirs)} vistorias in input folder")


    # Find index of current_vistoria to resume from there
    idx_current_vistoria = -1
    if len(dict_global_config["labeled_folders"]) > 0:
        for idx_vistoria_subdir, vistoria_subdir in enumerate(all_vistorias_subdirs):
            if list(dict_global_config["labeled_folders"][-1].keys())[-1] in vistoria_subdir:
                idx_current_vistoria = idx_vistoria_subdir
                break


    # Main loop
    for idx_vistoria_subdir, vistoria_subdir in enumerate(all_vistorias_subdirs):
        print("-----------")
        if idx_vistoria_subdir >= dict_global_config["start_labeling_index"] and idx_vistoria_subdir > idx_current_vistoria:
            # print(f"Num Placas Anotadas: {len(dict_global_config['labeled_folders'])}")
            print(f"{idx_vistoria_subdir}/{len(all_vistorias_subdirs)}: Processing vistoria subdir: {vistoria_subdir}")


            # json_path = os.path.join(vistoria_subdir, "dados_vistoria.json").replace('\\','/')
            json_path = glob.glob(os.path.join(vistoria_subdir, "dados_vistoria*.json").replace('\\','/'))
            assert len(json_path) > 0, f"No JSON file found in {vistoria_subdir}"
            json_path = json_path[0]
            print(f"    Loading JSON data from: {json_path}")
            dados_vistoria_orig = load_json(json_path)
            dados_vistoria_corrected = {}
            for idx_key_vistoria, key_vistoria in enumerate(dados_vistoria_orig.keys()):
                if key_vistoria:
                    if key_vistoria.startswith("URL ") and not dados_vistoria_orig[key_vistoria] is None:
                        dados_vistoria_corrected[key_vistoria] = dados_vistoria_orig[key_vistoria].split('/')[-1]
                    else:
                        dados_vistoria_corrected[key_vistoria] = dados_vistoria_orig[key_vistoria]

            # Load img and detect license plate
            if "URL Placa LABELED" in dados_vistoria_corrected and not dados_vistoria_corrected["URL Placa LABELED"] is None and dados_vistoria_corrected["URL Placa LABELED"] != "":
                img_path = os.path.join(vistoria_subdir, "imgs", dados_vistoria_corrected["URL Placa LABELED"]).replace('\\','/')
                assert os.path.isfile(img_path), f"License plate image file not found: {img_path}"
                print(f"Loading img '{img_path}'")
                img = cv2.imread(img_path)
                # img_resized = cv2.resize(img, (640, 640))
                img_resized, scale = resize_with_scale(img, target_size=640)

                print("Performing inference...")
                results = model.predict(source=img_resized, conf=0.60, iou=0.45, max_det=1)

                if len(results[0].boxes) > 0:
                    for result in results:
                        for box in result.boxes:
                            bbox = box.xyxy[0].cpu().numpy()
                            conf = float(box.conf[0])
                            cls_id = int(box.cls[0])
                            label = result.names[cls_id]
                            print(f"Detection Found:")
                            print(f"    Label: {label}")
                            print(f"    Confidence: {conf:.2%}")
                            print(f"    Coordinates: x1={bbox[0]:.2f}, y1={bbox[1]:.2f}, x2={bbox[2]:.2f}, y2={bbox[3]:.2f}")

                            x1, y1, x2, y2 = int(round(bbox[0])), int(round(bbox[1])), int(round(bbox[2])), int(round(bbox[3]))
                            cv2.rectangle(img_resized, (x1, y1), (x2, y2), (0, 0, 255), 2)
                            cv2.putText(img_resized, "License Plate", (x1, y1 - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                            

                            dados_vistoria_corrected["Placa LABELED DETECTED"] = {"bbox": (bbox/scale).tolist(),
                                                                                  "conf": conf,
                                                                                  "class_id": cls_id,
                                                                                  "label": label}

                    json_output_path = json_path.replace('\\','/')
                    print(f"Saving output labeled JSON data to: {json_output_path}")
                    save_json(dados_vistoria_corrected, json_output_path)

                    # cv2.imshow('License Plate Detection (resized)', img_resized)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()
                    # if idx_vistoria_subdir == 9: sys.exit(0)    # TEST

                else:
                    print("No license plate detected.")

                # sys.exit(0)
                
        else:
            print(f"{idx_vistoria_subdir}/{len(all_vistorias_subdirs)}: Skipping vistoria subdir: {vistoria_subdir}")

        # sys.exit(0)



    print("\nFinished processing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
