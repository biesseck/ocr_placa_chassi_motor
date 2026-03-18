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
# from fast_plate_ocr import PlatePrediction


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='cct-s-v1-global-model')    # cct-xs-v1-global-model
    parser.add_argument('--path-dataset', type=str, default='C:/Users/Bernardo/GitHub/bot_download_chassi_img/qualit/vistorias_qualit/veiculos_vistoria_laudo_chassi_v2_LABELED/qualit_LABELED/vistorias_qualit_LABELED/vistorias_download_LABELED')
    
    parser.add_argument('--start-idx', type=int, default=0)
    parser.add_argument('--show-all-images', action='store_true')
    parser.add_argument('--show-error-images', action='store_true')
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

    plate_hits, plate_misses = 0, 0
    num_existing_plates, num_missing_plates = 0, 0
    
    num_valid_chars = 0
    chars_hits, chars_misses = 0, 0
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
                
                if args.show_all_images:
                    cv2.imshow("image", img_draw)

                x1, y1, x2, y2 = int(round(bbox_placa[0])), int(round(bbox_placa[1])), int(round(bbox_placa[2])), int(round(bbox_placa[3]))
                crop_placa = img[y1:y2, x1:x2]
                
                # crop_placa_resized = crop_placa
                # crop_placa_resized = cv2.resize(crop_placa, (128, 64))
                crop_placa_resized, scale = resize_with_scale(crop_placa, target_size=128)
                print('crop_placa_resized.shape:', crop_placa_resized.shape)

                print('Running OCR model...')
                pred_placa = model.run(crop_placa_resized)
                if type(pred_placa[0]) is str:
                    pred_placa = pred_placa[0].replace("_", "")
                # elif type(pred_placa[0]) is PlatePrediction:
                #     pred_placa = pred_placa[0].plate.replace("_", "")
                # print(f"type(pred_placa): {type(pred_placa)}")
                print(f"    GT Placa  :", gt_placa)
                print(f"    Pred Placa:", pred_placa)

                num_existing_plates += 1
                if pred_placa == gt_placa:
                    plate_hits += 1
                    print("    Placa reconhecida corretamente!")
                else:
                    plate_misses += 1
                    print("    Placa não reconhecida ou reconhecida parcialmente!")
                    if args.show_error_images:
                        cv2.imshow("image", img_draw)
                        cv2.imshow("crop_placa_resized", crop_placa_resized)
                        cv2.waitKey(0)

                chars_hits += sum(1 for p, g in zip(pred_placa, gt_placa) if p == g)
                chars_misses += sum(1 for p, g in zip(pred_placa, gt_placa) if p != g)
                num_valid_chars += len(gt_placa)

                if args.show_all_images:
                    cv2.imshow("crop_placa_resized", crop_placa_resized)
                    cv2.waitKey(0)

            else:
                num_missing_plates += 1

        else:
            print(f"Skipping vistoria idx {idx_dir_vistoria}", end="\r")

    print('-----------------')
    total_acc_plates = plate_hits / num_existing_plates
    print(f"Final Results:")
    print(f"num_vistorias: {len(all_vistorias_paths)}")
    print(f"num_existing_plates: {num_existing_plates}/{len(all_vistorias_paths)}: {num_existing_plates/len(all_vistorias_paths):.2%}")
    print(f"num_missing_plates: {num_missing_plates}/{len(all_vistorias_paths)}: {num_missing_plates/len(all_vistorias_paths):.2%}")
    print(f"    Plate Hits: {plate_hits}/{num_existing_plates}    acc_plates: {total_acc_plates:.2%}")
    print(f"    Plate Misses: {plate_misses}/{num_existing_plates}")
    print('-----------------')
    print(f"num_valid_chars: {num_valid_chars}")
    print(f"    Char Hits: {chars_hits}/{num_valid_chars}    acc_chars: {chars_hits/num_valid_chars:.2%}")
    print(f"    Char Misses: {chars_misses}/{num_valid_chars}")
    
    print("Finished\n")
