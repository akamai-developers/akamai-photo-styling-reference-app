"""
HTTP clients for VLM and Image Generator KServe services
"""
import base64
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class VLMClient:
    """Client for VLM KServe service"""

    PROMPT = (
        "Describe only what you can see in this image. Focus on the person's "
        "appearance: hair color and style, skin tone, facial hair if present, "
        "clothing, and expression. Do not mention features that are absent."
    )

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.describe_url = f"{self.base_url}/v1/models/vlm-predictor:describe"

    async def analyze_image(self, image_bytes: bytes) -> str:
        """
        Analyze image and extract features via multipart upload.

        Args:
            image_bytes: Raw image bytes

        Returns:
            Feature description string
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.describe_url,
                    files={"file": ("image.jpg", image_bytes, "image/jpeg")},
                    data={"prompt": self.PROMPT},
                )
                response.raise_for_status()

                result = response.json()
                predictions = result.get("predictions", [])
                if not predictions:
                    raise ValueError("No predictions returned from VLM service")

                features = predictions[0].get("features", "")
                if not features:
                    features = predictions[0].get("raw_output", "")

                return features.strip()

        except Exception as e:
            logger.error(f"Error calling VLM service: {e}")
            raise


class ImageGenClient:
    """Client for Image Generator KServe service"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.predict_url = f"{self.base_url}/v1/models/imagegen-predictor:predict"

    async def generate_image(self, prompt: str, num_inference_steps: int = 4) -> bytes:
        """
        Generate stylized image from prompt.

        Args:
            prompt: Text prompt for image generation
            num_inference_steps: Number of inference steps

        Returns:
            Generated image as bytes (PNG format)
        """
        try:
            request_data = {
                "instances": [
                    {
                        "prompt": prompt,
                        "num_inference_steps": num_inference_steps,
                    }
                ]
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.predict_url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()

                result = response.json()
                predictions = result.get("predictions", [])
                if not predictions:
                    raise ValueError("No predictions returned from Image Generator service")

                image_base64 = predictions[0].get("image", "")
                if not image_base64:
                    raise ValueError("No image in prediction response")

                return base64.b64decode(image_base64)

        except Exception as e:
            logger.error(f"Error calling Image Generator service: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Image Generator service is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                return response.status_code == 200
        except Exception:
            return False


async def check_vlm_health(base_url: str) -> bool:
    """Check if VLM service is available"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/v1/models")
            return response.status_code == 200
    except Exception:
        return False
