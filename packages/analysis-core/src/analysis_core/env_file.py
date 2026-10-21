"""Load the user's .env file."""

from dotenv import find_dotenv, load_dotenv


def load_env_file(override: bool = False) -> bool:
    """Load .env from the current working directory or its parents.

    Without a path, python-dotenv searches upward from the calling module's file,
    i.e. the installed package rather than the user's project directory.
    """
    return load_dotenv(find_dotenv(usecwd=True), override=override)
