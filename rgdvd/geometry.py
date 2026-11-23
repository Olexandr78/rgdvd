"""Small procedural mesh helpers used by the game world and car model."""
from __future__ import annotations

import math
from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, NodePath,
)


def mesh(parent: NodePath, name: str, vertices: list[tuple[float, float, float]],
         triangles: list[tuple[int, int, int]], color: tuple[float, float, float, float],
         uvs: list[tuple[float, float]] | None = None,
         normals: list[tuple[float, float, float]] | None = None) -> NodePath:
    fmt = GeomVertexFormat.getV3n3t2()
    data = GeomVertexData(name, fmt, Geom.UHStatic)
    vertex_writer = GeomVertexWriter(data, "vertex")
    normal_writer = GeomVertexWriter(data, "normal")
    uv_writer = GeomVertexWriter(data, "texcoord")
    for index, point in enumerate(vertices):
        vertex_writer.addData3(*point)
        normal = normals[index] if normals is not None else (0.0, 0.0, 1.0)
        normal_writer.addData3(*normal)
        uv = uvs[index] if uvs is not None else (0.0, 0.0)
        uv_writer.addData2f(*uv)
    primitive = GeomTriangles(Geom.UHStatic)
    for a, b, c in triangles:
        primitive.addVertices(a, b, c)
        primitive.closePrimitive()
    geometry = Geom(data)
    geometry.addPrimitive(primitive)
    node = GeomNode(name)
    node.addGeom(geometry)
    path = parent.attachNewNode(node)
    path.setColor(*color)
    path.setTwoSided(True)
    return path


def box(parent: NodePath, name: str, center: tuple[float, float, float],
        size: tuple[float, float, float], color: tuple[float, float, float, float]) -> NodePath:
    cx, cy, cz = center
    sx, sy, sz = (value * 0.5 for value in size)
    corners = [
        (cx-sx, cy-sy, cz-sz), (cx+sx, cy-sy, cz-sz),
        (cx+sx, cy+sy, cz-sz), (cx-sx, cy+sy, cz-sz),
        (cx-sx, cy-sy, cz+sz), (cx+sx, cy-sy, cz+sz),
        (cx+sx, cy+sy, cz+sz), (cx-sx, cy+sy, cz+sz),
    ]
    # Duplicate vertices per face so the box keeps crisp, flat normals.
    faces = [
        ((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)),
        ((0, 1, 5, 4), (0, -1, 0)), ((1, 2, 6, 5), (1, 0, 0)),
        ((2, 3, 7, 6), (0, 1, 0)), ((3, 0, 4, 7), (-1, 0, 0)),
    ]
    vertices, normals, triangles = [], [], []
    for face, normal in faces:
        base = len(vertices)
        vertices.extend(corners[i] for i in face)
        normals.extend([normal] * 4)
        triangles.extend(((base, base+1, base+2), (base, base+2, base+3)))
    return mesh(parent, name, vertices, triangles, color, normals=normals)


def cylinder_z(parent: NodePath, name: str, radius: float, height: float,
               color: tuple[float, float, float, float], segments: int = 16) -> NodePath:
    vertices, normals, triangles = [], [], []
    half = height * 0.5
    for z_sign in (-1, 1):
        z = half * z_sign
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            nx, ny = math.cos(angle), math.sin(angle)
            vertices.append((radius * nx, radius * ny, z))
            normals.append((nx, ny, 0.0))
    for index in range(segments):
        nxt = (index + 1) % segments
        triangles.extend(((index, nxt, segments+nxt),
                          (index, segments+nxt, segments+index)))
    for sign in (-1, 1):
        center_index = len(vertices)
        vertices.append((0.0, 0.0, half * sign))
        normals.append((0.0, 0.0, float(sign)))
        ring_start = 0 if sign < 0 else segments
        for index in range(segments):
            nxt = (index + 1) % segments
            if sign < 0:
                triangles.append((center_index, ring_start+nxt, ring_start+index))
            else:
                triangles.append((center_index, ring_start+index, ring_start+nxt))
    return mesh(parent, name, vertices, triangles, color, normals=normals)


