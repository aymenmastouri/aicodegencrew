"""Compile Python source to bytecode and remove .py files.

Usage: python compile_bytecode.py DIR1 [DIR2 ...]

Compiles all .py files to .pyc (optimized), removes .py source,
and flattens __pycache__ directories so .pyc files sit next to
where .py files were.
"""
import compileall
import glob
import os
import sys


def compile_and_strip(directories: list[str]) -> None:
    # Step 1: Compile all .py to .pyc
    for d in directories:
        compileall.compile_dir(d, force=True, quiet=1, optimize=2)

    # Step 2: Remove .py source files (keep only .pyc)
    for d in directories:
        for py in glob.glob(os.path.join(d, "**", "*.py"), recursive=True):
            pyc_dir = os.path.join(os.path.dirname(py), "__pycache__")
            if os.path.isdir(pyc_dir):
                os.remove(py)

    # Step 3: Flatten __pycache__/ — move .pyc up, remove empty dirs
    for d in directories:
        for root, dirs, files in os.walk(d, topdown=False):
            if os.path.basename(root) == "__pycache__":
                parent = os.path.dirname(root)
                for f in files:
                    # module.cpython-312.opt-2.pyc → module.pyc
                    new_name = f.split(".")[0] + ".pyc"
                    os.rename(
                        os.path.join(root, f),
                        os.path.join(parent, new_name),
                    )
                os.rmdir(root)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compile_bytecode.py DIR1 [DIR2 ...]")
        sys.exit(1)
    compile_and_strip(sys.argv[1:])
