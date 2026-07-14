# QuickWall

A Flow Launcher plugin for browsing local wallpaper folders and setting wallpapers with Enter.

Browse your wallpaper collection by folder, filter by name, and apply any image as the desktop wallpaper — all without leaving Flow Launcher.

## Usage

| Input | Action |
|-------|--------|
| `qw` | Show root folder contents |
| `qw foldername` | Enter a subfolder |
| `qw ..` | Go up one level |
| `qw partial_name` | Filter results by name |
| Enter on a folder | Browse inside it |
| Enter on an image | Set as desktop wallpaper |

## Installation

### Via Flow Launcher Plugin Store (recommended)

1. Open Flow Launcher
2. Type `pm install QuickWall`
3. Press Enter
4. Type `plugin reload`, then `qw` to start

### Manual

1. Download the latest `QuickWall.zip` from [Releases](https://github.com/yazan/QuickWall/releases)
2. Extract to `%APPDATA%\FlowLauncher\Plugins\QuickWall-1.0.0\`
3. Open Flow Launcher and type `plugin reload`
4. Type `qw` to start browsing

## Configuration

Open Flow Launcher Settings → Plugins → QuickWall:

| Setting | Description |
|---------|-------------|
| **wallpaper_root** | Full path to your wallpaper folder (e.g. `C:\Users\you\Pictures\Wallpapers`). Default: `~/Pictures/Wallpapers`. |

After changing settings, type `plugin reload` or restart Flow Launcher.

## Requirements

- Windows 10 or 11
- [Flow Launcher](https://www.flowlauncher.com/) v2.0.0+
- Python 3.8+ (bundled with Flow Launcher installation)

## Supported formats

`.jpg` `.jpeg` `.png` `.bmp` `.gif` `.webp` `.tiff` `.tif`

## License

MIT

---

*Vibe-coded with [Hermes Agent](https://hermes-agent.nousresearch.com)*
