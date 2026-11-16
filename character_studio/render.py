"""Cena e render no Blender sem tela (Cycles em CPU)."""
from __future__ import annotations
import math
import numpy as np
import bpy
from mathutils import Vector

from .skeleton import Skeleton


def srgb(hexcolor: str):
    """'#rrggbb' -> cor linear RGBA."""
    h = hexcolor.lstrip("#")
    return tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4)) + (1.0,)


def reset_scene(samples=24, res=(1080, 1920)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    s.render.resolution_x, s.render.resolution_y = res
    s.view_settings.view_transform = "Standard"
    return s


def material(name, hexcolor, roughness=0.55):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb(hexcolor)
    b.inputs["Roughness"].default_value = roughness
    return m


def add_mesh(name, verts, faces, mat, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.materials.append(mat)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def studio_backdrop(color="#b9bbbe", size=12.0):
    """Fundo infinito cinza: chão que sobe em curva atrás do personagem."""
    prof = [(-size, 0.0)]
    r, y0 = 1.5, 3.0
    prof.append((y0, 0.0))
    for i in range(1, 13):
        a = math.pi / 2 * i / 12
        prof.append((y0 + r * math.sin(a), r - r * math.cos(a)))
    prof.append((y0 + r, size))
    verts, faces = [], []
    for y, z in prof:
        verts += [(-size, y, z), (size, y, z)]
    for i in range(len(prof) - 1):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    return add_mesh("fundo", verts, faces, material("fundo", color, 0.9), smooth=True)


def studio_lights():
    def area(name, loc, energy, size):
        d = bpy.data.lights.new(name, "AREA")
        d.energy, d.size = energy, size
        ob = bpy.data.objects.new(name, d)
        ob.location = loc
        ob.rotation_euler = (Vector((0, 0, 0.9)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(ob)
    area("principal", (-2.2, -3.0, 3.2), 200, 3.0)
    area("preenchimento", (2.6, -2.4, 1.6), 60, 4.0)
    area("contra", (0.5, 2.2, 2.8), 80, 2.0)
    w = bpy.data.worlds.new("mundo")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.52, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.25
    bpy.context.scene.world = w


def camera(location, target, ortho_scale=None, lens=50):
    d = bpy.data.cameras.new("camera")
    if ortho_scale:
        d.type = "ORTHO"
        d.ortho_scale = ortho_scale
    else:
        d.lens = lens
    ob = bpy.data.objects.new("camera", d)
    ob.location = location
    ob.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


# ---------------------------------------------------------------- ossos

SIDE_COLORS = {"C": "#e8e2d4", "L": "#e0892f", "R": "#3b82c4"}


def _octa(head, tail, width):
    """Osso em octaedro (como no Blender): ponta fina no fim, mais largo perto do início."""
    head = np.asarray(head, float); tail = np.asarray(tail, float)
    y = tail - head
    L = np.linalg.norm(y)
    y /= L
    ref = np.array([0, 0, 1.0]) if abs(y[2]) < 0.9 else np.array([1.0, 0, 0])
    x = np.cross(y, ref); x /= np.linalg.norm(x)
    z = np.cross(x, y)
    w = min(width, L * 0.22)
    m = head + y * L * 0.12
    v = [head, m + x * w, m + z * w, m - x * w, m - z * w, tail]
    f = [(0, 2, 1), (0, 3, 2), (0, 4, 3), (0, 1, 4), (5, 1, 2), (5, 2, 3), (5, 3, 4), (5, 4, 1)]
    return v, f


def _sphere(c, r, n=12):
    v, f = [], []
    for i in range(n + 1):
        t = math.pi * i / n
        for j in range(2 * n):
            ph = math.pi * j / n
            v.append((c[0] + r * math.sin(t) * math.cos(ph), c[1] + r * math.sin(t) * math.sin(ph), c[2] + r * math.cos(t)))
    for i in range(n):
        for j in range(2 * n):
            a = i * 2 * n + j; b = i * 2 * n + (j + 1) % (2 * n)
            f.append((a, a + 2 * n, b + 2 * n, b))
    return v, f


def add_skeleton_visual(sk: Skeleton, width=0.022):
    """Desenha os ossos como octaedros e as articulações como esferas, coloridos por lado."""
    mats = {k: material(f"osso_{k}", c, 0.5) for k, c in SIDE_COLORS.items()}
    joint = material("articulacao", "#2b2d33", 0.4)
    objs = []
    for b in sk.bones.values():
        if b.role == "raiz":
            continue
        v, f = _octa(b.head, b.tail, width)
        objs.append(add_mesh(f"osso_{b.name}", v, f, mats[b.side]))
        v, f = _sphere(b.head, width * 0.62)
        objs.append(add_mesh(f"junta_{b.name}", v, f, joint, smooth=True))
        if not sk.children(b.name):
            v, f = _sphere(b.tail, width * 0.4)
            objs.append(add_mesh(f"ponta_{b.name}", v, f, joint, smooth=True))
    return objs
