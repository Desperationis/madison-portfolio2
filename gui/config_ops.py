"""Read/write config.yaml — site name, navigation items, footer copyright."""

from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

_REQUIRED_KEYS = {
    "site_name": str,
    "navigation": list,
    "footer": dict,
}


def read_config() -> dict:
    """Read and validate config.yaml, returning the parsed dict."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    text = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML in {CONFIG_PATH}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {CONFIG_PATH}, got {type(data).__name__}")

    _validate_config(data)

    return data


def _validate_config(data: dict) -> None:
    """Validate that data has all required keys and types."""
    if not isinstance(data, dict):
        raise ValueError(f"Expected a dict, got {type(data).__name__}")

    for key, expected_type in _REQUIRED_KEYS.items():
        if key not in data:
            raise ValueError(f"missing required key: {key}")
        if not isinstance(data[key], expected_type):
            raise ValueError(
                f"key '{key}' must be {expected_type.__name__}, got {type(data[key]).__name__}"
            )

    if "copyright" not in data.get("footer", {}):
        raise ValueError("missing required key: footer.copyright")


def write_config(data: dict) -> None:
    """Validate and atomically write config data to config.yaml."""
    _validate_config(data)

    tmp_path = CONFIG_PATH.with_suffix(".yaml.tmp")
    tmp_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    tmp_path.rename(CONFIG_PATH)


def update_site_name(name: str) -> None:
    """Set site_name in config.yaml. Raises ValueError if name is empty/whitespace."""
    if not name or not name.strip():
        raise ValueError("site_name must not be empty or whitespace-only")
    config = read_config()
    config["site_name"] = name
    write_config(config)


def update_footer_copyright(text: str) -> None:
    """Set footer.copyright in config.yaml. Raises ValueError if text is empty."""
    if not text or not text.strip():
        raise ValueError("footer copyright must not be empty or whitespace-only")
    config = read_config()
    config["footer"]["copyright"] = text
    write_config(config)


def get_nav_items() -> list[dict]:
    """Return the navigation list from config.yaml (list of {label, url} dicts)."""
    return read_config()["navigation"]


def add_nav_item(label: str, url: str) -> list[dict]:
    """Append a nav item and write back. Return the updated list."""
    if not label or not label.strip():
        raise ValueError("label must not be empty")
    if not url or not url.strip():
        raise ValueError("url must not be empty")
    config = read_config()
    config["navigation"].append({"label": label, "url": url})
    write_config(config)
    return config["navigation"]


def update_nav_item(index: int, label: str, url: str) -> list[dict]:
    """Update the nav item at index. Return the updated list."""
    if not label or not label.strip():
        raise ValueError("label must not be empty")
    if not url or not url.strip():
        raise ValueError("url must not be empty")
    config = read_config()
    nav = config["navigation"]
    if index < 0 or index >= len(nav):
        raise IndexError(f"nav index {index} out of range (0–{len(nav) - 1})")
    nav[index] = {"label": label, "url": url}
    write_config(config)
    return nav


def delete_nav_item(index: int) -> list[dict]:
    """Remove the nav item at index. Return the updated list."""
    config = read_config()
    nav = config["navigation"]
    if index < 0 or index >= len(nav):
        raise IndexError(f"nav index {index} out of range (0–{len(nav) - 1})")
    nav.pop(index)
    write_config(config)
    return nav


def reorder_nav_items(new_order: list[int]) -> list[dict]:
    """Rearrange nav items per new_order (a permutation of indices). Return updated list."""
    config = read_config()
    nav = config["navigation"]
    if sorted(new_order) != list(range(len(nav))):
        raise ValueError(f"new_order must be a permutation of range({len(nav)}), got {new_order}")
    config["navigation"] = [nav[i] for i in new_order]
    write_config(config)
    return config["navigation"]
