"""
FastAPI orchestration application for Photo Styling App
Coordinates VLM and Image Generator services
"""
import os
import time
import logging
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional

from app.models import TransformRequest, TransformResponse, HealthResponse, Theme
from app.prompt_engine import generate_prompt
from app.client import VLMClient, ImageGenClient, check_vlm_health

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Photo Styling App",
    description="Transform selfies into stylized images using AI",
    version="1.0.0"
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Get service URLs from environment variables
VLM_SERVICE_URL = os.getenv("VLM_SERVICE_URL", "http://vlm-service")
IMAGEGEN_SERVICE_URL = os.getenv("IMAGEGEN_SERVICE_URL", "http://imagegen-service")

# Initialize clients
vlm_client = VLMClient(VLM_SERVICE_URL)
imagegen_client = ImageGenClient(IMAGEGEN_SERVICE_URL)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    try:
        with open("static/index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Photo Styling App</h1><p>Frontend not found. Please ensure static/index.html exists.</p>",
            status_code=404
        )


@app.post("/transform", response_model=TransformResponse)
async def transform_image(
    image: UploadFile = File(..., description="User's selfie image"),
    theme: str = Form(..., description="Styling theme (superhero, cyberpunk, fantasy, professional)")
):
    """
    Transform a selfie into a stylized image based on the selected theme
    
    Process:
    1. Receive selfie upload
    2. Call VLM service to extract features
    3. Generate prompt combining features + theme
    4. Call Image Generator service to create stylized image
    5. Return stylized image
    
    All processing is done in-memory (no disk storage).
    """
    start_time = time.time()
    
    try:
        # Validate theme
        try:
            theme_enum = Theme(theme.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid theme. Must be one of: {', '.join([t.value for t in Theme])}"
            )
        
        # Validate image file
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="File must be an image"
            )
        
        # Read image into memory (no disk storage)
        image_bytes = await image.read()
        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Image file is empty"
            )
        
        # Validate image size (max 10MB)
        MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
        if len(image_bytes) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large. Maximum size is {MAX_IMAGE_SIZE / 1024 / 1024}MB"
            )
        
        logger.info(f"Processing image transformation: theme={theme_enum.value}, size={len(image_bytes)} bytes")
        
        # Step 1: Call VLM service to extract features
        logger.info("Calling VLM service to extract features...")
        features = await vlm_client.analyze_image(image_bytes)
        logger.info(f"Extracted features: {features[:100]}...")
        
        # Step 2: Generate prompt combining features + theme
        logger.info(f"Generating prompt for theme: {theme_enum.value}")
        prompt = generate_prompt(features, theme_enum)
        logger.info(f"Generated prompt: {prompt[:100]}...")

        # Step 3: Call Image Generator service
        logger.info("Calling Image Generator service...")
        stylized_image_bytes = await imagegen_client.generate_image(prompt=prompt)
        logger.info(f"Generated stylized image: {len(stylized_image_bytes)} bytes")
        
        # Step 4: Encode result as base64
        import base64
        stylized_image_base64 = base64.b64encode(stylized_image_bytes).decode("utf-8")
        
        processing_time = time.time() - start_time
        logger.info(f"Transformation complete in {processing_time:.2f} seconds")
        
        return TransformResponse(
            stylized_image=stylized_image_base64,
            features=features,
            prompt=prompt,
            status="success",
            processing_time_seconds=round(processing_time, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during transformation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transformation failed: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns status of the service and connected model services
    """
    try:
        vlm_available = await check_vlm_health(VLM_SERVICE_URL)
        imagegen_available = await imagegen_client.health_check()
        
        return HealthResponse(
            status="healthy" if (vlm_available and imagegen_available) else "degraded",
            vlm_service_url=VLM_SERVICE_URL,
            imagegen_service_url=IMAGEGEN_SERVICE_URL,
            vlm_available=vlm_available,
            imagegen_available=imagegen_available
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            vlm_service_url=VLM_SERVICE_URL,
            imagegen_service_url=IMAGEGEN_SERVICE_URL,
            vlm_available=False,
            imagegen_available=False
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
