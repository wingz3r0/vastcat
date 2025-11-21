"""Minimal setup script for vastcat.

Note: Hashcat installation is checked at runtime via 'vastcat doctor' command.
Modern pip installations don't reliably trigger post-install hooks, so we
check for hashcat when the CLI is actually used.
"""
from setuptools import setup

# All configuration is in pyproject.toml
# This file exists only for compatibility
setup()
