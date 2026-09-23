# Base sandbox image for the Adversarial ML Red-Teaming Platform.
# Owner: M2 (Cybersecurity #1)
#
# This image is intentionally generic — it just has the ML/attack stack
# pre-installed. M4's orchestrator code and job scripts are mounted in at
# `docker run` time, not baked into the image, so M2 and M4 never touch
# the same files.

FROM python:3.10-slim

# --- OS deps -----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# --- Python deps ---------------------------------------------------------
# Pinned loosely for M1 (skeleton). Tighten pins once M4's attack code is
# integrated and we know exact version requirements.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# --- Non-root user -------------------------------------------------------
# Defense in depth: even though we also drop capabilities and disable
# network at `docker run` time, the process inside should not be root.
RUN useradd -m -u 1000 sandboxuser
USER sandboxuser

WORKDIR /workspace

# No ENTRYPOINT/CMD baked in — sandbox_wrapper.py passes the script to run
# explicitly as the container command (contract-driven, not image-driven).
