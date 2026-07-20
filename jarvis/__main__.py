"""Allow `python -m jarvis [gui]` to launch the CLI or the holographic GUI."""
import sys

if len(sys.argv) > 1 and sys.argv[1] == "gui":
    from jarvis.gui import main

    if __name__ == "__main__":
        main()
else:
    from jarvis.cli import main

    if __name__ == "__main__":
        main()
