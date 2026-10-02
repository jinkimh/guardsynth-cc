"""Restricted-free review export fixtures used by multiple GuardSynth tests."""


def image_review_export() -> dict:
    def record(review_id: str, scene_id: str, tags: list[str]) -> dict:
        return {
            "scene_tags": tags,
            "scene_id": scene_id,
            "image_filename": f"{scene_id}.jpg",
            "slot_id": "",
            "image_usability": "USABLE",
            "other_scene_description": "",
            "primary_situation": "ROAD_USER_IN_EGO_PATH",
            "visual_hazard": "TRUE",
            "subject_description": "화면의 보행자",
            "conflict_region": "CROSSWALK_VISIBLE",
            "subject_position": "IN_CONFLICT_REGION",
            "occlusion": "UNOBSTRUCTED",
            "traffic_control": "NONE_VISIBLE",
            "ego_motion": "APPEARS_MOVING",
            "temporal_change": "ENTERING",
            "human_disposition": "VISUAL_HAZARD_CANDIDATE",
            "review_confidence": "HIGH",
            "override_reason": "",
            "review_id": review_id,
            "recommended_disposition": "VISUAL_HAZARD_CANDIDATE",
            "reason_codes": ["IMAGE_ONLY_CANNOT_ESTABLISH_SOURCE_CLOSURE"],
            "review_completed_at": "2026-08-11T19:00:00Z",
            "reviewer_id": "reviewer-A",
            "review_version": "guardsynth-image-only-scene-review-v0.2",
            "metadata_availability": "NOT_AVAILABLE_FROM_IMAGE",
            "contract_readiness": "REVIEW_REQUIRED",
            "review_complete": True,
            "image_bytes_included": False,
            "notes": "",
        }

    return {
        "review_version": "guardsynth-image-only-scene-review-v0.2",
        "exported_at": "2026-08-11T19:10:00Z",
        "input_class": "IMAGE_ONLY",
        "image_bytes_included": False,
        "records": [
            record("IMG-001", "scene-001", ["PEDESTRIAN", "CROSSWALK"]),
            record("IMG-002", "scene-002", ["PEDESTRIAN", "FOLLOWING"]),
        ],
    }
