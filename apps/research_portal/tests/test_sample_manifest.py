import copy
import unittest

from apps.research_portal.sample_manifest import (
    M16_OUTCOMES,
    M16_SLICES,
    REQUIRED_SOURCE_FIELDS,
    SampleManifestError,
    validate_sample_manifest,
)


def valid_m16_manifest():
    samples = []
    index = 0
    for slice_index, slice_name in enumerate(M16_SLICES):
        extra = {2 * slice_index, 2 * slice_index + 1}
        for outcome_index, outcome in enumerate(M16_OUTCOMES):
            count = 4 if outcome_index in extra else 3
            for _ in range(count):
                index += 1
                samples.append(
                    {
                        "sample_id": f"sample-{index:03d}",
                        "slice": slice_name,
                        "outcome": outcome,
                        "source_closure": "SOURCE_COMPLETE",
                        "required_sources": {
                            field: {"source_id": f"src-{index:03d}-{field.replace('_', '-')}", "sha256": f"{index:064x}"[-64:]}
                            for field in REQUIRED_SOURCE_FIELDS
                        },
                        "reason_codes": [],
                    }
                )
    return {
        "schema_version": 1,
        "project_id": "guardsynth-coc",
        "review_round_id": "m16-round-001",
        "review_type": "M16_EXPERT_PILOT",
        "classification": "RESTRICTED",
        "samples": samples,
    }


class SampleManifestTest(unittest.TestCase):
    def test_locked_m16_manifest_closes_all_source_and_quota_gates(self):
        report = validate_sample_manifest(valid_m16_manifest())

        self.assertEqual(report["distinct_samples"], 60)
        self.assertEqual(report["source_complete"], 60)
        self.assertTrue(report["slice_quota_ready"])
        self.assertTrue(report["outcome_quota_ready"])
        self.assertTrue(report["joint_cells_ready"])
        self.assertTrue(report["source_cohort_ready"])
        self.assertRegex(report["manifest_hash"], r"^[a-f0-9]{64}$")

    def test_duplicate_sample_and_missing_source_field_fail_closed(self):
        manifest = valid_m16_manifest()
        manifest["samples"][1]["sample_id"] = manifest["samples"][0]["sample_id"]
        del manifest["samples"][0]["required_sources"]["coordinate_transform"]

        with self.assertRaises(SampleManifestError) as caught:
            validate_sample_manifest(manifest)
        self.assertIn("duplicate sample_id", str(caught.exception))

    def test_image_only_round_cannot_establish_source_closure(self):
        manifest = copy.deepcopy(valid_m16_manifest())
        manifest["review_type"] = "IMAGE_ONLY_SCENE_REVIEW"

        with self.assertRaisesRegex(SampleManifestError, "IMAGE_ONLY_CANNOT_ESTABLISH_SOURCE_CLOSURE"):
            validate_sample_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
