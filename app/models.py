"""
Pydantic models for Photo Styling App API
"""
from pydantic import BaseModel
from typing import Optional, Literal
from enum import Enum


class Theme(str, Enum):
    """Available styling themes"""
    SUPERHERO = "superhero"
    CYBERPUNK = "cyberpunk"
    FANTASY = "fantasy"
    PROFESSIONAL = "professional"


class TransformRequest(BaseModel):
    """Request model for image transformation"""
    theme: Theme
    # Image will be sent as multipart/form-data, not in JSON


class TransformResponse(BaseModel):
    """Response model for transformation results"""
    stylized_image: str  # Base64 encoded image
    features: str  # Extracted features from VLM
    prompt: str  # Generated prompt used for image generation
    status: str
    processing_time_seconds: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    vlm_service_url: Optional[str] = None
    imagegen_service_url: Optional[str] = None
    vlm_available: bool = False
    imagegen_available: bool = False