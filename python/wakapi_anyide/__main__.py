import asyncio
import logging
from json import dumps
from pathlib import Path
from typing import Annotated
from typing import TypeAlias

import typer

from wakapi_anyide import __version__
from wakapi_anyide.models.config import WakatimeConfig
from wakapi_anyide.models.environment import Environment
from wakapi_anyide.models.project import Project
from wakapi_anyide.runner import run

logger = logging.getLogger(__name__)


DEFAULT_IGNOREFILES = [".gitignore"]
TEMPLATE = """
# https://github.com/iamawatermelo/wakapi-anyide v{version}

[meta]
version = 1
watchers = ['files']

[files]
include = {include}  # files to include in tracking
exclude = {exclude}  # files to exclude in tracking
exclude_files = {exclude_files}  # files whose contents will be used to exclude other files from tracking
exclude_binary_files = true  # whether to ignore binary files
language_mapping = {language_mapping} # custom language mapping
editor_mapping = {editor_mapping} # custom editor mapping
large_file_threshold = "64KiB" # files larger than this will not do precise line diffing, it will only count total lines. 
# It is recommended to set the threshold to 0 for thousands of files, because they are all stored in RAM
# Make sure to capture all relavant groups that would be part of the original file. Don't include the extension in the captures though, the extension is already determined.
# Also make sure to double escape, TOML uses backslashes for line breaks already
autosave_masking = {".kicad_sch" = {"regex" = "(^.*)(?:\\.kicad_sch-bak)", folder = ""}}

[project]
name = "{name}"  # your project name
"""

# Note that not all feilds have to be filled, they will default to their types' empty status
PROJECT_PRESETS = {
    "kicad" : {
        "include": ["*.kicad_pcb", "*.kicad_pcb-bak", "*.kicad_sch", "*.kicad_sch-bak"],
        "exclude": ["*.zip", "*fp-info-cache", "*#auto_saved_files#"],
        "language_mapping": {".kicad_sch": "KiCAD Schematic", ".kicad_pcb": "KiCAD PCB"},
        "editor_mapping": {".kicad_sch": "kicad", ".kicad_pcb": "kicad"}
    },
    "cpp" : {
        "include": ["*.cpp", "*.h"],
        "exclude": ["*.so", "*.dll", "*.lib",  "*.o", "*.log", "*.log.*", "*.exe", "*.out", "*.d"],
    },
    "python" : {
        "include": ["*.py"],
        "exclude": ["*.whl", "*.gz", "*.pyd", "*.pyc"],   
    },
    "rust" : {
        "include": ["*.rs"],
        "exclude": ["Cargo.lock", "*target*", "target/", "debug/", "**/*.rs.bk"],
    },
    "go" : {
        "include": ["*.go"], 
        "exclude": ["*.mod", "*.go.sum", "*.so", "*.dll", "*.lib",  "*.o", "*.log", "*.log.*", "*.a"],
    },
    "c" : {
        "include": ["*.c", "*.h"],
        "exclude": ["*.so", "*.dll", "*.lib",  "*.o", "*.log", "*.log.*", "*.exe", "*.out", "*.d"],
    },
    "blender" : {
        "include": ["*.blend"],
        "language_mapping": {".blend": "Blender"},
        "editor_mapping": {".blend": "blender"}
    },
    "freecad" : {
        "include": ["*.FCStd", "*.FCBak"],
        "language_mapping": {".FCStd": "FreeCAD"},
        "editor_mapping": {".FCStd": "freecad"}
    },
    "manual" : {
        "include": ["*"],
    }
}

app = typer.Typer(
    pretty_exceptions_enable=False  # they don't report asyncio taskgroup exceptions correctly
)

try:
    from rich.highlighter import Highlighter
    from rich.text import Text

    class NoHighlights(Highlighter):
        def highlight(self, text: Text) -> None:
            pass
except ImportError:
    pass


def setup_logging(is_verbose: bool):
    try:
        from rich.logging import RichHandler

        logging.basicConfig(
            level="DEBUG" if is_verbose else "INFO",
            format="[bold magenta]{module}[/bold magenta][bright_black]:{funcName}@{lineno:03}[/bright_black]  {message}",
            style="{",
            datefmt="[%X]",
            handlers=[
                RichHandler(
                    highlighter=NoHighlights(),
                    rich_tracebacks=True,
                    markup=True,
                    show_time=False,
                    show_path=False,
                )
            ],
        )
    except ImportError:
        logging.basicConfig(
            level="DEBUG" if is_verbose else "INFO",
            format="{levelname} {filename}:{funcName}@{lineno:03} {message}",
            style="{",
            datefmt="[%X]",
        )
        logger.warning("Rich is not available, using basic logging (pip install rich?)")


