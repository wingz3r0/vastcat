"""Vastcat package."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("vastcat")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

CAT_TAGLINE = "Serving GPU purr-formance for your hashes."
