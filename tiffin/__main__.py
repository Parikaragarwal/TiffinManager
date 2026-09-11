import sys
import typer
from tiffin.cli import app


def main():
    try:
        app()
    except (KeyboardInterrupt, typer.Abort):
        print("\n\033[33m👋 Interrupted. Exiting Tiffin CLI.\033[0m")
        sys.exit(0)
    except Exception as err:
        print(f"\n\033[31m✗ Error: {err}\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
