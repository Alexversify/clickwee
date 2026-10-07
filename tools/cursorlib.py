"""Read X11 cursors and Windows .cur/.ani, write Windows .cur/.ani. Needs Pillow and numpy."""
import io
import struct
from PIL import Image


# ---------------------------------------------------------------- XCursor
def read_xcursor(path):
    """-> {nominal_size: [(Image RGBA, xhot, yhot, delay_ms), ...]}"""
    data = open(path, "rb").read()
    if data[:4] != b"Xcur":
        raise ValueError(f"not an xcursor: {path}")
    _, _, ntoc = struct.unpack_from("<III", data, 4)
    out = {}
    for i in range(ntoc):
        typ, _sub, pos = struct.unpack_from("<III", data, 16 + i * 12)
        if typ != 0xFFFD0002:
            continue
        _hl, _t, nominal, _v, w, h, xh, yh, delay = struct.unpack_from("<IIIIIIIII", data, pos)
        px = data[pos + 36: pos + 36 + w * h * 4]
        # premultiplied ARGB (little endian -> B,G,R,A bytes) to straight RGBA
        img = Image.frombuffer("RGBA", (w, h), px, "raw", "BGRA", 0, 1).copy()
        img = unpremultiply(img)
        out.setdefault(nominal, []).append((img, xh, yh, delay))
    return out


def unpremultiply(img):
    import numpy as np
    a = np.asarray(img).astype(np.float32)
    al = a[..., 3:4]
    rgb = np.where(al > 0, np.minimum(255, a[..., :3] * 255 / np.maximum(al, 1)), 0)
    return Image.fromarray(np.concatenate([rgb, al], -1).round().astype(np.uint8), "RGBA")


# ---------------------------------------------------------------- Windows read
def _read_icondir(data):
    _, typ, n = struct.unpack_from("<HHH", data, 0)
    imgs = []
    for i in range(n):
        w, h, _c, _r, hx, hy, size, off = struct.unpack_from("<BBBBHHII", data, 6 + i * 16)
        blob = data[off: off + size]
        if blob[:8] == b"\x89PNG\r\n\x1a\n":
            img = Image.open(io.BytesIO(blob)).convert("RGBA")
        else:
            img = _dib_to_image(blob)
        imgs.append((img, hx, hy))
    return imgs


def _dib_to_image(blob):
    hs, w, h2, _pl, bpp = struct.unpack_from("<IiiHH", blob, 0)
    h = h2 // 2
    if bpp != 32:
        # rare in modern themes; let Pillow decode it as an .ico
        ico = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", w & 255, h & 255, 0, 0, 1, 32, len(blob), 22) + blob
        return Image.open(io.BytesIO(ico)).convert("RGBA")
    px = blob[hs: hs + w * h * 4]
    return Image.frombuffer("RGBA", (w, h), px, "raw", "BGRA", 0, -1).copy()


def read_windows_cursor(path):
    """-> list of frames; frame = (largest Image, xhot, yhot, delay_ms)"""
    data = open(path, "rb").read()
    if data[:4] != b"RIFF":
        imgs = _read_icondir(data)
        img, hx, hy = max(imgs, key=lambda t: t[0].width)
        return [(img, hx, hy, 0)]
    icons, rates, seq, jif = [], None, None, 6
    def walk(buf):
        nonlocal rates, seq, jif
        p = 0
        while p + 8 <= len(buf):
            cid, size = buf[p:p + 4], struct.unpack_from("<I", buf, p + 4)[0]
            body = buf[p + 8: p + 8 + size]
            if cid == b"anih":
                jif = struct.unpack_from("<9I", body)[7] or 6
            elif cid == b"rate":
                rates = list(struct.unpack_from(f"<{size // 4}I", body))
            elif cid == b"seq ":
                seq = list(struct.unpack_from(f"<{size // 4}I", body))
            elif cid == b"LIST":
                walk(body[4:])
            elif cid == b"icon":
                icons.append(body)
            p += 8 + size + (size & 1)
    walk(data[12:])
    order = seq or list(range(len(icons)))
    frames = []
    for i, idx in enumerate(order):
        img, hx, hy = max(_read_icondir(icons[idx]), key=lambda t: t[0].width)
        r = rates[i] if rates and i < len(rates) else jif
        frames.append((img, hx, hy, round(r * 1000 / 60)))
    return frames


# ---------------------------------------------------------------- Windows write
def _dib(img):
    w, h = img.size
    px = img.transpose(Image.FLIP_TOP_BOTTOM).tobytes("raw", "BGRA")
    mask_row = ((w + 31) // 32) * 4
    hdr = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, len(px) + mask_row * h, 0, 0, 0, 0)
    return hdr + px + b"\x00" * (mask_row * h)


def cur_bytes(images):
    """images: [(Image RGBA, xhot, yhot)] -> .cur file bytes"""
    # PNG-compressed entries, like the ful1e5 builds that Windows 10/11 load fine
    blobs = [_png(im) for im, _, _ in images]
    head = struct.pack("<HHH", 0, 2, len(images))
    off = 6 + 16 * len(images)
    entries = b""
    for (im, hx, hy), b in zip(images, blobs):
        entries += struct.pack("<BBBBHHII", im.width & 255, im.height & 255, 0, 0, hx, hy, len(b), off)
        off += len(b)
    return head + entries + b"".join(blobs)


def _png(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); return b.getvalue()


def ani_bytes(frames, delays_ms):
    """frames: [cur_bytes, ...]; delays_ms: per frame"""
    jif = [max(1, round(d * 60 / 1000)) for d in delays_ms]
    def chunk(cid, body):
        return cid + struct.pack("<I", len(body)) + body + (b"\x00" if len(body) & 1 else b"")
    # same header values and chunk order as the ful1e5 (clickgen) .ani files
    anih = struct.pack("<9I", 36, len(frames), len(frames), 0, 0, 32, 1, jif[0], 1)
    rate = struct.pack(f"<{len(jif)}I", *jif)
    fram = b"fram" + b"".join(chunk(b"icon", f) for f in frames)
    body = b"ACON" + chunk(b"anih", anih) + chunk(b"LIST", fram) + chunk(b"rate", rate)
    return b"RIFF" + struct.pack("<I", len(body)) + body


# ---------------------------------------------------------------- scaling
def fit(img, xh, yh, src_nominal, canvas, scale):
    """Scale a cursor image so its nominal box is `scale` x canvas, anchored top-left.
    Windows always draws cursors on the same canvas (32px at 100% DPI), so sizes
    differ by how much of the canvas the shape fills, not by canvas size."""
    f = canvas * scale / src_nominal
    w, h = max(1, round(img.width * f)), max(1, round(img.height * f))
    im = img.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    out.paste(im.crop((0, 0, min(w, canvas), min(h, canvas))), (0, 0))
    return out, min(canvas - 1, round(xh * f)), min(canvas - 1, round(yh * f))
