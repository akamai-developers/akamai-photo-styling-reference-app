"""
Direct pipeline test: VLM describe → ImageGen generate
Bypasses the FastAPI app and talks directly to the two model servers.

Usage:
    python tests/test_pipeline.py <vlm_ip> <imagegen_ip> <image_file> [output_file]

Example:
    python tests/test_pipeline.py 192.168.1.10 192.168.1.20 selfie.jpg output.png
"""
import sys
import os
import time
import json
import base64
import requests


def main():
    if len(sys.argv) < 4:
        print("Usage: python test_pipeline.py <vlm_ip> <imagegen_ip> <image_file> [output_file]")
        sys.exit(1)

    vlm_ip = sys.argv[1]
    imagegen_ip = sys.argv[2]
    image_file = sys.argv[3]
    output_file = sys.argv[4] if len(sys.argv) > 4 else "generated.png"

    vlm_url = f"http://{vlm_ip}:30080"
    imagegen_url = f"http://{imagegen_ip}:30081"

    if not os.path.exists(image_file):
        print(f"ERROR: Image file not found: {image_file}")
        sys.exit(1)

    # Step 1: Check both services are up
    print(f"Checking VLM at {vlm_url} ...")
    try:
        r = requests.get(f"{vlm_url}/v1/models", timeout=10)
        print(f"  VLM models: {r.json()}")
    except Exception as e:
        print(f"  ERROR: VLM not reachable: {e}")
        sys.exit(1)

    print(f"Checking ImageGen at {imagegen_url} ...")
    try:
        r = requests.get(f"{imagegen_url}/v1/models", timeout=10)
        print(f"  ImageGen models: {r.json()}")
    except Exception as e:
        print(f"  ERROR: ImageGen not reachable: {e}")
        sys.exit(1)

    # Step 2: Send image to VLM for description
    print(f"\nSending {image_file} to VLM for description...")
    t0 = time.time()
    with open(image_file, "rb") as f:
        r = requests.post(
            f"{vlm_url}/v1/models/vlm-predictor:describe",
            files={"file": (os.path.basename(image_file), f)},
            timeout=120,
        )
    vlm_elapsed = time.time() - t0

    if r.status_code != 200:
        print(f"  ERROR: VLM returned {r.status_code}: {r.text}")
        sys.exit(1)

    vlm_result = r.json()
    features = vlm_result["predictions"][0]["features"]
    print(f"  VLM response ({vlm_elapsed:.1f}s):")
    print(f"  {features}")

    # Step 3: Send description to ImageGen
    prompt = features
    print(f"\nSending prompt to ImageGen...")
    t0 = time.time()
    r = requests.post(
        f"{imagegen_url}/v1/models/imagegen-predictor:predict",
        json={"instances": [{"prompt": prompt}]},
        timeout=300,
    )
    imagegen_elapsed = time.time() - t0

    if r.status_code != 200:
        print(f"  ERROR: ImageGen returned {r.status_code}: {r.text}")
        sys.exit(1)

    imagegen_result = r.json()
    image_b64 = imagegen_result["predictions"][0]["image"]
    print(f"  ImageGen response ({imagegen_elapsed:.1f}s): got base64 image ({len(image_b64)} chars)")

    # Step 4: Save the image
    image_bytes = base64.b64decode(image_b64)
    with open(output_file, "wb") as f:
        f.write(image_bytes)

    total = vlm_elapsed + imagegen_elapsed
    print(f"\nSaved to {output_file} ({len(image_bytes)} bytes)")
    print(f"Total time: {total:.1f}s (VLM {vlm_elapsed:.1f}s + ImageGen {imagegen_elapsed:.1f}s)")


if __name__ == "__main__":
    main()
