"""
KServe Predictor for Image Generator (FLUX.1-schnell)
Generates images from text prompts using the FLUX.1-schnell model
"""
import os
import base64
import io
import logging
from typing import Dict, Any
from PIL import Image
import torch
from diffusers import FluxPipeline
import kserve
from kserve import Model, ModelServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageGenPredictor(Model):
    """
    KServe predictor for FLUX.1-schnell image generation
    """

    def __init__(self, name: str, model_name: str):
        super().__init__(name)
        self.name = name
        self.model_name = model_name
        self.pipe = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
        self.ready = False

    def load(self):
        """Load the FLUX.1-schnell model"""
        try:
            logger.info(f"Loading image generation model: {self.model_name}")
            logger.info(f"Using device: {self.device}")

            if self.device == "cuda" and self.num_gpus > 1:
                logger.info(f"Sharding model across {self.num_gpus} GPUs with device_map='balanced'")
                self.pipe = FluxPipeline.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.bfloat16,
                    device_map="balanced",
                )
            else:
                self.pipe = FluxPipeline.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.bfloat16,
                )
                if self.device == "cuda":
                    self.pipe = self.pipe.to(self.device)

            self.ready = True
            logger.info("Image generation model loaded successfully")

        except Exception as e:
            logger.error(f"Error loading image generation model: {str(e)}")
            raise

    def _generate_image(
        self,
        prompt: str,
        num_inference_steps: int = 4,
        height: int = 1024,
        width: int = 1024,
        guidance_scale: float = 0.0,
    ) -> dict:
        """Core inference: generate an image from a text prompt."""
        if not self.ready:
            raise RuntimeError("Model not loaded")

        with torch.no_grad():
            output = self.pipe(
                prompt=prompt,
                num_inference_steps=num_inference_steps,
                height=height,
                width=width,
                guidance_scale=guidance_scale,
            )

        generated_image = output.images[0]

        buffer = io.BytesIO()
        generated_image.save(buffer, format="PNG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {"image": image_base64}

    def predict(self, request: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Generate image from prompt (JSON endpoint).

        Expected request format:
        {
            "instances": [
                {
                    "prompt": "A superhero in a red cape flying over a city",
                    "num_inference_steps": 4,
                    "height": 1024,
                    "width": 1024,
                    "guidance_scale": 0.0
                }
            ]
        }
        """
        try:
            instances = request.get("instances", [])
            if not instances:
                raise ValueError("No instances provided in request")

            predictions = []

            for instance in instances:
                prompt = instance.get("prompt")
                if not prompt:
                    raise ValueError("No prompt provided in instance")

                predictions.append(self._generate_image(
                    prompt=prompt,
                    num_inference_steps=instance.get("num_inference_steps", 4),
                    height=instance.get("height", 1024),
                    width=instance.get("width", 1024),
                    guidance_scale=instance.get("guidance_scale", 0.0),
                ))

            return {"predictions": predictions}

        except Exception as e:
            logger.error(f"Error during image generation: {str(e)}")
            raise


if __name__ == "__main__":
    model_name = os.getenv("IMAGEGEN_MODEL_NAME", "black-forest-labs/FLUX.1-schnell")
    predictor = ImageGenPredictor(name="imagegen-predictor", model_name=model_name)
    predictor.load()

    model_server = ModelServer()
    model_server.models = [predictor]
    model_server.start([predictor])
