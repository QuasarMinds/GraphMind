"""
Install tree-sitter grammars for GraphMind.
Run: python scripts/install_grammars.py
"""

import subprocess
import sys


PACKAGES = [
    "tree-sitter>=0.21",
    "tree-sitter-python>=0.21",
    "tree-sitter-javascript>=0.21",
]


def main():
    print("Installing tree-sitter grammar packages...")
    for pkg in PACKAGES:
        print(f"  pip install {pkg}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr}")
        else:
            print(f"  OK")
    print("\nDone. Verify with: python -c \"import tree_sitter_python; print('OK')\"")


if __name__ == "__main__":
    main()
