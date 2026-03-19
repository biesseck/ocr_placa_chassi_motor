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

import matplotlib.pyplot as plt
import matplotlib.patches as patches


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='cct-s-v1-global-model')    # cct-xs-v1-global-model
    parser.add_argument('--path-dataset', type=str, default='C:/Users/Bernardo/GitHub/bot_download_chassi_img/qualit/vistorias_qualit/vistorias_download_v2_SEM_FOTOS_EXTRAS_LABELED')
    
    parser.add_argument('--start-idx', type=int, default=0)
    parser.add_argument('--show-all-images', action='store_true')
    parser.add_argument('--show-error-images', action='store_true')
    parser.add_argument('--save-predictions', action='store_true')
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

def save_json(obj: dict, path: str, indent: int = 4) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=indent)
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)

def save_to_txt(content, file_path, append=False):
    mode = 'a' if append else 'w'
    with open(file_path, mode, encoding='utf-8') as f:
        if isinstance(content, list):
            f.write('\n'.join(map(str, content)) + '\n')
        else:
            f.write(str(content) + '\n')

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


def save_ocr_comparison(image_crop, ground_truth, prediction, title, save_path, 
                        figsize=(10, 4), font_size=14, font_family='Consolas'):
    fig, ax = plt.subplots(1, 2, figsize=figsize, gridspec_kw={'width_ratios': [1, 1]})
    fig.suptitle(title, fontsize=font_size+4, family=font_family)

    if type(image_crop) == np.ndarray:
        image_crop = cv2.cvtColor(image_crop, cv2.COLOR_BGR2RGB)
    ax[0].imshow(image_crop)
    ax[0].set_title(f"License Plate Crop - shape: {image_crop.shape}px", fontsize=font_size, family=font_family)
    ax[0].axis('off')  # Hide axis for the image
    ax[1].axis('off')
    
    match_color = 'green' if ground_truth.strip().upper() == prediction.strip().upper() else 'red'
    
    text_content = (
        f"Ground Truth: {ground_truth}\n\n"
        f"Prediction:   {prediction}"
    )
    
    ax[1].text(0.1, 0.5, text_content, 
               fontsize=font_size+4, 
               family=font_family,
               verticalalignment='center',
               bbox=dict(facecolor='white', alpha=0.5, edgecolor=match_color, boxstyle='round,pad=1'))

    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Adjust to fit the suptitle
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


