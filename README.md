# bblocks-client

A Python client library for working with [OGC Blocks](https://ogcincubator.github.io/bblocks-docs/) registers.

OGC Blocks are reusable specification components that support validation, semantic annotation via JSON-LD,
and federation across distributed registers.

## Installation

```bash
pip install bblocks_client
```

Optional extras for validation and semantic uplift:

```bash
# JSON Schema validation
pip install bblocks_client[jsonschema]

# SHACL validation and semantic uplift (RDF/JSON-LD)
pip install bblocks_client[rdf]

# All extras
pip install bblocks_client[all]
```

## Usage

### Loading a register

```python
from ogc.bblocks.register import load_register

register = load_register("https://example.org/bblocks/register.json")

# Look up a block by identifier
bblock = register.get_item_summary("my.org.bblock-id")
```

Imported registers (dependencies) are loaded automatically. Pass `load_dependencies=False` to skip this.

### Accessing block metadata

`get_item_summary()` returns a `BuildingBlockSummary` with lightweight metadata.
`get_item_full()` fetches the full `BuildingBlock`, including examples and semantic uplift configuration.

```python
bblock = register.get_item_full("my.org.bblock-id")

print(bblock.name)
print(bblock.status)        # Status enum: stable, experimental, etc.
print(bblock.depends_on)    # Set of dependency identifiers
print(bblock.ld_context)    # URL to JSON-LD context
print(bblock.schema)        # Dict of media-type -> schema URL
```

### JSON Schema validation

Requires `bblocks_client[jsonschema]`.

```python
from ogc.bblocks.validate import validate_json

result = validate_json(bblock, {"type": "Feature", ...})
if not result.valid:
    print(result.exception)

# Or raise directly:
result.raise_for_invalid()
```

### SHACL validation

Requires `bblocks_client[rdf]`.

```python
from rdflib import Graph
from ogc.bblocks.validate import validate_shacl

graph = Graph().parse("data.ttl")
result = validate_shacl(bblock, graph)
print(result.report)
result.raise_for_invalid()
```

### Semantic uplift (JSON to RDF)

Requires `bblocks_client[rdf]`.

```python
from ogc.bblocks.semantic_uplift import uplift_json

rdf_graph = uplift_json(bblock, {"name": "Alice", ...})
print(rdf_graph.serialize(format="turtle"))
```

This applies the block's JSON-LD context to the input data, producing an RDF graph.
Pre- and post-processing steps (jq, SPARQL, SHACL rules) defined in the block are applied automatically.

## License

Apache 2.0
