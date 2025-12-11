"""
Presets Router - Load preset configurations.
"""

import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter
from pydantic import ValidationError

from api.schemas.preset import PresetSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/presets")

# Presets directory path
PRESETS_DIR = Path(__file__).parent.parent.parent / "presets"


@router.get("/", summary="List all presets", response_model=List[PresetSchema])
async def list_presets() -> List[PresetSchema]:
    """
    List all available preset configurations with full details.

    Returns:
        List of complete preset configurations (validated against schema)
    """
    presets = []

    if not PRESETS_DIR.exists():
        logger.warning(f"Presets directory not found: {PRESETS_DIR}")
        return presets

    for preset_file in sorted(PRESETS_DIR.glob("*.json")):
        try:
            with open(preset_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Add ID from filename
            data["id"] = preset_file.stem

            # Validate against schema
            preset = PresetSchema(**data)
            presets.append(preset)

        except ValidationError as e:
            logger.error(f"Invalid preset schema {preset_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load preset {preset_file}: {e}")

    return presets


@router.get("/schema", summary="Get preset schema")
async def get_preset_schema() -> dict:
    """
    Get the JSON schema for preset configuration.

    Returns:
        JSON schema definition for presets
    """
    return PresetSchema.model_json_schema()
