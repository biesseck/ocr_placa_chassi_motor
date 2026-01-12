#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
import os
from pathlib import Path
import json
from PIL import Image

from typing import Dict, Any
import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont
from PIL import ImageTk
    

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


def show_gui_for_labeling(dados_vistoria: dict, imgs_vistoria: dict[str, Image.Image]) -> dict:
    return dados_vistoria



def show_gui_for_labeling(
    dados_vistoria: dict,
    imgs_vistoria: dict[str, Image.Image],
) -> dict:
    """
    GUI to select exactly 3 images from imgs_vistoria (dict key = image key / id).
    - Window auto-sizes to a percentage of the user's screen.
    - Thumbnail size is computed from available window width and the number of columns.
    - Shows both the dict key and a "filename" (basename of the key) in a larger/bold font.

    Returns:
      {
        "dados_vistoria": <original>,
        "selected_filenames": [<3 selected keys in order>]   # keys of imgs_vistoria
      }
    """
    if not imgs_vistoria:
        return {"dados_vistoria": dados_vistoria, "selected_filenames": []}

    root = tk.Tk()
    root.title("Select 3 images")

    # ---- Size window relative to screen ----
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    # Use ~90% of screen, with sane minimums
    win_w = max(900, int(screen_w * 0.90))
    win_h = max(650, int(screen_h * 0.85))

    # Center the window
    x = max(0, (screen_w - win_w) // 2)
    y = min(10, (screen_h - win_h) // 2)
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    # --- State ---
    selected: list[str] = []
    thumb_cache: dict[str, ImageTk.PhotoImage] = {}
    tile_widgets: dict[str, tk.Frame] = {}
    img_labels: dict[str, tk.Label] = {}

    # --- Fonts (bigger + bold) ---
    label_font = tkfont.Font(root=root, size=11, weight="bold")  # slightly bigger, bold

    # --- Top bar ---
    top = tk.Frame(root)
    top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 6))

    info_var = tk.StringVar(value="Click to select up to 3 images.")
    info_lbl = tk.Label(top, textvariable=info_var, anchor="w")
    info_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    selected_var = tk.StringVar(value="Selected (0/3): ")
    selected_lbl = tk.Label(top, textvariable=selected_var, anchor="e")
    selected_lbl.pack(side=tk.RIGHT)

    # --- Scrollable area ---
    container = tk.Frame(root)
    container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    canvas = tk.Canvas(container, highlightthickness=0)
    vsb = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    grid_frame = tk.Frame(canvas)
    grid_window = canvas.create_window((0, 0), window=grid_frame, anchor="nw")

    def _on_frame_configure(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(event):
        canvas.itemconfigure(grid_window, width=event.width)

    grid_frame.bind("<Configure>", _on_frame_configure)
    canvas.bind("<Configure>", _on_canvas_configure)

    # Mouse wheel (Windows/macOS/Linux)
    def _on_mousewheel(event):
        if event.delta:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            if event.num == 4:
                canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                canvas.yview_scroll(3, "units")

    root.bind_all("<MouseWheel>", _on_mousewheel)
    root.bind_all("<Button-4>", _on_mousewheel)
    root.bind_all("<Button-5>", _on_mousewheel)

    # --- Layout + thumbnail sizing ---
    COLS = 4
    PADX = 10
    PADY = 10

    def _compute_thumb_size() -> tuple[int, int]:
        """
        Compute thumbnail size based on *current* canvas width.
        """
        # canvas.winfo_width() is 1 early on; fallback to window width
        cw = canvas.winfo_width()
        if cw <= 2:
            cw = win_w - 40

        # Approx scrollbar width
        scrollbar_w = 18

        # available width inside canvas for tiles
        available = max(300, cw - scrollbar_w)

        # total horizontal padding between tiles: each tile has left+right PADX in grid()
        # within 4 columns there are 8 PADX spaces, but grid pads apply per-widget.
        # We approximate with: COLS * 2*PADX plus a little margin.
        total_pad = COLS * (2 * PADX) + 10
        tile_w = max(160, int((available - total_pad) / COLS))

        # Keep a nice aspect ratio for thumbs
        thumb_w = tile_w
        thumb_h = int(tile_w * 0.72)  # ~ wide thumbnail
        return thumb_w, thumb_h

    def _make_thumbnail(img: Image.Image, max_size: tuple[int, int]) -> ImageTk.PhotoImage:
        im = img.copy()
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        im.thumbnail(max_size, Image.LANCZOS)
        return ImageTk.PhotoImage(im)

    # --- Selection helpers ---
    def _update_selected_label():
        selected_var.set(f"Selected ({len(selected)}/3): " + ", ".join(selected))

    def _set_tile_selected_visual(key: str, is_selected: bool):
        tile = tile_widgets.get(key)
        if not tile:
            return
        if is_selected:
            tile.configure(
                highlightbackground="#2a7fff",
                highlightcolor="#2a7fff",
                highlightthickness=3,
                bg="#eaf3ff",
            )
        else:
            tile.configure(highlightthickness=1, bg=tile.master.cget("bg"))

    def _toggle_selection(key: str):
        if key in selected:
            selected.remove(key)
            _set_tile_selected_visual(key, False)
            _update_selected_label()
            return

        if len(selected) >= 3:
            messagebox.showwarning("Limit reached", "You can select only 3 images. Unselect one to choose another.")
            return

        selected.append(key)
        _set_tile_selected_visual(key, True)
        _update_selected_label()

    # --- Build grid ---
    keys = list(imgs_vistoria.keys())

    # Keep the original PIL images around so we can rescale thumbs if needed
    pil_cache: dict[str, Image.Image] = {k: imgs_vistoria[k] for k in keys}

    def _bind_click(widget, _key: str):
        widget.bind("<Button-1>", lambda _e: _toggle_selection(_key))

    def _build_grid():
        thumb_w, thumb_h = _compute_thumb_size()

        for idx, key in enumerate(keys):
            r = idx // COLS
            c = idx % COLS

            tile = tk.Frame(grid_frame, bd=0, relief="flat", highlightthickness=1, highlightbackground="#b0b0b0", highlightcolor="#b0b0b0")
            tile.grid(row=r, column=c, padx=PADX, pady=PADY, sticky="n")
            tile_widgets[key] = tile

            try:
                thumb = _make_thumbnail(pil_cache[key], (thumb_w, thumb_h))
                thumb_cache[key] = thumb
                img_lbl = tk.Label(tile, image=thumb, cursor="hand2")
                img_lbl.pack()
                img_labels[key] = img_lbl
            except Exception as e:
                err = tk.Label(tile, text=f"Failed to load\n{key}\n{e}", justify="center", width=25, height=8)
                err.pack()

            # Show both: dict key + filename (basename of the key)
            # filename = os.path.basename(key)
            filename = os.path.basename(dados_vistoria[key]) 
            # text = f"Key: {key}\nFile: {filename}"
            # text = f"{key}\n{filename}"
            text = f"{key}"
            name_lbl = tk.Label(
                tile,
                text=text,
                wraplength=max(180, thumb_w),
                justify="center",
                cursor="hand2",
                font=label_font,
            )
            name_lbl.pack(pady=(6, 0))

            _bind_click(tile, key)
            for child in tile.winfo_children():
                _bind_click(child, key)

    _build_grid()

    # Optional: rescale thumbs once after first layout is stable (helps get correct canvas width)
    def _refresh_thumbnails_once():
        thumb_w, thumb_h = _compute_thumb_size()
        changed_any = False
        for key, lbl in img_labels.items():
            try:
                thumb = _make_thumbnail(pil_cache[key], (thumb_w, thumb_h))
                thumb_cache[key] = thumb
                lbl.configure(image=thumb)
                changed_any = True
            except Exception:
                pass
        if changed_any:
            canvas.configure(scrollregion=canvas.bbox("all"))

    root.after(80, _refresh_thumbnails_once)

    # --- Bottom actions ---
    bottom = tk.Frame(root)
    bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

    result: Dict[str, Any] = {"dados_vistoria": dados_vistoria, "selected_filenames": []}

    def _confirm():
        if len(selected) != 3:
            messagebox.showinfo("Select 3 images", f"Please select exactly 3 images (currently {len(selected)}).")
            return
        result["selected_filenames"] = selected.copy()
        root.destroy()

    def _clear():
        for k in list(selected):
            _set_tile_selected_visual(k, False)
        selected.clear()
        _update_selected_label()

    def _on_close():
        # Return what is selected (possibly <3) if user closes.
        result["selected_filenames"] = selected.copy()
        root.destroy()

    tk.Button(bottom, text="Clear", command=_clear).pack(side=tk.LEFT)
    tk.Button(bottom, text="Confirm (3)", command=_confirm).pack(side=tk.RIGHT)

    root.protocol("WM_DELETE_WINDOW", _on_close)

    _update_selected_label()
    root.mainloop()
    return result






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
                    # imgs_vistoria[dados_vistoria_corrected[key_vistoria]] = Image.open(img_path)
                    imgs_vistoria[key_vistoria] = Image.open(img_path)
                else:
                    raise FileNotFoundError(f"Image file not found: {img_path}")

        show_gui_for_labeling(dados_vistoria_corrected, imgs_vistoria)

        print("-----------")
        # sys.exit(0)


    print("\nFinished processing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
