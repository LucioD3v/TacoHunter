"""Unit tests for the DynamoDB seed data in scripts/seed_stores.py.

These run inside the existing `unittest discover` suite (no CI YAML change
needed) and guard against malformed seed data: invalid specialty/vibe enums,
missing fields, duplicate store_ids, and out-of-range coordinates.

The seed script lives in scripts/, so that folder is added to sys.path before
importing it. Importing does not touch AWS.
"""

import os
import sys
import unittest

# Make scripts/ importable regardless of the working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(_HERE, os.pardir, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import seed_stores as seed  # noqa: E402  (import after sys.path setup)


class SeedDataTests(unittest.TestCase):
    def test_seed_data_passes_validation(self):
        errors = seed.validate(seed.STORES)
        self.assertEqual(errors, [], f"Seed data has validation errors: {errors}")

    def test_has_at_least_15_stores(self):
        self.assertGreaterEqual(len(seed.STORES), 15)

    def test_store_ids_are_unique(self):
        ids = [s["store_id"] for s in seed.STORES]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate store_id found")

    def test_specialties_and_vibes_are_valid_enums(self):
        for s in seed.STORES:
            self.assertIn(s["specialty"], seed.VALID_SPECIALTIES, s["name"])
            self.assertIn(s["vibe"], seed.VALID_VIBES, s["name"])

    def test_coordinates_are_in_valid_range(self):
        for s in seed.STORES:
            self.assertTrue(-90 <= s["lat"] <= 90, f"{s['name']} lat out of range")
            self.assertTrue(-180 <= s["lng"] <= 180, f"{s['name']} lng out of range")

    def test_variety_across_specialties_and_vibes(self):
        # A good demo set should exercise more than one specialty and vibe.
        specialties = {s["specialty"] for s in seed.STORES}
        vibes = {s["vibe"] for s in seed.STORES}
        self.assertGreaterEqual(len(specialties), 3)
        self.assertGreaterEqual(len(vibes), 3)


class ValidateNegativeTests(unittest.TestCase):
    """Confirm validate() actually rejects bad data (so the guard is real)."""

    def test_rejects_invalid_specialty(self):
        bad = [{
            "store_id": "x", "name": "Bad", "specialty": "tofu",
            "vibe": "nocturno", "address": "A", "lat": 19.4, "lng": -99.1,
        }]
        errors = seed.validate(bad)
        self.assertTrue(any("invalid specialty" in e for e in errors))

    def test_rejects_invalid_vibe(self):
        bad = [{
            "store_id": "x", "name": "Bad", "specialty": "pastor",
            "vibe": "zen", "address": "A", "lat": 19.4, "lng": -99.1,
        }]
        errors = seed.validate(bad)
        self.assertTrue(any("invalid vibe" in e for e in errors))

    def test_rejects_missing_field(self):
        bad = [{"store_id": "x", "name": "Bad", "specialty": "pastor"}]
        errors = seed.validate(bad)
        self.assertTrue(any("missing field" in e for e in errors))

    def test_rejects_duplicate_store_id(self):
        base = {
            "name": "Dup", "specialty": "pastor", "vibe": "nocturno",
            "address": "A", "lat": 19.4, "lng": -99.1,
        }
        bad = [dict(base, store_id="dup"), dict(base, store_id="dup")]
        errors = seed.validate(bad)
        self.assertTrue(any("duplicate store_id" in e for e in errors))

    def test_rejects_out_of_range_coordinates(self):
        bad = [{
            "store_id": "x", "name": "Bad", "specialty": "pastor",
            "vibe": "nocturno", "address": "A", "lat": 999, "lng": -999,
        }]
        errors = seed.validate(bad)
        self.assertTrue(any("out of range" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
