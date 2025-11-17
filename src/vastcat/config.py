"""Configuration helpers for Vastcat."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import os
import yaml

CONFIG_PATH = Path(os.environ.get("VASTCAT_CONFIG", "~/.config/vastcat/config.yaml")).expanduser()
DEFAULTS: Dict[str, Any] = {
    "cache_dir": str(Path(os.environ.get("VASTCAT_CACHE", "~/.cache/vastcat")).expanduser()),
    "base_image": "pytorch/pytorch:latest",
    "ubuntu_cuda_image": "nvidia/cuda:12.2.0-devel-ubuntu22.04",
    "hashcat_binary": "/opt/hashcat/hashcat",
    "discord_webhook": None,
    "vast_api_url": "https://api.vast.ai/v0",
    "auto_download_assets": True,
    "asset_manifest": "~/.config/vastcat/assets.yaml",
}


@dataclass
class Config:
    """Serializable config with a little sugar."""

    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_PATH.exists():
            loaded = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        else:
            loaded = {}
        defaults = DEFAULTS.copy()
        defaults.update(loaded)
        return cls(defaults)

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(yaml.safe_dump(self.data, sort_keys=True))

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    @property
    def cache_dir(self) -> Path:
        path = Path(self.data["cache_dir"]).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def asset_dir(self, category: str) -> Path:
        base = self.cache_dir / category
        base.mkdir(parents=True, exist_ok=True)
        return base


def ensure_config() -> Config:
    cfg = Config.load()
    if not CONFIG_PATH.exists():
        cfg.save()
    return cfg
