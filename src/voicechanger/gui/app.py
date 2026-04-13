"""Desktop GUI for real-time effect authoring (tkinter)."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from voicechanger.effects import EFFECT_REGISTRY
from voicechanger.gui.logic import (
    GuiEffectState,
    build_profile_from_gui_state,
    param_to_slider,
    slider_to_param,
)
from voicechanger.profile import Profile, ProfileValidationError


class VoiceChangerApp:
    """Desktop profile authoring application."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Voice Changer — Profile Editor")
        self.root.geometry("800x600")

        self.effects: list[dict[str, Any]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        # Profile metadata frame
        meta_frame = ttk.LabelFrame(self.root, text="Profile Info", padding=10)
        meta_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(meta_frame, text="Name:").grid(row=0, column=0, sticky=tk.W)
        self.name_var = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.name_var, width=40).grid(row=0, column=1)

        ttk.Label(meta_frame, text="Author:").grid(row=1, column=0, sticky=tk.W)
        self.author_var = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.author_var, width=40).grid(row=1, column=1)

        ttk.Label(meta_frame, text="Description:").grid(row=2, column=0, sticky=tk.W)
        self.desc_var = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.desc_var, width=40).grid(row=2, column=1)

        # Effects frame
        effects_frame = ttk.LabelFrame(self.root, text="Effects Chain", padding=10)
        effects_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Effect type selector
        ctrl_frame = ttk.Frame(effects_frame)
        ctrl_frame.pack(fill=tk.X)

        ttk.Label(ctrl_frame, text="Add Effect:").pack(side=tk.LEFT)
        self.effect_type_var = tk.StringVar()
        effect_types = sorted(EFFECT_REGISTRY.keys())
        self.effect_dropdown = ttk.Combobox(
            ctrl_frame, textvariable=self.effect_type_var, values=effect_types, state="readonly"
        )
        self.effect_dropdown.pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Add", command=self._add_effect).pack(side=tk.LEFT)
        ttk.Button(ctrl_frame, text="Remove Last", command=self._remove_last_effect).pack(
            side=tk.LEFT, padx=5
        )

        # Scrollable effects area
        self.effects_canvas = tk.Canvas(effects_frame)
        scrollbar = ttk.Scrollbar(
            effects_frame, orient=tk.VERTICAL,
            command=self.effects_canvas.yview,
        )
        self.effects_inner = ttk.Frame(self.effects_canvas)

        self.effects_inner.bind(
            "<Configure>",
            lambda e: self.effects_canvas.configure(scrollregion=self.effects_canvas.bbox("all")),
        )
        self.effects_canvas.create_window((0, 0), window=self.effects_inner, anchor=tk.NW)
        self.effects_canvas.configure(yscrollcommand=scrollbar.set)

        self.effects_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons frame
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="Save Profile", command=self._save_profile).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Load Profile", command=self._load_profile).pack(
            side=tk.LEFT, padx=5
        )

        self.slider_widgets: list[dict[str, Any]] = []

    def _add_effect(self) -> None:
        effect_type = self.effect_type_var.get()
        if not effect_type:
            return

        schema = EFFECT_REGISTRY.get(effect_type, {})
        params = schema.get("params", {})

        frame = ttk.LabelFrame(self.effects_inner, text=effect_type, padding=5)
        frame.pack(fill=tk.X, pady=2)

        sliders: dict[str, tk.Scale] = {}
        for param_name, pschema in params.items():
            ttk.Label(frame, text=param_name).pack(anchor=tk.W)
            default_slider = param_to_slider(effect_type, param_name, pschema.get("default", 0.0))
            slider = tk.Scale(frame, from_=0, to=100, orient=tk.HORIZONTAL, length=300)
            slider.set(default_slider)
            slider.pack(fill=tk.X)
            sliders[param_name] = slider

        self.effects.append({"type": effect_type, "frame": frame})
        self.slider_widgets.append({"type": effect_type, "sliders": sliders})

    def _remove_last_effect(self) -> None:
        if self.effects:
            last = self.effects.pop()
            last["frame"].destroy()
            self.slider_widgets.pop()

    def _get_gui_effects(self) -> list[GuiEffectState]:
        result: list[GuiEffectState] = []
        for widget_info in self.slider_widgets:
            effect_type = widget_info["type"]
            params: dict[str, float] = {}
            for param_name, slider in widget_info["sliders"].items():
                params[param_name] = slider_to_param(effect_type, param_name, slider.get())
            result.append(GuiEffectState(type=effect_type, params=params))
        return result

    def _save_profile(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Profile name is required")
            return

        try:
            effects = self._get_gui_effects()
            profile = build_profile_from_gui_state(
                name=name,
                author=self.author_var.get().strip(),
                description=self.desc_var.get().strip(),
                effects=effects,
            )
        except ProfileValidationError as e:
            messagebox.showerror("Validation Error", str(e))
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{name}.json",
        )
        if path:
            profile.save(Path(path))
            messagebox.showinfo("Saved", f"Profile saved to {path}")

    def _load_profile(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return

        try:
            profile = Profile.load(Path(path))
        except (ProfileValidationError, Exception) as e:
            messagebox.showerror("Error", f"Failed to load profile: {e}")
            return

        # Populate UI
        self.name_var.set(profile.name)
        self.author_var.set(profile.author)
        self.desc_var.set(profile.description)

        # Clear existing effects
        for item in self.effects:
            item["frame"].destroy()
        self.effects.clear()
        self.slider_widgets.clear()

        # Add loaded effects
        for effect in profile.effects:
            self.effect_type_var.set(effect["type"])
            self._add_effect()
            # Set slider values
            if self.slider_widgets:
                widget = self.slider_widgets[-1]
                for param_name, value in effect.get("params", {}).items():
                    slider = widget["sliders"].get(param_name)
                    if slider:
                        slider_val = param_to_slider(effect["type"], param_name, float(value))
                        slider.set(slider_val)

    def run(self) -> None:
        self.root.mainloop()
