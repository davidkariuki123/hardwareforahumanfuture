"""Build the design-authoritative Relay Thin web model in Blender.

The product render approved on 2026-07-27 is the exterior visual authority.
Mechanical dimensions remain bound to the Relay Thin production contract:
62 x 88 x 5.15 mm nominal.  This script creates one continuous hard-surface
object for the website animation; no camera-view raster handoff is involved.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "models" / "relay-thin-authoritative.glb"
PREVIEW = ROOT / ".build" / "relay-thin-authoritative-preview.png"
BLEND = ROOT / ".build" / "relay-thin-authoritative.blend"
FONT = Path("/System/Library/Fonts/SFNS.ttf")

MM = 0.01
WIDTH = 62.0 * MM
HEIGHT = 88.0 * MM
DEPTH = 5.15 * MM
CORNER_RADIUS = 7.2 * MM
PRESSURE_FACE_Z = DEPTH / 2 + 0.72 * MM + 0.55 * MM / 2


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


def rounded_prism(name: str, width: float, height: float, depth: float, radius: float, z: float, mat, segments: int = 12):
    """Create an exact rounded-rectangle extrusion without isotropic cube bevels."""
    radius = min(radius, width / 2, height / 2)
    cx = width / 2 - radius
    cy = height / 2 - radius
    outline = []
    for center_x, center_y, start_deg in (
        (cx, cy, 0),
        (-cx, cy, 90),
        (-cx, -cy, 180),
        (cx, -cy, 270),
    ):
        for step in range(segments + 1):
            angle = math.radians(start_deg + step * 90 / segments)
            outline.append((center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))

    bottom_z = z - depth / 2
    top_z = z + depth / 2
    vertices = [(x, y, bottom_z) for x, y in outline] + [(x, y, top_z) for x, y in outline]
    count = len(outline)
    faces = [tuple(reversed(range(count))), tuple(range(count, count * 2))]
    faces.extend((i, (i + 1) % count, (i + 1) % count + count, i + count) for i in range(count))

    mesh = bpy.data.meshes.new(f"{name} mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def box(name: str, dimensions, location, mat, bevel: float = 0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("Controlled edge radius", "BEVEL")
        modifier.width = bevel
        modifier.segments = 5
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    obj.data.materials.append(mat)
    return obj


def add_wordmark(mat):
    bpy.ops.object.text_add(location=(0.0, -0.050, PRESSURE_FACE_Z + 0.08 * MM))
    wordmark = bpy.context.object
    wordmark.name = "RELAY engraved wordmark"
    wordmark.data.body = "R E L A Y"
    wordmark.data.align_x = "CENTER"
    wordmark.data.align_y = "CENTER"
    wordmark.data.size = 0.044
    wordmark.data.extrude = 0.00012
    wordmark.data.bevel_depth = 0.000025
    wordmark.data.bevel_resolution = 2
    if FONT.exists():
        wordmark.data.font = bpy.data.fonts.load(str(FONT))
    wordmark.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")
    return wordmark


def add_microphone_line(mat):
    objects = []
    count = 12
    spacing = 1.75 * MM
    for index in range(count):
        x = (index - (count - 1) / 2) * spacing
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=20,
            radius=0.32 * MM,
            depth=0.10 * MM,
            location=(x, HEIGHT / 2 - 5.55 * MM, PRESSURE_FACE_Z + 0.055 * MM),
        )
        hole = bpy.context.object
        hole.name = f"Microphone perforation {index + 1:02d}"
        hole.data.materials.append(mat)
        objects.append(hole)
    return objects


def add_preview_camera():
    bpy.ops.object.camera_add(location=(1.12, -1.42, 1.35))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    camera.rotation_euler = (-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 1.22


def add_area_light(name: str, location, energy: float, size: float, colour):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.data.color = colour
    light.rotation_euler = (-math.pi / 5, 0, math.pi / 5)


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    face = material("Warm titanium pressure surface", "#91887D", 0.72, 0.46)
    frame = material("Warm titanium perimeter", "#777169", 0.84, 0.36)
    seam = material("Perimeter seam", "#77736D", 0.45, 0.56)
    aperture = material("Recessed apertures", "#393735", 0.18, 0.62)
    engraving = material("Recessed RELAY engraving", "#5F5A54", 0.52, 0.55)

    product_objects = []
    product_objects.append(rounded_prism("Relay structural frame", WIDTH, HEIGHT, DEPTH, CORNER_RADIUS, 0, frame))
    product_objects.append(rounded_prism("Dark perimeter seam", WIDTH - 1.20 * MM, HEIGHT - 1.20 * MM, 0.35 * MM, CORNER_RADIUS - 0.55 * MM, DEPTH / 2 + 0.40 * MM, seam))
    product_objects.append(rounded_prism("Solid-state pressure surface", WIDTH - 1.85 * MM, HEIGHT - 1.85 * MM, 0.55 * MM, CORNER_RADIUS - 0.85 * MM, DEPTH / 2 + 0.72 * MM, face))

    # The quiet top notch, microphone line, bottom USB-C mouth and recessed
    # side power key reproduce the approved industrial-design render.
    product_objects.append(box("Top acoustic notch", (12.0 * MM, 0.90 * MM, 0.08 * MM), (0, HEIGHT / 2 - 1.02 * MM, PRESSURE_FACE_Z + 0.045 * MM), frame, 0.20 * MM))
    product_objects.extend(add_microphone_line(aperture))
    product_objects.append(box("USB-C aperture", (11.0 * MM, 0.55 * MM, 1.45 * MM), (0, -HEIGHT / 2 - 0.10 * MM, -0.55 * MM), aperture, 0.60 * MM))
    product_objects.append(box("Recessed power key", (0.55 * MM, 7.4 * MM, 1.45 * MM), (WIDTH / 2 + 0.10 * MM, -2.5 * MM, 0.0), seam, 0.42 * MM))
    product_objects.append(add_wordmark(engraving))

    product = bpy.data.objects.new("Relay Thin — approved exterior", None)
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
    add_area_light("Key", (-1.8, -1.4, 2.6), 430, 2.2, (1.0, 0.91, 0.79))
    add_area_light("Fill", (1.6, -0.4, 1.7), 260, 2.0, (0.78, 0.86, 1.0))
    add_area_light("Rim", (0.0, 1.6, 2.1), 350, 1.6, (1.0, 0.96, 0.88))

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
