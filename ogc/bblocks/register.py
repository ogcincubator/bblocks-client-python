import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import dacite

from ogc.bblocks.util import fetch_yaml

logger = logging.getLogger(__name__)

_CAMEL_OVERRIDES = {
    "gitHubRepository": "github_repository",
}

YamlLoader = Callable[[str], Any]


def to_snake_case(name: str) -> str:
    if name in _CAMEL_OVERRIDES:
        return _CAMEL_OVERRIDES[name]
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def snake_keys(d: Any) -> Any:
    """Recursively convert dict keys from camelCase to snake_case."""
    if isinstance(d, dict):
        return {to_snake_case(k): snake_keys(v) for k, v in d.items()}
    if isinstance(d, list):
        return [snake_keys(i) for i in d]
    return d


class Status(str, Enum):
    RETIRED = "retired"
    SUPERSEDED = "superseded"
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    UNDER_DEVELOPMENT = "under-development"
    INVALID = "invalid"
    RESERVED = "reserved"
    SUBMITTED = "submitted"


@dataclass
class Source:
    title: str
    link: str | None = None


@dataclass
class ExampleSnippet:
    language: str
    code: str
    url: str | None = None


@dataclass
class Example:
    snippets: list[ExampleSnippet] = field(default_factory=list)
    title: str | None = None
    content: str | None = None
    base_uri: str | None = None
    prefixes: dict[str, str] = field(default_factory=dict)


@dataclass
class Link:
    rel: str
    href: str
    type: str | None = None
    title: str | None = None


@dataclass
class DocumentationEntry:
    mediatype: str
    url: str

class SemanticUpliftAdditionalStepStage(str, Enum):
    PRE = 'pre'
    POST = 'post'

@dataclass
class SemanticUpliftAdditionalStep:
    type: str
    stage: SemanticUpliftAdditionalStepStage
    ref: str | None = None
    code: str | None = None


@dataclass
class SemanticUplift:
    additional_steps: list[SemanticUpliftAdditionalStep] = field(default_factory=list)


class ItemClass(str, Enum):
    SCHEMA = "schema"
    DATATYPE = "datatype"
    PATH = "path"
    PARAMETER = "parameter"
    HEADER = "header"
    COOKIE = "cookie"
    RESPONSE = "response"
    API = "api"
    MODEL = "model"


@dataclass
class BuildingBlockSummary:
    item_identifier: str
    name: str
    abstract: str | None = None
    status: Status | None = None
    date_time_addition: str | None = None
    item_class: ItemClass | None = None
    register: str | None = None  # raw register name string from JSON
    version: str | None = None
    date_of_last_change: str | None = None
    maturity: str | None = None
    scope: str | None = None
    group: str | None = None
    highlighted: bool = False
    validation_passed: bool = False
    sources: list[Source] = field(default_factory=list)
    depends_on: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    shacl_shapes: dict[str, list[str]] = field(default_factory=dict)
    schema: dict[str, str] = field(default_factory=dict)
    ld_context: str | None = None
    ontology: str | None = None
    source_schema: str | None = None
    source_ld_context: str | None = None
    source_files: str | None = None
    source_open_api_document: str | None = None
    open_api_document: str | None = None
    test_outputs: str | None = None
    rdf_data: list[str] = field(default_factory=list)
    documentation: dict[str, DocumentationEntry] = field(default_factory=dict)
    is_profile_of: list[str] = field(default_factory=list)
    extension_points: dict[str, Any] = field(default_factory=dict)
    transforms: list[dict[str, Any]] = field(default_factory=list)

    # back-reference, populated by BuildingBlockRegister.from_dict
    source_register: 'BuildingBlockRegister | None' = field(default=None, init=False, repr=False)

    def _get_cached_yaml(self, url: str) -> Any:
        if not url:
            return None
        cache = self.source_register._url_cache
        if url in cache:
            return cache[url]
        data = self.source_register.yaml_loader(url)
        cache[url] = data
        return data

    @property
    def resolved_schema(self) -> dict | None:
        return self._get_cached_yaml(
            self.schema.get('application/yaml', self.schema.get('application/json'))
            if self.schema else None
        )

    @property
    def resolved_ld_context(self) -> dict | None:
        return self._get_cached_yaml(self.ld_context)