def cylinder_x(parent: NodePath, name: str, radius: float, width: float,
               color: tuple[float, float, float, float], segments: int = 24) -> NodePath:
    """Cylinder whose axle runs along local X (ideal for car tyres)."""
    vertices, normals, triangles = [], [], []
    half = width * 0.5
    for x in (-half, half):
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            ny, nz = math.cos(angle), math.sin(angle)
            vertices.append((x, radius * ny, radius * nz))
            normals.append((0.0, ny, nz))
    for index in range(segments):
        nxt = (index + 1) % segments
        triangles.extend(((index, nxt, segments+nxt),
                          (index, segments+nxt, segments+index)))
    for sign in (-1, 1):
        center_index = len(vertices)
        vertices.append((half * sign, 0.0, 0.0))
        normals.append((float(sign), 0.0, 0.0))
        ring_start = 0 if sign < 0 else segments
        for index in range(segments):
            nxt = (index + 1) % segments
            if sign < 0:
                triangles.append((center_index, ring_start+index, ring_start+nxt))
            else:
                triangles.append((center_index, ring_start+nxt, ring_start+index))
    return mesh(parent, name, vertices, triangles, color, normals=normals)


def make_car_body(parent: NodePath, name: str, color: tuple[float, float, float, float]) -> NodePath:
    """Create a tapered, multi-section sports-car body shell."""
    sections = [
        (-2.30, 0.70, 0.62, 0.47, 0.88, 1.11),
        (-1.95, 0.88, 0.77, 0.43, 1.03, 1.34),
        (-1.25, 0.96, 0.83, 0.42, 1.14, 1.44),
        ( 0.55, 0.97, 0.84, 0.42, 1.12, 1.42),
        ( 1.45, 0.91, 0.78, 0.44, 1.08, 1.32),
        ( 2.20, 0.77, 0.65, 0.49, 0.94, 1.18),
    ]
    vertices, normals, triangles = [], [], []
    ring_size = 8
    for y, width, upper, z_bottom, z_shoulder, z_top in sections:
        ring = [
            (-width, y, z_shoulder), (-upper, y, z_top),
            (upper, y, z_top), (width, y, z_shoulder),
            (width*0.92, y, z_bottom), (width*0.45, y, z_bottom-0.02),
            (-width*0.45, y, z_bottom-0.02), (-width*0.92, y, z_bottom),
        ]
        base = len(vertices)
        vertices.extend(ring)
        for x, _, z in ring:
            nx, nz = x * 0.55, z - 0.82
            length = math.hypot(nx, nz) or 1.0
            normals.append((nx/length, 0.0, nz/length))
        if base >= ring_size:
            previous = base - ring_size
            for j in range(ring_size):
                k = (j + 1) % ring_size
                triangles.extend(((previous+j, base+j, base+k),
                                  (previous+j, base+k, previous+k)))
    # Close front and rear ends.
    for offset in (0, (len(sections)-1)*ring_size):
        center = len(vertices)
        x = sum(vertices[offset+j][0] for j in range(ring_size))/ring_size
        y = sum(vertices[offset+j][1] for j in range(ring_size))/ring_size
        z = sum(vertices[offset+j][2] for j in range(ring_size))/ring_size
        vertices.append((x, y, z))
        normals.append((0.0, -1.0 if offset else 1.0, 0.0))
        for j in range(ring_size):
            k = (j + 1) % ring_size
            triangles.append((center, offset+k, offset+j) if offset else
                             (center, offset+j, offset+k))
    return mesh(parent, name, vertices, triangles, color, normals=normals)


def make_glass(parent: NodePath, name: str,
               vertices: list[tuple[float, float, float]],
               color: tuple[float, float, float, float]) -> NodePath:
    return mesh(parent, name, vertices, [(0, 1, 2), (0, 2, 3)], color)
