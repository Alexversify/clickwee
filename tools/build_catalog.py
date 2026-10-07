"""Build catalog.json, previews/ and packs/ from tools/sources.json.

    pip install pillow numpy
    python3 tools/build_catalog.py            # build what is missing
    python3 tools/build_catalog.py --force    # rebuild every pack and preview

Adding a cursor = add an entry to tools/sources.json and run this. Connected PCs read
catalog.json at apply time, so nobody has to re-run the connect file.

kinds
  upstream : Windows zip published by the author (ful1e5 layout: <name>-<Size>-Windows/)
  xcursor  : Linux X11 cursor theme, converted here into packs/<id>/<Size>.zip
  recolor  : animated edition made from another theme's Windows files
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import cursorlib as cl  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("CLICKWEE_CACHE", ROOT / "tools" / ".cache"))
REPO_RAW = "https://raw.githubusercontent.com/Alexversify/clickwee/main"
REPO_CDN = "https://cdn.jsdelivr.net/gh/Alexversify/clickwee@main"
FORCE = "--force" in sys.argv

# share of the canvas the cursor's nominal box fills, same ratios as ful1e5's builds (22:32 ...)
SIZES = {"Regular": 0.6875, "Large": 0.86, "Extra-Large": 1.0}
CANVASES = [32, 48, 64, 96]   # 100% .. 300% display scaling; Windows upscales beyond that

# Windows file name -> X11 cursor names, in priority order
X11 = {
    "Pointer": ["left_ptr", "default", "arrow", "top_left_arrow"],
    "Help": ["help", "question_arrow", "whats_this", "left_ptr_help", "5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b"],
    "Work": ["progress", "left_ptr_watch", "half-busy", "3ecb610c1bf2410f44200f48c40d3599", "08e8e1c95fe2fc01f976f1e063a24ccd"],
    "Busy": ["wait", "watch"],
    "Cross": ["crosshair", "cross", "tcross", "cross_reverse", "diamond_cross"],
    "Text": ["text", "xterm", "ibeam"],
    "Handwriting": ["pencil", "draft", "draft_large"],
    "Unavailable": ["not-allowed", "circle", "crossed_circle", "forbidden", "no-drop", "dnd-no-drop", "03b6e0fcb3499374a867c041f52298f0"],
    "Vert": ["ns-resize", "size_ver", "sb_v_double_arrow", "v_double_arrow", "row-resize", "00008160000006810000408080010102"],
    "Horz": ["ew-resize", "size_hor", "sb_h_double_arrow", "h_double_arrow", "col-resize", "028006030e0e7ebffc7f7070c0600140"],
    "Dgn1": ["nwse-resize", "size_fdiag", "bd_double_arrow", "c7088f0f3e6c8088236ef8e1e3e70000"],
    "Dgn2": ["nesw-resize", "size_bdiag", "fd_double_arrow", "fcf1c3c7cd4491d801f1e1c78f100000"],
    "Move": ["fleur", "all-scroll", "size_all", "4498f0e0c1937ffe01fd06f973665830", "9081237383d90e509aa00f00170e968f", "move"],
    "Alternate": ["up-arrow", "up_arrow", "center_ptr", "sb_up_arrow"],
    "Link": ["pointer", "hand2", "pointing_hand", "hand1", "hand", "e29285e634086352946a0e7090d73106", "9d800788f1b08800ae810202380a0822"],
}
# Windows file name spellings used by the different ful1e5 builds
WIN_ALIASES = {
    "Pointer": ["Pointer", "Default"], "Link": ["Link"], "Text": ["Text", "IBeam"], "Move": ["Move"],
    "Dgn1": ["Dgn1", "Dng1", "Diagonal_1"], "Dgn2": ["Dgn2", "Dng2", "Diagonal_2"], "Help": ["Help"],
    "Unavailable": ["Unavailable", "Unavailiable"], "Cross": ["Cross"], "Busy": ["Busy"], "Work": ["Work"],
    "Vert": ["Vert", "Vertical"], "Horz": ["Horz", "Horizontal"], "Handwriting": ["Handwriting"],
    "Alternate": ["Alternate"], "Pin": ["Pin"], "Person": ["Person"],
}
# preview role on the website -> Windows file
PREVIEW = {"default": "Pointer", "pointer": "Link", "text": "Text", "move": "Move", "nwse": "Dgn1",
           "help": "Help", "notallowed": "Unavailable", "crosshair": "Cross", "busy": "Busy", "work": "Work"}
MAX_FRAMES = 24
ANIMATED_ROLES = {"Pointer", "Link", "Help", "Alternate"}


# ------------------------------------------------------------------ fetching
def download(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    dst = CACHE / ("dl-" + hashlib.sha1(url.encode()).hexdigest()[:16] + "-" + url.rsplit("/", 1)[-1])
    if not dst.exists():
        print("  download", url)
        tmp = dst.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.rename(dst)
    return dst


def fetch(spec):
    """-> directory containing the source"""
    if "git" in spec:
        d = CACHE / ("git-" + hashlib.sha1(spec["git"].encode()).hexdigest()[:16])
        if not d.exists():
            print("  clone", spec["git"])
            subprocess.run(["git", "clone", "-q", "--depth", "1", spec["git"], str(d)], check=True)
        return d
    arc = download(spec["archive"])
    d = Path(str(arc) + ".d")
    if not d.exists():
        tmp = Path(str(d) + ".part"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
        # CLI tools keep the symlinks that X11 cursor themes are full of
        if arc.name.endswith(".zip"):
            subprocess.run(["unzip", "-q", str(arc), "-d", str(tmp)], check=True)
        else:
            subprocess.run(["tar", "xf", str(arc), "-C", str(tmp)], check=True)
        tmp.rename(d)
    return d


# ------------------------------------------------------------------ converting
def resolve_x11(d, names):
    for n in names:
        p = d / n
        for _ in range(8):
            if not p.exists() and not p.is_symlink():
                break
            data = p.read_bytes() if p.is_file() else b""
            if data[:4] == b"Xcur":
                return p
            if 0 < len(data) < 256:          # a symlink stored as a text file
                p = d / data.decode(errors="ignore").strip(); continue
            break
    return None


def limit_frames(frames):
    if len(frames) <= MAX_FRAMES:
        return frames
    k = -(-len(frames) // MAX_FRAMES)
    out = []
    for i in range(0, len(frames), k):
        grp = frames[i:i + k]
        img, hx, hy, _ = grp[0]
        out.append((img, hx, hy, sum(f[3] or 50 for f in grp)))
    return out


def write_role(dirpath, name, frames_per_canvas):
    """frames_per_canvas: [[(img,hx,hy) per canvas] per frame], delays from frame tuples"""
    curs = [cl.cur_bytes(imgs) for imgs, _ in frames_per_canvas]
    if len(curs) == 1:
        (dirpath / f"{name}.cur").write_bytes(curs[0])
    else:
        (dirpath / f"{name}.ani").write_bytes(cl.ani_bytes(curs, [d for _, d in frames_per_canvas]))


def build_from_x11(theme, src_dir, out_dir):
    for size, scale in SIZES.items():
        d = out_dir / f"{theme['id']}-{size}-Windows"; d.mkdir(parents=True)
        for name, xnames in X11.items():
            p = resolve_x11(src_dir, xnames)
            if not p:
                continue
            sets = cl.read_xcursor(p)
            need = max(CANVASES) * scale
            nominal = min((n for n in sets if n >= need), default=max(sets))
            frames = limit_frames(sets[nominal])
            write_role(d, name, [([cl.fit(img, hx, hy, nominal, c, scale) for c in CANVASES], delay or 50)
                                 for img, hx, hy, delay in frames])


def find_win_file(d, name):
    for n in WIN_ALIASES.get(name, [name]):
        for ext in (".cur", ".ani"):
            if (d / f"{n}{ext}").exists():
                return d / f"{n}{ext}"
    return None


def size_dir(root, size):
    for d in sorted(Path(root).rglob(f"*-{size}-Windows")):
        if d.is_dir() and (size != "Large" or "Extra-Large" not in d.name):
            return d
    return None


def hsv(h, s, v):
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    v = np.full_like(h, v)
    r = np.choose(i, [v, q, p, p, t, v]); g = np.choose(i, [t, v, v, q, p, p]); b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1).astype(np.float32)


def recolor_frame(img, effect, t, fill_dark):
    a = np.asarray(img).astype(np.float32) / 255
    rgb, al = a[..., :3], a[..., 3:4]
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    w = (1 - lum if fill_dark else lum)[..., None]
    h, wd = lum.shape
    if effect == "rainbow":
        yy, xx = np.mgrid[0:h, 0:wd].astype(np.float32)
        hue = (t + (xx + yy) / (h + wd) * 0.6) % 1.0
        col = hsv(hue, 0.85, 1.0)
        out = rgb * (1 - w) + col * w
        return Image.fromarray((np.concatenate([out, al], -1) * 255).round().astype(np.uint8), "RGBA")
    base = {"neon": (0.16, 0.91, 1.0), "neon-pink": (1.0, 0.3, 0.75)}[effect]
    pulse = 0.5 + 0.5 * np.cos(t * 2 * np.pi)
    col = np.array(base, np.float32) * (0.7 + 0.3 * pulse)
    out = rgb * (1 - w) + col * w
    core = Image.fromarray((np.concatenate([out, al], -1) * 255).round().astype(np.uint8), "RGBA")
    # soft glow behind the shape
    glow_a = (al[..., 0] * w[..., 0] * (0.35 + 0.5 * pulse) * 255).astype(np.uint8)
    glow = Image.new("RGBA", img.size, tuple(int(c * 255) for c in base) + (0,))
    glow.putalpha(Image.fromarray(glow_a).filter(ImageFilter.GaussianBlur(img.width / 28)))
    return Image.alpha_composite(glow, core)


def build_recolor(theme, base_root, out_dir):
    src = size_dir(base_root, "Extra-Large")
    fill_dark = theme["effect"] == "rainbow"
    dirs = {}
    for size in SIZES:
        dirs[size] = out_dir / f"{theme['id']}-{size}-Windows"; dirs[size].mkdir(parents=True)
    for name in WIN_ALIASES:
        p = find_win_file(src, name)
        if not p:
            continue
        frames = limit_frames(cl.read_windows_cursor(p))
        # colour-animate the cursors people see most; the rest get one still frame
        n = len(frames) if len(frames) > 1 else (12 if name in ANIMATED_ROLES else 1)
        colored = []
        for i in range(n):
            img, hx, hy, delay = frames[i % len(frames)]
            colored.append((recolor_frame(img, theme["effect"], i / n, fill_dark), hx, hy,
                            delay if len(frames) > 1 else 90))
        for size, scale in SIZES.items():
            # source is the Extra-Large build, whose shape fills the whole canvas
            write_role(dirs[size], name, [([cl.fit(img, hx, hy, img.width, c, scale) for c in CANVASES], d)
                                          for img, hx, hy, d in colored])


def zip_dir(src, dst):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                zi = zipfile.ZipInfo(str(p.relative_to(src)).replace(os.sep, "/"), (1980, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi, p.read_bytes(), compresslevel=9)
    dst.write_bytes(buf.getvalue())


def readme(theme):
    return (f"{theme['name']} cursor for Windows\r\n\r\n"
            f"Design: {theme['author']}\r\nSource: {theme['source']}\r\nLicense: {theme['license']} ({theme['licenseUrl']})\r\n\r\n"
            "Converted to Windows .cur/.ani by Clickwee (https://clickwee.com).\r\n"
            "The conversion tool is at https://github.com/Alexversify/clickwee/tree/main/tools\r\n")


# ------------------------------------------------------------------ previews
def write_previews(theme, regular_dir):
    out = ROOT / "previews" / theme["id"]
    shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    hot, anim = {}, {}
    for role, name in PREVIEW.items():
        p = find_win_file(regular_dir, name)
        if not p:
            continue
        frames = limit_frames(cl.read_windows_cursor(p))
        img, hx, hy, _ = frames[0]
        f = 64 / img.width
        small = [fr[0].resize((64, round(fr[0].height * f)), Image.LANCZOS) for fr in frames]
        small[0].save(out / f"{role}.png", optimize=True)
        hot[role] = [round(hx / img.width, 4), round(hy / img.height, 4)]
        if len(frames) > 1:
            strip = Image.new("RGBA", (64 * len(small), small[0].height))
            for i, s in enumerate(small):
                strip.paste(s, (64 * i, 0))
            strip.save(out / f"{role}-strip.png", optimize=True)
            anim[role] = [max(20, fr[3] or 50) for fr in frames]
    return hot, anim


# ------------------------------------------------------------------ main
def main():
    themes = json.load(open(ROOT / "tools" / "sources.json", encoding="utf-8"))
    built = {}
    catalog = []
    (ROOT / "packs").mkdir(exist_ok=True)
    for t in themes:
        print(t["id"])
        work = CACHE / "work" / t["id"]
        if t["kind"] == "upstream":
            z = download(t["zip"])
            root = Path(str(z) + ".d")
            if not root.exists():
                with zipfile.ZipFile(z) as zf:
                    zf.extractall(root)
            urls, rev = [t["zip"]], hashlib.sha1(t["zip"].encode()).hexdigest()[:10]
        else:
            packdir = ROOT / "packs" / t["id"]
            root = work
            if FORCE or not (packdir / "Regular.zip").exists() or not work.exists():
                shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
                if t["kind"] == "xcursor":
                    src = fetch(t["fetch"]) / t["path"]
                    build_from_x11(t, src, work)
                else:
                    build_recolor(t, built[t["base"]], work)
                # the license text travels with every pack (some upstream archives lack one)
                lic = ROOT / "tools" / "licenses" / f"{t['license']}.txt"
                shutil.rmtree(packdir, ignore_errors=True); packdir.mkdir(parents=True)
                for size in SIZES:
                    stage = CACHE / "stage" / t["id"]; shutil.rmtree(stage, ignore_errors=True); stage.mkdir(parents=True)
                    shutil.copytree(work / f"{t['id']}-{size}-Windows", stage / f"{t['id']}-{size}-Windows")
                    shutil.copy(lic, stage / "LICENSE.txt")
                    (stage / "README.txt").write_text(readme(t), encoding="utf-8")
                    zip_dir(stage, packdir / f"{size}.zip")
            h = hashlib.sha1()
            for size in SIZES:
                h.update((packdir / f"{size}.zip").read_bytes())
            rev = h.hexdigest()[:10]
            urls = [f"{REPO_RAW}/packs/{t['id']}/{{size}}.zip", f"{REPO_CDN}/packs/{t['id']}/{{size}}.zip"]
        built[t["id"]] = root
        hot, anim = write_previews(t, size_dir(root, "Regular"))
        entry = {k: t[k] for k in ("id", "name", "desc", "tags", "dark", "author", "license", "licenseUrl", "source")}
        if anim.get("default") and "anim" not in entry["tags"]:
            entry["tags"] = entry["tags"] + ["anim"]
        entry.update(urls=urls, rev=rev, hot=hot, anim=anim)
        catalog.append(entry)
    data = {"version": 1, "themes": catalog}
    (ROOT / "catalog.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(catalog)} themes")


if __name__ == "__main__":
    main()
