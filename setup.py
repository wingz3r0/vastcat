"""Setup script for vastcat with automatic hashcat installation."""
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def install_hashcat_if_needed():
    """Try to install hashcat if not already installed."""
    try:
        # Import from the installed package location
        from vastcat.install_hashcat import download_and_install_hashcat
        download_and_install_hashcat()
    except ImportError:
        # If package not yet installed, try to import from source
        try:
            sys.path.insert(0, str(Path(__file__).parent / "src"))
            from vastcat.install_hashcat import download_and_install_hashcat
            download_and_install_hashcat()
        except Exception as e:
            print(f"\n⚠️  Could not auto-install hashcat: {e}")
            print("Run 'vastcat install-hashcat' after installation for instructions.")


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        develop.run(self)
        install_hashcat_if_needed()


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        install_hashcat_if_needed()


# Use pyproject.toml for most configuration, but need setup.py for custom commands
setup(
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
)
