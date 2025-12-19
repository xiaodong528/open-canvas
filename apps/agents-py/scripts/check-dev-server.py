import subprocess
import threading
import time
from pathlib import Path

READY_PATTERNS = (
    "ready",
    "started",
    "server running",
    "uvicorn running",
    "application startup complete",
)

ERROR_PATTERNS = (
    "error",
    "exception:",
    "traceback",
    "failed to compile",
    "failed",
)

IGNORE_ERROR_PATTERNS = ("warning",)

STDERR_ERROR_PATTERNS = (
    "error",
    "exception:",
    "traceback",
    "failed to",
    "fatal",
)

IGNORE_STDERR_PATTERNS = ("warning:", "deprecated")

BROWSER_OPEN_IGNORE_PATTERNS = (
    "browser_opener",
    "opening studio",
    "studio ui",
    "smith.langchain.com/studio",
    "osascript",
    "hiservices-xpcservice",
    "execution error",
    "connection invalid",
    'application "chrome"',
    'application "firefox"',
    'application "safari"',
)


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(needle in haystack for needle in needles)


def check_dev_server(timeout_seconds: int = 15) -> None:
    print("Starting development server in apps/agents-py...")

    script_dir = Path(__file__).resolve().parent
    target_cwd = script_dir.parent

    process = subprocess.Popen(
        "langgraph dev --port 54367",
        cwd=str(target_cwd),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    state = {
        "error_detected": False,
        "server_ready": False,
    }
    lock = threading.Lock()

    def handle_output(stream, is_stderr: bool) -> None:
        for line in iter(stream.readline, ""):
            if not line:
                break
            print(line, end="")
            lowered = line.lower()

            if _contains_any(lowered, READY_PATTERNS):
                with lock:
                    state["server_ready"] = True
                print("Server ready message detected.")

            if is_stderr:
                if _contains_any(lowered, BROWSER_OPEN_IGNORE_PATTERNS) or _contains_any(
                    lowered, IGNORE_STDERR_PATTERNS
                ):
                    continue
                if _contains_any(lowered, STDERR_ERROR_PATTERNS) and not _contains_any(
                    lowered, IGNORE_ERROR_PATTERNS
                ):
                    with lock:
                        state["error_detected"] = True
                    print("Error detected in server stderr output!")
            else:
                if _contains_any(lowered, ERROR_PATTERNS) and not _contains_any(
                    lowered, IGNORE_ERROR_PATTERNS
                ):
                    with lock:
                        state["error_detected"] = True
                    print("Error detected in server output!")

    stdout_thread = threading.Thread(
        target=handle_output, args=(process.stdout, False), daemon=True
    )
    stderr_thread = threading.Thread(
        target=handle_output, args=(process.stderr, True), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if process.poll() is not None:
            break
        time.sleep(0.1)

    if process.poll() is None:
        print(f"Timeout reached ({timeout_seconds}s). Terminating server process.")
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            print("Failed to terminate with SIGTERM, killing process.")
            process.kill()
            process.wait(timeout=3)
    else:
        print(f"Server process exited with code {process.returncode}")

    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)

    with lock:
        error_detected = state["error_detected"]
        server_ready = state["server_ready"]

    if process.returncode not in (0, None) and not server_ready:
        error_detected = True

    if error_detected:
        raise RuntimeError(
            "Errors detected during server startup. Check logs for details."
        )
    if not server_ready:
        raise RuntimeError(
            "Server did not indicate successful startup within timeout."
        )

    print("Server check passed! Server started successfully and indicated readiness.")


def main() -> None:
    try:
        check_dev_server()
    except Exception as exc:
        print(f"❌ Dev server check failed: {exc}")
        raise SystemExit(1) from exc
    print("✅ Dev server check completed successfully!")


if __name__ == "__main__":
    main()
