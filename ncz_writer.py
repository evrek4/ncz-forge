"""
ncz_writer.py - Netcad (NCZ) Binary File Writer / Encoder
Copyright (C) 2026.
Supports Netcad 8.x/7.x/6.x/5.x compatible NCZ binary generation.
"""

from __future__ import annotations
import math
import os
import struct
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Union


# Block Type Constants
BLOCK_TYPE_FILE_HEADER = 1
BLOCK_TYPE_USER_INFO = 2
BLOCK_TYPE_EXTENT_SCALE = 3
BLOCK_TYPE_VISIBLE_EXTENT = 4
BLOCK_TYPE_LAYER_TABLE = 6
BLOCK_TYPE_INDEX = 8
BLOCK_TYPE_FONT_TABLE = 11
BLOCK_TYPE_SYMBOL_TABLE = 12
BLOCK_TYPE_CONTAINER_13 = 13
BLOCK_TYPE_BITMAP = 14
BLOCK_TYPE_GEOMETRY = 21
BLOCK_TYPE_GEOMETRY_EXTENDED = 22
BLOCK_TYPE_CONTAINER_23 = 23
BLOCK_TYPE_VERSION = 25
BLOCK_TYPE_NAMED_DATA = 28


def _build_block(block_type: int, payload: bytes) -> bytes:
    """Build a standard NCZ block: [1-byte type] [4-byte payload_len] [payload]."""
    return bytes([block_type]) + struct.pack("<I", len(payload)) + payload


@dataclass
class NCZPointEntity:
    x: float  # CAD X (Easting)
    y: float  # CAD Y (Northing)
    z: float = 0.0
    layer_code: int = 0
    name: str = ""
    color_code: int = 0


@dataclass
class NCZLineEntity:
    x1: float
    y1: float
    x2: float
    y2: float
    z1: float = 0.0
    z2: float = 0.0
    layer_code: int = 0
    color_code: int = 0


@dataclass
class NCZCircleEntity:
    cx: float
    cy: float
    radius: float
    z: float = 0.0
    layer_code: int = 0
    color_code: int = 0


@dataclass
class NCZTextEntity:
    x: float
    y: float
    text: str
    height: float = 2.0
    rotation_deg: float = 0.0
    z: float = 0.0
    layer_code: int = 0
    color_code: int = 0


@dataclass
class NCZPolylineEntity:
    points: List[Tuple[float, float, float]]
    is_closed: bool = False
    layer_code: int = 0
    label: str = ""
    color_code: int = 0


@dataclass
class NCZSymbolEntity:
    x: float
    y: float
    symbol_code: int = 0
    size: float = 2.0
    rotation_deg: float = 0.0
    z: float = 0.0
    layer_code: int = 0
    color_code: int = 0


