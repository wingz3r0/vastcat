"""Setup script for vastcat with hashcat auto-installation."""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def check_hashcat_installed():
    """Check if hashcat is already installed."""
    return shutil.which("hashcat") is not None


def install_hashcat():
    """Check for hashcat and provide installation instructions if missing."""
    if check_hashcat_installed():
        print("\n✓ Hashcat is already installed")
        return True

    print("\n⚠️  Hashcat is not installed.")
    print("Hashcat is required to run password cracking operations.")
    _show_manual_instructions()

    # Log to file for debugging
    log_file = Path.home() / ".vastcat" / "install.log"
    log_file.parent.mkdir(exist_ok=True)
    with open(log_file, "a") as f:
        import datetime
        f.write(f"\n[{datetime.datetime.now()}] Hashcat not found during installation\n")
        f.write(f"System: {platform.system()}, {platform.platform()}\n")

    return False


def _show_manual_instructions():
    """Display manual installation instructions."""
    print("\n" + "="*70)
    print("📋 Manual Hashcat Installation Instructions")
    print("="*70)
    print("\nUbuntu/Debian:")
    print("  sudo apt update && sudo apt install -y hashcat")
    print("\nFedora/RHEL:")
    print("  sudo dnf install -y hashcat")
    print("\nArch Linux:")
    print("  sudo pacman -S hashcat")
    print("\nmacOS:")
    print("  brew install hashcat")
    print("\nFrom Source:")
    print("  wget https://hashcat.net/files/hashcat-7.1.2.tar.gz")
    print("  tar -xzf hashcat-7.1.2.tar.gz")
    print("  cd hashcat-7.1.2 && make && sudo make install")
    print("\nVerify installation:")
    print("  hashcat --version")
    print("="*70 + "\n")


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        develop.run(self)
        install_hashcat()


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        install_hashcat()


# Use pyproject.toml for most configuration, but need setup.py for custom commands
setup(
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
)
