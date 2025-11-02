from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from installs.install_utils.install_utils import (
    download_file_with_progress,
    get_distro_info,
    run_command,
    setup_logging,
)
from packages.utilities.general_utils import start_docker_daemon

# Constants
DOCKERFILE_CONTENT = """
FROM python:3.12-slim-bookworm

ARG USER_NAME=sandboxuser
ARG USER_UID=1001
ARG USER_GID=${USER_UID}

RUN apt-get update && \\
    apt-get install -y --no-install-recommends \\
    libopenblas-dev libgfortran5 gfortran liblapack-dev git sudo && \\
    pip install --upgrade pip && \\
    pip install --no-cache-dir -f /dev/null numpy scipy sympy astropy \\
    biopython pandas statsmodels && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid ${USER_GID} ${USER_NAME} && \\
    useradd --uid ${USER_UID} --gid ${USER_GID} --create-home ${USER_NAME} && \\
    echo "${USER_NAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

WORKDIR /home/${USER_NAME}

USER ${USER_NAME}
"""
DOCKER_IMAGE_NAME = "python-sandbox-image"
TEMP_DIR = "../temp"  # Relative path for temporary files

system = platform.system()


# Helper Functions
def _run_installation_commands(commands: list[str | list[str]]) -> bool:
    """Run a sequence of shell commands.

    Args:
        commands: The command to run

    """
    for cmd in commands:
        cmd_list = cmd.split if isinstance(cmd, str) else cmd

        # Add sudo if not running as root and command likely needs it
        needs_sudo = (
             os.geteuid() != 0 and
             cmd_list[0] in [
                 "apt-get", "dnf",
                 "yum", "systemctl",
                 "install", "echo",
                 "tee", "groupadd",
                 "useradd", "usermod",
                 "chmod", "mkdir",
             ]
        )

        logger.debug(f"Running command: {' '.join(cmd_list)}")
        if not run_command(cmd_list, admin=needs_sudo):
            logger.error(f"Command failed: {' '.join(cmd_list)}")
            return False
    return True

def _configure_docker_group() -> bool:
    """Add the current user to the docker group."""
    logger.info("Configuring Docker group...")
    try:
        # Get user who ran sudo or current user
        current_user = os.environ.get("SUDO_USER")
        if not current_user and os.geteuid() == 0:
             logger.warning(
                 "Running as root, SUDO_USER not set. "
                 "Skipping adding user to docker group (root doesn't need it).",
             )
             return True # Assume root doesn't need this step
        if not current_user:
             current_user = os.getlogin()


        logger.info(f"Attempting to add user '{current_user}' to the 'docker' group.")
        # Ensure the group exists first (might fail harmlessly if it does)
        run_command(["sudo", "groupadd", "docker"])

        if not run_command(["sudo", "usermod", "-aG", "docker", current_user]):
             logger.error(f"Failed to add user '{current_user}' to the docker group.")
             return False

        logger.info(f"Added user '{current_user}' to the 'docker' group.")
        logger.warning(
            "IMPORTANT: You MUST log out and log back in "
            "for this group change to take effect.",
        )
        logger.warning(
            "Alternatively, you can try 'newgrp docker' "
            "in your current shell (may have side effects).",
        )
        return True

    except Exception:
        logger.exception("Error configuring docker group")
        logger.warning(
            "You may need to run 'docker' commands with 'sudo' "
            "or configure permissions manually.",
        )
        return False

