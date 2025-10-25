import logging
import platform
import sys

try:
    from installs.install_utils.install_utils import run_command, setup_logging
except ModuleNotFoundError:
    print("tdqm and/or requests not found!")
    print("Please install using")
    print("pip install tqdm requests")
    sys.exit(1)

if __name__ == "__main__":
    python_interpreter = "python3" if platform.platform() == "Linux" else "python"
    pip = "pip3" if platform.platform() == "Linux" else "pip"

    setup_logging()
    logger = logging.getLogger(__name__)

    cmake_command = run_command([python_interpreter, "installs/install_cmake.py"])
    logger.info(f"Command returned: {cmake_command}")

    install_command = run_command([pip, "install", "-r", "requirements.txt"])
    logger.info(f"Command returned: {install_command}")

    docker_command = run_command([python_interpreter, "installs/install_docker.py"])
    logger.info(f"Docker command exited with code {docker_command}")

    latex_command = run_command([python_interpreter, "installs/install_latex.py"])
    logger.info(f"LaTeX command exited with code {latex_command}")

    logger.info("Review any errors and run main.py!")
