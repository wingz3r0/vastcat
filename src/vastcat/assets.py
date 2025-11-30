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
    # Hashcat default rules - essentials
    "best66": Asset(
        name="best66.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/best66.rule",
        filename="best66.rule",
        output_name="best66.rule",
        description="Hashcat best66 - highly effective starter rule (66 rules)",
    ),
    "rockyou_30000": Asset(
        name="rockyou-30000.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/rockyou-30000.rule",
        filename="rockyou-30000.rule",
        output_name="rockyou-30000.rule",
        description="Hashcat rockyou-30000 - comprehensive ruleset (30K rules)",
    ),
    "d3ad0ne": Asset(
        name="d3ad0ne.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/d3ad0ne.rule",
        filename="d3ad0ne.rule",
        output_name="d3ad0ne.rule",
        description="Hashcat d3ad0ne - effective 30K ruleset",
    ),
    "generated2": Asset(
        name="generated2.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/generated2.rule",
        filename="generated2.rule",
        output_name="generated2.rule",
        description="Hashcat generated2 - generated ruleset (30K rules)",
    ),
    "combinator": Asset(
        name="combinator.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/combinator.rule",
        filename="combinator.rule",
        output_name="combinator.rule",
        description="Hashcat combinator - word combination rules (51 rules)",
    ),
    "toggles1": Asset(
        name="toggles1.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/toggles1.rule",
        filename="toggles1.rule",
        output_name="toggles1.rule",
        description="Hashcat toggles1 - case mutation rules (15 rules)",
    ),
    "toggles2": Asset(
        name="toggles2.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/toggles2.rule",
        filename="toggles2.rule",
        output_name="toggles2.rule",
        description="Hashcat toggles2 - case mutation rules (32 rules)",
    ),
    "toggles3": Asset(
        name="toggles3.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/toggles3.rule",
        filename="toggles3.rule",
        output_name="toggles3.rule",
        description="Hashcat toggles3 - case mutation rules (94 rules)",
    ),
    "toggles4": Asset(
        name="toggles4.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/toggles4.rule",
        filename="toggles4.rule",
        output_name="toggles4.rule",
        description="Hashcat toggles4 - case mutation rules (434 rules)",
    ),
    "toggles5": Asset(
        name="toggles5.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/toggles5.rule",
        filename="toggles5.rule",
        output_name="toggles5.rule",
        description="Hashcat toggles5 - case mutation rules (4943 rules)",
    ),
    # Community rules
    "onerule_still": Asset(
        name="OneRuleToRuleThemStill.rule",
        category="rules",
        url="https://raw.githubusercontent.com/stealthsploit/OneRuleToRuleThemStill/main/OneRuleToRuleThemStill.rule",
        filename="OneRuleToRuleThemStill.rule",
        output_name="OneRuleToRuleThemStill.rule",
        description="OneRuleToRuleThemStill - optimized 48K rules (improved version)",
    ),
    "clem9669_small": Asset(
        name="clem9669_small.rule",
        category="rules",
        url="https://raw.githubusercontent.com/clem9669/hashcat-rule/master/clem9669_small.rule",
        filename="clem9669_small.rule",
        output_name="clem9669_small.rule",
        description="Clem9669 small - for slow hashes like bcrypt (386 rules)",
    ),
    "clem9669_medium": Asset(
        name="clem9669_medium.rule",
        category="rules",
        url="https://raw.githubusercontent.com/clem9669/hashcat-rule/master/clem9669_medium.rule",
        filename="clem9669_medium.rule",
        output_name="clem9669_medium.rule",
        description="Clem9669 medium - balanced ruleset (179K rules)",
    ),
    "clem9669_large": Asset(
        name="clem9669_large.rule",
        category="rules",
        url="https://raw.githubusercontent.com/clem9669/hashcat-rule/master/clem9669_large.rule",
        filename="clem9669_large.rule",
        output_name="clem9669_large.rule",
        description="Clem9669 large - for fast hashes MD5/NTLM (4M+ rules, large download)",
    ),
    # InsidePro rules
    "insidepro_hashmanager": Asset(
        name="InsidePro-HashManager.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/InsidePro-HashManager.rule",
        filename="InsidePro-HashManager.rule",
        output_name="InsidePro-HashManager.rule",
        description="InsidePro HashManager - professional ruleset",
    ),
    "insidepro_passwordspro": Asset(
        name="InsidePro-PasswordsPro.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/InsidePro-PasswordsPro.rule",
        filename="InsidePro-PasswordsPro.rule",
        output_name="InsidePro-PasswordsPro.rule",
        description="InsidePro PasswordsPro - professional ruleset",
    ),
    # Additional hashcat defaults
    "dive": Asset(
        name="dive.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/dive.rule",
        filename="dive.rule",
        output_name="dive.rule",
        description="Hashcat dive rule",
    ),
    "leetspeak": Asset(
        name="leetspeak.rule",
        category="rules",
        url="https://raw.githubusercontent.com/hashcat/hashcat/master/rules/leetspeak.rule",
        filename="leetspeak.rule",
        output_name="leetspeak.rule",
        description="Hashcat leetspeak mutations",
    ),
    # Additional wordlists
    "xato_10m": Asset(
        name="xato-net-10-million-passwords.txt",
        category="wordlists",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/xato-net-10-million-passwords.txt",
        filename="xato-net-10-million-passwords.txt",
        output_name="xato-net-10-million-passwords.txt",
        description="Xato 10 million passwords - research-based wordlist",
    ),
    "ncsc_100k": Asset(
        name="100k-most-used-passwords-NCSC.txt",
        category="wordlists",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/100k-most-used-passwords-NCSC.txt",
        filename="100k-most-used-passwords-NCSC.txt",
        output_name="100k-most-used-passwords-NCSC.txt",
        description="NCSC 100K most used passwords",
    ),
    "best1050": Asset(
        name="best1050.txt",
        category="wordlists",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/best1050.txt",
        filename="best1050.txt",
        output_name="best1050.txt",
        description="Best 1050 passwords - curated list",
    ),
    "top_shortlist": Asset(
        name="top-passwords-shortlist.txt",
        category="wordlists",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/top-passwords-shortlist.txt",
        filename="top-passwords-shortlist.txt",
        output_name="top-passwords-shortlist.txt",
        description="Top passwords shortlist - quick starter",
    ),
    "darkweb2017_10k": Asset(
        name="darkweb2017-top10000.txt",
        category="wordlists",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/darkweb2017-top10000.txt",
        filename="darkweb2017-top10000.txt",
        output_name="darkweb2017-top10000.txt",
        description="Dark web 2017 top 10K passwords",
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
