"""
Build script for Wagner Windows executable.
Usage: python build.py
"""

import os
import sys
import shutil
import subprocess


def build():
    print("=== Building Wagner.exe ===")

    static_dir = os.path.join(os.path.dirname(__file__), 'wagner', 'static')
    if not os.path.isdir(static_dir):
        print(f"ERROR: static dir not found: {static_dir}")
        sys.exit(1)

    dist_dir = os.path.join(os.path.dirname(__file__), 'dist')
    os.makedirs(dist_dir, exist_ok=True)

    sep = ';' if sys.platform == 'win32' else ':'
    static_dest = 'wagner/static'
    if sys.platform == 'win32':
        static_dest = 'wagner\\static'

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--name', 'Wagner',
        '--add-data', f'{static_dir}{sep}{static_dest}',
        '--icon', os.path.join(os.path.dirname(__file__), 'icon.ico'),
        '--hidden-import', 'acd',
        '--hidden-import', 'acd.acd',
        '--hidden-import', 'flask',
        '--hidden-import', 'werkzeug',
        '--hidden-import', 'jinja2',
        '--hidden-import', 'jinja2.ext',
        '--hidden-import', 'webview',
        '--hidden-import', 'webview.platforms.winforms' if sys.platform == 'win32' else 'webview.platforms.cocoa',
        '--collect-all', 'acd',
        '--clean',
        '--noconfirm',
        os.path.join(os.path.dirname(__file__), 'wagner', 'app.py'),
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    if result.returncode != 0:
        print("PyInstaller failed!")
        sys.exit(result.returncode)

    exe = os.path.join(os.path.dirname(__file__), 'dist', 'Wagner.exe')
    if os.path.exists(exe):
        size_mb = os.path.getsize(exe) / (1024 * 1024)
        print(f"Built: {exe} ({size_mb:.1f} MB)")
    else:
        print("Build completed but .exe not found? Check dist/")
        for f in os.listdir(dist_dir):
            print(f"  {f}")


if __name__ == '__main__':
    build()