class NCZWriter:
    """
    High-level generator for Netcad NCZ binary drawing files.
    
    Coordinate System:
      In CAD / GIS (DXF, Shapefile, etc.):
        - X = Sağa (Easting)
        - Y = Yukarı (Northing)
      Internally, Netcad NCZ binary stores:
        - raw_x = Northing (CAD Y)
        - raw_y = Easting (CAD X)
      This writer takes standard CAD coordinates (X = Easting, Y = Northing)
      and serializes them into the exact Netcad binary format.
    """

    def __init__(self, template_path: Optional[str] = None):
        self.layers: List[str] = ["0"]
        self.layer_color_codes: Dict[int, int] = {0: 1}
        self.layer_rgb: Dict[int, Tuple[int, int, int]] = {0: (255, 255, 255)}
        self.entities = []
        self.template_path = template_path
        self._raw_header_blocks: List[Tuple[int, bytes]] = []

        if template_path and os.path.exists(template_path):
            self._load_template(template_path)

    def _load_template(self, file_path: str):
        with open(file_path, "rb") as f:
            data = f.read()

        cursor = 0
        blocks = []
        while cursor + 5 <= len(data):
            btype = data[cursor]
            payload_len = int.from_bytes(data[cursor + 1 : cursor + 5], "little")
            payload = data[cursor + 5 : cursor + 5 + payload_len]
            if btype in (BLOCK_TYPE_GEOMETRY, BLOCK_TYPE_GEOMETRY_EXTENDED):
                break
            blocks.append((btype, payload))
            cursor += 5 + payload_len

        self._raw_header_blocks = blocks

    def add_layer(
        self,
        name: str,
        color_code: int = 1,
        rgb: Tuple[int, int, int] = (255, 255, 255),
    ) -> int:
        """Register a layer and return its integer index."""
        clean_name = name.strip()
        if clean_name in self.layers:
            idx = self.layers.index(clean_name)
            return idx

        idx = len(self.layers)
        self.layers.append(clean_name)
        self.layer_color_codes[idx] = color_code
        self.layer_rgb[idx] = rgb
        return idx

    def get_layer_code(self, layer_name: str) -> int:
        """Get or create layer index by name."""
        if not layer_name:
            return 0
        if layer_name in self.layers:
            return self.layers.index(layer_name)
        return self.add_layer(layer_name)

    def add_point(
        self,
        x: float,
        y: float,
        z: float = 0.0,
        layer: Union[int, str] = 0,
        name: str = "",
        color: int = 0,
    ):
        lcode = layer if isinstance(layer, int) else self.get_layer_code(layer)
        self.entities.append(NCZPointEntity(x, y, z, lcode, name, color))

    def add_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        z1: float = 0.0,
        z2: float = 0.0,
        layer: Union[int, str] = 0,
        color: int = 0,
    ):
        lcode = layer if isinstance(layer, int) else self.get_layer_code(layer)
        self.entities.append(NCZLineEntity(x1, y1, x2, y2, z1, z2, lcode, color))

    def add_circle(
        self,
        cx: float,
        cy: float,
        radius: float,
        z: float = 0.0,
        layer: Union[int, str] = 0,
        color: int = 0,
    ):
        lcode = layer if isinstance(layer, int) else self.get_layer_code(layer)
        self.entities.append(NCZCircleEntity(cx, cy, radius, z, lcode, color))

    def add_text(
        self,
        x: float,
        y: float,
        text: str,
        height: float = 2.0,
        rotation_deg: float = 0.0,
        z: float = 0.0,
        layer: Union[int, str] = 0,
        color: int = 0,
    ):
        lcode = layer if isinstance(layer, int) else self.get_layer_code(layer)
        self.entities.append(NCZTextEntity(x, y, text, height, rotation_deg, z, lcode, color))

    def add_polyline(
        self,
        points: List[Tuple[float, float, float]],
        is_closed: bool = False,
        layer: Union[int, str] = 0,
        label: str = "",
        color: int = 0,
    ):
        if len(points) < 2:
            return
        lcode = layer if isinstance(layer, int) else self.get_layer_code(layer)
        self.entities.append(NCZPolylineEntity(points, is_closed, lcode, label, color))

    def add_polygon(
        self,
        points: List[Tuple[float, float, float]],
        layer: Union[int, str] = 0,
        label: str = "",
        color: int = 0,
    ):
        """Add closed polygon."""
        if not points:
            return
        # Ensure closed ring
        if points[0][:2] != points[-1][:2]:
            points = list(points) + [points[0]]
        self.add_polyline(points, is_closed=True, layer=layer, label=label, color=color)

    def _encode_point_block(self, e: NCZPointEntity) -> bytes:
        # Netcad raw: raw_x is Northing (CAD Y), raw_y is Easting (CAD X)
        nx, ny = e.y, e.x
        p = bytearray(104)
        p[0] = 1
        p[1] = 1
        p[2] = e.layer_code & 0xFF
        struct.pack_into("<dd", p, 3, nx, ny)
        struct.pack_into("<ff", p, 19, e.z, e.z)
        p[30] = e.layer_code & 0xFF
        p[32] = e.color_code & 0xFF
        d = 0.00001
        struct.pack_into("<dddd", p, 45, nx - d, ny - d, nx + d, ny + d)
        nb = e.name.encode("windows-1254", errors="ignore")[:20]
        p[81] = len(nb)
        p[82 : 82 + len(nb)] = nb
        return _build_block(BLOCK_TYPE_GEOMETRY, bytes(p))

    def _encode_line_block(self, e: NCZLineEntity) -> bytes:
        nx1, ny1 = e.y1, e.x1
        nx2, ny2 = e.y2, e.x2
        p = bytearray(101)
        p[0] = 2
        p[1] = 2
        p[2] = e.layer_code & 0xFF
        struct.pack_into("<dd", p, 3, nx1, ny1)
        struct.pack_into("<ff", p, 19, e.z1, e.z1)
        p[30] = e.layer_code & 0xFF
        p[32] = e.color_code & 0xFF
        struct.pack_into("<dddd", p, 45, min(nx1, nx2), min(ny1, ny2), max(nx1, nx2), max(ny1, ny2))
        struct.pack_into("<ddf", p, 81, nx2, ny2, e.z2)
        return _build_block(BLOCK_TYPE_GEOMETRY, bytes(p))

    def _encode_circle_block(self, e: NCZCircleEntity) -> bytes:
        nx, ny = e.cy, e.cx
        r = float(e.radius)
        p = bytearray(89)
        p[0] = 3
        p[1] = 3
        p[2] = e.layer_code & 0xFF
        struct.pack_into("<dd", p, 3, nx, ny)
        struct.pack_into("<ff", p, 19, e.z, e.z)
        p[30] = e.layer_code & 0xFF
        p[32] = e.color_code & 0xFF
        struct.pack_into("<dddd", p, 45, nx - r, ny - r, nx + r, ny + r)
        struct.pack_into("<d", p, 81, r)
        return _build_block(BLOCK_TYPE_GEOMETRY, bytes(p))

    def _encode_text_block(self, e: NCZTextEntity) -> bytes:
        nx, ny = e.y, e.x
        tb = e.text.encode("windows-1254", errors="ignore")[:200]
        p = bytearray(93 + len(tb))
        p[0] = 5
        p[1] = 5
        p[2] = e.layer_code & 0xFF
        struct.pack_into("<dd", p, 3, nx, ny)
        struct.pack_into("<ff", p, 19, e.z, e.z)
        p[30] = e.layer_code & 0xFF
        p[32] = e.color_code & 0xFF
        rot_rad = math.radians(e.rotation_deg)
        w = max(e.height * len(tb) * 0.6, e.height)
        struct.pack_into("<dddd", p, 45, nx - w, ny - e.height, nx + w, ny + e.height)
        struct.pack_into("<ff", p, 81, float(e.height), float(rot_rad))
        p[89] = 0x4C  # Font / style flag
        p[92] = len(tb)
        p[93 : 93 + len(tb)] = tb
        return _build_block(BLOCK_TYPE_GEOMETRY, bytes(p))

    def _encode_polyline_block(self, e: NCZPolylineEntity) -> bytes:
        # Convert all vertices: CAD X, Y, Z -> Netcad Northing, Easting, Z
        pts = [(pt[1], pt[0], pt[2] if len(pt) > 2 else 0.0) for pt in e.points]
        lb = e.label.encode("windows-1254", errors="ignore")[:20]
        total_len = 108 + len(pts) * 24
        p = bytearray(total_len)
        p[0] = 7
        p[1] = 7
        p[2] = e.layer_code & 0xFF
        nx0, ny0, nz0 = pts[0]
        struct.pack_into("<dd", p, 3, nx0, ny0)
        struct.pack_into("<ff", p, 19, nz0, nz0)
        p[30] = e.layer_code & 0xFF
        p[32] = e.color_code & 0xFF
        min_x = min(pt[0] for pt in pts)
        max_x = max(pt[0] for pt in pts)
        min_y = min(pt[1] for pt in pts)
        max_y = max(pt[1] for pt in pts)
        struct.pack_into("<dddd", p, 45, min_x, min_y, max_x, max_y)
        if lb:
            p[81] = len(lb)
            p[82 : 82 + len(lb)] = lb
        for i, (px, py, pz) in enumerate(pts):
            struct.pack_into("<ddd", p, 108 + i * 24, px, py, pz)
        return _build_block(BLOCK_TYPE_GEOMETRY, bytes(p))

    def _calculate_bounds(self) -> Tuple[float, float, float, float]:
        """Calculate global bounding box in Netcad coordinates (min_northing, min_easting, max_northing, max_easting)."""
        all_nx = []
        all_ny = []
        for e in self.entities:
            if isinstance(e, NCZPointEntity):
                all_nx.append(e.y)
                all_ny.append(e.x)
            elif isinstance(e, NCZLineEntity):
                all_nx.extend([e.y1, e.y2])
                all_ny.extend([e.x1, e.x2])
            elif isinstance(e, NCZCircleEntity):
                all_nx.extend([e.cy - e.radius, e.cy + e.radius])
                all_ny.extend([e.cx - e.radius, e.cx + e.radius])
            elif isinstance(e, NCZTextEntity):
                all_nx.append(e.y)
                all_ny.append(e.x)
            elif isinstance(e, NCZPolylineEntity):
                all_nx.extend(pt[1] for pt in e.points)
                all_ny.extend(pt[0] for pt in e.points)

        if not all_nx:
            return (0.0, 0.0, 1000.0, 1000.0)

        min_nx, max_nx = min(all_nx), max(all_nx)
        min_ny, max_ny = min(all_ny), max(all_ny)
        return (min_nx, min_ny, max_nx, max_ny)

    def _build_layer_table_block(self) -> bytes:
        """Construct Block Type 6 (Layer Table)."""
        layer_p = bytearray()
        layer_p += b"\x00\x00\x00\x01\x00\x00\x00\x01\x00\x01\x01"
        layer_p += struct.pack("<H", len(self.layers))
        for idx, name in enumerate(self.layers):
            rec = bytearray(29)
            rec[0:4] = b"\xfd\x00\x12\x00"
            nb = name.encode("windows-1254", errors="ignore")[:20]
            rec[4] = len(nb)
            rec[5 : 5 + len(nb)] = nb
            color_code = self.layer_color_codes.get(idx, (idx % 250) + 1)
            struct.pack_into("<H", rec, 25, color_code)
            struct.pack_into("<H", rec, 27, 1)
            layer_p += rec
        return _build_block(BLOCK_TYPE_LAYER_TABLE, bytes(layer_p))

    def _build_default_header_blocks(
        self, min_nx: float, min_ny: float, max_nx: float, max_ny: float
    ) -> List[Tuple[int, bytes]]:
        """Construct standard Netcad header blocks if no template is provided."""
        blocks = []

        # Block 1 placeholder (120 bytes)
        b1_payload = bytearray(120)
        blocks.append((BLOCK_TYPE_FILE_HEADER, bytes(b1_payload)))

        # Block 2: User / Project info
        b2_payload = bytearray(366)
        sig = b"\x06netcad"
        b2_payload[: len(sig)] = sig
        blocks.append((BLOCK_TYPE_USER_INFO, bytes(b2_payload)))

        # Block 3: Scale factor
        b3_payload = struct.pack("<d", 1.0)
        blocks.append((BLOCK_TYPE_EXTENT_SCALE, b3_payload))

        # Block 4: Visible Extents (32 bytes = 4 doubles)
        # Margin around coordinates
        dx = max(max_nx - min_nx, 100.0) * 0.1
        dy = max(max_ny - min_ny, 100.0) * 0.1
        b4_payload = struct.pack(
            "<dddd",
            min_nx - dx,
            min_ny - dy,
            max_nx + dx,
            max_ny + dy,
        )
        blocks.append((BLOCK_TYPE_VISIBLE_EXTENT, b4_payload))

        # Block 25: Version string
        v_str = b"8.5.2.1027"
        b25_payload = bytes([len(v_str)]) + v_str
        blocks.append((BLOCK_TYPE_VERSION, b25_payload))

        # Block 14: Bitmap thumbnail (empty/minimal BMP)
        blocks.append((BLOCK_TYPE_BITMAP, b""))

        # Block 8: Spatial index table (empty/zeros)
        blocks.append((BLOCK_TYPE_INDEX, b"\x00" * 256))

        # Block 6: Layer Table
        blocks.append((BLOCK_TYPE_LAYER_TABLE, b""))  # Will be replaced in assembly

        # Block 11: Font Table
        font_p = bytearray(84)
        font_p[0] = 1  # 1 font
        f_name = b"ARIAL.NCF"
        font_p[4] = len(f_name)
        font_p[5 : 5 + len(f_name)] = f_name
        blocks.append((BLOCK_TYPE_FONT_TABLE, bytes(font_p)))

        # Block 12: Symbol Table
        sym_p = bytearray(404)
        sym_p[0] = 5
        s_name = b"PLAN.NCS"
        sym_p[4] = len(s_name)
        sym_p[5 : 5 + len(s_name)] = s_name
        blocks.append((BLOCK_TYPE_SYMBOL_TABLE, bytes(sym_p)))

        # Block 13 & 23: markers
        blocks.append((BLOCK_TYPE_CONTAINER_13, b""))
        blocks.append((BLOCK_TYPE_CONTAINER_23, b""))

        return blocks

    def save(self, output_path: str):
        """Assemble all blocks and write the binary NCZ file."""
        min_nx, min_ny, max_nx, max_ny = self._calculate_bounds()

        # Step 1: Encode all geometries
        geom_blocks = []
        for e in self.entities:
            if isinstance(e, NCZPointEntity):
                geom_blocks.append(self._encode_point_block(e))
            elif isinstance(e, NCZLineEntity):
                geom_blocks.append(self._encode_line_block(e))
            elif isinstance(e, NCZCircleEntity):
                geom_blocks.append(self._encode_circle_block(e))
            elif isinstance(e, NCZTextEntity):
                geom_blocks.append(self._encode_text_block(e))
            elif isinstance(e, NCZPolylineEntity):
                geom_blocks.append(self._encode_polyline_block(e))

        geom_bytes = b"".join(geom_blocks)

        # Step 2: Prepare header blocks
        if self._raw_header_blocks:
            # Clone template header blocks
            headers = [
                (btype, bytearray(payload)) for btype, payload in self._raw_header_blocks
            ]
            # Replace layer table block (Block 6) if layers were customized
            new_headers = []
            for btype, payload in headers:
                if btype == BLOCK_TYPE_LAYER_TABLE:
                    new_headers.append((btype, self._build_layer_table_block()[5:]))
                elif btype == BLOCK_TYPE_VISIBLE_EXTENT:
                    # Update visible extent
                    dx = max(max_nx - min_nx, 100.0) * 0.05
                    dy = max(max_ny - min_ny, 100.0) * 0.05
                    v_p = struct.pack(
                        "<dddd",
                        min_nx - dx,
                        min_ny - dy,
                        max_nx + dx,
                        max_ny + dy,
                    )
                    new_headers.append((btype, v_p))
                else:
                    new_headers.append((btype, payload))
            headers = new_headers
        else:
            headers = self._build_default_header_blocks(min_nx, min_ny, max_nx, max_ny)
            # Inject layer table
            headers = [
                (btype, self._build_layer_table_block()[5:] if btype == BLOCK_TYPE_LAYER_TABLE else p)
                for btype, p in headers
            ]

        # Step 3: Compute exact byte offsets for the Master Index (Block 1)
        # Block 1 is headers[0]
        block_offsets: Dict[int, int] = {}
        assembled_header_data = bytearray()

        current_offset = 0
        # Block 1 size is 5 + 120 = 125
        block_offsets[BLOCK_TYPE_FILE_HEADER] = current_offset
        current_offset += 125

        # Measure remaining headers (from headers[1:])
        header_blocks_bytes = bytearray()
        for btype, payload in headers[1:]:
            block_offsets[btype] = current_offset
            block_bytes = _build_block(btype, payload)
            header_blocks_bytes += block_bytes
            current_offset += len(block_bytes)

        # Geometry start offset:
        geometry_start_offset = current_offset
        total_file_size = current_offset + len(geom_bytes)

        # Step 4: Populate Block 1 payload (120 bytes)
        b1_payload = bytearray(headers[0][1])
        if len(b1_payload) < 120:
            b1_payload.extend(b"\x00" * (120 - len(b1_payload)))

        struct.pack_into("<I", b1_payload, 0, total_file_size)
        struct.pack_into("<I", b1_payload, 4, block_offsets.get(BLOCK_TYPE_USER_INFO, 125))
        struct.pack_into("<I", b1_payload, 8, block_offsets.get(BLOCK_TYPE_LAYER_TABLE, 0))
        struct.pack_into("<I", b1_payload, 12, block_offsets.get(BLOCK_TYPE_INDEX, 0))
        struct.pack_into("<I", b1_payload, 24, block_offsets.get(BLOCK_TYPE_FONT_TABLE, 0))
        struct.pack_into("<I", b1_payload, 28, block_offsets.get(BLOCK_TYPE_SYMBOL_TABLE, 0))
        struct.pack_into("<I", b1_payload, 32, block_offsets.get(BLOCK_TYPE_BITMAP, 0))
        struct.pack_into("<I", b1_payload, 36, block_offsets.get(BLOCK_TYPE_CONTAINER_13, 0))
        struct.pack_into("<I", b1_payload, 40, block_offsets.get(BLOCK_TYPE_CONTAINER_23, 0))

        # Master Bounding box (4 doubles = 32 bytes at offset 44..76)
        struct.pack_into("<dddd", b1_payload, 44, min_nx, min_ny, max_nx, max_ny)

        # Geometry count at offset 76 (uint32)
        struct.pack_into("<I", b1_payload, 76, len(geom_blocks))

        # Step 5: Write final file
        b1_block = _build_block(BLOCK_TYPE_FILE_HEADER, bytes(b1_payload))
        final_data = b1_block + header_blocks_bytes + geom_bytes

        with open(output_path, "wb") as f:
            f.write(final_data)

        return len(final_data)
