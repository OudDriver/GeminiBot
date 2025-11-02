import logging
import sys

try:
    from installs.install_utils.install_utils import run_command, setup_logging
except ModuleNotFoundError:
    print("tdqm and/or requests not found!")
    print("Please install using")
    print("pip install tqdm requests")
    sys.exit(1)

if __name__ == "__main__":
    python_interpreter = sys.executable

    setup_logging()
    logger = logging.getLogger(__name__)

    cmake_command = run_command([python_interpreter, "-m", "installs.install_cmake"])
    logger.info(f"Command returned: {cmake_command}")

    install_command = run_command([python_interpreter, "-m", "pip", "install", "-r", "requirements.txt"])
    logger.info(f"Command returned: {install_command}")

    docker_command = run_command([python_interpreter, "-m", "installs.install_docker"])
    logger.info(f"Docker command exited with code {docker_command}")

    latex_command = run_command([python_interpreter, "-m", "installs.install_latex"])
    logger.info(f"LaTeX command exited with code {latex_command}")

    logger.info("Review any errors and run main.py!")