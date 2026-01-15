#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
import sys
import os
from pathlib import Path
import json
from PIL import Image
from datetime import datetime

import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import tkinter.font as tkfont
from typing import Any
from PIL import Image, ImageTk
    

__version__ = "0.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, required=True,  default="D:/Datasets/veiculos_vistoria_laudo_chassi_v1_DADOS_BRUTOS/qualit/vistorias_qualit/vistorias_download")
    parser.add_argument("-o", "--output", type=str, required=True, default="D:/Datasets/veiculos_vistoria_laudo_chassi_v2_LABELED/qualit_LABELED/vistorias_qualit_LABELED/vistorias_download_LABELED")
    return parser.parse_args(argv)


def make_default_global_config(path_config_global = "config_global.json") -> None:
    default_config = {
        "input":           "",
        "output":          "",
        "labeled_folders": []
    }
    save_json(default_config, path_config_global)


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





def show_gui_for_labeling_licenseplate_chassi_engine(
    dados_vistoria: dict,
    imgs_vistoria: dict[str, Image.Image],
) -> dict[str, str]:
    SLOT_LABELS = ["URL Placa LABELED", "URL Chassi LABELED", "URL Motor LABELED"]
    SLOT_COLORS = {
        "URL Placa LABELED": "#f1c40f",   # yellow/gold
        "URL Chassi LABELED": "#2ecc71",  # green
        "URL Motor LABELED": "#3498db",   # blue
    }

    if not imgs_vistoria:
        return {lab: "" for lab in SLOT_LABELS}

    root = tk.Tk()
    root.title("Select 3 images for labels")

    # ---- Size window relative to screen ----
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    win_w = max(900, int(screen_w * 0.90))
    win_h = max(650, int(screen_h * 0.85))

    x = max(0, (screen_w - win_w) // 2)
    y = min(10, (screen_h - win_h) // 2)
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    # --- State ---
    slot_to_key: dict[str, str | None] = {lab: None for lab in SLOT_LABELS}
    active_slot: str | None = None

    # keep PhotoImages alive
    thumb_cache: dict[str, ImageTk.PhotoImage] = {}
    slot_thumb_cache: dict[str, ImageTk.PhotoImage] = {}

    tile_widgets: dict[str, tk.Frame] = {}
    img_labels: dict[str, tk.Label] = {}

    slot_frames: dict[str, tk.Frame] = {}
    slot_img_labels: dict[str, tk.Label] = {}
    slot_text_vars: dict[str, tk.StringVar] = {}

    # --- Fonts ---
    grid_label_font = tkfont.Font(root=root, size=11, weight="bold")
    slot_title_font = tkfont.Font(root=root, size=11, weight="bold")
    slot_filename_font = tkfont.Font(root=root, size=10, weight="normal")

    # --- Top bar ---
    top = tk.Frame(root)
    top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 6))

    info_var = tk.StringVar(value="Click a slot above, then click an image below to assign it.")
    tk.Label(top, textvariable=info_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

    assigned_var = tk.StringVar(value="Assigned (0/3)")
    tk.Label(top, textvariable=assigned_var, anchor="e").pack(side=tk.RIGHT)

    # --- Slots row (FIRST ROW) ---
    slots_row = tk.Frame(root)
    slots_row.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

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

    # Mouse wheel
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

    # --- Grid layout ---
    COLS = 4
    PADX = 10
    PADY = 10

    keys = list(imgs_vistoria.keys())
    pil_cache: dict[str, Image.Image] = {k: imgs_vistoria[k] for k in keys}

    def _make_thumbnail(img: Image.Image, max_size: tuple[int, int]) -> ImageTk.PhotoImage:
        im = img.copy()
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        im.thumbnail(max_size, Image.LANCZOS)
        return ImageTk.PhotoImage(im)

    def _filename_for_key(key: str) -> str:
        try:
            return os.path.basename(dados_vistoria[key])
        except Exception:
            return os.path.basename(str(key))

    def _assigned_count() -> int:
        return sum(1 for v in slot_to_key.values() if v is not None)

    def _update_assigned_label():
        assigned_var.set(f"Assigned ({_assigned_count()}/3)")

    def _slot_for_key(key: str) -> str | None:
        for lab, k in slot_to_key.items():
            if k == key:
                return lab
        return None

    def _first_empty_slot() -> str | None:
        for lab in SLOT_LABELS:
            if slot_to_key[lab] is None:
                return lab
        return None

    # --- Compute thumbnail sizes ---
    def _compute_grid_thumb_size() -> tuple[int, int]:
        cw = canvas.winfo_width()
        if cw <= 2:
            cw = win_w - 40

        scrollbar_w = 18
        available = max(300, cw - scrollbar_w)
        total_pad = COLS * (2 * PADX) + 10
        tile_w = max(160, int((available - total_pad) / COLS))

        thumb_w = tile_w
        # thumb_h = int(tile_w * 0.72)
        thumb_h = int(tile_w * 0.5)
        return thumb_w, thumb_h

    def _compute_slot_thumb_size() -> tuple[int, int]:
        # Use the slots_row width to give slots a "grid-like" comfortable size.
        sw = slots_row.winfo_width()
        if sw <= 2:
            sw = win_w - 40

        # 3 slots, with grid padx=10 and some internal padding
        # subtract approximate spacing between the 3 frames
        slot_frame_w = int((sw - 2 * 10 * 3 - 20) / 3)  # rough but stable
        slot_frame_w = max(240, slot_frame_w)

        # allow some room for title + filename lines and padding
        thumb_w = max(220, slot_frame_w - 30)
        # thumb_h = int(thumb_w * 0.72)
        thumb_h = int(thumb_w * 0.4)
        return thumb_w, thumb_h

    # --- Slot visuals ---
    def _set_slot_active_visual(label: str, is_active: bool):
        frame = slot_frames[label]
        color = SLOT_COLORS[label]
        frame.configure(
            highlightbackground=color,
            highlightcolor=color,
            highlightthickness=4 if is_active else 2,
        )

    def _refresh_all_slot_active_visuals():
        for lab in SLOT_LABELS:
            _set_slot_active_visual(lab, lab == active_slot)

    # --- Tile visuals based on slot assignment ---
    def _highlight_tiles_from_slots():
        # Reset all tiles
        for k, tile in tile_widgets.items():
            tile.configure(
                highlightthickness=1,
                highlightbackground="#b0b0b0",
                highlightcolor="#b0b0b0",
                bg=tile.master.cget("bg"),
            )

        # Color assigned tiles by their slot
        for lab, key in slot_to_key.items():
            if key is None:
                continue
            tile = tile_widgets.get(key)
            if tile:
                color = SLOT_COLORS[lab]
                tile.configure(
                    highlightthickness=4,
                    highlightbackground=color,
                    highlightcolor=color,
                    bg="#eef6ff",
                )

    # --- Slot UI update ---
    def _update_slot_ui(label: str):
        key = slot_to_key[label]
        if key is None:
            slot_img_labels[label].configure(image="", text="(click to choose)", compound="center")
            slot_text_vars[label].set("")
            slot_thumb_cache.pop(label, None)
            return

        try:
            tw, th = _compute_slot_thumb_size()
            thumb = _make_thumbnail(pil_cache[key], (tw, th))
            slot_thumb_cache[label] = thumb
            slot_img_labels[label].configure(image=thumb, text="", compound="center")
        except Exception:
            slot_img_labels[label].configure(image="", text="(preview failed)", compound="center")
            slot_thumb_cache.pop(label, None)

        slot_text_vars[label].set(_filename_for_key(key))

    def _update_all_slots_ui():
        for lab in SLOT_LABELS:
            _update_slot_ui(lab)
        _update_assigned_label()
        _highlight_tiles_from_slots()
        _refresh_all_slot_active_visuals()

    # --- Actions ---
    def _on_slot_click(label: str):
        nonlocal active_slot
        active_slot = None if active_slot == label else label
        _refresh_all_slot_active_visuals()

    def _assign_key_to_slot(label: str, key: str):
        prev = _slot_for_key(key)
        if prev is not None and prev != label:
            slot_to_key[prev] = None
            _update_slot_ui(prev)

        slot_to_key[label] = key
        _update_slot_ui(label)
        _update_assigned_label()
        _highlight_tiles_from_slots()

    def _unassign_slot(label: str):
        slot_to_key[label] = None
        _update_slot_ui(label)
        _update_assigned_label()
        _highlight_tiles_from_slots()

    def _on_tile_click(key: str):
        nonlocal active_slot

        target = active_slot
        if target is None:
            target = _first_empty_slot()
            if target is None:
                messagebox.showwarning("All slots filled", "Click a slot to replace its image.")
                return

        if _slot_for_key(key) == target:
            _unassign_slot(target)
            return

        _assign_key_to_slot(target, key)

    # --- Build slots row ---
    def _build_slots_row():
        for i, lab in enumerate(SLOT_LABELS):
            frame = tk.Frame(
                slots_row,
                bd=0,
                relief="flat",
                padx=8,
                pady=8,
                highlightthickness=2,
                highlightbackground=SLOT_COLORS[lab],
                highlightcolor=SLOT_COLORS[lab],
            )
            frame.grid(row=0, column=i, padx=10, pady=0, sticky="nsew")
            slots_row.grid_columnconfigure(i, weight=1)

            slot_frames[lab] = frame

            tk.Label(frame, text=lab, font=slot_title_font, anchor="center").pack(fill=tk.X)

            # IMPORTANT: no width/height here; let it grow and show the image big
            img_lbl = tk.Label(
                frame,
                text="(click to choose)",
                bd=0,
                relief="flat",
                cursor="hand2",
                compound="center",
            )
            img_lbl.pack(fill=tk.BOTH, expand=True, pady=(6, 4))
            slot_img_labels[lab] = img_lbl

            fn_var = tk.StringVar(value="")
            slot_text_vars[lab] = fn_var
            tk.Label(frame, textvariable=fn_var, font=slot_filename_font, anchor="center").pack(fill=tk.X)

            def bind_all(widget):
                widget.bind("<Button-1>", lambda _e, _lab=lab: _on_slot_click(_lab))

            bind_all(frame)
            for child in frame.winfo_children():
                bind_all(child)

    _build_slots_row()

    # --- Build grid ---
    def _bind_tile_click(widget, _key: str):
        widget.bind("<Button-1>", lambda _e: _on_tile_click(_key))

    def _build_grid():
        thumb_w, thumb_h = _compute_grid_thumb_size()

        for idx, key in enumerate(keys):
            r = idx // COLS
            c = idx % COLS

            tile = tk.Frame(
                grid_frame,
                bd=0,
                relief="flat",
                highlightthickness=1,
                highlightbackground="#b0b0b0",
                highlightcolor="#b0b0b0",
            )
            tile.grid(row=r, column=c, padx=PADX, pady=PADY, sticky="n")
            tile_widgets[key] = tile

            try:
                thumb = _make_thumbnail(pil_cache[key], (thumb_w, thumb_h))
                thumb_cache[key] = thumb
                img_lbl = tk.Label(tile, image=thumb, cursor="hand2")
                img_lbl.pack()
                img_labels[key] = img_lbl
            except Exception as e:
                tk.Label(tile, text=f"Failed to load\n{key}\n{e}", justify="center", width=25, height=8).pack()

            tk.Label(
                tile,
                text=f"{key}",
                wraplength=max(180, thumb_w),
                justify="center",
                cursor="hand2",
                font=grid_label_font,
            ).pack(pady=(6, 0))

            _bind_tile_click(tile, key)
            for child in tile.winfo_children():
                _bind_tile_click(child, key)

    _build_grid()

    # Refresh thumbs after layout settles (grid + slots)
    def _refresh_thumbnails_once():
        # grid thumbs
        thumb_w, thumb_h = _compute_grid_thumb_size()
        for key, lbl in img_labels.items():
            try:
                thumb = _make_thumbnail(pil_cache[key], (thumb_w, thumb_h))
                thumb_cache[key] = thumb
                lbl.configure(image=thumb)
            except Exception:
                pass

        # slot thumbs (recompute sizes now that slots_row has a real width)
        for lab in SLOT_LABELS:
            if slot_to_key[lab] is not None:
                _update_slot_ui(lab)

        canvas.configure(scrollregion=canvas.bbox("all"))

    root.after(120, _refresh_thumbnails_once)

    # Also refresh slot thumbs if the window is resized (so previews stay big)
    def _on_root_resize(_event=None):
        for lab in SLOT_LABELS:
            if slot_to_key[lab] is not None:
                _update_slot_ui(lab)

    root.bind("<Configure>", lambda e: root.after_idle(_on_root_resize))

    # --- Bottom actions ---
    bottom = tk.Frame(root)
    bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

    result: dict[str, str] = {lab: "" for lab in SLOT_LABELS}

    def _confirm():
        if _assigned_count() != 3:
            messagebox.showinfo("Select 3 images", f"Please assign exactly 3 images (currently {_assigned_count()}).")
            return

        for lab in SLOT_LABELS:
            key = slot_to_key[lab]
            result[lab] = _filename_for_key(key) if key is not None else ""
        root.destroy()

    def _clear():
        nonlocal active_slot
        for lab in SLOT_LABELS:
            slot_to_key[lab] = None
        active_slot = None
        _update_all_slots_ui()

    def _on_close():
        for lab in SLOT_LABELS:
            key = slot_to_key[lab]
            result[lab] = _filename_for_key(key) if key is not None else ""
        root.destroy()

    tk.Button(bottom, text="Clear", command=_clear).pack(side=tk.LEFT)
    tk.Button(bottom, text="Confirm (3)", command=_confirm).pack(side=tk.RIGHT)

    root.protocol("WM_DELETE_WINDOW", _on_close)

    _update_all_slots_ui()
    root.mainloop()
    return result





def show_gui_for_labeling_license_plate(
    dados_vistoria: dict,
    imgs_vistoria: dict[str, Image.Image],
) -> dict[str, str]:
    SLOT_LABELS = ["URL Placa LABELED"]
    SLOT_COLORS = {"URL Placa LABELED": "#f1c40f"}  # yellow/gold (same as before)

    if not imgs_vistoria:
        return {lab: "" for lab in SLOT_LABELS}

    root = tk.Tk()
    root.title("Select license plate image")

    # ---- Size window relative to screen ----
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    win_w = max(900, int(screen_w * 0.90))
    win_h = max(650, int(screen_h * 0.85))

    x = max(0, (screen_w - win_w) // 2)
    y = min(10, (screen_h - win_h) // 2)
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    # --- State ---
    slot_to_key: dict[str, str | None] = {SLOT_LABELS[0]: None}
    active_slot: str | None = None

    # keep PhotoImages alive
    thumb_cache: dict[str, ImageTk.PhotoImage] = {}
    slot_thumb_cache: dict[str, ImageTk.PhotoImage] = {}

    tile_widgets: dict[str, tk.Frame] = {}
    img_labels: dict[str, tk.Label] = {}

    slot_frames: dict[str, tk.Frame] = {}
    slot_img_labels: dict[str, tk.Label] = {}
    slot_text_vars: dict[str, tk.StringVar] = {}

    # --- Fonts ---
    grid_label_font = tkfont.Font(root=root, size=11, weight="bold")
    slot_title_font = tkfont.Font(root=root, size=11, weight="bold")
    slot_filename_font = tkfont.Font(root=root, size=10, weight="normal")

    # --- Top bar ---
    top = tk.Frame(root)
    top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 6))

    info_var = tk.StringVar(value="Click the slot above, then click an image below to assign it.")
    tk.Label(top, textvariable=info_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

    assigned_var = tk.StringVar(value="Assigned (0/1)")
    tk.Label(top, textvariable=assigned_var, anchor="e").pack(side=tk.RIGHT)

    # --- Slot row (FIRST ROW) ---
    slots_row = tk.Frame(root)
    slots_row.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))

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

    # Mouse wheel
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

    # --- Grid layout ---
    COLS = 4
    PADX = 10
    PADY = 10

    keys = list(imgs_vistoria.keys())
    pil_cache: dict[str, Image.Image] = {k: imgs_vistoria[k] for k in keys}

    def _make_thumbnail(img: Image.Image, max_size: tuple[int, int]) -> ImageTk.PhotoImage:
        im = img.copy()
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        im.thumbnail(max_size, Image.LANCZOS)
        return ImageTk.PhotoImage(im)

    def _filename_for_key(key: str) -> str:
        try:
            return os.path.basename(dados_vistoria[key])
        except Exception:
            return os.path.basename(str(key))

    def _assigned_count() -> int:
        return 1 if slot_to_key[SLOT_LABELS[0]] is not None else 0

    def _update_assigned_label():
        assigned_var.set(f"Assigned ({_assigned_count()}/1)")

    # --- Compute thumbnail sizes (same logic style as before) ---
    def _compute_grid_thumb_size() -> tuple[int, int]:
        cw = canvas.winfo_width()
        if cw <= 2:
            cw = win_w - 40

        scrollbar_w = 18
        available = max(300, cw - scrollbar_w)
        total_pad = COLS * (2 * PADX) + 10
        tile_w = max(160, int((available - total_pad) / COLS))

        thumb_w = tile_w
        # thumb_h = int(tile_w * 0.72)
        thumb_h = int(tile_w * 0.5)
        return thumb_w, thumb_h

    def _compute_slot_thumb_size() -> tuple[int, int]:
        # With 1 slot, use nearly the full available width
        sw = slots_row.winfo_width()
        if sw <= 2:
            sw = win_w - 40

        # subtract outer padding + internal margins
        slot_frame_w = max(420, sw - 40)
        thumb_w = max(320, slot_frame_w - 30)
        # thumb_h = int(thumb_w * 0.72)
        thumb_h = int(thumb_w * 0.08)
        return thumb_w, thumb_h

    # --- Slot visuals ---
    def _set_slot_active_visual(label: str, is_active: bool):
        frame = slot_frames[label]
        color = SLOT_COLORS[label]
        frame.configure(
            highlightbackground=color,
            highlightcolor=color,
            highlightthickness=4 if is_active else 2,
        )

    def _refresh_slot_active_visual():
        _set_slot_active_visual(SLOT_LABELS[0], active_slot == SLOT_LABELS[0])

    # --- Tile visuals based on assignment ---
    def _highlight_tiles():
        # Reset all tiles
        for _, tile in tile_widgets.items():
            tile.configure(
                highlightthickness=1,
                highlightbackground="#b0b0b0",
                highlightcolor="#b0b0b0",
                bg=tile.master.cget("bg"),
            )

        # Color assigned tile
        assigned_key = slot_to_key[SLOT_LABELS[0]]
        if assigned_key is not None:
            tile = tile_widgets.get(assigned_key)
            if tile:
                color = SLOT_COLORS[SLOT_LABELS[0]]
                tile.configure(
                    highlightthickness=4,
                    highlightbackground=color,
                    highlightcolor=color,
                    bg="#eef6ff",
                )

    # --- Slot UI update ---
    def _update_slot_ui():
        lab = SLOT_LABELS[0]
        key = slot_to_key[lab]
        if key is None:
            slot_img_labels[lab].configure(image="", text="(click to choose)", compound="center")
            slot_text_vars[lab].set("")
            slot_thumb_cache.pop(lab, None)
            return

        try:
            tw, th = _compute_slot_thumb_size()
            thumb = _make_thumbnail(pil_cache[key], (tw, th))
            slot_thumb_cache[lab] = thumb
            slot_img_labels[lab].configure(image=thumb, text="", compound="center")
        except Exception:
            slot_img_labels[lab].configure(image="", text="(preview failed)", compound="center")
            slot_thumb_cache.pop(lab, None)

        slot_text_vars[lab].set(_filename_for_key(key))

    def _refresh_ui():
        _update_slot_ui()
        _update_assigned_label()
        _highlight_tiles()
        _refresh_slot_active_visual()

    # --- Actions ---
    def _on_slot_click():
        nonlocal active_slot
        lab = SLOT_LABELS[0]
        active_slot = None if active_slot == lab else lab
        _refresh_slot_active_visual()

    def _assign_key(key: str):
        lab = SLOT_LABELS[0]
        slot_to_key[lab] = key
        _update_slot_ui()
        _update_assigned_label()
        _highlight_tiles()

    def _unassign():
        lab = SLOT_LABELS[0]
        slot_to_key[lab] = None
        _update_slot_ui()
        _update_assigned_label()
        _highlight_tiles()

    def _on_tile_click(key: str):
        nonlocal active_slot
        lab = SLOT_LABELS[0]

        # If slot not active, we still allow assigning (convenience)
        if active_slot is None:
            active_slot = lab
            _refresh_slot_active_visual()

        # If clicking the assigned tile while active => unassign
        if slot_to_key[lab] == key and active_slot == lab:
            _unassign()
            return

        _assign_key(key)

    # --- Build slot row ---
    def _build_slot_row():
        lab = SLOT_LABELS[0]
        frame = tk.Frame(
            slots_row,
            bd=0,
            relief="flat",
            padx=8,
            pady=8,
            highlightthickness=2,
            highlightbackground=SLOT_COLORS[lab],
            highlightcolor=SLOT_COLORS[lab],
        )
        frame.grid(row=0, column=0, padx=10, pady=0, sticky="nsew")
        slots_row.grid_columnconfigure(0, weight=1)

        slot_frames[lab] = frame

        tk.Label(frame, text=lab, font=slot_title_font, anchor="center").pack(fill=tk.X)

        img_lbl = tk.Label(
            frame,
            text="(click to choose)",
            bd=0,
            relief="flat",
            cursor="hand2",
            compound="center",
        )
        img_lbl.pack(fill=tk.BOTH, expand=True, pady=(6, 4))
        slot_img_labels[lab] = img_lbl

        fn_var = tk.StringVar(value="")
        slot_text_vars[lab] = fn_var
        tk.Label(frame, textvariable=fn_var, font=slot_filename_font, anchor="center").pack(fill=tk.X)

        # click anywhere in slot to activate
        def bind_all(widget):
            widget.bind("<Button-1>", lambda _e: _on_slot_click())

        bind_all(frame)
        for child in frame.winfo_children():
            bind_all(child)

    _build_slot_row()

    # --- Build grid ---
    def _bind_tile_click(widget, _key: str):
        widget.bind("<Button-1>", lambda _e: _on_tile_click(_key))

    def _build_grid():
        thumb_w, thumb_h = _compute_grid_thumb_size()

        for idx, key in enumerate(keys):
            r = idx // COLS
            c = idx % COLS

            tile = tk.Frame(
                grid_frame,
                bd=0,
                relief="flat",
                highlightthickness=1,
                highlightbackground="#b0b0b0",
                highlightcolor="#b0b0b0",
            )
            tile.grid(row=r, column=c, padx=PADX, pady=PADY, sticky="n")
            tile_widgets[key] = tile

            try:
                thumb = _make_thumbnail(pil_cache[key], (thumb_w, thumb_h))
                thumb_cache[key] = thumb
                img_lbl = tk.Label(tile, image=thumb, cursor="hand2")
                img_lbl.pack()
                img_labels[key] = img_lbl
            except Exception as e:
                tk.Label(tile, text=f"Failed to load\n{key}\n{e}", justify="center", width=25, height=8).pack()

            tk.Label(
                tile,
                text=f"{key}",
                wraplength=max(180, thumb_w),
                justify="center",
                cursor="hand2",
                font=grid_label_font,
            ).pack(pady=(6, 0))

            _bind_tile_click(tile, key)
            for child in tile.winfo_children():
                _bind_tile_click(child, key)

    _build_grid()

    # Refresh thumbs after layout settles (grid + slot)
    def _refresh_thumbnails_once():
        # grid thumbs
        thumb_w, thumb_h = _compute_grid_thumb_size()
        for key, lbl in img_labels.items():
            try:
                thumb = _make_thumbnail(pil_cache[key], (thumb_w, thumb_h))
                thumb_cache[key] = thumb
                lbl.configure(image=thumb)
            except Exception:
                pass

        # slot thumb (after slots_row has a real width)
        if slot_to_key[SLOT_LABELS[0]] is not None:
            _update_slot_ui()

        canvas.configure(scrollregion=canvas.bbox("all"))

    root.after(120, _refresh_thumbnails_once)

    # Refresh slot thumbs on resize to keep it big
    def _on_root_resize(_event=None):
        if slot_to_key[SLOT_LABELS[0]] is not None:
            _update_slot_ui()

    root.bind("<Configure>", lambda e: root.after_idle(_on_root_resize))

    # --- Bottom actions ---
    bottom = tk.Frame(root)
    bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

    result: dict[str, str] = {SLOT_LABELS[0]: ""}

    def _confirm():
        lab = SLOT_LABELS[0]
        if slot_to_key[lab] is None:
            messagebox.showinfo("Select 1 image", "Please assign exactly 1 image.")
            return
        result[lab] = _filename_for_key(slot_to_key[lab])  # type: ignore[arg-type]
        root.destroy()

    def _clear():
        nonlocal active_slot
        slot_to_key[SLOT_LABELS[0]] = None
        active_slot = None
        _refresh_ui()

    '''
    def _on_close():
        lab = SLOT_LABELS[0]
        key = slot_to_key[lab]
        result[lab] = _filename_for_key(key) if key is not None else ""
        root.destroy()
    '''
    def _on_close():
        root.destroy()
        print("        User closed the window. Exiting program.")
        sys.exit(0)

    tk.Button(bottom, text="Clear", command=_clear).pack(side=tk.LEFT)
    tk.Button(bottom, text="Confirm (1)", command=_confirm).pack(side=tk.RIGHT)

    root.protocol("WM_DELETE_WINDOW", _on_close)

    _refresh_ui()
    root.mainloop()
    return result





