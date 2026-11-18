#!/usr/bin/env python3
"""main.py -- make.fun entrypoint for the news-image-20261118 bounty.

Validates ``./entry.png`` as a whole, well-formed PNG within the contest
limits (<= 1024x1024 px, <= 1 MiB) and deterministically copies it to
``$MAKEFUN_OUTPUT_DIR/entry.png`` (default ``/output``).

Python 3.13 standard library only. Both runs write identical bytes.
"""

from __future__ import annotations

import os
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "entry.png"
OUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
OUT_FILE = OUT_DIR / "entry.png"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1_048_576          # 1 MiB
MAX_SIDE = 1024                # px, width and height
COLOUR_BYTES = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}  # PNG colour type -> bytes/pixel


class EntryInvalid(Exception):
    """entry.png failed a contest gate check."""


def validate_png(data: bytes) -> tuple[int, int]:
    """Return (width, height) if ``data`` is a whole, valid PNG.

    Verifies everything the contest gate verifies: the signature, the
    IHDR dimensions and format, every chunk's CRC, the IEND trailer as
    the final chunk, and that the concatenated IDAT stream inflates to
    exactly the image data the header describes (a truncated or
    trailing-garbage file fails here).
    """
    if not data.startswith(PNG_SIGNATURE):
        raise EntryInvalid("missing PNG signature")
    if len(data) > MAX_BYTES:
        raise EntryInvalid(f"file is {len(data)} bytes (limit {MAX_BYTES})")

    width = height = None
    colour_type = None
    idat = bytearray()
    chunk_types: list[bytes] = []
    offset = len(PNG_SIGNATURE)

    while offset < len(data):
        if offset + 12 > len(data):
            raise EntryInvalid("truncated chunk header")
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        ctype = data[offset + 4 : offset + 8]
        cend = offset + 8 + length
        if cend + 4 > len(data):
            raise EntryInvalid(f"truncated chunk {ctype!r}")
        cdata = data[offset + 8 : cend]
        (crc,) = struct.unpack(">I", data[cend : cend + 4])
        if zlib.crc32(ctype + cdata) & 0xFFFFFFFF != crc:
            raise EntryInvalid(f"bad CRC in chunk {ctype!r}")

        if not chunk_types and ctype != b"IHDR":
            raise EntryInvalid("first chunk is not IHDR")
        chunk_types.append(ctype)

        if ctype == b"IHDR":
            if width is not None:
                raise EntryInvalid("duplicate IHDR chunk")
            if length != 13:
                raise EntryInvalid("IHDR is not 13 bytes")
            width, height, bit_depth, colour_type, compression, flt, interlace = (
                struct.unpack(">IIBBBBB", cdata)
            )
            if not (1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE):
                raise EntryInvalid(f"dimensions {width}x{height} exceed {MAX_SIDE}")
            if bit_depth != 8:
                raise EntryInvalid(f"unsupported bit depth {bit_depth}")
            if colour_type not in COLOUR_BYTES:
                raise EntryInvalid(f"unsupported colour type {colour_type}")
            if compression != 0 or flt != 0 or interlace != 0:
                raise EntryInvalid("unsupported compression/filter/interlace")
        elif ctype == b"IDAT":
            idat += cdata
        elif ctype == b"IEND":
            if length != 0:
                raise EntryInvalid("IEND chunk is not empty")
            if offset + 12 + length != len(data):
                raise EntryInvalid("data after IEND chunk")

        offset = cend + 4

    if width is None:
        raise EntryInvalid("no IHDR chunk")
    if b"IEND" not in chunk_types:
        raise EntryInvalid("no IEND chunk")
    if chunk_types[-1] != b"IEND":
        raise EntryInvalid("IEND is not the final chunk")
    if not idat:
        raise EntryInvalid("no IDAT data")

    # The image data the header describes: one filter byte per row plus
    # the packed scanlines.
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise EntryInvalid(f"IDAT stream does not decompress: {exc}") from exc
    expected = height * (1 + width * COLOUR_BYTES[colour_type])
    if len(raw) != expected:
        raise EntryInvalid(
            f"decompressed image data is {len(raw)} bytes, header describes {expected}"
        )
    for row in range(height):
        if raw[row * (1 + width * COLOUR_BYTES[colour_type])] > 4:
            raise EntryInvalid(f"invalid filter byte in scanline {row}")

    return width, height


def main() -> None:
    try:
        data = SRC.read_bytes()
    except OSError as exc:
        print(f"cannot read {SRC}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    try:
        width, height = validate_png(data)
    except EntryInvalid as exc:
        print(f"entry.png invalid: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    # Deterministic write: fixed path, fixed bytes, fresh file each run.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_bytes(data)
    print(f"valid {width}x{height} PNG, {len(data)} bytes -> {OUT_FILE}")


if __name__ == "__main__":
    main()