Verbose: TypeAlias = Annotated[bool, typer.Option("--verbose", callback=setup_logging)]


def start(is_test):
    asyncio.run(
        run(
            Environment(
                is_test_only=is_test,
                config=WakatimeConfig(),  # type: ignore
                project=Project(),  # type: ignore
            )
        )
    )


@app.command()
def test(verbose: Verbose = False):
    start(True)


@app.command()
def track(verbose: Verbose = False):
    start(False)


@app.command()
def version():
    print(f"wakapi-anyide v{__version__}")


def prompt(prompt, default: str | None = None):
    try:
        from rich import get_console

        return (
            get_console().input(
                f"[bold magenta]{prompt}[/bold magenta] [cyan](default {default})[/cyan]\n[bright_cyan]>>> [bright_cyan]"
            )
            or default
        )
    except ImportError:
        return input(f"{prompt}\n>>> ") or default


def prompt_choices(prompt, choices, default):
    try:
        from rich import get_console

        response = get_console().input(
            f"[bold magenta]{prompt} {repr(choices)}[/bold magenta] [cyan](default {default})[/cyan]\n[bright_cyan]>>> [bright_cyan]"
        )
    except ImportError:
        response = input(f"{prompt} {repr(choices)} (default {default})\n>>> ")

    if response == "":
        return default

    if response in choices:
        return response
    else:
        raise ValueError("response not allowed")


def prompt_yn(prompt, default: bool):
    prompt_str = "[Y/n]" if default else "[y/N]"

    try:
        from rich import get_console

        response = get_console().input(
            f"[bold magenta]{prompt}[/bold magenta] [cyan]\\{prompt_str}: [cyan]"
        )
    except ImportError:
        response = input(f"{prompt} {prompt_str}: ")

    if response == "":
        return default

    if response.lower() not in ("y", "n"):
        raise ValueError("expected y or n")

    return response.lower() == "y"


@app.command()
def setup():
    output = Path("wak.toml")
    if output.exists():
        raise Exception("a wak.toml already exists in this directory")

    included_paths = list()
    excluded_paths = list()
    exclude_files = list()
    language_mapping = dict()
    editor_mapping = dict()

    project_name = prompt(
        "What's your project name?", default=Path("./").absolute().name
    )
    choice = prompt_choices("Would you like to use one of these presets? If not, enter 'manual'", list(PROJECT_PRESETS.keys()), "manual")
    if choice != "manual":
        project = PROJECT_PRESETS[choice]
        included_paths = project.get("include", [])
        excluded_paths = project.get("exclude", [])
        exclude_files = project.get("exclude_files", [])
        language_mapping = project.get("language_mapping", {})
        editor_mapping = project.get("editor_mapping", {})
    
    else: 
        
        if prompt_yn("Would you like to watch all files in the directory?", True):
            included_paths.append("*")
        elif prompt_yn("Would you like to add include paths?", True):
            while True:
                included_paths.append(
                    prompt("Please enter a path to include in gitignore format (e.g /src)")
                )

                if not prompt_yn("Would you like to add another include path?", True):
                    break

        if prompt_yn("Would you like to add exclude paths?", False):
            while True:
                excluded_paths.append(
                    prompt(
                        "Please enter a path to exclude in gitignore format (e.g /node_modules)"
                    )
                )

                if not prompt_yn("Would you like to add another exclude path?", False):
                    break
                
        if prompt_yn("Would you like to add custom language mappings?", False):
            while True:
                language = prompt("Please enter a language (e.g Python)")
                mapping = prompt("Please enter a file extension (e.g .py)")
                language_mapping[language] = mapping

                if not prompt_yn("Would you like to add another language mapping?", False):
                    break
                
        if prompt_yn("Would you like to add custom editor mappings?", False):
            while True:
                editor = prompt("Please enter an editor (e.g wakapi-anyide)")
                mapping = prompt("Please enter a file extension (e.g .py)")
                editor_mapping[editor] = mapping

                if not prompt_yn("Would you like to add another editor mapping?", False):
                    break

    exclude_files = []
    for file in DEFAULT_IGNOREFILES:
        if Path(file).exists():
            exclude_files.append(file)

    with open(output, "w") as file:
        file.write(
            TEMPLATE.format(
                version=__version__,
                include=dumps(included_paths),
                exclude=dumps(excluded_paths),
                exclude_files=dumps(exclude_files),
                language_mapping=dumps(language_mapping).replace(":", " ="),
                editor_mapping=dumps(editor_mapping).replace(":", " ="),
                name=project_name,
            ).strip()
        )


if __name__ == "__main__":
    app()
