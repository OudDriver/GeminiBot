import subprocess
import platform
import sys
import time
import requests
from tqdm import tqdm
import os
from urllib.parse import urlparse
from setup import run_command

# Updated Dockerfile content to use Python 3.12 and a unique user
DOCKERFILE_CONTENT = """
FROM python:3.12-slim-bookworm

ARG USER_NAME=sandboxuser
ARG USER_UID=1001
ARG USER_GID=${USER_UID}

RUN apt-get update && \\
    apt-get install -y --no-install-recommends libopenblas-dev libgfortran5 gfortran liblapack-dev git && \\
    pip install --upgrade pip && \\
    pip install --no-cache-dir -f numpy scipy sympy astropy biopython pandas statsmodels && \\
    apt-get clean && \\
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid ${USER_GID} ${USER_NAME} && \\
    useradd --uid ${USER_UID} --gid ${USER_GID} --create-home ${USER_NAME}

WORKDIR /home/${USER_NAME}

USER ${USER_NAME}
"""

def download_file_with_progress(url: str, local_filename: str=None, chunk_size: int=8192):
    """
    Downloads a file from a URL showing a progress bar.

    Args:
        url (str): The URL of the file to download.
        local_filename (str, optional): The local path to save the file.
                                         If None, derives filename from URL.
        chunk_size (int, optional): Size of download chunks in bytes. Defaults to 8192.
    """
    try:
        # If local_filename is not specified, derive it from the URL
        if local_filename is None:
            parsed_url = urlparse(url)
            local_filename = os.path.basename(parsed_url.path)
            if not local_filename: # Handle cases where path is empty or just '/'
                local_filename = "downloaded_file"
                print(f"Warning: Could not derive filename from URL. Saving as '{local_filename}'.")

        print(f"Attempting to download '{url}' to '{local_filename}'...")

        # Send a GET request to the URL, streaming the response
        with requests.get(url, stream=True, timeout=30) as r:
            # Check if the request was successful
            r.raise_for_status()

            # Get the total file size from headers, if available
            total_size_in_bytes = int(r.headers.get('content-length', 0))

            # Warn if Content-Length header is missing
            if total_size_in_bytes == 0:
                 print("Warning: Content-Length header not found. Progress bar may be inaccurate or infinite.")

            # Open the local file in binary write mode
            with open(local_filename, 'wb') as f:
                # Initialize tqdm progress bar
                with tqdm(
                    total=total_size_in_bytes,
                    unit='B',         # Unit = Bytes
                    unit_scale=True,  # Automatically convert to KB, MB, etc.
                    unit_divisor=1024,# Use 1024 for conversion
                    desc=local_filename, # Description shown next to progress bar
                    ncols=100,        # Width of the progress bar
                    miniters=1,       # Update progress bar after each chunk
                    ascii=True        # Use ASCII characters for wider compatibility
                ) as pbar:
                    # Iterate over the response data in chunks
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk: # filter out keep-alive new chunks
                            # Write chunk to file
                            f.write(chunk)
                            # Update progress bar by the size of the chunk written
                            pbar.update(len(chunk))

        # Check if the downloaded file size matches the expected size (if known)
        if total_size_in_bytes != 0 and os.path.getsize(local_filename) != total_size_in_bytes:
            print(f"\nError: Download incomplete. Expected {total_size_in_bytes} bytes, got {os.path.getsize(local_filename)} bytes.")
        else:
             print(f"\nDownload complete: '{local_filename}'")

    except requests.exceptions.RequestException as e:
        print(f"\nError during download: {e}")
    except IOError as e:
        print(f"\nError writing file: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

def get_linux_distro():
    """Attempts to identify the Linux distribution using /etc/os-release."""
    try:
        with open("/etc/os-release") as f:
            distro_info = dict(line.strip().split('=', 1) for line in f if '=' in line)
            # Remove quotes from values
            for key, value in distro_info.items():
                distro_info[key] = value.strip('"')
        return distro_info.get('ID', '').lower(), distro_info.get('ID_LIKE', '').lower().split()
    except FileNotFoundError:
        print("Warning: /etc/os-release not found. Trying deprecated platform.linux_distribution().", file=sys.stderr)
        # Fallback for older systems or unusual setups
        try:
             # platform.linux_distribution is deprecated and will be removed in Python 3.8+
             # Using it here as a fallback, but be aware it might not work reliably.
             dist_tuple = platform.linux_distribution()
             # Handle potential empty tuple if detection fails
             distro_id = dist_tuple[0].lower() if dist_tuple and dist_tuple[0] else ''
             return distro_id, [distro_id] # Simulate ID_LIKE with just the ID
        except AttributeError:
             print("Could not determine Linux distribution.", file=sys.stderr)
             return '', []


def install_docker():
    """Installs Docker on the system (Linux, macOS, or Windows). Returns True if Docker is ready."""
    system = platform.system()

    # Check if Docker is already installed and runnable
    x = run_command(["docker", "--version"])
    y = run_command(["docker", "info"])
    if x and y:
        print("Docker is already installed and the daemon is running.")
        return True # Indicate Docker is ready

    print("Docker command not found. Attempting installation...")
    print("Attempting installation/configuration steps...")
    try:
        if system == "Linux":
            distro_id, distro_like = get_linux_distro()
            print(f"Detected Linux distribution: ID='{distro_id}', ID_LIKE='{' '.join(distro_like)}'")

            # Debian / Ubuntu
            if distro_id == "ubuntu" or "debian" in distro_like:
                print("Configuring Docker repository for Debian/Ubuntu...")
                install_cmds = [
                    "sudo apt-get update",
                    "sudo apt-get install -y apt-transport-https ca-certificates curl gnupg", # Ensure pre-reqs
                    "sudo install -m 0755 -d /etc/apt/keyrings",
                    "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
                    "sudo chmod a+r /etc/apt/keyrings/docker.gpg",
                    'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
                    "sudo apt-get update",
                ]
                package_install_cmd = "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
                repo_setup_done = True

            # Fedora
            elif distro_id == "fedora" or "fedora" in distro_like:
                print("Configuring Docker repository for Fedora...")
                install_cmds = [
                    "sudo dnf -y install dnf-plugins-core",
                    "sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo",
                ]
                package_install_cmd = "sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
                repo_setup_done = True

            # CentOS / RHEL
            elif distro_id in ["centos", "rhel"] or "rhel" in distro_like or "centos" in distro_like:
                print("Configuring Docker repository for CentOS/RHEL...")
                install_cmds = [
                    "sudo yum install -y yum-utils",
                    "sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
                ]
                package_install_cmd = "sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
                repo_setup_done = True

            else:
                print(f"Warning: Linux distribution ID '{distro_id}' (or ID_LIKE '{' '.join(distro_like)}') not explicitly supported by this script's automated install.", file=sys.stderr)
                print("Manual Docker installation is recommended: https://docs.docker.com/engine/install/", file=sys.stderr)
                return False # Indicate installation likely failed

            a = False
            if repo_setup_done:
                for cmd in install_cmds:
                    a = run_command(cmd)
                print("Installing Docker packages...")
                b = run_command(package_install_cmd)

                print("Starting and enabling Docker service...")
                c = run_command("sudo systemctl start docker")
                d = run_command("sudo systemctl enable docker")

                e = False
                print("Configuring Docker group")
                try:
                    e = current_user = os.environ.get('SUDO_USER', os.getlogin()) # Get user who ran sudo or current user
                    run_command(["sudo", "usermod", "-aG", "docker", current_user])
                    print(f"Added user '{current_user}' to the 'docker' group.")
                    print("IMPORTANT: You MUST log out and log back in for this group change to take effect.")
                    print("Alternatively, you can run 'newgrp docker' in your current shell (may have side effects).")
                except Exception as group_err:
                    print(
                        f"Warning: Could not add user to docker group: {group_err}",
                        file=sys.stderr,
                    )
                    print(
                        "You may need to run 'docker' commands with 'sudo' or manually configure permissions.",
                        file=sys.stderr,
                    )

                if not a and b and c and d and e:
                    print(
                        "\n--- An error occurred during the Docker setup process ---",
                        file=sys.stderr,
                    )
                    print("Docker setup failed.", file=sys.stderr)
                    return False # Indicate failure


            else: # Should not happen if logic is correct, but as a safeguard
                 return False

        elif system == "Darwin":
            print("Checking for Homebrew...")
            try:
                a = run_command(["brew", "--version"])
                print("Homebrew found. Installing/updating Docker Desktop via Homebrew...")
                # `brew install` will update if already installed
                b = run_command(["brew", "install", "--cask", "docker"])
                print("Docker Desktop installation/update initiated via Homebrew.")
                print("Please follow any on-screen prompts from Docker Desktop itself.")
                print("You may need to start Docker Desktop manually after installation.")
                # Note: We can't easily wait for the GUI app to be ready from here.

                if not a and b:
                    print("Homebrew not found or 'brew install' failed.", file=sys.stderr)
                    print("Please download and install Docker Desktop for Mac manually from:", file=sys.stderr)
                    print("https://docs.docker.com/desktop/mac/install/", file=sys.stderr)
                    print("Ensure Docker Desktop is running, then run this script again.", file=sys.stderr)
                    return False # Indicate manual step needed

            except Exception as e:
                print("Installing Docker on MacOS failed! " + e)

        elif system == "Windows":
            download_url_windows = 'https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe'
            output_file = 'temp/docker_installer.exe'
            os.makedirs('temp', exist_ok=True)
            download_file_with_progress(download_url_windows, output_file)
            print("A GUI will show up. Follow the instructions. Then, log out and log back in.")
            print("Open the \"Docker Desktop\" app, press skip on all (or sign in, it's up to you) and run this script.")
            subprocess.run(output_file)
            return False # Indicate manual step needed
        else:
            print(f"Unsupported operating system: {system}.", file=sys.stderr)
            print("Manual Docker installation is required.", file=sys.stderr)
            return False # Indicate failure

        # --- Verification Step after Installation ---
        print("\nVerifying Docker daemon connectivity after installation...")
        max_retries = 6
        retry_delay = 5 # seconds
        for i in range(max_retries):
            try:
                # Use a simple command like 'docker info' which requires daemon connection
                a = run_command(["docker", "info"])
                if a:
                    print("Docker daemon is running and responding.")
                    return True # Success! Docker is ready.
                # FileNotFoundError should ideally not happen here if install succeeded, but check anyway
                print(f"Waiting for Docker daemon... ({i+1}/{max_retries})")
                if i < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    print("Could not connect to Docker daemon after installation attempts.", file=sys.stderr)
                    if system == "Linux":
                        print("Check Docker service status: sudo systemctl status docker", file=sys.stderr)
                        print("Check user permissions (are you in the 'docker' group? did you log out/in?)", file=sys.stderr)
                    elif system == "Darwin" or system == "Windows":
                        print("Ensure Docker Desktop is running.", file=sys.stderr)
                    return False # Indicate failure
            except Exception as e:
                print("An error occurred while trying to verify Docker! " + e)

    except Exception as e:
        print("\n--- An error occurred during the Docker setup process ---", file=sys.stderr)
        print(e)
        print("Docker setup failed.", file=sys.stderr)
        return False # Indicate failure

    finally:
        try:
            os.remove('./temp/docker_installer.exe')
            print("Removed docker_installer.exe")
        except FileNotFoundError:
            print("docker_installer not found. It means that you're not running Windows.")
            pass


def build_docker_image():
    """Builds the Docker image for the Python sandbox."""
    dockerfile_path = "Dockerfile.sandbox" # Use a more specific name
    image_name = "python-sandbox-image"
    print(f"\nBuilding Docker image '{image_name}' using Python 3.12...")

    try:
        # Create Dockerfile
        with open(dockerfile_path, "w") as f:
            f.write(DOCKERFILE_CONTENT)
        print(f"Created temporary Dockerfile: {dockerfile_path}")

        # Build the image
        # Note: On Linux, this might require sudo or the user to be in the 'docker' group
        print("\n--- Docker Build Output ---")
        if not run_command(
            [
                "docker",
                "build",
                "--no-cache",
                "-t",
                image_name,
                "-f",
                dockerfile_path,
                ".",
            ]
        ):
            print("--- End Docker Build Output. ERROR! ---")
            print(f"\nError building Docker image '{image_name}'.")
            print("1. Is the Docker daemon running?")
            print("2. Do you have permissions to interact with the Docker daemon?")
            print("Docker installation failed.")
            print("(On Linux, try running this script with 'sudo', or log out/in if added to 'docker' group).")
            return False

        print("--- End Docker Build Output ---")
        print(f"\nDocker image '{image_name}' built successfully.")
        return True # Indicate success

    except Exception as e:
         print(f"\nAn unexpected error occurred during image build: {e}", file=sys.stderr)
         return False

    finally:
         # Cleanup the Dockerfile
         if os.path.exists(dockerfile_path):
              try:
                  os.remove(dockerfile_path)
                  print(f"Removed temporary Dockerfile: {dockerfile_path}")
              except OSError as e:
                  print(f"Warning: Could not remove temporary Dockerfile {dockerfile_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    print("--- Starting Docker Setup and Sandbox Image Build ---")

    docker_ready = install_docker()

    if not docker_ready:
        print("\n--- Docker Installation/Setup Incomplete ---", file=sys.stderr)
        print("Docker is not ready. Please review the messages above, ensure Docker is installed and running correctly.", file=sys.stderr)
        print("If Docker is already installed in Windows, please log out and run this script again.", file=sys.stderr)
        sys.exit(1) # Exit if Docker isn't ready

    print("\n--- Docker Ready - Proceeding to Image Build ---")

    if build_docker_image():
        print("\n--- Setup Complete ---")
        print(f"The Docker image '{'python-sandbox-image'}' using Python 3.12 is ready.")
        sys.exit(0) # Success
    else:
        print("\n--- Image Build Failed ---", file=sys.stderr)
        print("Please check the error messages above.", file=sys.stderr)
        sys.exit(1) # Exit if build failed