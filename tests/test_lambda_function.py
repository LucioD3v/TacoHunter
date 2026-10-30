"""Unit tests for the pure helpers in lambda_function.py.

These tests exercise logic that does NOT call AWS services:
  - parse_intent (Bedrock output parsing / validation)
  - store_matches / filter_stores (DynamoDB result filtering)
  - build_prompt (prompt construction)
  - build_response (CORS response shaping)

Importing lambda_function creates boto3 clients, but constructing a client
does not make a network call, so no AWS credentials are required to import
or to run these tests. A default region is set to avoid NoRegionError on
environments without AWS config.
"""

import json
import os
import unittest

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import lambda_function as lf  # noqa: E402  (import after env setup)


class ParseIntentTests(unittest.TestCase):
    def test_parses_plain_json(self):
        raw = '{"specialty": "pastor", "vibe": "crudo", "search_keywords": ["pastor"]}'
        result = lf.parse_intent(raw)
        self.assertEqual(result["specialty"], "pastor")
        self.assertEqual(result["vibe"], "crudo")
        self.assertEqual(result["search_keywords"], ["pastor"])

    def test_strips_markdown_code_fences(self):
        raw = '```json\n{"specialty": "suadero", "vibe": "nocturno", "search_keywords": []}\n```'
        result = lf.parse_intent(raw)
        self.assertEqual(result["specialty"], "suadero")
        self.assertEqual(result["vibe"], "nocturno")

    def test_isolates_json_from_surrounding_prose(self):
        raw = 'Claro, aquí tienes: {"specialty": "carnitas", "vibe": "familiar", "search_keywords": ["carnitas"]} ¡buen provecho!'
        result = lf.parse_intent(raw)
        self.assertEqual(result["specialty"], "carnitas")
        self.assertEqual(result["vibe"], "familiar")

    def test_invalid_specialty_falls_back_to_all(self):
        raw = '{"specialty": "tofu", "vibe": "zen", "search_keywords": []}'
        result = lf.parse_intent(raw)
        self.assertEqual(result["specialty"], "all")
        self.assertEqual(result["vibe"], "all")

    def test_missing_fields_default_to_all(self):
        raw = "{}"
        result = lf.parse_intent(raw)
        self.assertEqual(result["specialty"], "all")
        self.assertEqual(result["vibe"], "all")
        self.assertEqual(result["search_keywords"], [])

    def test_keywords_coerced_to_strings(self):
        raw = '{"specialty": "all", "vibe": "all", "search_keywords": [1, true, "x"]}'
        result = lf.parse_intent(raw)
        self.assertEqual(result["search_keywords"], ["1", "True", "x"])

    def test_non_list_keywords_become_empty_list(self):
        raw = '{"specialty": "all", "vibe": "all", "search_keywords": "pastor"}'
        result = lf.parse_intent(raw)
        self.assertEqual(result["search_keywords"], [])

    def test_case_insensitive_enum_values(self):
        raw = '{"specialty": "PASTOR", "vibe": "Nocturno", "search_keywords": []}'
        result = lf.parse_intent(raw)
        self.assertEqual(result["specialty"], "pastor")
        self.assertEqual(result["vibe"], "nocturno")

    def test_raises_on_non_json(self):
        with self.assertRaises(json.JSONDecodeError):
            lf.parse_intent("no json here at all")


class StoreMatchTests(unittest.TestCase):
    def _store(self, specialty, vibe):
        return {"specialty": specialty, "vibe": vibe}

    def test_exact_match(self):
        store = self._store("pastor", "nocturno")
        self.assertTrue(lf.store_matches(store, "pastor", "nocturno"))

    def test_specialty_mismatch(self):
        store = self._store("carnitas", "nocturno")
        self.assertFalse(lf.store_matches(store, "pastor", "nocturno"))

    def test_all_specialty_is_wildcard(self):
        store = self._store("carnitas", "nocturno")
        self.assertTrue(lf.store_matches(store, "all", "nocturno"))

    def test_all_vibe_is_wildcard(self):
        store = self._store("pastor", "familiar")
        self.assertTrue(lf.store_matches(store, "pastor", "all"))

    def test_all_all_matches_everything(self):
        store = self._store("barbacoa", "crudo")
        self.assertTrue(lf.store_matches(store, "all", "all"))

    def test_match_is_case_insensitive_on_store_values(self):
        store = self._store("Pastor", "Nocturno")
        self.assertTrue(lf.store_matches(store, "pastor", "nocturno"))


class FilterStoresTests(unittest.TestCase):
    def setUp(self):
        self.stores = [
            {"store_id": "1", "name": "A", "specialty": "pastor",
             "vibe": "nocturno", "lat": 19.4, "lng": -99.1, "extra": "drop me"},
            {"store_id": "2", "name": "B", "specialty": "carnitas",
             "vibe": "familiar", "lat": 19.5, "lng": -99.2},
        ]

    def test_filters_by_specialty(self):
        result = lf.filter_stores(self.stores, "pastor", "all")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["store_id"], "1")

    def test_projects_only_expected_fields(self):
        result = lf.filter_stores(self.stores, "pastor", "all")
        self.assertNotIn("extra", result[0])
        self.assertEqual(
            set(result[0].keys()),
            {"store_id", "name", "specialty", "vibe", "address", "lat", "lng"},
        )

    def test_all_all_returns_everything(self):
        result = lf.filter_stores(self.stores, "all", "all")
        self.assertEqual(len(result), 2)


class BuildPromptTests(unittest.TestCase):
    def test_includes_user_prompt_and_demands_json(self):
        prompt = lf.build_prompt("tacos al pastor para la cruda")
        self.assertIn("tacos al pastor para la cruda", prompt)
        self.assertIn("JSON", prompt)
        self.assertIn("specialty", prompt)
        self.assertIn("search_keywords", prompt)


class BuildResponseTests(unittest.TestCase):
    def test_cors_headers_and_json_body(self):
        resp = lf.build_response(200, {"ok": True})
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(resp["headers"]["Access-Control-Allow-Origin"], "*")
        self.assertEqual(json.loads(resp["body"]), {"ok": True})

    def test_serializes_decimal_values(self):
        from decimal import Decimal
        resp = lf.build_response(200, {"lat": Decimal("19.5"), "n": Decimal("3")})
        body = json.loads(resp["body"])
        self.assertEqual(body["lat"], 19.5)
        self.assertEqual(body["n"], 3)


if __name__ == "__main__":
    unittest.main()
