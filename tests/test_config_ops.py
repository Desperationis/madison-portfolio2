"""Tests for gui.config_ops — config round-trip and validation."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from gui.config_ops import (
    CONFIG_PATH,
    add_nav_item,
    delete_nav_item,
    get_nav_items,
    read_config,
    reorder_nav_items,
    update_footer_copyright,
    update_nav_item,
    update_site_name,
    write_config,
)


def test_round_trip():
    """Read config.yaml, write it back, read again — data should be identical."""
    original = read_config()
    write_config(original)
    reloaded = read_config()
    assert reloaded == original


@pytest.fixture()
def tmp_config(tmp_path):
    """Copy the real config.yaml to a temp dir and patch CONFIG_PATH to point there."""
    tmp_cfg = tmp_path / "config.yaml"
    shutil.copy2(CONFIG_PATH, tmp_cfg)
    with patch("gui.config_ops.CONFIG_PATH", tmp_cfg):
        yield tmp_cfg


def test_update_site_name(tmp_config):
    original = read_config()["site_name"]
    update_site_name("NEW NAME")
    assert read_config()["site_name"] == "NEW NAME"
    # restore
    update_site_name(original)
    assert read_config()["site_name"] == original


def test_update_site_name_empty_raises(tmp_config):
    with pytest.raises(ValueError):
        update_site_name("")
    with pytest.raises(ValueError):
        update_site_name("   ")


def test_update_footer_copyright(tmp_config):
    original = read_config()["footer"]["copyright"]
    update_footer_copyright("New Footer")
    assert read_config()["footer"]["copyright"] == "New Footer"
    # restore
    update_footer_copyright(original)
    assert read_config()["footer"]["copyright"] == original


def test_update_footer_copyright_empty_raises(tmp_config):
    with pytest.raises(ValueError):
        update_footer_copyright("")
    with pytest.raises(ValueError):
        update_footer_copyright("   ")


def test_get_nav_items(tmp_config):
    items = get_nav_items()
    assert isinstance(items, list)
    assert len(items) == 2
    assert all("label" in item and "url" in item for item in items)


def test_add_nav_item(tmp_config):
    original_count = len(get_nav_items())
    result = add_nav_item("Blog", "https://blog.example.com")
    assert len(result) == original_count + 1
    assert result[-1] == {"label": "Blog", "url": "https://blog.example.com"}
    assert len(get_nav_items()) == original_count + 1


def test_add_nav_item_empty_raises(tmp_config):
    with pytest.raises(ValueError):
        add_nav_item("", "https://example.com")
    with pytest.raises(ValueError):
        add_nav_item("Blog", "")


def test_update_nav_item(tmp_config):
    original = get_nav_items()
    result = update_nav_item(0, "Updated", "https://updated.com")
    assert result[0] == {"label": "Updated", "url": "https://updated.com"}
    assert len(result) == len(original)


def test_update_nav_item_out_of_range(tmp_config):
    with pytest.raises(IndexError):
        update_nav_item(99, "X", "https://x.com")


def test_delete_nav_item(tmp_config):
    original_count = len(get_nav_items())
    result = delete_nav_item(0)
    assert len(result) == original_count - 1


def test_delete_nav_item_out_of_range(tmp_config):
    with pytest.raises(IndexError):
        delete_nav_item(99)


def test_reorder_nav_items(tmp_config):
    original = get_nav_items()
    result = reorder_nav_items([1, 0])
    assert result[0] == original[1]
    assert result[1] == original[0]


def test_reorder_nav_items_invalid(tmp_config):
    with pytest.raises(ValueError):
        reorder_nav_items([0, 0])
    with pytest.raises(ValueError):
        reorder_nav_items([0, 1, 2])
