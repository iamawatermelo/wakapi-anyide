from typing import List
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic_settings import TomlConfigSettingsSource
from pydantic_settings.main import SettingsConfigDict


class ProjectMeta(BaseModel):
    version: Literal[1]
    watchers: List[str] = ["files"]


class ProjectFiles(BaseModel):
    include: List[str]
    exclude: List[str]
    exclude_files: List[str]
    exclude_binary_files: bool = True
    language_mapping: dict = {}
    editor_mapping: dict = {}
    large_file_threshold: str = "64KiB"
    autosave_masking: dict = {"fileext": {"regex": "", "folder": ""}}


class ProjectDescription(BaseModel):
    name: str


class Project(BaseSettings):
    model_config = SettingsConfigDict(toml_file="wak.toml")

    meta: ProjectMeta
    files: ProjectFiles
    project: ProjectDescription

    @classmethod
    def settings_customise_sources(cls, settings_cls, *_args, **_kwargs):
        return (TomlConfigSettingsSource(settings_cls),)
