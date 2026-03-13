"""Ensure __init__.pyc exists for all Python packages.

After bytecode compilation and source removal, some packages may
lack __init__.pyc files. This script creates empty ones so Python
can resolve package imports correctly.

Usage: python ensure_init.py /app
"""
import os
import pathlib
import py_compile
import sys
import tempfile


def ensure_init_files(root_dir: str) -> None:
    for d in pathlib.Path(root_dir).rglob("*"):
        if d.is_dir() and any(d.glob("*.pyc")):
            init = d / "__init__.pyc"
            if not init.exists():
                # Create empty __init__.pyc from a blank .py file
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".py", delete=False, mode="w"
                )
                tmp.write("")
                tmp.close()
                py_compile.compile(tmp.name, str(init), doraise=True)
                os.unlink(tmp.name)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ensure_init.py ROOT_DIR")
        sys.exit(1)
    ensure_init_files(sys.argv[1])
