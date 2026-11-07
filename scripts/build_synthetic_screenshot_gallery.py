"""Build a local gallery of real Blender-rendered synthetic CI PNGs.

Only CBDK-authored fixture render paths are accepted. Do not pass user GLBs or
private screenshots to public CI; screenshots here are synthetic-only evidence.
"""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import shutil

VIEWS = ("front", "back", "right", "left", "top", "bottom", "iso")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def build_gallery(root: Path) -> int:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("CI evidence root does not exist")
    gallery = root / "screenshot_gallery"
    if gallery.exists():
        raise ValueError("Gallery destination already exists; do not overwrite")
    items = []
    for view in VIEWS:
        items.append((f"Reference / {view}", f"glb_preview/{view}.png"))
    for view in ("front", "right", "top", "iso"):
        items.append((f"Silhouette drift / {view}", f"glb_drift_preview/{view}.png"))
    for index in (0, 1):
        items.append((f"Reference part {index + 1}", f"glb_preview/objects/{index:03}.png"))

    # Validate everything before creating output. This is an index of real
    # PNG render output, not AI-generated imagery or mesh screenshots.
    verified = []
    for title, relative in items:
        source = (root / relative).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError(f"Missing or unsafe synthetic Blender render: {relative}")
        size = source.stat().st_size
        if not 100 <= size <= 10 * 1024 * 1024:
            raise ValueError(f"Invalid synthetic PNG size: {relative}")
        with source.open("rb") as handle:
            if handle.read(8) != PNG_MAGIC:
                raise ValueError(f"Invalid synthetic PNG signature: {relative}")
        filename = relative.replace("/", "_")
        verified.append((title, source, filename))

    gallery.mkdir()
    cards = []
    for title, source, filename in verified:
        shutil.copyfile(source, gallery / filename)
        cards.append(
            f'<figure><img src="{escape(filename, quote=True)}" '
            f'alt="{escape(title, quote=True)}" loading="lazy">'
            f'<figcaption>{escape(title)}</figcaption></figure>'
        )
    content = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline'">
<title>CBDK Synthetic Blender Render Gallery</title>
<style>
body{background:#101622;color:#edf1f7;font:16px system-ui,sans-serif;margin:0 auto;max-width:1250px;padding:28px}
h1{margin:0 0 10px}p{color:#bdc9db;line-height:1.6}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}
figure{margin:0;background:#1e293b;border:1px solid #334155;border-radius:12px;overflow:hidden}
img{display:block;width:100%;height:235px;object-fit:contain;background:#283444}
figcaption{padding:12px;font-size:14px}
</style></head><body>
<h1>CBDK / Blender 実レンダリング画像集</h1>
<p>実際のBlender CIで生成したCBDK自作・合成テストモデルのPNGです。
参考モデル、輪郭差のある比較モデル、部品別プレビューを収録しています。
生成されたレンダリング画像であり、Blender画面のGUIスクリーンショットではありません。
私有ユーザーデータや実モデルの検証結果ではありません。</p>
<section class="grid">
""" + "\n".join(cards) + """
</section></body></html>
"""
    (gallery / "index.html").write_text(content, encoding="utf-8")
    return len(cards)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci-root", type=Path, default=Path("reports/ci"))
    args = parser.parse_args()
    count = build_gallery(args.ci_root)
    print(f"CBDK_SYNTHETIC_BLENDER_GALLERY_PASS {count} real render PNGs")


if __name__ == "__main__":
    main()