def select_folder(title="Select a folder"):
    root = tk.Tk()
    root.withdraw()          # hide the main window
    root.attributes("-topmost", True)  # bring dialog to front (optional)
    folder = filedialog.askdirectory(title=title)
    root.destroy()
    return folder




def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)


    path_config_global = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_global.json")
    if not os.path.isfile(path_config_global):
        make_default_global_config(path_config_global)
    dict_global_config = load_json(path_config_global)

    if not os.path.isdir(dict_global_config["input"]):
        dict_global_config["input"] = select_folder("Select INPUT folder")
        save_json(dict_global_config, path_config_global)
    if not os.path.isdir(dict_global_config["output"]):
        dict_global_config["output"] = select_folder("Select OUTPUT folder")
        save_json(dict_global_config, path_config_global)


    if not os.path.isdir(args.input):
        print(f"Error: input folder '{args.input}' does not exist", file=sys.stderr)
        return 2
    os.makedirs(args.output, exist_ok=True)


    print(f"Scanning input folder: {args.input}")
    all_vistorias_subdirs = load_all_subdirs(args.input)
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
        if idx_vistoria_subdir > idx_current_vistoria:
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

            print("    Launching GUI for labeling...")
            # dict_selected_labeled_imgs = show_gui_for_labeling_licenseplate_chassi_engine(dados_vistoria_corrected, imgs_vistoria)
            dict_selected_labeled_imgs = show_gui_for_labeling_license_plate(dados_vistoria_corrected, imgs_vistoria)
            print("        dict_selected_labeled_imgs:", dict_selected_labeled_imgs)
            dados_vistoria_corrected.update(dict_selected_labeled_imgs)
            print("        dados_vistoria_corrected:", dados_vistoria_corrected)


            dict_global_config["labeled_folders"].append({os.path.basename(vistoria_subdir): str(datetime.now())})


            # TODO: Save results to output folder


            save_json(dict_global_config, path_config_global)

        else:
            print(f"{idx_vistoria_subdir}/{len(all_vistorias_subdirs)}: Skipping vistoria subdir: {vistoria_subdir}")

        # sys.exit(0)



    print("\nFinished processing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
