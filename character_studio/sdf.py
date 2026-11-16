"""Campos de distância (SDF) e conversão em malha.

Tudo em metros, Z para cima, personagem olhando para -Y, lado esquerdo em +X.
"""
from __future__ import annotations
import numpy as np
from skimage.measure import marching_cubes

F = np.float32


def v3(x):
    return np.asarray(x, dtype=F)


def sphere(p, c, r):
    return np.linalg.norm(p - v3(c), axis=-1) - r


def ellipsoid(p, c, r, frame=None):
    """Elipsoide aproximado. `frame` (3x3, colunas = eixos) orienta os raios."""
    q = p - v3(c)
    if frame is not None:
        q = q @ np.asarray(frame, dtype=F)
    r = v3(r)
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def capsule(p, a, b, ra, rb=None):
    """Cápsula de a até b; raio varia linearmente de ra a rb."""
    a = v3(a); b = v3(b)
    rb = ra if rb is None else rb
    pa = p - a
    ba = b - a
    h = np.clip((pa @ ba) / float(ba @ ba), 0.0, 1.0)
    d = np.linalg.norm(pa - h[..., None] * ba, axis=-1)
    return d - (ra + (rb - ra) * h)


def rbox(p, c, half, r=0.0, frame=None):
    """Caixa arredondada (meias-dimensões incluem o raio)."""
    q = p - v3(c)
    if frame is not None:
        q = q @ np.asarray(frame, dtype=F)
    q = np.abs(q) - (v3(half) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(axis=-1), 0) - r


def plane(p, point, normal):
    """Negativo do lado oposto à normal."""
    n = v3(normal); n = n / np.linalg.norm(n)
    return (p - v3(point)) @ n


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def union(*ds, k=0.0):
    out = ds[0]
    for d in ds[1:]:
        out = smin(out, d, k)
    return out


def mesh_from_sdf(fn, bounds, voxel=0.005):
    """Malha (verts, faces) da superfície fn(p)=0 dentro de bounds=((x0,y0,z0),(x1,y1,z1))."""
    lo = np.asarray(bounds[0], dtype=np.float64) - 2 * voxel
    hi = np.asarray(bounds[1], dtype=np.float64) + 2 * voxel
    n = np.ceil((hi - lo) / voxel).astype(int) + 1
    xs = (lo[0] + voxel * np.arange(n[0])).astype(F)
    ys = (lo[1] + voxel * np.arange(n[1])).astype(F)
    zs = (lo[2] + voxel * np.arange(n[2])).astype(F)
    vol = np.empty(n, dtype=F)
    yy, zz = np.meshgrid(ys, zs, indexing="ij")
    slab = np.empty((n[1], n[2], 3), dtype=F)
    slab[..., 1] = yy
    slab[..., 2] = zz
    for i, x in enumerate(xs):
        slab[..., 0] = x
        vol[i] = fn(slab.reshape(-1, 3)).reshape(n[1], n[2])
    if vol.min() >= 0 or vol.max() <= 0:
        raise ValueError("SDF sem superfície dentro dos limites")
    verts, faces, _, _ = marching_cubes(vol, 0.0, spacing=(voxel,) * 3)
    verts = verts + lo
    faces = faces.astype(np.int32)
    # garante normais para fora (volume positivo)
    a, b, c = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    if np.einsum("ij,ij->i", a, np.cross(b, c)).sum() < 0:
        faces = faces[:, ::-1].copy()
    return verts.astype(np.float64), faces


def segment_weights(verts, bones, sigma=0.02):
    """Pesos de pele por distância a segmentos de osso.

    bones: lista de (nome, a, b, raio). Peso ~ exp(-(d - dmin)/sigma), d = distância
    ao segmento menos o raio (>= 0). Devolve (nomes, W[n_verts, n_bones]).
    """
    p = verts.astype(F)
    ds = []
    for _, a, b, r in bones:
        a = v3(a); b = v3(b)
        if np.allclose(a, b):
            d = np.linalg.norm(p - a, axis=-1)
        else:
            d = capsule(p, a, b, 0.0)
        ds.append(np.maximum(d - r, 0.0))
    d = np.stack(ds, axis=1)
    w = np.exp(-(d - d.min(axis=1, keepdims=True)) / sigma)
    w[w < 0.02] = 0
    w /= w.sum(axis=1, keepdims=True)
    return [b[0] for b in bones], w.astype(np.float64)
