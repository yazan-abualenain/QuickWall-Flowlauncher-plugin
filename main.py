import sys
import os
import ctypes

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from flox import Flox

IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}


class QuickWall(Flox):
    """Flow Launcher plugin for browsing and setting desktop wallpapers.

    Usage:
      qw              → show root folder
      qw foldername   → enter subfolder
      qw ..           → go up
      qw <filter>     → filter by name

    Enter on an image applies it as the desktop wallpaper.
    """

    def query(self, query):
        query = query.strip().replace('\\', '/')

        # Resolve root — prefer RPC settings (most current),
        # fall back to file settings, then default
        rpc_settings = getattr(self, '_settings', None) or {}
        root = rpc_settings.get('wallpaper_root', '') or ''
        if not root:
            root = self.settings.get('wallpaper_root', '')
        if not root:
            root = os.path.expanduser('~/Pictures/Wallpapers')
        root = os.path.abspath(root)
        self._root = root

        if not os.path.isdir(root):
            self._show_not_found(root)
            return

        # Parse relative path
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
                if os.path.isdir(pd):
                    current_dir = pd
                else:
                    current_dir = root
            else:
                current_dir = root
            filter_text = rel_path.lower()

        # Safety: never escape root
        if not current_dir.startswith(root.rstrip('\\') + os.sep) and current_dir != root:
            current_dir = root

        # List directory
        if not os.path.isdir(current_dir):
            return
        try:
            entries = sorted(os.listdir(current_dir))
        except PermissionError:
            self.add_item(
                title="Permission denied",
                subtitle=f"Cannot read {current_dir}",
                icon=self._icon('app.png'),
            )
            return

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

        # Display path
        display_rel = '' if current_dir == root else os.path.relpath(current_dir, root).replace('\\', '/')

        # Go Up button
        if current_dir != root:
            parent_rel = os.path.dirname(display_rel) if display_rel else ''
            parent_rel = parent_rel.replace('\\', '/')
            self.add_item(
                title=".. (Go Up)",
                subtitle=f"Back to {'root' if not parent_rel else parent_rel}",
                icon=self._icon('up.png'),
                method=self._navigate_to,
                parameters=[parent_rel],
                auto_complete_text=f"{self.action_keyword} "
                if not parent_rel
                else f"{self.action_keyword} {parent_rel}/",
                dont_hide=True,
            )

        # Location header
        header = display_rel if display_rel else '(root)'
        self.add_item(
            title=f"{header}",
            subtitle=f"{len(dirs)} folders \u00b7 {len(images)} wallpapers  |  Root: {root}",
            icon=self._icon('app.png'),
            score=-1,
        )

        # Folder results
        for d in dirs[:50]:
            child_rel = f"{display_rel}/{d}" if display_rel else d
            child_rel = child_rel.strip('/')
            self.add_item(
                title=d,
                subtitle="Enter to browse",
                icon=self._icon('folder.png'),
                method=self._navigate_to,
                parameters=[child_rel],
                auto_complete_text=f"{self.action_keyword} {child_rel}/",
                score=10,
                dont_hide=True,
            )

        # Image results
        for img_name in images[:50]:
            img_path = os.path.join(current_dir, img_name)
            size_str = self._format_size(os.path.getsize(img_path))

            self.add_item(
                title=img_name,
                subtitle=f"{size_str}  Enter to set wallpaper",
                icon=img_path,
                method=self._apply_wallpaper,
                parameters=[img_path],
                score=5,
            )

        # Empty
        if not dirs and not images:
            self.add_item(
                title="(empty)",
                subtitle="No images or folders here",
                icon=self._icon('app.png'),
                score=-2,
            )

    # ── Navigation ────────────────────────────────────────

    def _navigate_to(self, rel_path):
        new_query = f"{self.action_keyword} {rel_path}" if rel_path else self.action_keyword
        self.change_query(new_query, True)

    # ── Apply wallpaper ───────────────────────────────────

    def _apply_wallpaper(self, image_path):
        try:
            abs_path = os.path.abspath(image_path)
            if not os.path.exists(abs_path):
                self._show_message("QuickWall", f"File not found:\n{abs_path}")
                return

            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATE = 1 | 2  # SPIF_UPDATEINIFILE | SPIF_SENDCHANGE

            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, abs_path, SPIF_UPDATE
            )

            self._show_message(
                "QuickWall",
                f"Wallpaper set to:\n{os.path.basename(abs_path)}"
            )
        except Exception as e:
            self._show_message("QuickWall Error", str(e))

    # ── Error states ──────────────────────────────────────

    def _show_not_found(self, root):
        self.add_item(
            title="Root folder not found",
            subtitle=f"{root} — Set wallpaper_root in plugin settings and reload Flow",
            icon=self._icon('app.png'),
        )
        self.add_item(
            title="Open QuickWall Settings",
            subtitle="Right-click this result or Flow Settings > Plugins > QuickWall",
            icon=self._icon('app.png'),
            score=-2,
        )

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _format_size(size_bytes):
        for unit in ('B', 'KB', 'MB'):
            if size_bytes < 1024:
                return f"{size_bytes:.0f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} GB"

    @staticmethod
    def _icon(name):
        return os.path.join(os.path.dirname(__file__), 'Images', name)

    def _show_message(self, title, message):
        try:
            self.show_msg(title, message)
        except Exception:
            pass


if __name__ == '__main__':
    QuickWall()
