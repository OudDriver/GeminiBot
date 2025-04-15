import os
import platform
from setup import run_command
import sys
import shutil

system = platform.system()

def get_distro_info():
    """
    Detects Linux distribution information from /etc/os-release.
    Returns a dictionary with 'ID' and 'ID_LIKE' (list).
    """
    distro_info = {'ID': None, 'ID_LIKE': []}
    
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

def install_latex_linux():
    """
    Installs LaTeX on Linux.
    """
    distro_info = get_distro_info()
    distro_id = distro_info.get('ID')
    id_like = distro_info.get('ID_LIKE', [])

    if not distro_id and not id_like:
        print("Could not reliably determine the distribution.", file=sys.stderr)
        return False

    print(f"Detected Distro ID: {distro_id}")
    print(f"Detected ID_LIKE: {id_like}")

    latex_installed = False

    # --- Debian / Ubuntu / Mint etc. ---
    if distro_id in ["debian", "ubuntu", "mint", "pop", "raspbian", "linuxmint"] or "debian" in id_like:
        print("Detected Debian-based distribution (apt).")
        if run_command(["apt-get", "update", "-y"]):
            print("\nAttempting to install texlive-bin...")
            if run_command(["apt-get", "install", "-y", "texlive-bin"]):
                latex_installed = True
            else:
                 print("Failed to install texlive-bin.", file=sys.stderr)
        else:
            print("Failed to update package lists (apt-get update).", file=sys.stderr)

    # --- Fedora / RHEL / CentOS / Rocky / Alma ---
    elif distro_id in ["fedora", "rhel", "centos", "rocky", "almalinux"] or "fedora" in id_like or "rhel" in id_like:
        print("Detected Red Hat-based distribution (dnf/yum).")
        pkg_manager = "dnf" if shutil.which("dnf") else "yum" if shutil.which("yum") else None

        if pkg_manager:
            print(f"Using {pkg_manager} package manager.")
            print("\nAttempting to install texlive...")
            if run_command([pkg_manager, "install", "-y", "texlive"]):
                latex_installed = True
            else:
                print("Failed to install texlive.", file=sys.stderr)
        else:
            print("Error: Neither dnf nor yum package managers found.", file=sys.stderr)

    # --- Arch Linux / Manjaro ---
    elif distro_id in ["arch", "manjaro"] or "arch" in id_like:
        print("Detected Arch-based distribution (pacman).")
        print("\nAttempting to sync repositories and install texlive-bin...")
        # Combine update and install for typical Arch workflow
        # Using --needed ensures packages aren't reinstalled unnecessarily
        if run_command(["pacman", "-Syu", "--noconfirm", "--needed", "texlive-bin"]):
            latex_installed = True
        else:
            print("Failed to sync repositories or install texlive-bin.", file=sys.stderr)

    # --- openSUSE / SLES ---
    elif distro_id in ["opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles"] or "suse" in id_like:
        print("Detected SUSE-based distribution (zypper).")
        print("\nAttempting to install texlive...")
        if run_command(["zypper", "install", "--non-interactive", "texlive"]):
            latex_installed = True
        else:
             print("Failed to install texlive.", file=sys.stderr)

    # --- Alpine Linux ---
    elif distro_id == "alpine":
        print("Detected Alpine Linux (apk).")
        if run_command(["apk", "update"]):
            print("\nAttempting to install texlive...")
            if run_command(["apk", "add", "texlive"]):
                latex_installed = True
            else:
                print("Failed to install texlive.", file=sys.stderr)
        else:
            print("Failed to update apk repositories.", file=sys.stderr)

    # --- Unsupported ---
    else:
        print(f"Error: Unsupported distribution: ID='{distro_id}', ID_LIKE='{id_like}'", file=sys.stderr)
        print("Please install CMake and build tools manually using your system's package manager.", file=sys.stderr)
        return False # Definitely failed

    if not latex_installed:
        print("\nCMake installation failed.", file=sys.stderr)

    return latex_installed

