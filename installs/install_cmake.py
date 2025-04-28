from __future__ import annotations

import logging
import os
import platform
import shutil
import sys

from install_utils.install_utils import get_distro_info, run_command, setup_logging


def install_build_essentials_debian() -> bool:
    """Install cmake, build-essential, and python3-dev on Debian-based systems.

    Returns:
        bool: True if all steps succeed, False otherwise.

    """
    logger.info("Detected Debian-based distribution (apt).")

    logger.info("Updating package lists (apt-get update)...")
    if not run_command(["apt-get", "update", "-y"]):
        logger.error("Failed to update package lists.")
        return False
    logger.info("Package lists updated successfully.")

    logger.info("Attempting to install cmake...")
    if not run_command(["apt-get", "install", "-y", "cmake"]):
        logger.error("Failed to install cmake.")
        return False
    logger.info("cmake installed successfully.")

    logger.info("Attempting to install essential build tools (build-essential)...")
    if not run_command(["apt-get", "install", "-y", "build-essential"]):
        logger.error("Failed to install build-essential.")
        return False
    logger.info("build-essential installed successfully.")

    logger.info("Attempting to install python3-dev...")
    if not run_command(["apt-get", "install", "-y", "python3-dev"]):
        logger.error("Failed to install python3-dev.")
        return False
    logger.info("python3-dev installed successfully.")

    logger.info("All essential build packages installed successfully.")
    return True


def install_build_essentials_rhel() -> bool:
    """Install cmake, Development Tools group, and python3-devel on RHEL-based systems.

    Returns:
        bool: True if all steps succeed, False otherwise.

    """
    logger.info("Detected Red Hat-based distribution (dnf/yum).")

    # 1. Determine package manager
    pkg_manager = None
    if shutil.which("dnf"):
        pkg_manager = "dnf"
    elif shutil.which("yum"):
        pkg_manager = "yum"

    if not pkg_manager:
        logger.error("Neither dnf nor yum package managers found.")
        return False
    logger.info(f"Using {pkg_manager} package manager.")

    logger.info("Attempting to install cmake...")
    if not run_command([pkg_manager, "install", "-y", "cmake"]):
        logger.error("Failed to install cmake.")
        return False
    logger.info("cmake installed successfully.")

    logger.info(
        "Attempting to install essential build tools (Development Tools group)...",
    )
    cmd_groupinstall = [pkg_manager, "groupinstall", "-y", "Development Tools"]
    cmd_group_install = [pkg_manager, "group", "install", "-y", "Development Tools"]

    if run_command(cmd_groupinstall):
        logger.info(
            "Development Tools group installed successfully using 'groupinstall'.",
        )
    else:
        logger.warning("Command '%s' failed, trying '%s' instead...",
                       " ".join(cmd_groupinstall), " ".join(cmd_group_install))
        if not run_command(cmd_group_install):
            # If both failed
            logger.error(
                "Failed to install Development Tools group "
                "using both 'groupinstall' and 'group install'.",
            )
            return False
        logger.info(
            "Development Tools group installed successfully using 'group install'.",
        )

    logger.info("Attempting to install python3-devel...")
    if not run_command([pkg_manager, "install", "-y", "python3-devel"]):
        logger.error("Failed to install python3-devel.")
        return False
    logger.info("python3-devel installed successfully.")

    logger.info(
        "All essential build packages installed successfully on RHEL-based system.",
    )
    return True

def install_build_essentials_arch() -> bool:
    """Installs cmake and base-devel on Arch-based systems using pacman.

    Returns:
        True if all steps succeed, False otherwise.

    """
    logger.info("Detected Arch-based distribution (pacman).")

    logger.info("Attempting to sync repositories and install cmake (--needed)...")
    cmd_cmake = ["pacman", "-Syu", "--noconfirm", "--needed", "cmake"]
    if not run_command(cmd_cmake):
        logger.error("Failed to sync repositories or install cmake.")
        return False
    logger.info("cmake is up-to-date or installed successfully.")

    logger.info("Attempting to install essential build tools (base-devel --needed)...")
    cmd_base_devel = ["pacman", "-S", "--noconfirm", "--needed", "base-devel"]
    if not run_command(cmd_base_devel):
        logger.error("Failed to install base-devel group.")
        return False
    logger.info("base-devel group is up-to-date or installed successfully.")

    logger.info(
        "All essential build packages "
        "installed successfully on Arch-based system.",
    )
    return True


def install_build_essentials_suse() -> bool:
    """Install cmake, devel_basis pattern, and python3-devel on SUSE-based systems.

    Returns:
        True if all steps succeed, False otherwise.

    """
    logger.info("Detected SUSE-based distribution (zypper).")

    # 1. Install cmake
    logger.info("Attempting to install cmake...")
    cmd_cmake = ["zypper", "install", "--non-interactive", "cmake"]
    if not run_command(cmd_cmake):
        logger.error("Failed to install cmake.")
        return False
    logger.info("cmake installed successfully.")

    # 2. Install devel_basis pattern
    logger.info("Attempting to install essential build tools pattern (devel_basis)...")
    cmd_devel_basis = [
        "zypper",
        "install",
        "--non-interactive",
        "-t",
        "pattern",
        "devel_basis",
    ]
    if not run_command(cmd_devel_basis):
        logger.error("Failed to install devel_basis pattern.")
        return False
    logger.info("devel_basis pattern installed successfully.")

    # 3. Install python3-devel (Assuming sequential requirement)
    # Note: Original code used '-y', zypper typically uses '--non-interactive'.
    # Sticking to '--non-interactive' for consistency, but adjust if '-y' is needed.
    logger.info("Attempting to install python3-devel...")
    cmd_pydevel = ["zypper", "install", "--non-interactive", "python3-devel"]
    if not run_command(cmd_pydevel):
        logger.error("Failed to install python3-devel.")
        return False
    logger.info("python3-devel installed successfully.")

    # If all checks passed without returning False, everything succeeded.
    logger.info(
        "All essential build packages installed successfully on SUSE-based system.",
    )
    return True

