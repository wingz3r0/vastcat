"""Asset manifest + download helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
import gzip
import bz2

import requests
from tqdm import tqdm

from .config import Config, ensure_config


@dataclass
class Asset:
    name: str
    category: str
    url: str
    filename: Optional[str] = None
    checksum: Optional[str] = None
    decompress: Optional[str] = None  # one of {"zip", "tar", "gz", "bz2"}
    output_name: Optional[str] = None
    description: str = ""


ASSET_LIBRARY: Dict[str, Asset] = {
    "rockyou": Asset(
        name="rockyou.txt",
        category="wordlists",
        url="https://github.com/praetorian-inc/Hob0Rules/raw/master/wordlists/rockyou.txt.gz",
        filename="rockyou.txt.gz",
        decompress="gz",
        output_name="rockyou.txt",
        description="Classic rockyou list in gzip format",
    ),
    "common_10k": Asset(
        name="10k-most-common.txt",
        category="wordlists",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt",
        filename="10k-most-common.txt",
        decompress=None,
        output_name="10k-most-common.txt",
        description="10,000 most common passwords",
    ),
    "weakpass_3": Asset(
        name="weakpass_3",
        category="wordlists",
        url="https://download.weakpass.com/wordlists/1947/weakpass_3.7z",
        filename="weakpass_3.7z",
        decompress="7z",
        output_name="weakpass_3",
        description="Weakpass 3 wordlist (28GB decompressed, large download)",
    ),
    "seclists_passwords": Asset(
        name="SecLists",
        category="wordlists",
        url="https://github.com/danielmiessler/SecLists/archive/refs/heads/master.zip",
        filename="SecLists-master.zip",
        decompress="zip",
        output_name="SecLists-master",
        description="Full SecLists repo (large download)",
    ),
    "dive": Asset(
        name="dive.rule",
        category="rules",
        url="https://github.com/hashcat/hashcat/blob/master/rules/dive.rule?raw=1",
        filename="dive.rule",
        output_name="dive.rule",
        description="Dive rule",
    ),
    "onerule": Asset(
        name="OneRuleToRuleThemAll.rule",
        category="rules",
        url="https://github.com/NotSoSecure/password_cracking_rules/blob/master/OneRuleToRuleThemAll.rule?raw=1",
        filename="OneRuleToRuleThemAll.rule",
        output_name="OneRuleToRuleThemAll.rule",
        description="OneRuleToRuleThemAll",
    ),
    "kaonashi_yubaba": Asset(
        name="yubaba64.rule",
        category="rules",
        url="https://raw.githubusercontent.com/kaonashi-passwords/Kaonashi/master/rules/yubaba64.rule",
        filename="yubaba64.rule",
        output_name="yubaba64.rule",
        description="Kaonashi yubaba64 rule",
    ),
    "kaonashi_haku": Asset(
        name="haku34K.rule",
        category="rules",
        url="https://raw.githubusercontent.com/kaonashi-passwords/Kaonashi/master/rules/haku34K.rule",
        filename="haku34K.rule",
        output_name="haku34K.rule",
        description="Kaonashi haku34K rule",
    ),
}


class AssetManager:
    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or ensure_config()

    def sync(self, selection: Optional[Iterable[str]] = None, force: bool = False) -> List[Path]:
        targets = selection or ASSET_LIBRARY.keys()
        downloaded: List[Path] = []
        for key in targets:
            asset = ASSET_LIBRARY.get(key)
            if not asset:
                raise KeyError(f"Unknown asset '{key}'")
            final_path = self._output_path(asset)
            if final_path.exists() and not force:
                downloaded.append(final_path)
                continue
            downloaded.append(self._download(asset))
        return downloaded

    def _download_target(self, asset: Asset) -> Path:
        filename = asset.filename or Path(asset.url).name
        return self.config.asset_dir(asset.category) / filename

    def _output_path(self, asset: Asset) -> Path:
        name = asset.output_name or asset.filename or Path(asset.url).name
        return self.config.asset_dir(asset.category) / name

    def _download(self, asset: Asset) -> Path:
        target = self._download_target(asset)
        target.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(asset.url, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                progress = tqdm(
                    total=total or None,
                    unit="B",
                    unit_scale=True,
                    desc=f"Fetching {asset.name}",
                )
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        tmp.write(chunk)
                        progress.update(len(chunk))
                progress.close()
                tmp_path = Path(tmp.name)
        if asset.checksum:
            self._verify_checksum(tmp_path, asset.checksum)
        final_path = self._handle_compression(tmp_path, target, self._output_path(asset), asset)
        return final_path

    def _verify_checksum(self, file_path: Path, checksum: str) -> None:
        digest = hashlib.sha256()
        with file_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != checksum:
            file_path.unlink(missing_ok=True)
            raise ValueError("Checksum mismatch for downloaded asset")

    def _handle_compression(self, temp_path: Path, download_target: Path, output_path: Path, asset: Asset) -> Path:
        if asset.decompress == "zip":
            with zipfile.ZipFile(temp_path) as zf:
                extract_dir = output_path
                extract_dir.mkdir(parents=True, exist_ok=True)
                zf.extractall(extract_dir)
            temp_path.unlink(missing_ok=True)
            return output_path
        if asset.decompress == "tar":
            with tarfile.open(temp_path) as tf:
                tf.extractall(output_path)
            temp_path.unlink(missing_ok=True)
            return output_path
        if asset.decompress == "gz":
            with gzip.open(temp_path, "rb") as src, open(output_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            temp_path.unlink(missing_ok=True)
            return output_path
        if asset.decompress == "bz2":
            with bz2.open(temp_path, "rb") as src, open(output_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            temp_path.unlink(missing_ok=True)
            return output_path
        if asset.decompress == "7z":
            # Extract 7z using system command
            extract_dir = output_path
            extract_dir.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(
                    ["7z", "x", str(temp_path), f"-o{extract_dir}", "-y"],
                    check=True,
                    capture_output=True
                )
            except FileNotFoundError:
                raise RuntimeError(
                    "7z command not found. Install p7zip: "
                    "Ubuntu/Debian: sudo apt install p7zip-full | "
                    "Fedora: sudo dnf install p7zip | "
                    "macOS: brew install p7zip"
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"7z extraction failed: {e.stderr.decode()}")
            temp_path.unlink(missing_ok=True)
            return output_path
        # default: move file as-is
        shutil.move(str(temp_path), output_path)
        return output_path

    def resolved_paths(self, keys: Iterable[str]) -> List[Path]:
        paths: List[Path] = []
        for key in keys:
            asset = ASSET_LIBRARY.get(key)
            if not asset:
                raise KeyError(key)
            paths.append(self._output_path(asset))
        return paths


def list_assets(category: Optional[str] = None) -> List[str]:
    if not category:
        return list(ASSET_LIBRARY.keys())
    return [key for key, asset in ASSET_LIBRARY.items() if asset.category == category]