@dataclass
class BuildingBlock(BuildingBlockSummary):
    annotated_schema: str | None = None
    git_repository: str | None = None
    git_path: str | None = None
    examples: list[Example] = field(default_factory=list)
    summary: BuildingBlockSummary | None = None
    semantic_uplift: SemanticUplift = field(default_factory=SemanticUplift)


@dataclass
class BuildingBlockRegister:
    name: str
    abstract: str | None = None
    description: str | None = None
    modified: str | None = None
    git_repository: str | None = None
    github_repository: str | None = None
    base_url: str | None = None
    viewer_url: str | None = None
    validation_report: str | None = None
    validation_report_json: str | None = None
    sparql_endpoint: str | None = None
    remote_cache_dir: str | None = None
    imports: list[str] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    tooling: dict[str, Any] = field(default_factory=dict)
    bblocks: dict[str, BuildingBlockSummary] = field(default_factory=dict, init=False)
    imported_registers: list['BuildingBlockRegister'] = field(default_factory=list, init=False, repr=False)
    url: str | None = None
    _bblocks_cache: dict[str, BuildingBlock] = field(default_factory=dict, init=False, repr=False)
    _url_cache: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    yaml_loader: YamlLoader = fetch_yaml

    def get_item_summary(self, identifier: str) -> BuildingBlockSummary | None:
        if bblock := self.bblocks.get(identifier):
            return bblock
        for reg in self.imported_registers:
            if bblock := reg.bblocks.get(identifier):
                logger.debug('Summary for %s found in register %s', identifier, reg.url)
                return bblock
        return None

    def get_item_full(self, identifier: str) -> BuildingBlock | None:
        logger.debug('Fetching remote item %s', identifier)
        summary = self.get_item_summary(identifier)
        if summary is None:
            logger.debug('No summary found for %s', identifier)
            return None
        bblock = summary.source_register._bblocks_cache.get(identifier)
        if not bblock:
            data = self.yaml_loader(summary.documentation['json-full'].url)
            bblock = dacite.from_dict(BuildingBlock, snake_keys(data),
                                      config=dacite.Config(
                                          cast=[Status, ItemClass, SemanticUpliftAdditionalStepStage, set]))
            bblock.summary = summary
            bblock.source_register = summary.source_register
            summary.source_register._bblocks_cache[identifier] = bblock
        else:
            logger.debug('Remote item %s found in cache', identifier)

        return bblock


def _load_register(url: str,
                   load_dependencies=True,
                   _seen_registers: dict[str, BuildingBlockRegister] | None = None,
                   yaml_loader: YamlLoader = fetch_yaml) -> BuildingBlockRegister:
    logger.debug('Fetching register %s', url)
    data = yaml_loader(url)
    bblocks_raw = data.pop('bblocks', [])

    register = dacite.from_dict(
        BuildingBlockRegister,
        snake_keys(data),
        config=dacite.Config(cast=[Status, ItemClass]),
    )
    register.url = url
    register.yaml_loader = yaml_loader
    for bblock_raw in bblocks_raw:
        bblock = dacite.from_dict(
            BuildingBlockSummary,
            snake_keys(bblock_raw),
            config=dacite.Config(cast=[Status, ItemClass, set]),
        )
        bblock.source_register = register
        register.bblocks[bblock.item_identifier] = bblock

    if _seen_registers is None:
        _seen_registers = {}
    _seen_registers[url] = register

    if load_dependencies:
        if not register.imports:
            logger.debug('Register %s has no dependencies', url)
        else:
            logger.debug('Loading %d dependencies for %s', len(register.imports), url)
            imported_urls = {url}
            for import_url in register.imports:
                if import_url in imported_urls:
                    continue
                imported_register = _seen_registers.get(import_url)
                imported_urls.add(import_url)
                if not imported_register:
                    imported_register = _load_register(import_url, load_dependencies=True,
                                                       _seen_registers=_seen_registers)

                register.imported_registers.append(imported_register)
                for rec_imported_register in imported_register.imported_registers:
                    if rec_imported_register.url not in imported_urls:
                        register.imported_registers.append(rec_imported_register)
                        imported_urls.add(rec_imported_register.url)

    return register


def load_register(url: str,
                  load_dependencies=True,
                  yaml_loader: YamlLoader = fetch_yaml) -> BuildingBlockRegister:
    return _load_register(url, load_dependencies=load_dependencies, yaml_loader=yaml_loader)
