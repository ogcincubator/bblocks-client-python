import unittest

from ogc.bblocks.semantic_uplift import _apply_jsonld_context

LD_CONTEXT = {'@context': {'name': 'http://schema.org/name'}}


class ApplyJsonldContextTest(unittest.TestCase):

    def test_list_data_wrapped_in_graph(self):
        data = [{'name': 'Alice'}, {'name': 'Bob'}]
        result = _apply_jsonld_context(LD_CONTEXT, data)
        self.assertEqual(result['@context'], LD_CONTEXT['@context'])
        self.assertEqual(result['@graph'], data)

    def test_dict_without_context_gets_context_added(self):
        data = {'name': 'Alice'}
        result = _apply_jsonld_context(LD_CONTEXT, data)
        self.assertEqual(result['@context'], LD_CONTEXT['@context'])
        self.assertEqual(result['name'], 'Alice')

    def test_dict_with_string_context_data_context_has_priority(self):
        data = {'@context': 'http://example.org/ctx', 'name': 'Alice'}
        result = _apply_jsonld_context(LD_CONTEXT, data)
        # bblock context first, data context last (data wins on conflicts)
        self.assertIsInstance(result['@context'], list)
        self.assertEqual(result['@context'][0], LD_CONTEXT['@context'])
        self.assertEqual(result['@context'][1], 'http://example.org/ctx')
        self.assertEqual(result['name'], 'Alice')

    def test_dict_with_list_context_data_context_has_priority(self):
        existing = ['http://example.org/ctx1', {'age': 'http://schema.org/age'}]
        data = {'@context': existing, 'name': 'Alice'}
        result = _apply_jsonld_context(LD_CONTEXT, data)
        self.assertEqual(result['@context'], [LD_CONTEXT['@context']] + existing)
        self.assertEqual(result['name'], 'Alice')

    def test_original_data_not_mutated(self):
        data = {'@context': 'http://example.org/ctx', 'name': 'Alice'}
        original_keys = set(data.keys())
        _apply_jsonld_context(LD_CONTEXT, data)
        self.assertEqual(set(data.keys()), original_keys)
        self.assertEqual(data['@context'], 'http://example.org/ctx')


if __name__ == '__main__':
    unittest.main()
