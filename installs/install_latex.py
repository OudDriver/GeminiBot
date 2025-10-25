from __future__ import annotations

import logging
import os
import platform
import shutil
import sys


from install_utils.install_utils import get_distro_info, run_command, setup_logging
system = platform.system()

def install_latex_debian() -> bool | None:
    """Installs LaTeX on Debian-based distribution."""
    logger.info("Detected Debian-based distribution (apt).")
    if run_command(["apt-get", "update", "-y"]):
        logger.info("Attempting to install texlive-bin, dvipng, and extras...")
        if run_command(
            ["apt-get", "install", "-y", "texlive-bin", "texlive-type1cm", "dvipng"]
        ):
            return True
        logger.error("Failed to install texlive packages.")
        return None
    logger.error("Failed to update package lists (apt-get update).")
    return None


def install_latex_rhel() -> bool | None:
    """Installs LaTeX on Red Hat-based distribution."""
    logger.info("Detected Red Hat-based distribution (dnf/yum).")

    if shutil.which("dnf"):
        pkg_manager = "dnf"
    elif shutil.which("yum"):
        pkg_manager = "yum"
    else:
        pkg_manager = None

    if pkg_manager:
        logger.info(f"Using {pkg_manager} package manager.")
        logger.info("Attempting to install texlive, texlive-dvipng, and extras...")
        if run_command(
            [
                pkg_manager,
                "install",
                "-y",
                "texlive",
                "texlive-type1cm",
                "texlive-dvipng",
            ]
        ):
            return True
        logger.error("Failed to install texlive packages.")
        return None
    logger.error("Error: Neither dnf nor yum package managers found.")
    return None


def install_latex_arch() -> bool | None:
    """Installs LaTeX on Arch-based distribution."""
    logger.info("Detected Arch-based distribution (pacman).")
    logger.info("Attempting to sync repositories and install texlive packages...")
    if run_command(
        [
            "pacman",
            "-Syu",
            "--noconfirm",
            "--needed",
            "texlive-bin",
            "texlive-core",
            "texlive-type1cm",
        ],
    ):
        return True
    logger.error("Failed to sync repositories or install texlive packages.")
    return None


def install_latex_suse() -> bool | None:
    """Installs LaTeX on SUSE-based distribution."""
    logger.info("Detected SUSE-based distribution (zypper).")
    logger.info("Attempting to install texlive, texlive-dvipng, and extras...")
    # SUSE distros often have a dedicated texlive-dvipng package
    if run_command(
        [
            "zypper",
            "install",
            "--non-interactive",
            "texlive",
            "texlive-type1cm",
            "texlive-dvipng",
        ]
    ):
        return True

    logger.error("Failed to install texlive packages.")
    return None


def install_latex_alpine() -> bool | None:
    """Install LaTeX on Alpine Linux."""
    logger.info("Detected Alpine Linux (apk).")
    if run_command(["apk", "update"]):
        logger.info("Attempting to install texlive, dvipng, and extras...")
        if run_command(["apk", "add", "texlive", "texlive-type1cm", "dvipng"]):
            return True
        logger.error("Failed to install texlive packages.")
        return None
    logger.error("Failed to update apk repositories.")
    return None


def install_latex_linux() -> bool:
    """Installs LaTeX on Linux."""
    distro_info = get_distro_info()
    distro_id = distro_info.get("ID")
    id_like = distro_info.get("ID_LIKE", [])

    if not distro_id and not id_like:
        logger.error("Could not reliably determine the distribution.")
        return False

    logger.info(f"Detected Distro ID: {distro_id}")
    logger.info(f"Detected ID_LIKE: {id_like}")

    if (
        distro_id in ["debian", "ubuntu", "mint", "pop", "raspbian", "linuxmint"]
        or "debian" in id_like
    ):
        latex_installed = install_latex_debian()

    # --- Fedora / RHEL / CentOS / Rocky / Alma ---
    elif (
        distro_id in ["fedora", "rhel", "centos", "rocky", "almalinux"]
        or "fedora" in id_like
        or "rhel" in id_like
    ):
        latex_installed = install_latex_rhel()

    # --- Arch Linux / Manjaro ---
    elif distro_id in ["arch", "manjaro"] or "arch" in id_like:
        latex_installed = install_latex_arch()

    # --- openSUSE / SLES ---
    elif (
        distro_id in ["opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles"]
        or "suse" in id_like
    ):
        latex_installed = install_latex_suse()

    # --- Alpine Linux ---
    elif distro_id == "alpine":
        latex_installed = install_latex_alpine()

    # --- Unsupported ---
    else:
        logger.error(
            f"Error: Unsupported distribution:ID='{distro_id}', ID_LIKE='{id_like}'"
        )
        return False  # Definitely failed

    if not latex_installed:
        logger.error("LaTeX installation failed.")

    return latex_installed


