#!/usr/bin/env python3
from __future__ import annotations
import argparse
import glob
import re
import sys
import os
import math
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageTk
from datetime import datetime
import shutil

import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import tkinter.font as tkfont
from typing import Any
    

__version__ = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="labeling", choices=["labeling", "check"], help="Mode of operation.")
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


def display_single_image(pil_image, label_text, filename_text):
    if not pil_image:
        print("No valid PIL image provided.")
        return None

    # --- 1. Initialize Tkinter root & Main State ---
    root = tk.Tk()
    root.title(f"Labeling: {filename_text}")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    smallest_dimension = min(screen_width, screen_height)

    window_width = int(screen_width * 0.85)
    window_height = int(screen_height * 0.85)
    position_x = int((screen_width - window_width) / 2)
    position_y = int((screen_height - window_height) / 2 - screen_height * 0.06)
    root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

    max_image_dim = int(smallest_dimension * 0.70)
    img_width, img_height = pil_image.size
    scale_factor = min(max_image_dim / img_width, max_image_dim / img_height)
    scale_factor = min(scale_factor, 1.0)

    new_width = int(img_width * scale_factor)
    new_height = int(img_height * scale_factor)
    resized_image = (
        pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        if scale_factor < 1.0
        else pil_image
    )

    # State variables for Annotation
    polygon_pts = []  
    canvas_polygons = []  
    drag_node_idx = None  
    NODE_RADIUS = 6
    final_coords = None

    # Track state for right-click rotation
    last_rotation_angle = 0.0
    poly_center = (0, 0)

    # --- 2. Build Multi-Column Layout ---
    meta_frame = tk.Frame(root, bg="#f0f0f0", pady=5)
    meta_frame.pack(side="top", fill="x")
    tk.Label(
        meta_frame,
        text=f"File: {filename_text} | Left-Click Drag: Draw/Tweak | Right-Click Drag: Rotate Box",
        font=("Arial", 10, "italic"),
        bg="#f0f0f0",
    ).pack()

    workspace = tk.Frame(root)
    workspace.pack(side="top", expand=True, fill="both", padx=10, pady=5)

    left_panel = tk.Frame(workspace)
    left_panel.pack(side="left", expand=True, fill="both")

    right_panel = tk.Frame(workspace, width=300, bg="#e8e8e8", bd=1, relief="sunken")
    right_panel.pack(side="right", fill="y", padx=(10, 0))
    right_panel.pack_propagate(False)

    tk.Label(
        right_panel, text="Horizontal Preview Check", font=("Arial", 11, "bold"), bg="#e8e8e8"
    ).pack(pady=5)
    preview_lbl = tk.Label(
        right_panel, text="[Draw a box to view horizontal text]", bg="#dcdcdc"
    )
    preview_lbl.pack(expand=True, fill="both", padx=10, pady=10)

    canvas = tk.Canvas(
        left_panel, width=new_width, height=new_height, bg="black", highlightthickness=0
    )
    canvas.pack(expand=True)

    tk_img = ImageTk.PhotoImage(resized_image)
    root.tk_image_ref = tk_img
    canvas.create_image(0, 0, anchor="nw", image=tk_img)

    bottom_frame = tk.Frame(root, pady=10)
    bottom_frame.pack(side="bottom", fill="x")

    tk.Label(
        bottom_frame, text=label_text, font=("Arial", 12, "bold"), wrap=int(window_width * 0.6)
    ).pack(side="left", padx=20)

    # --- 3. Robust Invariant Perspective Transformation ---
    def update_visual_check():
        if len(polygon_pts) < 4:
            return

        orig_pts = [(x / scale_factor, y / scale_factor) for x, y in polygon_pts]
        tl, tr, br, bl = orig_pts

        out_w = int(math.hypot(tr[0] - tl[0], tr[1] - tl[1]))
        out_h = int(math.hypot(bl[0] - tl[0], bl[1] - tl[1]))

        if out_w <= 1 or out_h <= 1:
            return

        src_quad = [
            tl[0], tl[1],  
            bl[0], bl[1],  
            br[0], br[1],  
            tr[0], tr[1]   
        ]

        try:
            cropped_horizontal = pil_image.transform(
                (out_w, out_h),
                Image.Transform.QUAD,
                src_quad,
                resample=Image.Resampling.BILINEAR
            )
        except Exception:
            return

        p_width, p_height = cropped_horizontal.size
        p_scale = min(280 / p_width, 400 / p_height)
        if p_scale < 1.0:
            cropped_horizontal = cropped_horizontal.resize(
                (int(p_width * p_scale), int(p_height * p_scale)), Image.Resampling.LANCZOS
            )

        tk_preview = ImageTk.PhotoImage(cropped_horizontal)
        root.tk_preview_ref = tk_preview
        preview_lbl.configure(image=tk_preview, text="")

    def redraw_polygon():
        for item in canvas_polygons:
            canvas.delete(item)
        canvas_polygons.clear()

        if not polygon_pts:
            return

        if len(polygon_pts) == 4:
            poly_id = canvas.create_polygon(
                polygon_pts, outline="cyan", fill="", width=2
            )
            canvas_polygons.append(poly_id)
        elif len(polygon_pts) > 1:
            flat_pts = [coord for pt in polygon_pts for coord in pt]
            line_id = canvas.create_line(flat_pts, fill="yellow", width=2)
            canvas_polygons.append(line_id)

        for i, (x, y) in enumerate(polygon_pts):
            color = "green" if i == 0 else "red" if i == 2 else "gray"
            node_id = canvas.create_oval(
                x - NODE_RADIUS,
                y - NODE_RADIUS,
                x + NODE_RADIUS,
                y + NODE_RADIUS,
                fill=color,
                outline="white",
                width=1,
            )
            canvas_polygons.append(node_id)

    # --- 4. Mouse Callbacks (Left Click: Draw/Tweak | Right Click: Rotate) ---
    def on_mouse_down(event):
        nonlocal drag_node_idx, polygon_pts
        x, y = event.x, event.y

        if len(polygon_pts) == 4:
            for i, (nx, ny) in enumerate(polygon_pts):
                if math.hypot(x - nx, y - ny) <= NODE_RADIUS + 4:
                    drag_node_idx = i
                    return
            polygon_pts = [[x, y]]
            drag_node_idx = None
            redraw_polygon()
        else:
            polygon_pts = [[x, y]]
            drag_node_idx = None

    def on_mouse_drag(event):
        nonlocal polygon_pts
        if not polygon_pts:
            return
        x, y = max(0, min(event.x, new_width)), max(0, min(event.y, new_height))

        if drag_node_idx is not None:
            polygon_pts[drag_node_idx] = [x, y]
            redraw_polygon()
            update_visual_check()
        elif len(polygon_pts) <= 4:
            x0, y0 = polygon_pts[0]
            dx = x - x0
            dy = y - y0

            if dx >= 0 and dy >= 0:
                polygon_pts = [[x0, y0], [x, y0], [x, y], [x0, y]]
            elif dx < 0 and dy >= 0:
                polygon_pts = [[x0, y0], [x0, y], [x, y], [x, y0]]
            elif dx < 0 and dy < 0:
                polygon_pts = [[x0, y0], [x, y0], [x, y], [x0, y]]
            else:
                polygon_pts = [[x0, y0], [x0, y], [x, y], [x, y0]]

            redraw_polygon()

    def on_mouse_up(event):
        nonlocal drag_node_idx
        if len(polygon_pts) == 4:
            update_visual_check()
        drag_node_idx = None

    # --- New Right-Click Rotation Handlers ---
    def on_right_mouse_down(event):
        nonlocal last_rotation_angle, poly_center
        if len(polygon_pts) < 4:
            return
        
        # Calculate bounding box center of current polygon
        cx = sum(pt[0] for pt in polygon_pts) / 4
        cy = sum(pt[1] for pt in polygon_pts) / 4
        poly_center = (cx, cy)
        
        # Capture the baseline angle from center to mouse click point
        last_rotation_angle = math.atan2(event.y - cy, event.x - cx)

    def on_right_mouse_drag(event):
        nonlocal last_rotation_angle, polygon_pts
        if len(polygon_pts) < 4:
            return
        
        cx, cy = poly_center
        # Calculate current mouse angle relative to center
        current_angle = math.atan2(event.y - cy, event.x - cx)
        delta_angle = current_angle - last_rotation_angle
        
        # Rotate all 4 points uniformly around the center point
        new_pts = []
        for x, y in polygon_pts:
            tx, ty = x - cx, y - cy
            rx = tx * math.cos(delta_angle) - ty * math.sin(delta_angle)
            ry = tx * math.sin(delta_angle) + ty * math.cos(delta_angle)
            
            # Clip back to canvas bounds
            rx = max(0, min(rx + cx, new_width))
            ry = max(0, min(ry + cy, new_height))
            new_pts.append([rx, ry])
            
        polygon_pts = new_pts
        last_rotation_angle = current_angle
        redraw_polygon()
        update_visual_check()

    # Bind Left-Click bindings
    canvas.bind("<Button-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    
    # Bind Right-Click bindings (Button-3 is right-click in Tkinter)
    canvas.bind("<Button-3>", on_right_mouse_down)
    canvas.bind("<B3-Motion>", on_right_mouse_drag)
    canvas.bind("<ButtonRelease-3>", on_mouse_up)

    # --- 5. Return Value Submission Logic ---
    def on_confirm():
        nonlocal final_coords
        if len(polygon_pts) < 4:
            messagebox.showwarning(
                "Incomplete Annotation",
                "Please drag to create a bounding box area over the image before confirming.",
            )
            return

        final_coords = [(x / scale_factor, y / scale_factor) for x, y in polygon_pts]
        root.destroy()

    confirm_btn = tk.Button(
        bottom_frame,
        text="OK / Confirm",
        font=("Arial", 11, "bold"),
        bg="#4CAF50",
        fg="white",
        padx=15,
        command=on_confirm,
    )
    confirm_btn.pack(side="right", padx=20)

    root.mainloop()
    return final_coords




def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

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
        dict_global_config["output"] = dict_global_config["input"].replace('v2','v3') + "_CHASSI-LABELED_MOTOR-LABELED"
        dict_global_config["output"] = dict_global_config["output"].replace('\\','/')
        os.makedirs(dict_global_config["output"], exist_ok=True)
        save_json(dict_global_config, path_config_global)
    # sys.exit(0)


    print(f"Scanning input folder: {dict_global_config['input']}")
    all_vistorias_subdirs = load_all_subdirs(dict_global_config["input"])
    print(f"    Found {len(all_vistorias_subdirs)} vistorias in input folder")
    # sys.exit(0)


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
            print(f"Num Placas Anotadas: {len(dict_global_config['labeled_folders'])}")
            print(f"{idx_vistoria_subdir}/{len(all_vistorias_subdirs)}: Processing vistoria subdir: {vistoria_subdir}")


            json_pattern = os.path.join(vistoria_subdir, "dados_vistoria*.json").replace('\\','/')
            json_path = glob.glob(json_pattern)
            assert len(json_path) == 1, f"Expected exactly one JSON file in {vistoria_subdir}, but found {len(json_path)}"
            json_path = json_path[0]
            print(f"    Loading JSON data from: {json_path}")
            dados_vistoria_orig = load_json(json_path)
            dados_vistoria_corrected = {}
            for idx_key_vistoria, key_vistoria in enumerate(dados_vistoria_orig.keys()):
                if key_vistoria:
                    if key_vistoria.lower().startswith("URL ") and not dados_vistoria_orig[key_vistoria] is None:
                        dados_vistoria_corrected[key_vistoria] = dados_vistoria_orig[key_vistoria].split('/')[-1]
                    else:
                        dados_vistoria_corrected[key_vistoria] = dados_vistoria_orig[key_vistoria]

            keys_target = ["URL Chassi", "URL Motor"]
            images_folder = os.path.join(vistoria_subdir, "imgs").replace('\\','/')
            imgs_vistoria = {}
            print(f"    Loading images of vistoria:")
            for idx_key_vistoria, key_vistoria in enumerate(dados_vistoria_corrected.keys()):
                for key_target in keys_target:
                    if key_vistoria.lower().startswith(key_target.lower()):
                        img_filename = dados_vistoria_corrected[key_vistoria]
                        print(f"        {key_vistoria}: {img_filename}")
                        img_path = os.path.join(images_folder, img_filename).replace('\\','/')
                        if os.path.isfile(img_path):
                            imgs_vistoria[key_vistoria] = Image.open(img_path)
                            display_single_image(Image.open(img_path), key_vistoria, img_filename)
                        continue

            # print("imgs_vistoria:", imgs_vistoria)
            # sys.exit(0)


            '''
            if not "primeiro" in dados_vistoria_corrected["Observações"].lower():
                images_folder = os.path.join(vistoria_subdir, "imgs").replace('\\','/')
                imgs_vistoria = {}
                print(f"    Loading images of vistoria:")
                for idx_key_vistoria, key_vistoria in enumerate(dados_vistoria_corrected.keys()):
                    if key_vistoria.startswith("URL "):
                        img_filename = dados_vistoria_corrected[key_vistoria]
                        print(f"        {key_vistoria}: {img_filename}")
                        img_path = os.path.join(images_folder, img_filename).replace('\\','/')
                        if os.path.isfile(img_path):
                            # imgs_vistoria[dados_vistoria_corrected[key_vistoria]] = Image.open(img_path)
                            imgs_vistoria[key_vistoria] = Image.open(img_path)
                        else:
                            # raise FileNotFoundError(f"Image file not found: {img_path}")
                            missing_img = make_missing_image()
                            imgs_vistoria[key_vistoria] = missing_img

                # Launch GUI for labeling
                print("    Launching GUI for labeling...")
                # dict_selected_labeled_imgs = show_gui_for_labeling_licenseplate_chassi_engine(dados_vistoria_corrected, imgs_vistoria)
                dict_selected_labeled_imgs = show_gui_for_labeling_license_plate(dados_vistoria_corrected,
                                                                                 imgs_vistoria,
                                                                                 title=f"{os.path.basename(vistoria_subdir)}   -   Select license plate image")
                print("        dict_selected_labeled_imgs:", dict_selected_labeled_imgs)
                dados_vistoria_corrected.update(dict_selected_labeled_imgs)
                print("        dados_vistoria_corrected:", dados_vistoria_corrected)


                # Save results to output folder
                path_output_vistoria = os.path.join(dict_global_config["output"], os.path.basename(vistoria_subdir)).replace('\\','/')
                os.makedirs(path_output_vistoria, exist_ok=True)
                print(f"    Saving output labeled JSON data to: {path_output_vistoria}")
                json_output_path = os.path.join(path_output_vistoria, "dados_vistoria_LABELED.json").replace('\\','/')
                save_json(dados_vistoria_corrected, json_output_path)
                imgs_input_folder  = os.path.join(vistoria_subdir, "imgs").replace('\\','/')
                imgs_output_folder = os.path.join(path_output_vistoria, "imgs").replace('\\','/')
                print(f"    Copying output images to: {imgs_output_folder}")
                shutil.copytree(imgs_input_folder, imgs_output_folder, dirs_exist_ok=True)


                # Save labeling history
                dict_global_config["labeled_folders"].append({os.path.basename(vistoria_subdir): str(datetime.now())})
                save_json(dict_global_config, path_config_global)
            '''
        
        else:
            print(f"{idx_vistoria_subdir}/{len(all_vistorias_subdirs)}: Skipping vistoria subdir: {vistoria_subdir}")
        
            

        # sys.exit(0)



    print("\nFinished processing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
