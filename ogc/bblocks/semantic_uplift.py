import json
import logging
from typing import Any

import jq
import pyshacl
from ogc.bblocks.register import BuildingBlock, BuildingBlockSummary, SemanticUpliftAdditionalStepStage
from ogc.bblocks.util import fetch_url
from rdflib import Graph

logger = logging.Logger(__name__)


def _apply_uplift_steps(bblock: BuildingBlock, stage: SemanticUpliftAdditionalStepStage, data):
    logger.debug('Applying %s uplift steps for %s', stage, bblock.item_identifier)
    for step in bblock.semantic_uplift.additional_steps:
        if step.stage == stage:
            step_code = step.code
            if not step_code and step.ref:
                # Code is not inlined, but stored in remotely (URL in `ref`)
                logger.debug('Fetching step code from')
                step_code = fetch_url(step.ref)

            logger.debug('Applying %s %s uplift step', step.stage, step.type)
            if step.type == 'shacl':
                shacl_graph = Graph().parse(data=step_code, format='ttl')
                pyshacl.validate(data_graph=data, shacl_graph=shacl_graph, in_place=True, advanced=True)
            elif step.type == 'sparql-update':
                data.update(step_code)
            elif step.type == 'sparql-construct':
                data = data.query(step_code).graph
            elif step.type == 'jq':
                data = jq.compile(step_code).input_value(data).first()
            else:
                raise NotImplementedError(f"Unknown uplift type {step.type}")

    return data


def _apply_jsonld_context(ld_context: dict, data: dict | list) -> dict:
    if isinstance(data, list):
        return {
            '@context': ld_context['@context'],
            '@graph': data,
        }
    if '@context' in data:
        existing_context = data['@context']
        jsonld_data = {k: v for k, v in data.items() if k != '@context'}
        new_context = [ld_context['@context']]
        if isinstance(existing_context, list):
            new_context.extend(existing_context)
        else:
            new_context.append(existing_context)
        jsonld_data['@context'] = new_context
        return jsonld_data
    return {
        '@context': ld_context['@context'],
        **data,
    }


def uplift_json(bblock: BuildingBlockSummary, data: Any, base_uri=None) -> Graph:
    if not isinstance(bblock, BuildingBlock):
        # need to resolve fully for potential semantic uplift steps
        bblock = bblock.source_register.get_item_full(bblock.item_identifier)
    ld_context = bblock.resolved_ld_context

    _apply_uplift_steps(bblock, SemanticUpliftAdditionalStepStage.PRE, data)
    jsonld_data = _apply_jsonld_context(ld_context, data)
    rdf_graph = Graph().parse(data=json.dumps(jsonld_data), format='json-ld', base=base_uri)
    return _apply_uplift_steps(bblock, SemanticUpliftAdditionalStepStage.POST, rdf_graph)