if __name__ == "__main__":
    args = parse_arguments()
    args.path_dataset = args.path_dataset.replace('\\','/')

    print(f"Loading model '{args.model}'")
    model = LicensePlateRecognizer(args.model)
    print("    Done")

    print(f"Searching vistorias dirs in: '{args.path_dataset}'")
    all_vistorias_paths = load_all_subdirs(args.path_dataset)
    print(f"    Found {len(all_vistorias_paths)} vistorias")
    print('-----------------')

    output_folder_results = "./predictions_model_" + args.model
    success_folder = os.path.join(output_folder_results, "success").replace('\\','/')
    failure_folder = os.path.join(output_folder_results, "failure").replace('\\','/')
    success_predictions_path = os.path.join(success_folder, "success_predictions.json").replace('\\','/')
    failure_predictions_path = os.path.join(failure_folder, "failure_predictions.json").replace('\\','/')
    total_predictions_path = os.path.join(output_folder_results, "total_predictions.txt").replace('\\','/')
    if args.save_predictions:
        os.makedirs(output_folder_results, exist_ok=True)
        os.makedirs(success_folder, exist_ok=True)
        os.makedirs(failure_folder, exist_ok=True)

    all_success_predictions = {"path_dataset": args.path_dataset, "model": args.model, "predictions": {}}
    all_failure_predictions = {"path_dataset": args.path_dataset, "model": args.model, "predictions": {}}

    plate_hits, plate_misses = 0, 0
    num_imgs_with_plate, num_imgs_without_plate = 0, 0
    num_all_valid_chars = 0
    all_chars_hits, all_chars_misses = 0, 0

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
                
                chars_hits   = sum(1 for p, g in zip(pred_placa, gt_placa) if p == g)
                chars_misses = sum(1 for p, g in zip(pred_placa, gt_placa) if p != g)
                all_chars_hits   += chars_hits
                all_chars_misses += chars_misses
                num_all_valid_chars += len(gt_placa)

                prediction_info = {
                    "URL Placa LABELED":      dados_vistoria_corrected["URL Placa LABELED"],
                    "Placa LABELED DETECTED": dados_vistoria_corrected["Placa LABELED DETECTED"],
                    "gt_placa":               gt_placa,
                    "pred_placa":             pred_placa,
                    "chars_hits":             chars_hits,
                    "chars_misses":           chars_misses
                }

                print(f"    GT Placa  :", gt_placa)
                print(f"    Pred Placa:", pred_placa)

                num_imgs_with_plate += 1
                if pred_placa == gt_placa:
                    plate_hits += 1
                    all_success_predictions["predictions"][os.path.basename(path_dir_vistoria)] = prediction_info
                    print("    Placa reconhecida corretamente!")

                    if args.save_predictions:
                        chart_title = f"Vistoria: {os.path.basename(path_dir_vistoria)}\nURL Placa LABELED: {dados_vistoria_corrected['URL Placa LABELED']}\nGT Placa: {gt_placa}    Pred Placa: {pred_placa}"
                        chart_path = os.path.join(success_folder, 'imgs', f"chars-misses-{chars_misses}_chars-hits-{chars_hits}_{os.path.basename(path_dir_vistoria)}.png").replace('\\','/')
                        os.makedirs(os.path.dirname(chart_path), exist_ok=True)
                        print(f"    Saving chart prediction: '{chart_path}'")
                        save_ocr_comparison(crop_placa_resized, gt_placa, pred_placa, chart_title, chart_path)

                else:
                    plate_misses += 1
                    all_failure_predictions["predictions"][os.path.basename(path_dir_vistoria)] = prediction_info
                    print("    Placa não reconhecida ou reconhecida parcialmente!")
                    if args.show_error_images:
                        cv2.imshow("image", img_draw)
                        cv2.imshow("crop_placa_resized", crop_placa_resized)
                        cv2.waitKey(0)

                    if args.save_predictions:
                        chart_title = f"Vistoria: {os.path.basename(path_dir_vistoria)}\nURL Placa LABELED: {dados_vistoria_corrected['URL Placa LABELED']}\nGT Placa: {gt_placa}    Pred Placa: {pred_placa}"
                        chart_path = os.path.join(failure_folder, 'imgs', f"chars-misses-{chars_misses}_chars-hits-{chars_hits}_{os.path.basename(path_dir_vistoria)}.png").replace('\\','/')
                        os.makedirs(os.path.dirname(chart_path), exist_ok=True)
                        print(f"    Saving chart prediction: '{chart_path}'")
                        save_ocr_comparison(crop_placa_resized, gt_placa, pred_placa, chart_title, chart_path)

                if args.save_predictions:
                    print(f"    Saving predictions to JSON file: '{success_predictions_path}'")
                    save_json(all_success_predictions, success_predictions_path)
                    print(f"    Saving predictions to JSON file: '{failure_predictions_path}'")
                    save_json(all_failure_predictions, failure_predictions_path)

                if args.show_all_images:
                    cv2.imshow("crop_placa_resized", crop_placa_resized)
                    cv2.waitKey(0)

            else:
                num_imgs_without_plate += 1

        else:
            print(f"Skipping vistoria idx {idx_dir_vistoria}", end="\r")

    print('\n========================================\n')
    total_acc_plates = plate_hits / num_imgs_with_plate

    final_results_str = ""
    final_results_str += f"Final Results:\n"
    final_results_str += f"path_dataset: '{args.path_dataset}'\n"
    final_results_str += f"Model: '{args.model}'\n"
    final_results_str += f"-----------------\n"
    final_results_str += f"num_vistorias:       {len(all_vistorias_paths)}\n"
    final_results_str += f"num_imgs_with_plate: {num_imgs_with_plate}/{len(all_vistorias_paths)-args.start_idx}: {num_imgs_with_plate/(len(all_vistorias_paths)-args.start_idx):.2%}\n"
    final_results_str += f"num_imgs_without_plate: {num_imgs_without_plate}/{len(all_vistorias_paths)-args.start_idx}: {num_imgs_without_plate/(len(all_vistorias_paths)-args.start_idx):.2%}\n"
    final_results_str += f"-----------------\n"
    final_results_str += f"Plate Hits:   {plate_hits}/{num_imgs_with_plate}    acc_plates: {total_acc_plates:.2%}\n"
    final_results_str += f"Plate Misses: {plate_misses}/{num_imgs_with_plate}\n"
    final_results_str += f"-----------------\n"
    final_results_str += f"num_all_valid_chars: {num_all_valid_chars}\n"
    final_results_str += f"    Char Hits:   {all_chars_hits}/{num_all_valid_chars}    acc_chars: {all_chars_hits/num_all_valid_chars:.2%}\n"
    final_results_str += f"    Char Misses: {all_chars_misses}/{num_all_valid_chars}\n"

    print(final_results_str)
    print(f"Saving final results to file: '{total_predictions_path}'")
    os.makedirs(os.path.dirname(total_predictions_path), exist_ok=True)
    save_to_txt(final_results_str, total_predictions_path)

    print("\nFinished\n")
