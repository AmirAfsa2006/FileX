"""FileX executable entry point."""

from bot import Bot
from config import validate_required_config


def main() -> None:
    """Validate configuration and run the Pyrofork client."""
    validate_required_config()
    Bot().run()


if __name__ == "__main__":
    main()