"""Main entry point for aicodegencrew CLI."""

import sys

from .cli import main as cli_main


def main():
    """Entry point — injects 'run' command if no subcommand is provided."""
    if len(sys.argv) == 1 or (
        len(sys.argv) > 1 and sys.argv[1] not in ("run", "index", "list", "plan", "codegen", "-h", "--help", "--env")
    ):
        sys.argv.insert(1, "run")
    cli_main()


# Alias for pyproject.toml entry point
run = main


if __name__ == "__main__":
    main()
