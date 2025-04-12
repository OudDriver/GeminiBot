import subprocess

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)  # shell=True is generally NOT recommended, see notes.

        print(result.stdout)
        print(result.stderr)

        return result.returncode # Return the exit code
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Return Code: {e.returncode}")  # access return code
        print(f"Standard Output: {e.stdout}")
        print(f"Standard Error: {e.stderr}")
        return e.returncode  # Or raise the exception, depending on desired behavior

install_command = run_command("pip install -m requirements.txt")
print(f"Command returned: {install_command}")

docker_command = run_command("python install_docker.py")
print(f"Docker command exited with code {docker_command}")

print("Review any errors and run main.py!")