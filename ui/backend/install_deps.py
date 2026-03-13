"""Extract dependencies from pyproject.toml and write to deps.txt.

Used during Docker build to install all Python dependencies from
the single source of truth (pyproject.toml) instead of a separate
requirements.txt.

Usage: python install_deps.py /path/to/pyproject.toml /path/to/deps.txt
"""
import sys
import tomllib


def main():
    if len(sys.argv) != 3:
        print("Usage: python install_deps.py PYPROJECT_PATH OUTPUT_PATH")
        sys.exit(1)

    pyproject_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    deps = config["project"]["dependencies"]

    # Add server dependencies not in pyproject.toml
    # (pyproject.toml defines the CLI tool, Docker needs the ASGI server too)
    server_deps = [
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "python-multipart>=0.0.9",
    ]

    all_deps = deps + server_deps

    with open(output_path, "w") as f:
        for dep in all_deps:
            f.write(dep + "\n")

    print(f"Wrote {len(all_deps)} dependencies to {output_path}")


if __name__ == "__main__":
    main()
