"""Build a self-contained zip of the app for testing, so you can poke at
features from a throwaway copy without touching the source tree.

The copy shares nothing with the source at runtime except code; point it at a
sandbox data dir with ITACLI_DATA_DIR so it also won't touch your real data.
"""
import os
import zipfile

from . import __version__

INCLUDE_FILES = ["run.py", "README.md", "SPECS.txt", "requirements.txt"]
INCLUDE_PKG = "itacli"
SKIP = {"__pycache__", ".git", ".DS_Store"}


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_zip(dest=None):
    root = _project_root()
    dest = dest or os.path.join(os.path.expanduser("~/Desktop"),
                                "itacli-test-%s.zip" % __version__)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for name in INCLUDE_FILES:
            p = os.path.join(root, name)
            if os.path.isfile(p):
                z.write(p, os.path.join("itacli-app", name))
        pkg = os.path.join(root, INCLUDE_PKG)
        for dirpath, dirnames, filenames in os.walk(pkg):
            dirnames[:] = [d for d in dirnames if d not in SKIP]
            for fn in filenames:
                if fn in SKIP or fn.endswith((".pyc", ".db")):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root)
                z.write(full, os.path.join("itacli-app", rel))
    return dest
