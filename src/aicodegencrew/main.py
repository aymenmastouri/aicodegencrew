"""Main entry point for crewai run command."""
import sys
from .cli import main as cli_main


def main():
    """Entry point for crewai run - injects 'run' command if not provided."""
    # When called via 'crewai run', no args are passed
    # We need to inject 'run' as the default command
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] not in ('run', 'index', 'list', '-h', '--help')):
        # Insert 'run' as first argument
        sys.argv.insert(1, 'run')
    cli_main()


# Alias for pyproject.toml entry point
run = main


if __name__ == "__main__":
    main()
