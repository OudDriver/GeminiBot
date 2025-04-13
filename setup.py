import os
import queue
import shutil
import subprocess
import sys
import threading


def _stream_reader(stream, queue_obj, label):
    """
    Reads lines from a stream (stdout/stderr) and puts them into a queue.
    Adds a label ('STDOUT' or 'STDERR') to distinguish them.
    Puts (label, None) into the queue when the stream is exhausted.
    """
    try:
        # Read line by line until the stream is closed
        for line in iter(stream.readline, ''):
            queue_obj.put((label, line))
    except Exception as e:
        # Handle potential errors during stream reading
        queue_obj.put((label, f"Error reading stream: {e}\n"))
    finally:
        # Signal that this stream is done
        queue_obj.put((label, None))
        # Close the stream from the Python side
        # This might be redundant if Popen manages it, but can be good practice
        try:
            stream.close()
        except IOError:
            pass # Stream might already be closed

def run_command(cmd_list: list[str] | str):
    """
    Runs a command using subprocess.Popen for real-time output.
    Prepends sudo if the script is not run as root.
    Prints stdout/stderr as it arrives.
    Returns True on success (exit code 0), False on failure.
    """
    if os.geteuid() != 0:
        if shutil.which("sudo"):
            cmd_list = ["sudo"] + cmd_list
        else:
            print("Error: Not running as root and 'sudo' command not found.", file=sys.stderr)
            print("Please run this script as root or install sudo.", file=sys.stderr)
            return False

    print(f"--- Running command: {' '.join(cmd_list)}")
    process = None # Initialize process to None
    try:
        # Start the process
        process = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, # Decode output as text
            bufsize=1, # Line-buffered
            universal_newlines=True, # Ensure cross-platform newline handling
        )

        # Create queue and threads for reading output
        output_queue = queue.Queue()
        stdout_thread = threading.Thread(
            target=_stream_reader,
            args=(process.stdout, output_queue, "STDOUT"),
            daemon=True # Allows main thread to exit even if this thread is running
        )
        stderr_thread = threading.Thread(
            target=_stream_reader,
            args=(process.stderr, output_queue, "STDERR"),
            daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()

        # --- Process output from the queue ---
        streams_finished = 0
        while streams_finished < 2: # Wait until both stdout and stderr readers signal completion
            try:
                # Get output line from the queue (block briefly if necessary)
                label, line = output_queue.get(timeout=0.1) # Timeout prevents indefinite block

                if line is None:
                    # The stream reader thread finished
                    streams_finished += 1
                    # print(f"--- {label} stream finished ---") # Optional debug message
                    continue # Go back to check the queue again

                # Print the line to the correct stream
                if label == "STDOUT":
                    # Print directly to sys.stdout, ensuring newline
                    sys.stdout.write(line)
                    sys.stdout.flush() # Ensure it appears immediately
                elif label == "STDERR":
                    sys.stderr.write(line)
                    sys.stderr.flush()

            except queue.Empty:
                # Queue is empty, check if the process ended unexpectedly
                if process.poll() is not None and output_queue.empty():
                    # Process finished, and queue is empty, might happen if no more output
                    # but threads haven't put None yet. Break if both threads are dead.
                    if not stdout_thread.is_alive() and not stderr_thread.is_alive():
                       streams_finished=2 # Ensure loop terminates
                       break
                # If process is still running and queue is empty, just continue waiting
                continue

        # --- Wait for process to terminate and get exit code ---
        # Threads are daemons, they will exit automatically, but we still need Popen's result
        return_code = process.wait() # Waits for the child process to exit

        if return_code == 0:
            print(f"\n--- Command successful: {' '.join(cmd_list)} (Exit Code: {return_code})")
            return True
        else:
            print(f"\n--- Command failed: {' '.join(cmd_list)} (Exit Code: {return_code})", file=sys.stderr)
            return False

    except FileNotFoundError:
        # This occurs if the command itself (e.g., sudo, apt-get) isn't found
        print(f"Error: Command not found: {cmd_list[0]}", file=sys.stderr)
        if process and process.poll() is None:
             process.kill() # Terminate if somehow started but command failed later
        return False
    except Exception as e:
        # Catch any other unexpected errors during Popen or processing
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        if process and process.poll() is None:
             process.kill() # Terminate if running
        return False
    finally:
        # Ensure process is cleaned up if something went very wrong early on
        # (wait() should handle normal termination)
        if process and process.poll() is None:
            print("Warning: Forcibly terminating process due to incomplete exit.", file=sys.stderr)
            process.terminate() # Try graceful termination first
            try:
                process.wait(timeout=2)  # Wait briefly
            except subprocess.TimeoutExpired:
                process.kill()  # Force kill if terminate didn't work


if "__name__" == "__main__":
    install_command = run_command("pip install -r requirements.txt".split(" "))
    print(f"Command returned: {install_command}")

    install_command = run_command("python install_cmake.py".split(" "))
    print(f"Command returned: {install_command}")

    docker_command = run_command("python install_docker.py".split(" "))
    print(f"Docker command exited with code {docker_command}")

    print("Review any errors and run main.py!")