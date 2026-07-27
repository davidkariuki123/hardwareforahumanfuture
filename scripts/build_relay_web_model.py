"""Build the dimensionally authoritative Relay Thin web GLB in Blender."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / ".build" / "relay-web-parts"
OUTPUT = ROOT / "assets" / "models" / "relay-thin-authoritative.glb"
PREVIEW = ROOT / ".build" / "relay-thin-authoritative-preview.png"
BLEND = ROOT / ".build" / "relay-thin-authoritative.blend"
FONT = Path("/System/Library/Fonts/SFNS.ttf")

MM_TO_SCENE = 0.01
MODEL_CENTER_MM = (31.0, 44.0, 2.575)


def srgb(hex_colour: str) -> tuple[float, float, float, float]:
    value = hex_colour.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)) + (1.0,)


def material(name: str, colour: str, metallic: float, roughness: float):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = srgb(colour)
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = srgb(colour)
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    return mat


def import_part(stem: str, name: str, mat) -> bpy.types.Object:
    bpy.ops.wm.stl_import(filepath=str(PARTS / f"{stem}.stl"))
    obj = bpy.context.selected_objects[0]
    obj.name = name
    obj.scale = (MM_TO_SCENE,) * 3
    obj.location = tuple(-v * MM_TO_SCENE for v in MODEL_CENTER_MM)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def add_wordmark(mat) -> bpy.types.Object:
    bpy.ops.object.text_add(location=(0.0, -0.055, 0.0262))
    wordmark = bpy.context.object
    wordmark.name = "RELAY engraved wordmark"
    wordmark.data.body = "R E L A Y"
    wordmark.data.align_x = "CENTER"
    wordmark.data.align_y = "CENTER"
    wordmark.data.size = 0.047
    wordmark.data.extrude = 0.00018
    wordmark.data.bevel_depth = 0.000035
    wordmark.data.bevel_resolution = 2
    if FONT.exists():
        wordmark.data.font = bpy.data.fonts.load(str(FONT))
    wordmark.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")
    return wordmark


def add_preview_camera() -> None:
    bpy.ops.object.camera_add(location=(1.18, -1.45, 1.42))
    camera = bpy.context.object
    camera.name = "Preview camera"
    bpy.context.scene.camera = camera

    direction = -camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.28


def add_area_light(name: str, location, energy: float, size: float, colour) -> None:
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.data.color = colour
    light.rotation_euler = (-math.pi / 5, 0, math.pi / 5)


def main() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    aluminum = material("RT-CMF-001 anodized aluminum", "#C8C5BF", 0.72, 0.48)
    polymer = material("RT-CMF-001 matched polymer", "#C8C5BF", 0.02, 0.58)
    seal = material("RT-CMF-001 matched LSR", "#BDBAB5", 0.0, 0.66)
    light = material("Status light guide", "#E8DCC6", 0.0, 0.24)
    engraving = material("Recessed RELAY engraving", "#817E78", 0.55, 0.54)

    product_objects = [
        import_part("phone-skin", "Phone-facing skin", polymer),
        import_part("midframe", "Aluminum perimeter midframe", aluminum),
        import_part("pressure-plate", "Solid-state pressure plate", aluminum),
        import_part("fixed-cap", "Fixed RF and acoustic cap", polymer),
        import_part("rf-window-left", "Left RF window", polymer),
        import_part("rf-window-right", "Right RF window", polymer),
        import_part("light-guide", "Dual-exit light guide", light),
        import_part("usb-seal", "USB-C environmental seal", seal),
        import_part("power-key-seal", "Recessed power-key boot", seal),
        add_wordmark(engraving),
    ]

    product = bpy.data.objects.new("Relay Thin — authoritative exterior", None)
    bpy.context.collection.objects.link(product)
    for obj in product_objects:
        obj.parent = product

    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    product.select_set(True)
    for obj in product_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = product

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )

    add_preview_camera()
    add_area_light("Key", (-1.8, -1.4, 2.6), 950, 2.2, (1.0, 0.91, 0.79))
    add_area_light("Fill", (1.6, -0.4, 1.7), 700, 2.0, (0.78, 0.86, 1.0))
    add_area_light("Rim", (0.0, 1.6, 2.1), 850, 1.6, (1.0, 0.96, 0.88))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(PREVIEW)
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.035, 0.035, 0.035)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
