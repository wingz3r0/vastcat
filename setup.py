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
    """Attempt to install hashcat automatically based on the platform."""
    if check_hashcat_installed():
        print("\n✓ Hashcat is already installed")
        return True

    print("\n🔧 Hashcat not found. Attempting automatic installation...")

    system = platform.system().lower()

    # Detect package manager and installation command
    install_commands = []

    if system == "linux":
        # Try to detect Linux distribution
        if Path("/etc/debian_version").exists():
            # Debian/Ubuntu
            install_commands = [
                ["sudo", "apt", "update"],
                ["sudo", "apt", "install", "-y", "hashcat"]
            ]
        elif Path("/etc/fedora-release").exists() or Path("/etc/redhat-release").exists():
            # Fedora/RHEL
            install_commands = [
                ["sudo", "dnf", "install", "-y", "hashcat"]
            ]
        elif Path("/etc/arch-release").exists():
            # Arch Linux
            install_commands = [
                ["sudo", "pacman", "-S", "--noconfirm", "hashcat"]
            ]
    elif system == "darwin":
        # macOS
        if shutil.which("brew"):
            install_commands = [
                ["brew", "install", "hashcat"]
            ]
        else:
            print("\n⚠️  Homebrew not found. Please install Homebrew first:")
            print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            return False

    if not install_commands:
        print(f"\n⚠️  Could not detect package manager for {system}")
        _show_manual_instructions()
        return False

    # Attempt installation
    try:
        for cmd in install_commands:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"\n⚠️  Installation command failed: {result.stderr}")
                _show_manual_instructions()
                return False

        # Verify installation
        if check_hashcat_installed():
            print("\n✓ Hashcat installed successfully!")
            return True
        else:
            print("\n⚠️  Installation completed but hashcat not found in PATH")
            _show_manual_instructions()
            return False

    except PermissionError:
        print("\n⚠️  Permission denied. You may need to run with sudo or install manually.")
        _show_manual_instructions()
        return False
    except Exception as e:
        print(f"\n⚠️  Installation failed: {e}")
        _show_manual_instructions()
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
