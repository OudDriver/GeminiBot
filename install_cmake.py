import os
from setup import run_command
import sys
import shutil # To check for command existence (e.g., dnf, yum, sudo)
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

def install_cmake():
    """
    Identifies the distro and attempts to install CMake using the correct package manager.
    """
    distro_info = get_distro_info()
    distro_id = distro_info.get('ID')
    id_like = distro_info.get('ID_LIKE', []) # Default to empty list

    if not distro_id and not id_like:
        print("Could not reliably determine the distribution.", file=sys.stderr)
        return False

    print(f"Detected Distro ID: {distro_id}")
    print(f"Detected ID_LIKE: {id_like}")

    success = False

    # --- Debian / Ubuntu / Mint etc. ---
    # Check ID or if 'debian' is in ID_LIKE
    if distro_id in ["debian", "ubuntu", "mint", "pop", "raspbian", "linuxmint"] or "debian" in id_like:
        print("Detected Debian-based distribution (apt).")
        # Use apt-get for better script stability compared to apt
        if run_command(["apt-get", "update", "-y"]):
            success = run_command(["apt-get", "install", "-y", "cmake"])
        else:
            print("Failed to update package lists (apt-get update).", file=sys.stderr)

    # --- Fedora / RHEL / CentOS / Rocky / Alma ---
    # Check ID or if 'fedora' or 'rhel' is in ID_LIKE
    elif distro_id in ["fedora", "rhel", "centos", "rocky", "almalinux"] or "fedora" in id_like or "rhel" in id_like:
        print("Detected Red Hat-based distribution (dnf/yum).")
        # Prefer dnf if available, otherwise fall back to yum
        if shutil.which("dnf"):
            print("Using dnf package manager.")
            success = run_command(["dnf", "install", "-y", "cmake"])
        elif shutil.which("yum"):
            print("dnf not found, using yum package manager.")
            success = run_command(["yum", "install", "-y", "cmake"])
        else:
            print("Error: Neither dnf nor yum package managers found.", file=sys.stderr)

    # --- Arch Linux / Manjaro ---
    # Check ID or if 'arch' is in ID_LIKE
    elif distro_id in ["arch", "manjaro"] or "arch" in id_like:
         print("Detected Arch-based distribution (pacman).")
         # Arch users typically sync repos and update (-Sy) when installing.
         # Use -Syu to also upgrade packages (common practice) or just -Sy cmake
         # --noconfirm is needed for non-interactive use. Be cautious.
         success = run_command(["pacman", "-Syu", "--noconfirm", "cmake"])
         # If you only want to install cmake without full system upgrade:
         # success = run_command(["pacman", "-Sy", "--noconfirm", "cmake"])


    # --- openSUSE / SLES ---
    # Check ID or if 'suse' is in ID_LIKE
    elif distro_id in ["opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles"] or "suse" in id_like:
        print("Detected SUSE-based distribution (zypper).")
        # -n for non-interactive mode is equivalent to -y for install/update
        success = run_command(["zypper", "install", "--non-interactive", "cmake"])

    # --- Alpine Linux ---
    elif distro_id == "alpine":
        print("Detected Alpine Linux (apk).")
        if run_command(["apk", "update"]):
             success = run_command(["apk", "add", "cmake"])
        else:
            print("Failed to update apk repositories.", file=sys.stderr)

    # --- Unsupported ---
    else:
        print(f"Error: Unsupported distribution: ID='{distro_id}', ID_LIKE='{id_like}'", file=sys.stderr)
        print("Please install CMake manually using your system's package manager.", file=sys.stderr)

    return success

def verify_installation():
    """Checks if cmake command is available and runs --version."""
    print("\n--- Verifying CMake installation ---")
    cmake_path = shutil.which("cmake")
    if cmake_path:
        print(f"CMake executable found at: {cmake_path}")
        return run_command(["cmake", "--version"])
    else:
        print("Error: 'cmake' command not found in PATH after installation attempt.", file=sys.stderr)
        return False

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting CMake installation script...")

    # Warn if running as root directly
    if os.geteuid() == 0:
        print("\nWarning: Running script as root.", file=sys.stderr)
        print("Package manager commands will be run directly without 'sudo'.\n", file=sys.stderr)

    install_successful = install_cmake()

    if install_successful:
        print("\nCMake installation command executed successfully.")
        if verify_installation():
             print("\nCMake successfully installed and verified.")
             sys.exit(0) # Exit with success code
        else:
             print("\nCMake installation command ran, but verification failed.", file=sys.stderr)
             sys.exit(1) # Exit with error code
    else:
        print("\nCMake installation failed.", file=sys.stderr)
        sys.exit(1) # Exit with error code