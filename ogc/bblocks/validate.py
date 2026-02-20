from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ogc.bblocks.util import fetch_yaml

try:
    import jsonschema as _jsonschema
    from referencing import Registry, Resource
except ImportError:
    _jsonschema = None
    Registry = None

try:
    from rdflib import Graph
    import pyshacl as _pyshacl
except ImportError:
    Graph = None
    _pyshacl = None

from ogc.bblocks.register import BuildingBlockSummary


class ValidationType(str, Enum):
    JSON = 'json'
    SHACL = 'shacl'


class ValidationError(Exception):
    pass


@dataclass
class ValidationResult:
    bblock_identifier: str
    validation_type: ValidationType
    valid: bool = True
    report: str | None = None
    exception: Exception | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def raise_for_invalid(self):
        if not self.valid:
            if self.exception:
                raise ValidationError() from self.exception
            else:
                raise ValidationError()


def _make_jsonschema_registry(bblock: BuildingBlockSummary) -> 'Registry':
    cache = {}

    def retrieve(uri: str):
        if bblock.schema and uri in bblock.schema.values():
            return Resource.from_contents(bblock.resolved_schema)

        if uri not in cache:
            cache[uri] = fetch_yaml(uri)
        return Resource.from_contents(cache[uri])

    return Registry(retrieve=retrieve)


def validate_json(bblock: BuildingBlockSummary, data: Any) -> ValidationResult:
    if _jsonschema is None:
        raise ImportError(
            "jsonschema is required for JSON validation. "
            "Install it with: pip install bblocks_client[jsonschema]"
        )
    schema = bblock.resolved_schema
    if not schema:
        raise ValueError(f"No JSON schema available for {bblock.item_identifier}")
    result = ValidationResult(bblock_identifier=bblock.item_identifier,
                              validation_type=ValidationType.JSON)
    try:
        registry = _make_jsonschema_registry(bblock)
        _jsonschema.validate(instance=data, schema=schema, registry=registry)
    except _jsonschema.exceptions.ValidationError as e:
        result.valid = False
        result.exception = e
    return result


def validate_shacl(bblock: BuildingBlockSummary, data: Graph) -> ValidationResult:
    if _pyshacl is None:
        raise ImportError(
            "rdflib and pyshacl are required for SHACL validation. "
            "Install them with: pip install bblocks_client[rdf]"
        )
    result = ValidationResult(bblock_identifier=bblock.item_identifier, validation_type=ValidationType.SHACL)
    if bblock.shacl_shapes:
        shacl_graph = Graph()
        for shacl_bblock_id, shacl_urls in bblock.shacl_shapes.items():
            for shacl_url in shacl_urls:
                shacl_graph.parse(shacl_url, format='ttl')
        conforms, results_graph, results_text = _pyshacl.validate(data_graph=data, shacl_graph=shacl_graph)
        result.valid = conforms
        result.extra['shacl_graph'] = results_graph
        result.report = results_text
    return result
