"""
Draw verbatim's icon, and write the sizes each platform wants.

Run it only when the icon changes; the results are committed, so neither the
application nor the tests depend on Pillow being present to show an icon.

    python tools/make_icon.py

The design has to survive 16 pixels in a Windows taskbar, so it is one letter
on a plain ground: anything finer turns to mush at that size.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

INK = (28, 46, 74)          # deep blue-grey, legible on light and dark bars
PAPER = (247, 247, 245)
ACCENT = (27, 107, 47)      # the green used for an accepted file
SIZE = 1024
OUT = Path(__file__).resolve().parent.parent / "verbatim" / "assets"


def font(size: int):
    for name in ("/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                 "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
                 "/Library/Fonts/Arial Bold.ttf",
                 "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw(small: bool = False) -> Image.Image:
    """The icon. `small` drops the check mark and fills the square.

    At 16 pixels — the size of a Windows taskbar button — a check mark is four
    pixels of mud and the padding wastes a quarter of the width. Small sizes
    get their own drawing, as icons normally do.
    """
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    pad = SIZE // 24 if small else SIZE // 12
    radius = SIZE // 7 if small else SIZE // 5
    pen.rounded_rectangle([pad, pad, SIZE - pad, SIZE - pad], radius, fill=INK)

    # A "V" in a serif face: a letter, for a tool about text.
    glyph = font(int(SIZE * (0.82 if small else 0.62)))
    box = pen.textbbox((0, 0), "V", font=glyph)
    pen.text(((SIZE - (box[2] - box[0])) / 2 - box[0],
              (SIZE - (box[3] - box[1])) / 2 - box[1] - SIZE * (0 if small else 0.03)),
             "V", font=glyph, fill=PAPER)
    if small:
        return image

    # A check under it: what the tool is for is verification, not conversion.
    y = SIZE * 0.78
    pen.line([(SIZE * 0.36, y), (SIZE * 0.46, y + SIZE * 0.07),
              (SIZE * 0.65, y - SIZE * 0.08)],
             fill=ACCENT, width=int(SIZE * 0.055), joint="curve")
    return image


def write_ico(frames: list, path: Path) -> None:
    """Assemble a .ico from one image per size.

    Pillow can write a multi-size .ico on its own, but passing it replacement
    images for particular sizes (which is how the small sizes get the simpler
    drawing) writes the wrong picture under the right label: every size after
    the replacements comes out as a copy of the last one. So each frame is
    encoded on its own — which Pillow does correctly — and the directory is
    assembled here.
    """
    import io
    import struct

    encoded = []
    for frame in frames:
        buffer = io.BytesIO()
        frame.save(buffer, format="ICO", sizes=[frame.size])
        blob = buffer.getvalue()
        # One frame in, one frame out. In a directory entry the byte count
        # comes before the offset, not after.
        size, offset = struct.unpack("<II", blob[14:22])
        encoded.append((frame.size, blob[offset:offset + size]))

    out = bytearray(struct.pack("<HHH", 0, 1, len(encoded)))
    offset = 6 + 16 * len(encoded)
    for (width, height), blob in encoded:
        out += struct.pack("<BBBBHHII", width % 256, height % 256, 0, 0, 1, 32,
                           len(blob), offset)
        offset += len(blob)
    for _size, blob in encoded:
        out += blob
    path.write_bytes(bytes(out))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    master, plain = draw(), draw(small=True)
    master.resize((256, 256), Image.LANCZOS).save(OUT / "icon.png")
    frames = [(plain if size <= 24 else master).resize((size, size), Image.LANCZOS)
              for size in (16, 24, 32, 48, 64, 128, 256)]
    write_ico(frames, OUT / "icon.ico")
    print(f"wrote {OUT / 'icon.png'} and {OUT / 'icon.ico'}")


if __name__ == "__main__":
    main()
