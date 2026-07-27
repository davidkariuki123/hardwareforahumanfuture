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
APPROVED_FACE_Z = DEPTH / 2 + 0.55 * MM

# The approved face render has a small asymmetric transparent gutter.  Its
# alpha>=0.5 silhouette is (10, 9)–(988, 1581) in a 988×1585 image.  Align the
# physical perimeter to that measured silhouette so it cannot protrude around
# the top/left edge as a doubled grey rim when viewed head-on.
FACE_IMAGE_WIDTH = 988.0
FACE_IMAGE_HEIGHT = 1585.0
FACE_ALPHA_LEFT = 10.0
FACE_ALPHA_TOP = 9.0
FACE_ALPHA_RIGHT = 988.0
FACE_ALPHA_BOTTOM = 1581.0
FRAME_WIDTH = WIDTH * (FACE_ALPHA_RIGHT - FACE_ALPHA_LEFT) / FACE_IMAGE_WIDTH
FRAME_HEIGHT = HEIGHT * (FACE_ALPHA_BOTTOM - FACE_ALPHA_TOP) / FACE_IMAGE_HEIGHT
FRAME_X = WIDTH * (((FACE_ALPHA_LEFT + FACE_ALPHA_RIGHT) / 2) - FACE_IMAGE_WIDTH / 2) / FACE_IMAGE_WIDTH
FRAME_Y = -HEIGHT * (((FACE_ALPHA_TOP + FACE_ALPHA_BOTTOM) / 2) - FACE_IMAGE_HEIGHT / 2) / FACE_IMAGE_HEIGHT


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


def rounded_prism(name: str, width: float, height: float, depth: float, radius: float, z: float, mat, segments: int = 12, x: float = 0, y: float = 0):
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
    vertices = [(px + x, py + y, bottom_z) for px, py in outline] + [(px + x, py + y, top_z) for px, py in outline]
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


def add_approved_front(mat):
    """Add a UV-mapped face whose runtime texture is the approved render.

    The website replaces this placeholder material with
    relay-thin-top-v2.webp.  That keeps the pressure surface pixel-faithful
    while the perimeter, USB-C aperture and side key remain real geometry.
    """
    vertices = (
        (-WIDTH / 2, -HEIGHT / 2, APPROVED_FACE_Z),
        (WIDTH / 2, -HEIGHT / 2, APPROVED_FACE_Z),
        (WIDTH / 2, HEIGHT / 2, APPROVED_FACE_Z),
        (-WIDTH / 2, HEIGHT / 2, APPROVED_FACE_Z),
    )
    mesh = bpy.data.meshes.new("ApprovedFront mesh")
    mesh.from_pydata(vertices, [], [(0, 1, 2, 3)])
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="ApprovedFrontUV")
    for loop, uv in zip(mesh.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv_layer.data[loop].uv = uv
    obj = bpy.data.objects.new("ApprovedFront", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


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

    face = material("Approved front placeholder", "#D8D2CA", 0.1, 0.54)
    frame = material("Warm titanium perimeter", "#AAA49B", 0.82, 0.30)
    seam = material("Perimeter seam", "#8D877F", 0.58, 0.42)
    aperture = material("Recessed apertures", "#393735", 0.18, 0.62)

    product_objects = []
    product_objects.append(rounded_prism("Relay structural frame", FRAME_WIDTH, FRAME_HEIGHT, DEPTH, CORNER_RADIUS, 0, frame, x=FRAME_X, y=FRAME_Y))
    product_objects.append(rounded_prism("Dark perimeter seam", FRAME_WIDTH - 1.20 * MM, FRAME_HEIGHT - 1.20 * MM, 0.35 * MM, CORNER_RADIUS - 0.55 * MM, DEPTH / 2 + 0.20 * MM, seam, x=FRAME_X, y=FRAME_Y))
    product_objects.append(add_approved_front(face))

    # The front texture already contains the exact pressure surface, notch,
    # microphone line and engraving.  Only true side-profile features belong
    # in geometry, preventing doubled or reinterpreted front details.
    product_objects.append(box("USB-C aperture", (11.0 * MM, 0.55 * MM, 1.45 * MM), (0, -HEIGHT / 2 - 0.10 * MM, -0.55 * MM), aperture, 0.60 * MM))
    product_objects.append(box("Recessed power key", (0.55 * MM, 7.4 * MM, 1.45 * MM), (WIDTH / 2 + 0.10 * MM, -2.5 * MM, 0.0), seam, 0.42 * MM))

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
