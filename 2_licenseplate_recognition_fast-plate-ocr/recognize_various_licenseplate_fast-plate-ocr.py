import os
import sys
import cv2
import numpy as np
import argparse
from pathlib import Path
import json
import glob
import re
from fast_plate_ocr import LicensePlateRecognizer


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='cct-s-v1-global-model')    # cct-xs-v1-global-model
    parser.add_argument('--path-dataset', type=str, default='C:/Users/Bernardo/GitHub/bot_download_chassi_img/qualit/vistorias_qualit/veiculos_vistoria_laudo_chassi_v2_LABELED/qualit_LABELED/vistorias_qualit_LABELED/vistorias_download_LABELED')
    
    parser.add_argument('--start-idx', type=int, default=0)
    return parser.parse_args()


def natural_sort_key(path):
    s = str(path)
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def load_all_subdirs(input_folder: str) -> list[str]:
    subdirs = [os.path.join(input_folder, name).replace('\\','/') for name in os.listdir(input_folder) if os.path.isdir(os.path.join(input_folder, name))]
    subdirs.sort(key=natural_sort_key)
    return subdirs

def load_json(path: str) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def resize_with_scale(image, target_size=128):
    h, w = image.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    resized_image = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
    return resized_image, scale


def draw_bbox(img, bbox):
    x1, y1, x2, y2 = int(round(bbox[0])), int(round(bbox[1])), int(round(bbox[2])), int(round(bbox[3]))
    img_copy = img.copy()
    cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 0, 255), 10)
    cv2.putText(img_copy, "License Plate", (x1, y1-20), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 4)
    return img_copy



if __name__ == "__main__":
    args = parse_arguments()

    print(f"Loading model '{args.model}'")
    model = LicensePlateRecognizer(args.model)
    print("    Done")

    print(f"Searching vistorias dirs in: '{args.path_dataset}'")
    all_vistorias_paths = load_all_subdirs(args.path_dataset)
    print(f"    Found {len(all_vistorias_paths)} vistorias")

    print('-----------------')
    for idx_dir_vistoria, path_dir_vistoria in enumerate(all_vistorias_paths):
        if idx_dir_vistoria >= args.start_idx:
            if args.start_idx > 0: print()
            print('-----------------')
            print(f"{idx_dir_vistoria}/{len(all_vistorias_paths)} Loading vistoria '{path_dir_vistoria}'")
            json_path = glob.glob(os.path.join(path_dir_vistoria, "dados_vistoria*.json").replace('\\','/'))
            assert len(json_path) > 0, f"No JSON file found in {path_dir_vistoria}"
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

            if "URL Placa LABELED" in dados_vistoria_corrected and not dados_vistoria_corrected["URL Placa LABELED"] is None and dados_vistoria_corrected["URL Placa LABELED"] != "":
                img_path = os.path.join(path_dir_vistoria, "imgs", dados_vistoria_corrected["URL Placa LABELED"]).replace('\\','/')
                assert os.path.isfile(img_path), f"License plate image file not found: {img_path}"
                
                print(f"Loading img '{img_path}'")
                img = cv2.imread(img_path)
                gt_placa = dados_vistoria_corrected["Placa"]
                dados_placa_detectada = dados_vistoria_corrected["Placa LABELED DETECTED"]
                bbox_placa = dados_placa_detectada["bbox"]
                
                print(f"Drawing bbox")
                img_draw = draw_bbox(img, bbox_placa)
                img_draw, scale = resize_with_scale(img_draw, target_size=600)
                cv2.imshow("image", img_draw)

                x1, y1, x2, y2 = int(round(bbox_placa[0])), int(round(bbox_placa[1])), int(round(bbox_placa[2])), int(round(bbox_placa[3]))
                crop_placa = img[y1:y2, x1:x2]
                
                # crop_placa_resized = crop_placa
                # crop_placa_resized = cv2.resize(crop_placa, (128, 64))
                crop_placa_resized, scale = resize_with_scale(crop_placa, target_size=128)
                print('crop_placa_resized.shape:', crop_placa_resized.shape)

                print('Running OCR model...')
                pred_placa = model.run(crop_placa_resized)
                pred_placa = pred_placa[0].replace("_", "")
                # print(f"type(pred_placa): {type(pred_placa)}")
                print(f"    GT Placa  :", gt_placa)
                print(f"    Pred Placa:", pred_placa)

                if pred_placa == gt_placa:
                    print("    Placa reconhecida corretamente!")
                else:
                    print("    Placa não reconhecida ou reconhecida parcialmente!")

                cv2.imshow("crop_placa_resized", crop_placa_resized)
                cv2.waitKey(0)
        
        else:
            print(f"Skipping vistoria idx {idx_dir_vistoria}", end="\r")

    '''
    print(f"Loading img '{args.image}'")
    img = cv2.imread(args.image)
    img_resized = cv2.resize(img, (640, 640))
    cv2.imshow("img_resized", img_resized)
    cv2.waitKey(0)

    print(f"Loading model '{args.model}'")
    model = YOLO(args.model)
    print("    Done")

    print("Performing inference...")
    results = model.predict(source=img_resized, conf=0.60, iou=0.45, max_det=1)
    # print("results:", results)

    if len(results[0].boxes) > 0:
        for result in results:
            for box in result.boxes:
                coords = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = result.names[cls_id]
                print(f"--- Detection Found ---")
                print(f"Label: {label}")
                print(f"Confidence: {conf:.2%}")
                print(f"Coordinates: x1={coords[0]:.1f}, y1={coords[1]:.1f}, x2={coords[2]:.1f}, y2={coords[3]:.1f}")

                # Extract coordinates (top-left x, top-left y, bottom-right x, bottom-right y)
                x1, y1, x2, y2 = box.xyxy[0]
                
                # Convert tensors/floats to integers for OpenCV
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # 4. Draw the red rectangle (BGR format: Red is 0, 0, 255)
                cv2.rectangle(img_resized, (x1, y1), (x2, y2), (0, 0, 255), 2)
                
                # Optional: Add a label
                cv2.putText(img_resized, "License Plate", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # 5. Show on screen
        cv2.imshow('License Plate Detection', img_resized)

        # Keep the window open until a key is pressed
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    else:
        print("No license plate detected.")
    '''
        
        
    print("Finished\n")
