"""
KServe Predictor for Vision-Language Model (VLM)
Analyzes user selfies and extracts feature descriptions
"""
import os
import io
import logging
from typing import Dict, Any
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
try:
    from transformers import Qwen3VLProcessor
except ImportError:
    Qwen3VLProcessor = None
import kserve
from kserve import Model, ModelServer
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from kserve.model_server import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLMPredictor(Model):
    """
    KServe predictor for VLM that analyzes images and returns feature descriptions
    """
    
    def __init__(self, name: str, model_name: str):
        super().__init__(name)
        self.name = name
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.ready = False
        
    def load(self):
        """Load the VLM model and processor"""
        try:
            logger.info(f"Loading VLM model: {self.model_name}")
            logger.info(f"Using device: {self.device}")
            
            # Load processor (use Qwen3VLProcessor for Qwen3-VL to avoid video_processing_auto bug)
            if Qwen3VLProcessor is not None and "Qwen3" in self.model_name:
                self.processor = Qwen3VLProcessor.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                )
            else:
                self.processor = AutoProcessor.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                )
            self.model = AutoModelForImageTextToText.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
            )
            
            if self.device == "cuda":
                self.model = self.model.to(self.device)
            
            self.model.eval()
            self.ready = True
            logger.info("VLM model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading VLM model: {str(e)}")
            raise
    
    DEFAULT_PROMPT = (
        "Describe the person in this image, focusing on facial features, "
        "hair, glasses, beard, and other distinctive characteristics. "
        "Be specific and detailed."
    )

    def _describe_image(self, image: Image.Image, prompt: str = None) -> dict:
        """Core inference: take a PIL Image and prompt, return description dict."""
        if not self.ready:
            raise RuntimeError("Model not loaded")

        if prompt is None:
            prompt = self.DEFAULT_PROMPT

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            }
        ]

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs.pop("token_type_ids", None)
        inputs = {k: v.to(self.device) if hasattr(v, "to") else v for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False
            )

        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
        ]
        generated_text = self.processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )[0]

        if prompt in generated_text:
            features = generated_text.replace(prompt, "").strip()
        else:
            features = generated_text.strip()

        return {"features": features, "raw_output": generated_text}


def register_describe_route(predictor: VLMPredictor) -> None:
    """Register the multipart/form-data describe endpoint on the KServe FastAPI app."""

    @app.post("/v1/models/vlm-predictor:describe")
    async def describe(
        file: UploadFile = File(...),
        prompt: str = Form(None),
    ):
        try:
            image_bytes = await file.read()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid image file"})

        try:
            result = predictor._describe_image(image, prompt)
            return {"predictions": [result]}
        except Exception as e:
            logger.error(f"Error during describe: {str(e)}")
            return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    model_name = os.getenv("VLM_MODEL_NAME", "Qwen/Qwen3-VL-8B-Instruct-FP8")
    predictor = VLMPredictor(name="vlm-predictor", model_name=model_name)
    predictor.load()

    register_describe_route(predictor)

    model_server = ModelServer()
    model_server.models = [predictor]
    model_server.start([predictor])