def install_build_essentials_alpine() -> bool:
    """Install cmake, build-base, and python3-dev on Alpine Linux.

    Returns:
        True if all steps succeed, False otherwise.

    """
    logger.info("Detected Alpine Linux (apk).")
    logger.info("Updating apk package index...")
    cmd_update = ["apk", "update"]
    if not run_command(cmd_update):
        logger.error("Failed to update apk repositories.")
        return False
    logger.info("apk package index updated successfully.")

    logger.info("Attempting to install cmake...")
    cmd_cmake = ["apk", "add", "cmake"]
    if not run_command(cmd_cmake):
        logger.error("Failed to install cmake.")
        return False
    logger.info("cmake installed successfully.")

    logger.info("Attempting to install essential build tools (build-base)...")
    cmd_build_base = ["apk", "add", "build-base"]
    if not run_command(cmd_build_base):
        logger.error("Failed to install build-base.")
        return False
    logger.info("build-base installed successfully.")

    logger.info("Attempting to install python3-dev...")
    cmd_pydev = ["apk", "add", "python3-dev"]
    if not run_command(cmd_pydev):
        logger.error("Failed to install python3-dev.")
        return False
    logger.info("python3-dev installed successfully.")

    logger.info("All essential build packages installed successfully on Alpine Linux.")
    return True

def install_build_essentials() -> bool:
    """Identify the distro and attempts to install CMake and essential build tools.

    Returns:
         True if both installations succeed, False otherwise.

    """
    distro_info = get_distro_info()
    distro_id = distro_info.get("ID")
    id_like = distro_info.get("ID_LIKE", [])

    if not distro_id and not id_like:
        logger.error("Could not reliably determine the distribution.")
        return False

    logger.info(f"Detected Distro ID: {distro_id}")
    logger.info(f"Detected ID_LIKE: {id_like}")

    cmake_installed = False
    compilers_installed = False

    # --- Debian / Ubuntu / Mint etc. ---
    if (
        distro_id in ["debian", "ubuntu", "mint", "pop", "raspbian", "linuxmint"]
        or "debian" in id_like
    ):
        install_build_essentials_debian()

    # --- Fedora / RHEL / CentOS / Rocky / Alma ---
    elif (
        distro_id in ["fedora", "rhel", "centos", "rocky", "almalinux"]
        or "fedora" in id_like or "rhel" in id_like
    ):
        install_build_essentials_rhel()

    # --- Arch Linux / Manjaro ---
    elif (
        distro_id in ["arch", "manjaro"]
        or "arch" in id_like
    ):
        install_build_essentials_arch()

    # --- openSUSE / SLES ---
    elif (
        distro_id in ["opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles"]
        or "suse" in id_like
    ):
        install_build_essentials_suse()

    # --- Alpine Linux ---
    elif distro_id == "alpine":
        install_build_essentials_alpine()

    # --- Unsupported ---
    else:
        logger.error(
            f"Error: Unsupported distribution: ID='{distro_id}', ID_LIKE='{id_like}'",
        )
        logger.error(
            "Please install CMake and build tools manually "
            "using your system's package manager.",
        )
        return False # Definitely failed

    if not cmake_installed:
        logger.error("CMake installation failed.")
    if cmake_installed and not compilers_installed:
        logger.error(
            "Warning: CMake installed, "
            "but failed to install essential C/C++ compilers.",
        )
        logger.error(
            "You may need to install them manually "
            "(e.g., gcc, g++, make, or a development tools group).",
        )
        # Consider this a partial failure? Return False for safety.
        return False

    return cmake_installed and compilers_installed

def verify_installation() -> bool:
    """Check if cmake command is available and runs --version."""
    logger.info("Verifying CMake installation")
    cmake_path = shutil.which("cmake")
    if cmake_path:
        logger.info(f"CMake executable found at: {cmake_path}")
        return run_command(["cmake", "--version"], False)
    logger.error("'cmake' command not found in PATH after installation attempt.")
    return False

# --- Main Execution ---
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    if platform.system() != "Linux":
        logger.info("On Windows / MacOS. No need to continue.")
        sys.exit(0)

    logger.info("Starting CMake installation script...")

    if verify_installation():
        logger.info("CMake already installed, no need to continue.")
        sys.exit(0)

    # Warn if running as root directly
    if os.geteuid() == 0:
        logger.warning("Running script as root.")
        logger.warning(
            "Package manager commands will be run directly without 'sudo'.\n",
        )

    install_successful = install_build_essentials()

    if install_successful:
        logger.info(
            "CMake and essential build tools installation "
            "commands executed successfully.",
        )
        if verify_installation():
             logger.info("\nCMake installation verified.")
             sys.exit(0) # Exit with success code
        else:
             logger.error("\nCMake installation command ran, but verification failed.")
             sys.exit(1) # Exit with error code
    else:
        logger.error("\nCMake installation failed.")
        sys.exit(1) # Exit with error code
