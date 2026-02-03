"""
AI Code Generation Crew - Package Entry Point

Usage:
    python -m aicodegencrew run              Run SDLC pipeline
    python -m aicodegencrew index            Index repository  
    python -m aicodegencrew list             List available phases
    python -m aicodegencrew --help           Show help
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
