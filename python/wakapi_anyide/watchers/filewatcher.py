import logging
import time
from asyncio import Task
from asyncio.queues import Queue
from asyncio.taskgroups import TaskGroup
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Dict

from aiofiles import open
from pathspec import PathSpec

from wakapi_anyide._rust.watch import Watch
from wakapi_anyide._rust.watch import WatchEventType
from wakapi_anyide.helpers.filediffer import autosave_masking
from wakapi_anyide.helpers.filediffer import File
from wakapi_anyide.helpers.filediffer import human_to_bytes
from wakapi_anyide.helpers.filediffer import process_file_change
from wakapi_anyide.models.environment import Environment
from wakapi_anyide.watchers.types import Event
from wakapi_anyide.watchers.types import Watcher

logger = logging.getLogger()


def bytes_to_human(size: int):
    if size == 0:
        return "(empty)"

    for i, suffix in enumerate(["B", "KiB", "MiB", "GiB", "TiB"]):
        if 1024**i < size < 1024 ** (i + 1):
            return f"{(size / (1024**i)):.2f} {suffix}"

    return f"{(size / 1024**6):.2f} PiB"


def format_file(file: File):
    color = "red" if file.too_large else "bright_black"
    extra = "  [yellow]Large file[/yellow]" if file.too_large else ""
    return f"{file.path}  [{color}]{bytes_to_human(file.size)}[/{color}]{extra}"


class FileWatcher(Watcher):
    """
    Watches filesystem events for file changes.
    """

    current_file: File | None = None
    env: Environment
    task: Task
    cache: Dict[str, File] = dict()

    def __init__(self, env: Environment):
        self.env = env

    @staticmethod
    def normalise(path: Path):
        return f"./{(path.relative_to(Path('./').absolute()))}"

    async def _task(self, queue: Queue[Event]):
        excluded_pathspecs = self.env.project.files.exclude.copy()
        max_size = human_to_bytes(self.env.project.files.large_file_threshold)

        for file in self.env.project.files.exclude_files:
            async with open(file, "r") as file:
                excluded_pathspecs.extend(await file.readlines())

        included_paths = PathSpec.from_lines(
            "gitwildmatch", self.env.project.files.include
        )
        excluded_paths = PathSpec.from_lines("gitwildmatch", excluded_pathspecs)

        watch = Watch()
        watch.add_watch("./", True)

        logger.info("Watched files:")

        for path in included_paths.match_tree("./"):
            resolved_path = self.normalise(Path("./").absolute() / Path(path))

            if excluded_paths.match_file(resolved_path):
                continue

            try:
                file = await File.read(resolved_path)
                file.max_size = max_size
            except Exception as e:
                logger.error(e)
                continue

            self.cache[resolved_path] = file
            logger.info(f"  {format_file(file)}")

        logger.info("Watching!")

        async for ev_list in watch:
            for event in ev_list:
                logger.debug(f"Got event: {event}")
                resolved_path = self.normalise(Path(event.target))

                if not included_paths.match_file(
                    resolved_path
                ) or excluded_paths.match_file(resolved_path):
                    continue

                if event.kind == WatchEventType.Delete:
                    new_file = File.empty(resolved_path)
                else:
                    try:
                        new_file = await File.read(resolved_path)
                        file.max_size = max_size
                    except OSError as e:
                        if not Path(resolved_path).is_dir():
                            logger.warning(
                                f"Failed to open a file: {e} (maybe it was deleted very quickly)"
                            )

                        continue

                if self.cache.get(resolved_path) is None:
                    logger.info(f"New file found: {format_file(new_file)} ")
                    self.cache[resolved_path] = File.empty(resolved_path)

                if self.current_file is None:
                    self.current_file = new_file

                    continue

                if self.current_file.path != resolved_path:
                    logger.debug(
                        f"File changed (was {self.current_file.path}, now {resolved_path})"
                    )
                    new_file, old_file = autosave_masking(
                        new_file=self.current_file,
                        old_file=self.cache[self.current_file.path],
                        env=self.env,
                        cache=self.cache,
                    )
                    
                    event = None
                    # Skip adding this to queue if the autosave needs to be ignored
                    if new_file is not None and old_file is not None:
                        event = process_file_change(
                            new_file,
                            old_file,
                            time=time.time(),
                            env=self.env,
                        )

                    if event is not None:
                        await queue.put(event)

                    self.cache[resolved_path] = self.current_file

                if new_file is not None: self.current_file = new_file

    async def setup(self, tg: TaskGroup, emit_event: Queue[Event]):
        self.task = tg.create_task(self._task(emit_event))

    async def shutdown(self):
        pass

    async def resolve_events(self) -> AsyncGenerator[Event, None]:
        if self.current_file is not None:
            new_file, old_file = autosave_masking(
                new_file=self.current_file,
                old_file=self.cache[self.current_file.path],
                env=self.env,
                cache=self.cache,
            )
            # Skip adding this to queue if the autosave needs to be ignored
            if new_file is not None and old_file is not None:
            
                event = process_file_change(
                    new_file,
                    old_file,
                    time=time.time(),
                    env=self.env,
                )

                if event is not None:
                    yield event

            self.cache[self.current_file.path] = self.current_file
            self.current_file = None