def verify_docker() -> bool:
    """
    Verify if docker command exists and the daemon is active.

    This function distinguishes between two main failure cases:
    1. 'docker' command is not found in the PATH (Docker not installed).
    2. 'docker' command is found, but it cannot connect to the daemon
       (Docker Desktop / daemon not running, or permissions issue).
    """
    logger.info("Verifying Docker...")

    # --- Step 1: Check if the 'docker' executable is in the PATH ---
    docker_path = shutil.which("docker")
    if not docker_path:
        logger.error("--- Docker Not Found ---")
        logger.error("'docker' command not found in your system's PATH.")
        logger.error("This means Docker is likely not installed.")
        return False
    logger.info(f"Docker executable found at: {docker_path}")

    # --- Step 2: Check for daemon connectivity by running 'docker info' ---
    logger.info("Checking Docker daemon connectivity ('docker info')...")
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10
        )

        if result.returncode == 0:
            logger.info("Docker daemon is running and responding.")
            return True

        # --- Step 3: Analyze the error if the command failed ---
        logger.warning("--- Docker Found, But Daemon Not Responding ---")
        stderr_lower = result.stderr.lower()

        if "permission denied" in stderr_lower:
            logger.error("Error: Permission denied while trying to connect to the Docker daemon socket.")
            logger.warning("This is a common issue on Linux.")
            logger.warning("1. Ensure your user is in the 'docker' group: `sudo usermod -aG docker $USER`")
            logger.warning("2. IMPORTANT: You MUST log out and log back in for the group change to take effect.")
            logger.warning("3. As a temporary workaround, you can try running commands with `sudo`.")

        # --- THIS IS THE MODIFIED LINE ---
        # Check for the generic "daemon not running" message OR the specific Windows pipe error.
        elif "is the docker daemon running" in stderr_lower or "pipe/docker" in stderr_lower:
            if system == "Linux":
                logger.error("Error: The Docker daemon does not appear to be running.")
                logger.warning("You can try to start it with: `sudo systemctl start docker`")
                logger.warning("Check its status with: `sudo systemctl status docker`")
            elif system in {"Darwin", "Windows"}:
                logger.error("Error: Could not connect to Docker Desktop.")
                logger.warning("Please ensure the Docker Desktop application is running and has finished starting.")

        else:
            # A more generic error message if we can't parse the specific reason
            logger.error("An unknown error occurred while trying to connect to the Docker daemon.")
            logger.error(f"Command 'docker info' failed with exit code {result.returncode}.")
            logger.error(f"Error details: {result.stderr.strip()}")

        return False

    except FileNotFoundError:
        logger.error("'docker' command was not found when trying to execute it.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("'docker info' command timed out. The Docker daemon might be starting up, or it could be frozen.")
        return False


# Linux Installation Functions
def install_docker_debian() -> bool:
    """Installs Docker on Debian/Ubuntu."""
    logger.info("Configuring Docker repository for Debian/Ubuntu...")
    repo_commands = [
        "apt-get update -y",
        "apt-get install -y apt-transport-https ca-certificates curl gnupg",
        "install -m 0755 -d /etc/apt/keyrings",
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | "
        "gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
        "chmod a+r /etc/apt/keyrings/docker.gpg",
        'sh -c \'echo "deb [arch=$(dpkg --print-architecture) '
        'signed-by=/etc/apt/keyrings/docker.gpg] '
        'https://download.docker.com/linux/ubuntu '
        '$(. /etc/os-release && echo "$VERSION_CODENAME") stable" '
        '> /etc/apt/sources.list.d/docker.list\'',
        "apt-get update -y",
    ]
    if not _run_installation_commands(repo_commands):
        logger.error("Failed to configure Docker repository.")
        return False

    logger.info("Installing Docker packages...")
    install_cmd = ("apt-get install -y docker-ce docker-ce-cli containerd.io "
                   "docker-buildx-plugin docker-compose-plugin")
    if not _run_installation_commands([install_cmd]):
        logger.error("Failed to install Docker packages.")
        return False

    logger.info("Starting and enabling Docker service...")
    service_commands = ["systemctl start docker", "systemctl enable docker"]
    if not _run_installation_commands(service_commands):
        logger.warning(
            "Failed to start or enable Docker service via systemctl. "
            "It might already be running or use a different init system.",
        )
        # Continue, as installation might still be okay, but verification will be key.

    return _configure_docker_group()


def install_docker_fedora() -> bool:
    """Installs Docker on Fedora/Rocky/RHEL(dnf)."""
    logger.info("Configuring Docker repository for Fedora/Rocky...")
    repo_commands = [
        "dnf -y install dnf-plugins-core",
        "dnf config-manager --add-repo "
        "https://download.docker.com/linux/centos/docker-ce.repo", # Use CentOS repo
    ]
    if not _run_installation_commands(repo_commands):
        logger.error("Failed to configure Docker repository.")
        return False

    logger.info("Installing Docker packages...")
    install_cmd = ("dnf install -y docker-ce docker-ce-cli containerd.io "
                   "docker-buildx-plugin docker-compose-plugin")
    if not _run_installation_commands([install_cmd]):
        logger.error("Failed to install Docker packages.")
        return False

    logger.info("Starting and enabling Docker service...")
    service_commands = ["systemctl start docker", "systemctl enable docker"]
    if not _run_installation_commands(service_commands):
         logger.warning("Failed to start or enable Docker service via systemctl.")
        # Continue, as installation might still be okay, but verification will be key.

    return _configure_docker_group()


def install_docker_rhel() -> bool:
    """Installs Docker on RHEL/CentOS (yum)."""
    logger.info("Configuring Docker repository for RHEL/CentOS...")
    repo_commands = [
        "yum install -y yum-utils",
        "yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
    ]
    if not _run_installation_commands(repo_commands):
        logger.error("Failed to configure Docker repository.")
        return False

    logger.info("Installing Docker packages...")
    install_cmd = ("yum install -y docker-ce docker-ce-cli containerd.io "
                   "docker-buildx-plugin docker-compose-plugin")
    if not _run_installation_commands([install_cmd]):
        logger.error("Failed to install Docker packages.")
        return False

    logger.info("Starting and enabling Docker service...")
    service_commands = ["systemctl start docker", "systemctl enable docker"]
    if not _run_installation_commands(service_commands):
        logger.warning("Failed to start or enable Docker service via systemctl.")
        # Continue, as installation might still be okay, but verification will be key.

    return _configure_docker_group()


def install_docker_linux() -> bool:
    """Installs Docker on Linux by detecting the distribution."""
    distro_info = get_distro_info()
    distro_id = distro_info.get("ID")
    id_like = distro_info.get("ID_LIKE", [])

    logger.info(
        f"Detected Linux distribution: ID='{distro_id}', "
        f"ID_LIKE='{' '.join(id_like)}'",
    )

    if distro_id in [
        "debian", "ubuntu", "mint", "pop", "raspbian", "linuxmint",
    ] or "debian" in id_like:
        return install_docker_debian()

    if distro_id in ["fedora", "rocky"] or "fedora" in id_like:
        return install_docker_fedora()

    if distro_id in [
        "centos", "rhel", "almalinux",
    ] or "rhel" in id_like or "centos" in id_like:
        if shutil.which("dnf"):
             logger.info("Detected dnf, "
                         "using Fedora/Rocky installation method for RHEL-like distro.")
             return install_docker_fedora()
        if shutil.which("yum"):
             logger.info("Detected yum, using RHEL/CentOS installation method.")
             return install_docker_rhel()
        logger.error("Found RHEL-like distro "
                     "but neither 'dnf' nor 'yum' package manager was found.")
        return False
    logger.error(
        f"Linux distribution ID '{distro_id}' (or ID_LIKE '{' '.join(id_like)}') "
        "not automatically supported by this script.",
    )
    logger.error(
        "Please follow manual Docker installation instructions: https://docs.docker.com/engine/install/",
    )
    return False


# macOS Installation Function

def install_docker_macos() -> bool:
    """Installs Docker Desktop on macOS using Homebrew."""
    logger.info("Detected macOS.")
    if not shutil.which("brew"):
        logger.error("Homebrew ('brew') not found.")
        logger.error("Please install Homebrew first: https://brew.sh/")
        return False

    logger.info("Found Homebrew. Updating Homebrew...")
    if not run_command(["brew", "update"]):
        logger.warning("'brew update' failed, attempting install anyway.")

    logger.info(
        "Installing/updating Docker Desktop via Homebrew "
        "('brew install --cask docker')...",
    )
    logger.info("This may take some time and might require password input.")
    if not run_command(["brew", "install", "--cask", "docker"]):
        logger.error("Homebrew command failed.")
        logger.error("Try running manually: brew install --cask docker")
        return False

    logger.info("Docker Desktop installation command sent via Homebrew.")
    logger.warning("You MUST start Docker Desktop manually after installation.")
    logger.warning(
        "Follow any on-screen prompts "
        "from Docker Desktop itself to complete setup.",
    )
    # Cannot guarantee Docker is ready immediately after 'brew install' returns.
    return True # Return True indicating the command was sent


# Windows Installation Function

def install_docker_windows() -> bool:
    """Download and start the Docker Desktop installer on Windows."""
    logger.info("Detected Windows.")
    download_url = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    installer_name = "Docker_Desktop_Installer.exe"
    Path(TEMP_DIR).mkdir(exist_ok=True, parents=True)
    output_file = Path(TEMP_DIR) / installer_name

    logger.info(f"Downloading Docker Desktop installer from {download_url}...")
    try:
        download_file_with_progress(download_url, output_file.name)
    except Exception:
        logger.exception("Failed to download Docker installer.")
        return False

    logger.info(f"Downloaded installer to {output_file}")
    logger.warning("Starting Docker Desktop Installer")
    logger.warning("A graphical installer will now launch.")
    logger.warning("Please follow the on-screen instructions in the installer.")
    logger.warning("IMPORTANT: The installer may require a system RESTART "
                   "or LOG OUT / LOG IN.")
    logger.warning("After installation and any required restarts/logins,"
                   " ensure Docker Desktop is RUNNING.")
    logger.warning(
        "Then, you may need to run this script *again* to build the sandbox image.",
    )

    try:
        # Use subprocess.Popen to launch GUI without waiting indefinitely
        subprocess.Popen([output_file])
        logger.info("Installer launched.")

    except Exception:
        logger.exception("Failed to launch Docker installer:")
        return False

    else:
        return True


def build_docker_image() -> bool:
    """Build the Docker image for the Python sandbox."""
    dockerfile_path = "Dockerfile.sandbox"  # Use a specific name
    logger.info(f"Building Docker image '{DOCKER_IMAGE_NAME}' using Python 3.12...")

    try:
        # Create Dockerfile
        logger.debug(f"Creating temporary Dockerfile: {dockerfile_path}")
        with open(dockerfile_path, "w") as f:
            f.write(DOCKERFILE_CONTENT)

        # Build the image
        logger.info("Docker Build Output")
        build_command = [
            "docker", "build",
            "--no-cache",
            "-t", DOCKER_IMAGE_NAME,
            "-f", dockerfile_path,
            ".", # Build context
        ]
        success = run_command(build_command) # Show build output
        logger.info("End Docker Build Output")

        if not success:
            logger.error(f"Error building Docker image '{DOCKER_IMAGE_NAME}'.")
            logger.error("Check the build output above for details.")
            logger.error("Common issues:")
            logger.error("1. Is the Docker daemon running?")
            logger.error("2. Do you have permissions? "
                         "(Try logout/login on Linux after group add, or use sudo)")
            logger.error("3. Is there enough disk space?")
            logger.error("4. Is the network connection stable "
                         "(for downloading base images/packages)?")
            return False

        logger.info(f"Docker image '{DOCKER_IMAGE_NAME}' built successfully.")
        return True

    except Exception:
        logger.exception("An unexpected error occurred during image build.")
        return False

    finally:
        # Cleanup the Dockerfile
        if Path(dockerfile_path).exists():
            try:
                Path(dockerfile_path).unlink()
                logger.debug(f"Removed temporary Dockerfile: {dockerfile_path}")
            except OSError as e:
                logger.warning(
                    f"Could not remove temporary Dockerfile {dockerfile_path}: {e}",
                )


def verify_image() -> bool:
    """Verify if the image exists."""
    logger.info(f"Trying to check if image exists.")
    if run_command(
        ["docker", "image", "inspect", DOCKER_IMAGE_NAME],
        suppress_output=True,
    ):
        logger.info("Image exists.")
        return True
    logger.info("Image doesn't exist. Installing.")
    return False

# Main Execution
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Docker Setup and Sandbox Image Build")

    # --- RESTRUCTURED LOGIC ---

    # Case 1: 'docker' command is not found at all. Docker needs to be installed.
    if not shutil.which("docker"):
        logger.warning("--- Docker Not Found ---")
        logger.info("'docker' command not found in PATH. Attempting installation...")

        # Warn if running as root
        if system != "Windows" and os.geteuid() == 0:
            logger.warning("Running script as root. Package manager commands will be run directly without 'sudo'.")

        # Attempt Installation based on OS
        install_initiated = False
        if system == "Linux":
            install_initiated = install_docker_linux()
        elif system == "Darwin":
            install_initiated = install_docker_macos()
        elif system == "Windows":
            install_initiated = install_docker_windows()
        else:
            logger.error(f"Unsupported operating system: {system}.")
            logger.error("Manual Docker installation is required.")
            sys.exit(1)

        if not install_initiated:
            logger.error("Docker Installation Failed. Please review the logs above.")
            sys.exit(1)

        # After attempting install, verify if it's now ready.
        logger.info("Installation commands/launcher executed.")
        logger.info("Re-checking Docker status...")
        if not verify_docker():
            logger.error("Docker is still not ready after the installation attempt.")
            logger.warning("This is common on macOS/Windows where Docker Desktop requires manual setup, or on Linux if a logout/login is needed.")
            logger.warning("Please complete the Docker installation, ensure it is running, and then run this script again.")
            sys.exit(1)


    # Case 2: Docker is installed, but the daemon/desktop is not running.
    elif not verify_docker():
        logger.warning("--- Docker Found, But Daemon Is Not Responding ---")
        logger.info("Attempting to start the Docker daemon automatically...")

        start_docker_daemon()

        is_docker_ready = False
        max_wait_seconds = 20
        poll_interval_seconds = 5
        for i in range(max_wait_seconds // poll_interval_seconds):
            print(".", end="", flush=True)
            if verify_docker():
                print("\n")
                logger.info("Docker daemon started successfully!")
                is_docker_ready = True
                break
            time.sleep(poll_interval_seconds)

        if not is_docker_ready:
            print("\n")
            logger.error("Timed out waiting for Docker daemon.")
            logger.error("The script could not automatically start Docker.")
            if system in {"Darwin", "Windows"}:
                logger.warning("ACTION REQUIRED: Please start Docker Desktop manually. Check for any pop-ups or error messages from the application.")
            elif system == "Linux":
                logger.warning("ACTION REQUIRED: Check the service status (`sudo systemctl status docker`) and ensure you have correct permissions.")
            logger.warning("Once Docker is running, please run this script again.")
            sys.exit(1)

    # Case 3: Docker is installed and the daemon is responding. Proceed to image build.
    logger.info("Docker is installed and the daemon is responding.")
    logger.info("Checking if sandbox image needs to be built...")

    if verify_image():
        logger.info(f"Docker image '{DOCKER_IMAGE_NAME}' already exists. Setup complete.")
        sys.exit(0)
    else:
        logger.info(f"Docker image '{DOCKER_IMAGE_NAME}' not found. Proceeding to build...")
        if build_docker_image():
            logger.info("Setup Complete. The Docker image is ready.")
            sys.exit(0)
        else:
            logger.error("Image Build Failed.")
            sys.exit(1)
