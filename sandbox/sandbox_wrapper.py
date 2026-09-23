"""
sandbox_wrapper.py
Owner: M2 (Cybersecurity #1)
Milestone 1 — plain subprocess wrapper around `docker run`.
(Milestone 2 replaces this with the Docker SDK version — see
sandbox_manager.py's `run_scan()` contract in ARCHITECTURE.md.)

Responsibilities (and ONLY these — M2 never touches attack code):
  - mount the model file + job_config.json (contract #3) read-only
  - mount a shared output volume read-write
  - enforce CPU / memory / network / timeout limits at `docker run` time
  - run whatever script is handed to it (M4's orchestrator, or this
    milestone's verify_dummy_predict.py) inside the container
  - capture stdout/stderr and the exit code
  - confirm the expected output file landed in the shared volume

Usage:
  python sandbox_wrapper.py \
      --image adv-ml-sandbox:latest \
      --model /path/to/model.pkl \
      --job-config /path/to/job_config.json \
      --output-dir ./scan_output \
      --script verify_dummy_predict.py \
      --cpus 1.0 \
      --memory 2g \
      --timeout 60 \
      --network none
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def build_docker_command(
    image: str,
    model_path: Path,
    job_config_path: Path,
    output_dir: Path,
    script_path: Path,
    cpus: str,
    memory: str,
    network: str,
    container_name: str,
) -> list[str]:
    """Assemble the `docker run` argv. Every resource limit lives here as an
    explicit CLI flag — nothing implicit, nothing left to the image default."""

    cmd = [
        "docker", "run",
        "--rm",  # never leave stopped containers lying around
        "--name", container_name,

        # --- resource limits (M2's core responsibility) ---
        "--cpus", cpus,
        "--memory", memory,
        "--memory-swap", memory,  # disable swap growth beyond the memory cap
        "--pids-limit", "256",  # fork-bomb guard
        "--network", network,  # "none" by default; "bridge" only if a scan explicitly needs egress
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--read-only",  # container root filesystem is read-only

        # --- mounts (contract #3 in, shared volume out) ---
        "-v", f"{model_path.resolve()}:/data/model.pkl:ro",
        "-v", f"{job_config_path.resolve()}:/data/job_config.json:ro",
        "-v", f"{output_dir.resolve()}:/output:rw",
        "-v", f"{script_path.resolve()}:/workspace/run.py:ro",

        # writable scratch space, since the root fs is read-only
        "--tmpfs", "/tmp",

        image,
        "python", "/workspace/run.py",
    ]
    return cmd


def run_sandboxed(
    image: str,
    model_path: Path,
    job_config_path: Path,
    output_dir: Path,
    script_path: Path,
    cpus: str = "1.0",
    memory: str = "2g",
    network: str = "none",
    timeout: int = 60,
    container_name: str = "adv-ml-scan",
) -> dict:
    """Runs the container and enforces the timeout ourselves (Docker has no
    native `docker run --timeout` flag, so this is wrapper-enforced, per
    ARCHITECTURE.md contract #3)."""

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_docker_command(
        image, model_path, job_config_path, output_dir, script_path,
        cpus, memory, network, container_name,
    )

    result = {
        "exit_code": None,
        "timed_out": False,
        "stdout": "",
        "stderr": "",
        "output_file_found": False,
    }

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result["exit_code"] = proc.returncode
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr

    except subprocess.TimeoutExpired as e:
        result["timed_out"] = True
        result["stdout"] = e.stdout or ""
        result["stderr"] = e.stderr or ""
        # kill/remove the container if the timeout wrapper fired mid-run
        subprocess.run(["docker", "kill", container_name], capture_output=True)
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    output_file = output_dir / "dummy_verify_result.json"
    result["output_file_found"] = output_file.exists()

    return result


def main():
    parser = argparse.ArgumentParser(description="M2 sandbox wrapper (Milestone 1)")
    parser.add_argument("--image", required=True, help="Docker image tag, e.g. adv-ml-sandbox:latest")
    parser.add_argument("--model", required=True, type=Path, help="Path to model file (.pkl/.onnx/.pt)")
    parser.add_argument("--job-config", required=True, type=Path, help="Path to job_config.json (contract #3)")
    parser.add_argument("--output-dir", required=True, type=Path, help="Shared output volume on host")
    parser.add_argument("--script", required=True, type=Path,
                         help="Script to run inside the container (e.g. verify_dummy_predict.py)")
    parser.add_argument("--cpus", default="1.0", help="CPU limit, e.g. '1.0' = 1 core")
    parser.add_argument("--memory", default="2g", help="Memory limit, e.g. '2g'")
    parser.add_argument("--network", default="none", choices=["none", "bridge"],
                         help="Network mode. 'none' = fully isolated (default). "
                              "Use 'bridge' only for scans that explicitly need egress.")
    parser.add_argument("--timeout", type=int, default=60, help="Wrapper-enforced timeout in seconds")
    parser.add_argument("--container-name", default="adv-ml-scan")

    args = parser.parse_args()

    for p, label in [(args.model, "model"), (args.job_config, "job-config"), (args.script, "script")]:
        if not p.exists():
            print(f"error: {label} path does not exist: {p}", file=sys.stderr)
            sys.exit(2)

    result = run_sandboxed(
        image=args.image,
        model_path=args.model,
        job_config_path=args.job_config,
        output_dir=args.output_dir,
        script_path=args.script,
        cpus=args.cpus,
        memory=args.memory,
        network=args.network,
        timeout=args.timeout,
        container_name=args.container_name,
    )

    print("--- container stdout ---")
    print(result["stdout"])
    if result["stderr"]:
        print("--- container stderr ---", file=sys.stderr)
        print(result["stderr"], file=sys.stderr)

    print(json.dumps({
        "exit_code": result["exit_code"],
        "timed_out": result["timed_out"],
        "output_file_found": result["output_file_found"],
    }, indent=2))

    if result["timed_out"]:
        sys.exit(124)  # conventional timeout exit code
    sys.exit(result["exit_code"] if result["exit_code"] is not None else 1)


if __name__ == "__main__":
    main()
