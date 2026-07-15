import sys
import os
import ctypes
from pathlib import Path

# Bundled lib (pyflowlauncher)
lib_dir = os.path.join(os.path.dirname(__file__), 'lib')
if os.path.isdir(lib_dir):
    sys.path.insert(0, lib_dir)

from pyflowlauncher import Plugin, Result
from pyflowlauncher.api import change_query, show_msg

plugin = Plugin()

# Supported image extensions
IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}


# ─── Helpers ───────────────────────────────────────────────

def _icon(name: str) -> str:
    return os.path.join(os.path.dirname(__file__), 'Images', name)


def _format_size(size_bytes: int) -> str:
    for unit in ('B', 'KB', 'MB'):
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


def _resolve_root() -> str:
    root = plugin.settings.get('wallpaper_root', '')
    if not root:
        root = os.path.expanduser('~/Pictures/Wallpapers')
    return os.path.abspath(root)


def _list_contents(current_dir: str, filter_text: str | None = None):
    """Return (dirs, images) sorted, or (None, None) on permission error."""
    try:
        entries = sorted(os.listdir(current_dir))
    except PermissionError:
        return None, None

    dirs, images = [], []
    for entry in entries:
        if entry.startswith('.'):
            continue
        fp = os.path.join(current_dir, entry)
        if os.path.isdir(fp):
            if filter_text is None or filter_text in entry.lower():
                dirs.append(entry)
        elif os.path.isfile(fp):
            ext = os.path.splitext(entry)[1].lower()
            if ext in IMG_EXTENSIONS:
                if filter_text is None or filter_text in entry.lower():
                    images.append(entry)
    return dirs, images


# ─── Query handler ─────────────────────────────────────────

@plugin.on_method
def query(query: str) -> list[Result]:
    """Main query handler — list folders and wallpapers."""
    results = []
    query = query.strip().replace('\\', '/')
    root = _resolve_root()

    # ── Validate root ─────────────────────────────────────
    if not os.path.isdir(root):
        results.append(Result(
            title="Root folder not found",
            subtitle=f"{root} — Set wallpaper_root in plugin settings and reload Flow",
            icon=_icon('app.png'),
        ))
        results.append(Result(
            title="Open QuickWall Settings",
            subtitle="Right-click or Flow Settings > Plugins > QuickWall",
            icon=_icon('app.png'),
            score=-2,
        ))
        return results

    # ── Parse relative path ───────────────────────────────
    rel_path = query.strip('/')
    if rel_path == '..':
        rel_path = ''

    current_dir = os.path.normpath(os.path.join(root, rel_path)) if rel_path else root

    # Non-existent path → treat as filter text
    filter_text = None
    if rel_path and not os.path.isdir(current_dir):
        parent_of_query = os.path.dirname(rel_path.rstrip('/'))
        if parent_of_query:
            pd = os.path.normpath(os.path.join(root, parent_of_query))
            current_dir = pd if os.path.isdir(pd) else root
        else:
            current_dir = root
        filter_text = rel_path.lower()

    # Safety: never escape root
    root_norm = root.rstrip('\\') + os.sep
    if not current_dir.startswith(root_norm) and current_dir != root:
        current_dir = root

    if not os.path.isdir(current_dir):
        return results

    # ── List contents ─────────────────────────────────────
    dirs, images = _list_contents(current_dir, filter_text)
    if dirs is None:
        results.append(Result(
            title="Permission denied",
            subtitle=f"Cannot read {current_dir}",
            icon=_icon('app.png'),
        ))
        return results

    display_rel = (
        '' if current_dir == root
        else os.path.relpath(current_dir, root).replace('\\', '/')
    )

    # ── Go Up button ──────────────────────────────────────
    if current_dir != root:
        parent_rel = os.path.dirname(display_rel) if display_rel else ''
        parent_rel = parent_rel.replace('\\', '/')
        r = Result(
            title=".. (Go Up)",
            subtitle=f"Back to {'root' if not parent_rel else parent_rel}",
            icon=_icon('up.png'),
            score=10,
        )
        r.add_action(_navigate_to, parameters=[parent_rel], dont_hide_after_action=True)
        results.append(r)

    # ── Location header ───────────────────────────────────
    header = display_rel if display_rel else '(root)'
    results.append(Result(
        title=header,
        subtitle=f"{len(dirs)} folders \u00b7 {len(images)} wallpapers  |  Root: {root}",
        icon=_icon('app.png'),
        score=-1,
    ))

    # ── Folder entries ────────────────────────────────────
    for d in dirs[:50]:
        child_rel = f"{display_rel}/{d}" if display_rel else d
        child_rel = child_rel.strip('/')
        r = Result(
            title=d,
            subtitle="Enter to browse",
            icon=_icon('folder.png'),
            score=10,
        )
        r.add_action(_navigate_to, parameters=[child_rel], dont_hide_after_action=True)
        results.append(r)

    # ── Image entries ─────────────────────────────────────
    for img_name in images[:50]:
        img_path = os.path.join(current_dir, img_name)
        size_str = _format_size(os.path.getsize(img_path))
        r = Result(
            title=img_name,
            subtitle=f"{size_str}  Enter to set wallpaper",
            icon=img_path,
            score=5,
        )
        r.add_action(_apply_wallpaper, parameters=[img_path])
        results.append(r)

    # ── Empty state ───────────────────────────────────────
    if not dirs and not images:
        results.append(Result(
            title="(empty)",
            subtitle="No images or folders here",
            icon=_icon('app.png'),
            score=-2,
        ))

    return results


# ─── Action handlers ───────────────────────────────────────

@plugin.on_method
def _navigate_to(rel_path: str):
    """Navigate into a subfolder by changing the query."""
    new_query = f"qw {rel_path}" if rel_path else "qw"
    return change_query(new_query, True)


@plugin.on_method
def _apply_wallpaper(image_path: str):
    """Set the given image as the desktop wallpaper."""
    try:
        abs_path = os.path.abspath(image_path)
        if not os.path.exists(abs_path):
            return show_msg("QuickWall", f"File not found:\n{abs_path}")

        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATE = 1 | 2  # SPIF_UPDATEINIFILE | SPIF_SENDCHANGE

        ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, abs_path, SPIF_UPDATE
        )

        return show_msg("QuickWall", f"Wallpaper set to:\n{os.path.basename(abs_path)}")

    except Exception as e:
        return show_msg("QuickWall Error", str(e))


if __name__ == '__main__':
    plugin.run()
