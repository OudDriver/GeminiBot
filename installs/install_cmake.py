import os
from setup import run_command
import sys
import shutil

def get_distro_info():
    """
    Detects Linux distribution information from /etc/os-release.
    Returns a dictionary with 'ID' and 'ID_LIKE' (list).
    """
    distro_info = {'ID': None, 'ID_LIKE': []}
    if sys.platform != "linux":
        print(f"Warning: This script is designed for Linux, but running on {sys.platform}.", file=sys.stderr)
        return

    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove potential quotes around value
                    value = value.strip('"\'')
                    if key == "ID":
                        distro_info['ID'] = value.lower() # Use lower case for easier matching
                    elif key == "ID_LIKE":
                        # ID_LIKE can be a space-separated list
                        distro_info['ID_LIKE'] = [item.lower() for item in value.split()]
    except FileNotFoundError:
        print("Error: /etc/os-release not found. Cannot determine distribution.", file=sys.stderr)
    except Exception as e:
         print(f"Error reading /etc/os-release: {e}", file=sys.stderr)

    return distro_info

def install_build_essentials():
    """
    Identifies the distro and attempts to install CMake and essential build tools
    (like C/C++ compilers) using the correct package manager.
    Returns True if both installations succeed, False otherwise.
    """
    distro_info = get_distro_info()
    distro_id = distro_info.get('ID')
    id_like = distro_info.get('ID_LIKE', [])

    if not distro_id and not id_like:
        print("Could not reliably determine the distribution.", file=sys.stderr)
        return False

    print(f"Detected Distro ID: {distro_id}")
    print(f"Detected ID_LIKE: {id_like}")

    cmake_installed = False
    compilers_installed = False

    # --- Debian / Ubuntu / Mint etc. ---
    if distro_id in ["debian", "ubuntu", "mint", "pop", "raspbian", "linuxmint"] or "debian" in id_like:
        print("Detected Debian-based distribution (apt).")
        if run_command(["apt-get", "update", "-y"]):
            print("\nAttempting to install cmake...")
            if run_command(["apt-get", "install", "-y", "cmake"]):
                cmake_installed = True
                print("\nAttempting to install essential build tools (build-essential)...")
                if run_command(["apt-get", "install", "-y", "build-essential"]):
                    compilers_installed = True
                else:
                    print("Failed to install build-essential.", file=sys.stderr)

                if not run_command(["apt-get", "install", "-y", "python3-dev"]):
                    print("Failed to install python3-dev")
            else:
                 print("Failed to install cmake.", file=sys.stderr)
        else:
            print("Failed to update package lists (apt-get update).", file=sys.stderr)

    # --- Fedora / RHEL / CentOS / Rocky / Alma ---
    elif distro_id in ["fedora", "rhel", "centos", "rocky", "almalinux"] or "fedora" in id_like or "rhel" in id_like:
        print("Detected Red Hat-based distribution (dnf/yum).")
        pkg_manager = "dnf" if shutil.which("dnf") else "yum" if shutil.which("yum") else None

        if pkg_manager:
            print(f"Using {pkg_manager} package manager.")
            print("\nAttempting to install cmake...")
            if run_command([pkg_manager, "install", "-y", "cmake"]):
                cmake_installed = True
                print("\nAttempting to install essential build tools (Development Tools group)...")
                # Use groupinstall or group install depending on manager/version
                if run_command([pkg_manager, "groupinstall", "-y", "Development Tools"]):
                     compilers_installed = True
                else:
                    print("Trying 'group install' instead of 'groupinstall'...")
                    if run_command(
                        [pkg_manager, "group", "install", "-y", "Development Tools"]
                    ):
                        compilers_installed = True
                    else:
                        print(
                            "Failed to install Development Tools group.",
                            file=sys.stderr,
                        )
                if not run_command([pkg_manager, "install", "-y", "python3-devel"]):
                    print("Failed to install python3-devel")
            else:
                print("Failed to install cmake.", file=sys.stderr)
        else:
            print("Error: Neither dnf nor yum package managers found.", file=sys.stderr)

    # --- Arch Linux / Manjaro ---
    elif distro_id in ["arch", "manjaro"] or "arch" in id_like:
        print("Detected Arch-based distribution (pacman).")
        print("\nAttempting to sync repositories and install cmake...")
        # Combine update and install for typical Arch workflow
        # Using --needed ensures packages aren't reinstalled unnecessarily
        if run_command(["pacman", "-Syu", "--noconfirm", "--needed", "cmake"]):
            cmake_installed = True
            print("\nAttempting to install essential build tools (base-devel)...")
            # base-devel might prompt for choices, handle non-interactively if possible
            # Often largely installed, --needed is important here.

            if run_command(["pacman", "-S", "--noconfirm", "--needed", "base-devel"]):
                compilers_installed = True
            else:
                print("Failed to install base-devel group.", file=sys.stderr)
        else:
            print("Failed to sync repositories or install cmake.", file=sys.stderr)

    # --- openSUSE / SLES ---
    elif distro_id in ["opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles"] or "suse" in id_like:
        print("Detected SUSE-based distribution (zypper).")
        print("\nAttempting to install cmake...")
        if run_command(["zypper", "install", "--non-interactive", "cmake"]):
            cmake_installed = True
            print("\nAttempting to install essential build tools pattern (devel_basis)...")
            if run_command(["zypper", "install", "--non-interactive", "-t", "pattern", "devel_basis"]):
                compilers_installed = True
            else:
                print("Failed to install devel_basis pattern.", file=sys.stderr)

            if not run_command(["zypper", "install", "-y", "python3-devel"]):
                print("Failed to install python3-devel")
        else:
             print("Failed to install cmake.", file=sys.stderr)

    # --- Alpine Linux ---
    elif distro_id == "alpine":
        print("Detected Alpine Linux (apk).")
        if run_command(["apk", "update"]):
            print("\nAttempting to install cmake...")
            if run_command(["apk", "add", "cmake"]):
                cmake_installed = True
                print("\nAttempting to install essential build tools (build-base)...")
                if run_command(["apk", "add", "build-base"]):
                    compilers_installed = True
                else:
                    print("Failed to install build-base.", file=sys.stderr)

                if not run_command(["apk", "install", "-y", "python3-devel"]):
                    print("Failed to install python3-devel")
            else:
                print("Failed to install cmake.", file=sys.stderr)
        else:
            print("Failed to update apk repositories.", file=sys.stderr)

    # --- Unsupported ---
    else:
        print(f"Error: Unsupported distribution: ID='{distro_id}', ID_LIKE='{id_like}'", file=sys.stderr)
        print("Please install CMake and build tools manually using your system's package manager.", file=sys.stderr)
        return False # Definitely failed

    if not cmake_installed:
        print("\nCMake installation failed.", file=sys.stderr)
    if cmake_installed and not compilers_installed:
        print("\nWarning: CMake installed, but failed to install essential C/C++ compilers.", file=sys.stderr)
        print("You may need to install them manually (e.g., gcc, g++, make, or a development tools group).", file=sys.stderr)
        # Consider this a partial failure? Return False for safety.
        return False

    return cmake_installed and compilers_installed

def verify_installation():
    """Checks if cmake command is available and runs --version."""
    print("\n--- Verifying CMake installation ---")
    cmake_path = shutil.which("cmake")
    if cmake_path:
        print(f"CMake executable found at: {cmake_path}")
        return run_command(["cmake", "--version"], False)
    else:
        print("Error: 'cmake' command not found in PATH after installation attempt.", file=sys.stderr)
        return False

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting CMake installation script...")

    if verify_installation():
        print("CMake already installed, no need to continue.")
        sys.exit(0)
    
    # Warn if running as root directly
    if os.geteuid() == 0:
        print("\nWarning: Running script as root.", file=sys.stderr)
        print("Package manager commands will be run directly without 'sudo'.\n", file=sys.stderr)

    install_successful = install_build_essentials()

    if install_successful:
        print("\nCMake and essential build tools installation commands executed successfully.")
        if verify_installation():
             print("\nCMake installation verified.")
             sys.exit(0) # Exit with success code
        else:
             print("\nCMake installation command ran, but verification failed.", file=sys.stderr)
             sys.exit(1) # Exit with error code
    else:
        print("\nCMake installation failed.", file=sys.stderr)
        sys.exit(1) # Exit with error code