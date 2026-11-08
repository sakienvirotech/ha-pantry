"""Grocy product userfields that the App options say to show.

Grocy lets each household add its own product fields, such as a shelf or a
box. The App options name the ones to fill in when creating a product.
"""
import logging
from datetime import date
from typing import Any

from pydantic import BaseModel

from .grocy import Grocy, GrocyError

logger = logging.getLogger(__name__)

PRESET_TYPES = {"preset-list", "preset-checklist"}
SUPPORTED_TYPES = PRESET_TYPES | {
    "text-single-line",
    "number-integral",
    "number-decimal",
    "checkbox",
    "date",
}
MAX_TEXT_LENGTH = 1000


class UserfieldDef(BaseModel):
    name: str
    caption: str
    type: str
    # Kept exactly as Grocy has them, as some end in a space.
    options: list[str] = []
    required: bool = False
    default: str | None = None


class UserfieldValue(BaseModel):
    caption: str
    value: str


def product_userfields(grocy: Grocy, wanted: list[str]) -> list[UserfieldDef]:
    """The configured product userfields Grocy has, in the configured order."""
    if not wanted:
        return []
    found = {}
    for row in grocy.get("objects/userfields"):
        if row.get("entity") != "products":
            continue
        if row.get("type") not in SUPPORTED_TYPES:
            if row.get("name") in wanted:
                logger.warning(
                    "Userfield %s has type %s, which HA-Pantry can't show",
                    row.get("name"),
                    row.get("type"),
                )
            continue
        found[row["name"]] = UserfieldDef(
            name=row["name"],
            caption=row.get("caption") or row["name"],
            type=row["type"],
            options=[
                line for line in (row.get("config") or "").splitlines() if line.strip()
            ]
            if row["type"] in PRESET_TYPES
            else [],
            required=bool(int(row.get("input_required") or 0)),
            default=row.get("default_value") or None,
        )
    for name in wanted:
        if name not in found:
            logger.warning("Grocy has no usable product userfield called %s", name)
    return [found[name] for name in wanted if name in found]


def checked_values(
    fields: list[UserfieldDef], values: dict[str, str | None]
) -> dict[str, str]:
    """The values to save, or a 422 GrocyError naming the first bad one.

    Names that aren't configured are dropped, and blank values aren't saved.
    """
    checked = {}
    for field in fields:
        value = values.get(field.name)
        if value is None or not value.strip():
            if field.required:
                raise GrocyError(422, f"{field.caption} is required.")
            continue
        if not valid(field, value):
            raise GrocyError(422, f"{value.strip()} isn't a valid {field.caption}.")
        checked[field.name] = value
    return checked


def valid(field: UserfieldDef, value: str) -> bool:
    if field.type == "preset-list":
        return value in field.options
    if field.type == "preset-checklist":
        # Grocy keeps several ticked options as one comma-separated value.
        return value in field.options or all(
            part in field.options for part in value.split(",")
        )
    if field.type == "checkbox":
        return value in {"0", "1"}
    if field.type == "number-integral":
        return value.strip().lstrip("-").isdigit()
    if field.type == "number-decimal":
        try:
            float(value)
        except ValueError:
            return False
        return True
    if field.type == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    return len(value) <= MAX_TEXT_LENGTH


def shown_values(
    fields: list[UserfieldDef], stored: dict[str, Any] | None
) -> list[UserfieldValue]:
    """A product's values for the configured fields, as people read them."""
    shown = []
    for field in fields:
        value = (stored or {}).get(field.name)
        if value is None or not str(value).strip():
            continue
        text = str(value).strip()
        if field.type == "checkbox":
            if text != "1":
                continue
            text = "Yes"
        shown.append(UserfieldValue(caption=field.caption, value=text))
    return shown
