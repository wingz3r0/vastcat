"""Automatic hashcat installation module."""
import os
import platform
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path


def get_hashcat_install_dir() -> Path:
    """Get the directory where hashcat should be installed."""
    return Path.home() / ".local" / "share" / "vastcat" / "hashcat"


def check_hashcat_installed() -> bool:
    """Check if hashcat is already installed (system-wide or local)."""
    # Check system PATH
    if shutil.which("hashcat"):
        return True

    # Check our local installation
    local_bin = get_hashcat_install_dir() / "hashcat"
    if local_bin.exists() and os.access(local_bin, os.X_OK):
        return True

    # Check ~/.local/bin
    local_bin_symlink = Path.home() / ".local" / "bin" / "hashcat"
    if local_bin_symlink.exists() and os.access(local_bin_symlink, os.X_OK):
        return True

    return False


def download_and_install_hashcat(verbose: bool = True) -> bool:
    """Download and install hashcat binaries to user-local directory."""
    if check_hashcat_installed():
        if verbose:
            print("\n✓ Hashcat is already installed")
        return True

    if verbose:
        print("\n🔧 Installing hashcat...")

    system = platform.system().lower()
    machine = platform.machine().lower()

    # Determine download URL based on platform
    hashcat_version = "6.2.6"

    if system == "linux":
        # Use official hashcat binaries
        if "x86_64" in machine or "amd64" in machine:
            url = f"https://hashcat.net/files/hashcat-{hashcat_version}.tar.gz"
        else:
            if verbose:
                print(f"⚠️  No pre-built binaries for {machine} architecture")
                _show_manual_instructions()
            return False
    elif system == "darwin":
        # macOS - use Homebrew or build from source
        if verbose:
            print("⚠️  macOS detected - attempting Homebrew installation...")
        if shutil.which("brew"):
            try:
                subprocess.run(["brew", "install", "hashcat"], check=True)
                if verbose:
                    print("✓ Hashcat installed via Homebrew")
                return True
            except subprocess.CalledProcessError:
                if verbose:
                    print("⚠️  Homebrew installation failed")
                    _show_manual_instructions()
                return False
        else:
            if verbose:
                print("⚠️  Homebrew not found")
                _show_manual_instructions()
            return False
    else:
        if verbose:
            print(f"⚠️  Unsupported platform: {system}")
            _show_manual_instructions()
        return False

    # Download hashcat
    install_dir = get_hashcat_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    download_path = install_dir / f"hashcat-{hashcat_version}.tar.gz"

    try:
        if verbose:
            print(f"  Downloading hashcat {hashcat_version}...")
        urllib.request.urlretrieve(url, download_path)

        if verbose:
            print("  Extracting...")
        with tarfile.open(download_path, "r:gz") as tar:
            tar.extractall(install_dir)

        # Find the extracted directory and compile
        extracted_dir = install_dir / f"hashcat-{hashcat_version}"

        if not extracted_dir.exists():
            if verbose:
                print(f"⚠️  Extraction failed - directory not found: {extracted_dir}")
                _show_manual_instructions()
            return False

        # Compile hashcat from source
        if verbose:
            print("  Compiling hashcat (this may take a few minutes)...")
        try:
            result = subprocess.run(
                ["make", "-j", str(os.cpu_count() or 4)],
                cwd=extracted_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            if result.returncode != 0:
                if verbose:
                    print(f"⚠️  Compilation failed:")
                    print(result.stderr)
                    _show_manual_instructions()
                return False
            if verbose:
                print("  ✓ Compilation successful")
        except subprocess.TimeoutExpired:
            if verbose:
                print("⚠️  Compilation timed out")
                _show_manual_instructions()
            return False
        except FileNotFoundError:
            if verbose:
                print("⚠️  'make' command not found - build tools not installed")
                print("  Install build tools first:")
                print("    Ubuntu/Debian: sudo apt install build-essential")
                print("    Fedora/RHEL:   sudo dnf groupinstall 'Development Tools'")
                print("    Arch:          sudo pacman -S base-devel")
                _show_manual_instructions()
            return False
        except Exception as e:
            if verbose:
                print(f"⚠️  Compilation error: {e}")
                _show_manual_instructions()
            return False

        # Check for compiled binary
        hashcat_binary = extracted_dir / "hashcat"
        if not hashcat_binary.exists():
            if verbose:
                print(f"⚠️  Compilation succeeded but binary not found in {extracted_dir}")
                _show_manual_instructions()
            return False

        # Make sure binary is executable
        hashcat_binary.chmod(0o755)

        # Create a wrapper script that sets library paths
        wrapper_script = install_dir / "hashcat"
        wrapper_content = f"""#!/bin/bash
HASHCAT_DIR="{extracted_dir}"
export LD_LIBRARY_PATH="$HASHCAT_DIR:$LD_LIBRARY_PATH"
exec "$HASHCAT_DIR/hashcat" "$@"
"""
        wrapper_script.write_text(wrapper_content)
        wrapper_script.chmod(0o755)

        # Clean up download
        download_path.unlink()

        # Add to PATH hint
        bin_dir = Path.home() / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        symlink = bin_dir / "hashcat"

        if not symlink.exists():
            symlink.symlink_to(wrapper_script)
            if verbose:
                print(f"\n✓ Hashcat installed to {install_dir}")
                print(f"✓ Symlink created at {symlink}")

            # Check if ~/.local/bin is in PATH
            local_bin_in_path = str(bin_dir) in os.environ.get("PATH", "")
            if not local_bin_in_path:
                if verbose:
                    print(f"\n⚠️  Add ~/.local/bin to your PATH:")
                    print(f"    export PATH=\"$HOME/.local/bin:$PATH\"")
                    print(f"    (Add this to your ~/.bashrc or ~/.zshrc)")
        else:
            if verbose:
                print(f"\n✓ Hashcat installed to {install_dir}")

        return True

    except Exception as e:
        if verbose:
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
    print("  wget https://hashcat.net/files/hashcat-6.2.6.tar.gz")
    print("  tar -xzf hashcat-6.2.6.tar.gz")
    print("  cd hashcat-6.2.6 && make && sudo make install")
    print("\nVerify installation:")
    print("  hashcat --version")
    print("  vastcat doctor")
    print("="*70 + "\n")
