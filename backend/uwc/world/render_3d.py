"""GLB site models. Units are metres; Y-up (glTF convention).

Node names are stable identifiers the UI binds to ("B-1", "ROOF-B-1",
"RACK-03", "SPRINKLER_DESIGN_PLANE", "GROUND"); per-node `extras` carry the
underwriting attributes shown on hover.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from uwc.world.truth import Building, Location

FT = 0.3048
PALETTE = {
    "body": [205, 211, 222, 255], "roof": [120, 130, 148, 255], "roof_hail": [150, 108, 78, 255], "ground": [232, 235, 230, 255],
    "rack": [214, 120, 36, 255], "plane": [30, 163, 163, 90], "glass": [150, 185, 215, 255], "datahall": [190, 198, 210, 255],
    "vacant": [228, 214, 214, 255], "new": [196, 226, 222, 255],
}


def _geom(w: float, h: float, d: float, at: tuple[float, float, float]) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=(w, h, d))
    m.apply_translation(at)
    return m


def _paint(m: trimesh.Trimesh, color: list[int]) -> trimesh.Trimesh:
    alpha = color[3] / 255
    mat = trimesh.visual.material.PBRMaterial(baseColorFactor=[c / 255 for c in color[:3]] + [alpha], metallicFactor=0.05,
                                              roughnessFactor=0.85, alphaMode="BLEND" if alpha < 1 else "OPAQUE", doubleSided=alpha < 1)
    m.visual = trimesh.visual.TextureVisuals(material=mat)
    return m


def _box(w: float, h: float, d: float, color: list[int], at: tuple[float, float, float]) -> trimesh.Trimesh:
    return _paint(_geom(w, h, d, at), color)


def building_meshes(b: Building, loc: Location, flags: dict[str, Any]) -> list[tuple[str, trimesh.Trimesh, dict]]:
    out = []
    h = b.stories * b.story_h_m
    body_color = PALETTE["vacant"] if b.extras.get("flag") == "vacant" else PALETTE["new"] if b.extras.get("flag") == "new" else PALETTE["datahall"] if b.kind == "datahall" else PALETTE["body"]
    cx, cz = b.x_m + b.width_m / 2, b.y_m + b.depth_m / 2
    extras = {"label": b.label, "stories": b.stories, "height_ft": round(h / FT), "footprint_sqft": round(b.width_m * b.depth_m / 0.0929),
              "construction": loc.construction_raw, "occupancy": loc.occupancy_raw, "year_built": loc.year_built,
              "roof_year": loc.roof_year, **{k: v for k, v in b.extras.items() if v is not None}, **flags}
    if b.kind == "warehouse" and b.racks:
        # translucent shell so racks are visible; solid roof slab separate
        shell = _box(b.width_m, h, b.depth_m, [205, 211, 222, 45], (cx, h / 2, cz))
        extras["transparent"] = True
        out.append((b.key, shell, extras))
        rack_h = b.rack_height_ft * FT
        n = b.racks
        gap = b.width_m / (n + 1)
        for i in range(n):
            rx = b.x_m + gap * (i + 1)
            rack = _box(max(2.4, gap * 0.35), rack_h, b.depth_m * 0.82, PALETTE["rack"], (rx, rack_h / 2, cz))
            out.append((f"RACK-{i + 1:02d}", rack, {"label": f"Rack row {i + 1}", "storage_height_ft": b.rack_height_ft,
                                                     "commodity": loc.commodity or "", "flag": "storage_over_design" if b.rack_height_ft > (b.sprinkler_design_ft or 99) else None}))
        if b.sprinkler_design_ft:
            ph = b.sprinkler_design_ft * FT
            plane = _box(b.width_m * 0.98, 0.08, b.depth_m * 0.98, PALETTE["plane"], (cx, ph, cz))
            out.append(("SPRINKLER_DESIGN_PLANE", plane, {"label": "Sprinkler design storage height", "height_ft": b.sprinkler_design_ft,
                                                         "note": f"Racks at {b.rack_height_ft:.0f} ft exceed design basis of {b.sprinkler_design_ft:.0f} ft",
                                                         "transparent": True}))
        roof = _box(b.width_m, 0.4, b.depth_m, [120, 130, 148, 60], (cx, h + 0.2, cz))
        out.append((f"ROOF-{b.key}", roof, {"label": f"Roof — {b.label}", "roof_year": loc.roof_year, "roof_type": loc.roof_type, "transparent": True}))
        return out
    if b.kind == "tower" and b.stories >= 6:
        podium_h = 2 * b.story_h_m
        podium = _geom(b.width_m, podium_h, b.depth_m, (cx, podium_h / 2, cz))
        tower_h = h - podium_h
        tower = _geom(b.width_m * 0.62, tower_h, b.depth_m * 0.62, (cx, podium_h + tower_h / 2, cz))
        mesh = _paint(trimesh.util.concatenate([podium, tower]), body_color)
    else:
        mesh = _box(b.width_m, h, b.depth_m, body_color, (cx, h / 2, cz))
    out.append((b.key, mesh, extras))
    roof_col = PALETTE["roof_hail"] if flags.get("roof_condition") == "Poor" else PALETTE["roof"]
    rw, rd = (b.width_m * 0.62, b.depth_m * 0.62) if b.kind == "tower" and b.stories >= 6 else (b.width_m, b.depth_m)
    roof = _box(rw, 0.35, rd, roof_col, (cx, h + 0.18, cz))
    out.append((f"ROOF-{b.key}", roof, {"label": f"Roof — {b.label}", "roof_year": loc.roof_year, "roof_type": loc.roof_type}))
    if b.kind == "datahall":
        for k in range(6):
            u = _box(3.0, 2.2, 3.0, [150, 158, 170, 255], (b.x_m + 8 + k * (b.width_m - 16) / 5, h + 1.3, b.y_m + 6))
            out.append((f"HVAC-{b.key}-{k + 1}", u, {"label": "Rooftop cooling unit"}))
    return out


def render_site(loc_list: list[Location], path: Path, flags_by_building: dict[str, dict] | None = None) -> dict:
    """Render one or more locations' buildings into a single GLB. Returns node → extras map."""
    scene = trimesh.Scene()
    extras_map: dict[str, dict] = {}
    minx = minz = 1e9
    maxx = maxz = -1e9
    for loc in loc_list:
        for b in loc.buildings:
            flags = (flags_by_building or {}).get(b.key, {})
            for name, mesh, ex in building_meshes(b, loc, flags):
                node = name if len(loc_list) == 1 else f"{loc.key}:{name}"
                scene.add_geometry(mesh, node_name=node, geom_name=node)
                extras_map[node] = {**ex, "location_key": loc.key}
                bmin, bmax = mesh.bounds
                minx, minz = min(minx, bmin[0]), min(minz, bmin[2])
                maxx, maxz = max(maxx, bmax[0]), max(maxz, bmax[2])
    pad = 25
    gw, gd = (maxx - minx) + 2 * pad, (maxz - minz) + 2 * pad
    ground = _box(gw, 0.2, gd, PALETTE["ground"], ((minx + maxx) / 2, -0.1, (minz + maxz) / 2))
    scene.add_geometry(ground, node_name="GROUND", geom_name="GROUND")
    extras_map["GROUND"] = {"label": "Site", "note": "Ground plane"}
    glb = scene.export(file_type="glb")
    glb = _inject_extras(glb, extras_map)
    path.write_bytes(glb)
    return extras_map


def _inject_extras(glb: bytes, extras_map: dict[str, dict]) -> bytes:
    """Add `extras` (→ three.js userData) to named nodes and enable alpha blending on translucent materials."""
    magic, version, _ = struct.unpack_from("<4sII", glb, 0)
    off = 12
    jlen, jtype = struct.unpack_from("<II", glb, off)
    doc = json.loads(glb[off + 8: off + 8 + jlen].decode())
    rest = glb[off + 8 + jlen:]
    for node in doc.get("nodes", []):
        ex = extras_map.get(node.get("name"))
        if ex:
            node["extras"] = json.loads(json.dumps(ex, default=str))
            if ex.get("transparent") and "mesh" in node:
                for prim in doc["meshes"][node["mesh"]]["primitives"]:
                    if "material" in prim:
                        mat = doc["materials"][prim["material"]]
                        mat["alphaMode"] = "BLEND"
                        mat["doubleSided"] = True
    j = json.dumps(doc, separators=(",", ":")).encode()
    j += b" " * ((4 - len(j) % 4) % 4)
    body = struct.pack("<II", len(j), 0x4E4F534A) + j + rest
    return struct.pack("<4sII", magic, version, 12 + len(body)) + body
