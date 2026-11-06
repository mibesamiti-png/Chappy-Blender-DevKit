"""Safe, standard-library-only structural inspection for GLB 2.0 files.

CBDK uses this parser to learn what a GLB contains before asking Blender to
render it. Only the GLB container header and JSON chunk are decoded. External
URIs, images, buffers and executable/project content are never loaded.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import struct
from typing import Any

GLB_MAGIC = b"glTF"
GLB_VERSION = 2
JSON_CHUNK_TYPE = 0x4E4F534A
BIN_CHUNK_TYPE = 0x004E4942
MAX_GLB_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_ITEMS_PER_SECTION = 100_000


class GLBInspectionError(ValueError):
    """Raised when a GLB cannot be safely and structurally inspected."""


@dataclass(frozen=True)
class GLBChunk:
    chunk_type: int
    length: int
    offset: int


def _safe_list(value: Any, label: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise GLBInspectionError(f"{label} must be a JSON array")
    if len(value) > MAX_ITEMS_PER_SECTION:
        raise GLBInspectionError(f"{label} exceeds safe item limit")
    return value


def _name(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() else fallback


def _read_glb_json(path: str | Path) -> tuple[dict, list[GLBChunk], int]:
    source = Path(path)
    if not source.is_file():
        raise GLBInspectionError(f"GLB file not found: {source}")
    size = source.stat().st_size
    if size < 20:
        raise GLBInspectionError("File is too small to be a GLB")
    if size > MAX_GLB_BYTES:
        raise GLBInspectionError("GLB exceeds safe size limit")

    with source.open("rb") as stream:
        header = stream.read(12)
        magic, version, declared_length = struct.unpack("<4sII", header)
        if magic != GLB_MAGIC:
            raise GLBInspectionError("Not a GLB/glTF binary file")
        if version != GLB_VERSION:
            raise GLBInspectionError(f"Unsupported GLB version: {version}")
        if declared_length != size:
            raise GLBInspectionError(
                f"GLB declared length mismatch: header={declared_length}, actual={size}"
            )

        chunks: list[GLBChunk] = []
        json_payload: bytes | None = None
        offset = 12
        while offset < size:
            if offset + 8 > size:
                raise GLBInspectionError("Truncated GLB chunk header")
            chunk_length, chunk_type = struct.unpack("<II", stream.read(8))
            payload_offset = offset + 8
            payload_end = payload_offset + chunk_length
            if payload_end > size:
                raise GLBInspectionError("GLB chunk extends beyond file length")
            chunks.append(GLBChunk(chunk_type, chunk_length, payload_offset))
            if chunk_type == JSON_CHUNK_TYPE:
                if json_payload is not None:
                    raise GLBInspectionError("GLB contains multiple JSON chunks")
                if chunk_length > MAX_JSON_BYTES:
                    raise GLBInspectionError("GLB JSON chunk exceeds safe size limit")
                json_payload = stream.read(chunk_length)
                if len(json_payload) != chunk_length:
                    raise GLBInspectionError("Truncated GLB JSON chunk payload")
            else:
                # Structure inspection does not need geometry/image payload bytes.
                # The file length and chunk bounds were already validated above.
                stream.seek(chunk_length, 1)
            offset = payload_end

        if json_payload is None:
            raise GLBInspectionError("GLB JSON chunk is missing")

    try:
        document = json.loads(json_payload.rstrip(b"\x20\x00").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GLBInspectionError("Invalid GLB JSON chunk") from exc
    if not isinstance(document, dict):
        raise GLBInspectionError("GLB root JSON must be an object")

    asset = document.get("asset")
    if not isinstance(asset, dict) or not isinstance(asset.get("version"), str):
        raise GLBInspectionError("GLB asset metadata is missing")
    if not asset["version"].startswith("2"):
        raise GLBInspectionError(f"Unsupported glTF asset version: {asset['version']}")
    return document, chunks, size


def _accessor_count(accessors: list, index: Any) -> int | None:
    if not isinstance(index, int) or index < 0 or index >= len(accessors):
        return None
    entry = accessors[index]
    if not isinstance(entry, dict):
        return None
    count = entry.get("count")
    return count if isinstance(count, int) and count >= 0 else None


def inspect_glb(path: str | Path) -> dict:
    """Return deterministic structural metadata without importing or rendering."""
    document, chunks, file_size = _read_glb_json(path)
    scenes = _safe_list(document.get("scenes"), "scenes")
    nodes = _safe_list(document.get("nodes"), "nodes")
    meshes = _safe_list(document.get("meshes"), "meshes")
    materials = _safe_list(document.get("materials"), "materials")
    accessors = _safe_list(document.get("accessors"), "accessors")
    images = _safe_list(document.get("images"), "images")
    textures = _safe_list(document.get("textures"), "textures")
    animations = _safe_list(document.get("animations"), "animations")
    skins = _safe_list(document.get("skins"), "skins")
    cameras = _safe_list(document.get("cameras"), "cameras")

    mesh_rows = []
    total_primitives = approximate_vertex_refs = approximate_index_refs = 0
    for i, mesh in enumerate(meshes):
        if not isinstance(mesh, dict):
            raise GLBInspectionError(f"meshes[{i}] must be an object")
        primitives = _safe_list(mesh.get("primitives"), f"meshes[{i}].primitives")
        prim_rows = []
        for j, primitive in enumerate(primitives):
            if not isinstance(primitive, dict):
                raise GLBInspectionError(f"meshes[{i}].primitives[{j}] must be an object")
            attributes = primitive.get("attributes") or {}
            if not isinstance(attributes, dict):
                raise GLBInspectionError(f"meshes[{i}].primitives[{j}].attributes must be an object")
            vertex_count = _accessor_count(accessors, attributes.get("POSITION"))
            index_count = _accessor_count(accessors, primitive.get("indices"))
            total_primitives += 1
            approximate_vertex_refs += vertex_count or 0
            approximate_index_refs += index_count or 0
            prim_rows.append({
                "primitive_index": j,
                "mode": primitive.get("mode", 4),
                "material": primitive.get("material"),
                "position_accessor": attributes.get("POSITION"),
                "vertex_count": vertex_count,
                "index_count": index_count,
                "attributes": sorted(str(k) for k in attributes),
            })
        mesh_rows.append({
            "index": i,
            "name": _name(mesh.get("name"), f"Mesh_{i}"),
            "primitive_count": len(primitives),
            "primitives": prim_rows,
        })

    node_rows = []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise GLBInspectionError(f"nodes[{i}] must be an object")
        children = node.get("children") or []
        if not isinstance(children, list) or any(not isinstance(v, int) for v in children):
            raise GLBInspectionError(f"nodes[{i}].children must contain integer indices")
        node_rows.append({
            "index": i,
            "name": _name(node.get("name"), f"Node_{i}"),
            "mesh": node.get("mesh"),
            "children": children,
            "translation": node.get("translation"),
            "rotation": node.get("rotation"),
            "scale": node.get("scale"),
            "matrix": node.get("matrix"),
        })

    scene_rows = []
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise GLBInspectionError(f"scenes[{i}] must be an object")
        roots = scene.get("nodes") or []
        if not isinstance(roots, list) or any(not isinstance(v, int) for v in roots):
            raise GLBInspectionError(f"scenes[{i}].nodes must contain integer indices")
        scene_rows.append({"index": i, "name": _name(scene.get("name"), f"Scene_{i}"), "nodes": roots})

    return {
        "schema_version": 1,
        "kind": "cbdk_glb_static_inspection",
        "source_name": Path(path).name,
        "file_size_bytes": file_size,
        "asset": {
            "version": document.get("asset", {}).get("version"),
            "generator": document.get("asset", {}).get("generator"),
            "copyright": document.get("asset", {}).get("copyright"),
        },
        "default_scene": document.get("scene"),
        "counts": {
            "scenes": len(scenes), "nodes": len(nodes), "meshes": len(meshes),
            "materials": len(materials), "accessors": len(accessors),
            "images": len(images), "textures": len(textures),
            "animations": len(animations), "skins": len(skins), "cameras": len(cameras),
            "primitives": total_primitives,
            "approximate_vertex_references": approximate_vertex_refs,
            "approximate_index_references": approximate_index_refs,
        },
        "scenes": scene_rows,
        "nodes": node_rows,
        "meshes": mesh_rows,
        "materials": [
            {"index": i, "name": _name(m.get("name") if isinstance(m, dict) else None, f"Material_{i}")}
            for i, m in enumerate(materials)
        ],
        "chunks": [{
            "type": "JSON" if c.chunk_type == JSON_CHUNK_TYPE else "BIN" if c.chunk_type == BIN_CHUNK_TYPE else f"0x{c.chunk_type:08X}",
            "length": c.length,
            "offset": c.offset,
        } for c in chunks],
        "safety": {
            "static_only": True,
            "executed_embedded_content": False,
            "loaded_external_uris": False,
            "decoded_images": False,
            "loaded_binary_payload": False,
            "blender_runtime_verified": False,
        },
    }


def write_glb_inspection(path: str | Path, output: str | Path) -> dict:
    report = inspect_glb(path)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
