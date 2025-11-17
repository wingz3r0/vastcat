"""Lightweight Vast.ai API client."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os
import requests

from .config import ensure_config


class VastError(RuntimeError):
    pass


@dataclass
class Offer:
    id: int
    gpu_name: str
    hourly: float
    vram_gb: float
    reliability: float
    machine_id: int

    @classmethod
    def from_api(cls, payload: Dict[str, Any]) -> "Offer":
        return cls(
            id=int(payload["id"]),
            gpu_name=payload.get("gpu_name", ""),
            hourly=float(payload.get("dph_total", 0.0)),
            vram_gb=float(payload.get("gpu_ram", 0.0)),
            reliability=float(payload.get("reliability2", 0)),
            machine_id=int(payload.get("machine_id", 0)),
        )


class VastClient:
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None) -> None:
        cfg = ensure_config()
        self.api_key = api_key or os.environ.get("VAST_API_KEY")
        if not self.api_key:
            raise VastError("Missing Vast.ai API key. Set VAST_API_KEY or pass --api-key.")
        self.api_url = api_url or cfg.get("vast_api_url")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _url(self, path: str) -> str:
        return f"{self.api_url.rstrip('/')}{path}"

    def list_offers(self, min_vram: int = 12, limit: int = 10) -> List[Offer]:
        params = {
            "q": f"verified=true gpu_ram>={min_vram} reliability2>0.9",
            "limit": limit,
        }
        resp = requests.get(self._url("/market/asks"), params=params, headers=self._headers(), timeout=20)
        if resp.status_code != 200:
            raise VastError(f"Unable to fetch offers: {resp.text}")
        offers_json = resp.json().get("offers", [])
        return [Offer.from_api(item) for item in offers_json]

    def create_instance(
        self,
        offer_id: int,
        image: str,
        disk_gb: int,
        cuda_visible_devices: str = "all",
        env: Optional[Dict[str, str]] = None,
        onstart: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "ask": offer_id,
            "image": image,
            "disk": disk_gb,
            "cuda_visible_devices": cuda_visible_devices,
            "env": env or {},
        }
        if onstart:
            payload["onstart"] = onstart
        resp = requests.post(self._url("/market/contracts"), json=payload, headers=self._headers(), timeout=20)
        if resp.status_code >= 400:
            raise VastError(f"Unable to create instance: {resp.text}")
        return resp.json()

    def run_command(self, instance_id: int, command: str) -> Dict[str, Any]:
        payload = {"instance_id": instance_id, "cmd": command}
        resp = requests.post(self._url("/container/spawn"), json=payload, headers=self._headers(), timeout=20)
        if resp.status_code >= 400:
            raise VastError(f"Command failed: {resp.text}")
        return resp.json()