def install_latex_macos():
    """Installs MacTeX on macOS using Homebrew."""
    print("Detected macOS.")
    if not shutil.which("brew"):
        print("*** ERROR: Homebrew ('brew') not found.", file=sys.stderr)
        print("Please install Homebrew first. See: https://brew.sh/", file=sys.stderr)
        return False

    print("Found Homebrew.")
    print("Updating Homebrew (this may take a while)...")
    success = run_command(["brew", "update"])
    if not success:
        # Don't stop if update fails, maybe install will still work
        print("*** WARNING: 'brew update' failed, attempting install anyway.", file=sys.stderr)
        # return False # Optional: be stricter

    print(f"Installing MacTeX (mactex)...")
    print("This is a large download and may take a significant amount of time.")
    success = run_command(["brew", "install", "--cask", "mactex"])
    if not success:
        print(f"*** ERROR: Failed to install mactex with Homebrew.", file=sys.stderr)
        print(f"   Try running manually: brew install --cask mactex", file=sys.stderr)
        print("   You might need to agree to licenses or enter your password.", file=sys.stderr)
        return False
    return True

def install_latex_windows():
    """Installs LaTeX (MiKTeX or TeX Live) on Windows using winget or choco."""
    print("Detected Windows.")
    print("This script requires Administrator privileges to install software.")
    print(f"Attempting to install MiKTeX.")

    use_winget = shutil.which("winget")
    use_choco = shutil.which("choco")

    if use_winget:
        print("Found 'winget' package manager.")
        pkg_id = 'MiKTeX.MiKTeX'

        print(f"Installing {pkg_id} using winget...")
        cmd = [
            "winget", "install",
            "--id", pkg_id,
            "-e",
            "--accept-source-agreements",
            "--accept-package-agreements"
        ]
        success, = run_command(cmd) # Requires script run as Admin
        if not success:
            print(f"*** ERROR: Failed to install {pkg_id} using winget.", file=sys.stderr)
            print("   Try running winget install manually in an Administrator prompt.", file=sys.stderr)
            return False
        return True

    elif use_choco:
        print("Found 'choco' package manager.")
        pkg_id = "miktex"

        print(f"Installing {pkg_id} using Chocolatey...")
        cmd = ["choco", "install", pkg_id, "-y"]
        success = run_command(cmd) 
        if not success:
            print(f"*** ERROR: Failed to install {pkg_id} using Chocolatey.", file=sys.stderr)
            print("   Try running choco install manually in an Administrator prompt.", file=sys.stderr)
            return False
        return True

    else:
        print("*** ERROR: Could not find 'winget' or 'choco'.", file=sys.stderr)
        print("Please install either Windows Package Manager (winget) or Chocolatey first,")
        print("or install MiKTeX/TeX Live manually from their respective websites:")
        print("   MiKTeX: https://miktex.org/download")
        print("   TeX Live: https://www.tug.org/texlive/acquire-netinstall.html")
        return False
        

def verify_installation():
    """Checks if cmake command is available and runs --version."""
    print("\n--- Verifying LaTeX (pdfTeX) installation ---")
    cmake_path = shutil.which("pdftex")
    if cmake_path:
        print(f"LaTeX executable found at: {cmake_path}")
        command = run_command(["pdftex", "--version"], False)
        return command
    else:
        print("Error: 'pdftex' command not found in PATH after installation attempt.", file=sys.stderr)
        return False

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting LaTeX installation script...")
    
    if verify_installation():
        print("LaTeX is already installed, no need to continue.")
        sys.exit(0)
        
    # Warn if running as root directly
    if os.geteuid() == 0:
        print("\nWarning: Running script as root.", file=sys.stderr)
        print("Package manager commands will be run directly without 'sudo'.\n", file=sys.stderr)

    install_succesful = False
    
    if system == "Linux":
        install_succesful = install_latex_linux()
    elif system == "MacOS":
        install_succesful = install_latex_macos()
    elif system == "Windows":
        install_succesfull = install_latex_windows()

    if install_succesful:
        print("\nLaTeX installation commands executed successfully.")
        if verify_installation():
             print("\nLaTeX installation verified.")
             sys.exit(0) # Exit with success code
        else:
             print("\nLaTeX installation command ran, but verification failed.", file=sys.stderr)
             sys.exit(1) # Exit with error code
    else:
        print("\nLaTeX installation failed.", file=sys.stderr)
        sys.exit(1) # Exit with error code