def install_latex_macos() -> bool:
    """Installs MacTeX on macOS using Homebrew."""
    logger.info("Detected macOS.")
    if not shutil.which("brew"):
        logger.error(
            "Homebrew ('brew') not found."
            "Please install Homebrew first. See: https://brew.sh/"
        )
        return False

    logger.info("Found Homebrew.")
    logger.info("Updating Homebrew (this may take a while)...")
    success = run_command(["brew", "update"])
    if not success:
        logger.warning("'brew update' failed, attempting install anyway.")

    logger.info(
        "Installing MacTeX (mactex)..."
        "This is a large download and may take a significant amount of time."
    )
    # The mactex cask is a full TeX distribution and includes dvipng.
    success = run_command(["brew", "install", "--cask", "mactex"])
    if not success:
        logger.error(
            "Failed to install mactex with Homebrew."
            "Try running manually: brew install --cask mactex"
            "You might need to agree to licenses or enter your password."
        )
        return False
    return True


def install_latex_windows() -> bool:
    """Installs LaTeX (MiKTeX or TeX Live) on Windows using winget or choco."""
    logger.info(
        "Detected Windows."
        "This script requires Administrator privileges to install software."
        "Attempting to install MiKTeX."
    )

    use_winget = shutil.which("winget")
    use_choco = shutil.which("choco")

    # Full MiKTeX distribution includes dvipng by default.
    if use_winget:
        logger.info("Found 'winget' package manager.")
        pkg_id = "MiKTeX.MiKTeX"

        logger.info(f"Installing {pkg_id} using winget...")
        cmd = [
            "winget",
            "install",
            "--id",
            pkg_id,
            "-e",
            "--accept-source-agreements",
            "--accept-package-agreements",
        ]
        success = run_command(cmd)
        if not success:
            logger.error(
                f"Failed to install {pkg_id} using winget."
                f"Try running winget install manually in an Admin prompt."
            )
            return False
        return True

    if use_choco:
        logger.info("Found 'choco' package manager.")
        pkg_id = "miktex"

        logger.info(f"Installing {pkg_id} using Chocolatey...")
        cmd = ["choco", "install", pkg_id, "-y"]
        success = run_command(cmd)
        if not success:
            logger.error(
                f"Failed to install {pkg_id} using Chocolatey. "
                f"Try running choco install manually in an Admin prompt."
            )
            return False
        return True

    error_msg = (
        "Could not find 'winget' or 'choco'."
        "Please install either Windows Package Manager (winget) or Chocolatey "
        "or install MiKTeX/TeX Live manually from their respective websites:"
        "MiKTeX: https://miktex.org/download"
        "TeX Live: https://www.tug.org/texlive/acquire-netinstall.html"
    )
    logger.error(error_msg)
    return False


def verify_installation() -> bool:
    """Check if essential LaTeX commands (pdftex, dvipng) are available."""
    logger.info("Verifying LaTeX installation (pdftex and dvipng)...")
    pdftex_path = shutil.which("pdftex")
    dvipng_path = shutil.which("dvipng")

    if pdftex_path:
        logger.info(f"pdfTeX executable found at: {pdftex_path}")
    else:
        logger.error("Error: 'pdftex' command not found in PATH.")
        return False

    if dvipng_path:
        logger.info(f"dvipng executable found at: {dvipng_path}")
    else:
        logger.error("Error: 'dvipng' command not found in PATH.")
        return False

    logger.info("Checking versions...")
    pdftex_ok = run_command(["pdftex", "--version"], suppress_output=True)
    dvipng_ok = run_command(["dvipng", "--version"], suppress_output=True)

    return pdftex_ok and dvipng_ok


# --- Main Execution ---
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting LaTeX installation script...")

    if verify_installation():
        logger.info("LaTeX (pdftex and dvipng) is already installed and verified.")
        sys.exit(0)
    else:
        logger.warning(
            "LaTeX installation not found or incomplete. Proceeding with installation."
        )

    # Warn if running as root directly on non-Windows
    if system != "Windows" and os.geteuid() == 0:
        logger.warning("Running script as root.")
        logger.info("Package manager commands will be run directly without 'sudo'.")

    install_successful = False

    if system == "Linux":
        install_successful = install_latex_linux()
    elif system == "Darwin":  # Correct platform name for macOS
        install_successful = install_latex_macos()
    elif system == "Windows":
        install_successful = install_latex_windows()

    if install_successful:
        logger.info("LaTeX installation commands executed successfully.")
        if verify_installation():
            logger.info("LaTeX installation fully verified.")
            sys.exit(0) # Exit with success code
        else:
            logger.error("LaTeX installation command ran, but verification failed.")
            sys.exit(1) # Exit with error code
    else:
        logger.error("LaTeX installation failed.")
        sys.exit(1) # Exit with error code