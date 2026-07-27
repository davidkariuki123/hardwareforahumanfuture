"""Export the authoritative Relay Thin exterior solids for web rendering.

Run with the Python bundled inside FreeCAD so the FCStd source remains the
single geometry authority.  No exterior dimension is reconstructed here.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import FreeCAD as App
import Mesh


EXTERIOR_OBJECTS = {
    "PhoneSkin": "phone-skin",
    "Midframe": "midframe",
    "PressurePlate": "pressure-plate",
    "FixedCap": "fixed-cap",
    "RFWindowLeft": "rf-window-left",
    "RFWindowRight": "rf-window-right",
    "LightGuide": "light-guide",
    "USBSeal": "usb-seal",
    "PowerKeySeal": "power-key-seal",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    document = App.openDocument(str(args.source.resolve()))

    for object_name, file_stem in EXTERIOR_OBJECTS.items():
        obj = document.getObject(object_name)
        if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
            raise RuntimeError(f"Missing authoritative solid: {object_name}")
        Mesh.export([obj], str((args.output / f"{file_stem}.stl").resolve()))

    App.closeDocument(document.Name)


if __name__ == "__main__":
    main()
