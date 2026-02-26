"""
Prompt generation engine that combines VLM features with selected theme
"""
import re

from app.models import Theme


THEME_PROMPTS = {
    Theme.SUPERHERO: {
        "base": "A powerful superhero version of",
        "style": "bold comic book illustration, thick ink outlines, cel shading, flat vibrant colors, halftone dots, heroic stance, cape flowing, dramatic lighting, graphic novel art, anatomically correct, five fingers on each hand, two arms, two legs",
    },
    Theme.CYBERPUNK: {
        "base": "A cyberpunk version of",
        "style": "digital illustration, stylized anime-inspired art, neon glow effects, futuristic cybernetic enhancements, holographic elements, dark urban setting, sharp lines, cel shaded, synthwave color palette, anatomically correct, five fingers on each hand, two arms, two legs",
    },
    Theme.FANTASY: {
        "base": "A fantasy character version of",
        "style": "painted illustration, fantasy concept art, rich brushstrokes, stylized proportions, magical elements, mystical atmosphere, fantasy armor or robes, ethereal lighting, storybook art style, anatomically correct, five fingers on each hand, two arms, two legs",
    },
    Theme.PROFESSIONAL: {
        "base": "A professional portrait of",
        "style": "professional headshot, business attire, clean background, professional lighting, corporate style, polished appearance, anatomically correct, five fingers on each hand",
    },
}


def generate_prompt(features: str, theme: Theme) -> str:
    """
    Generate a prompt for image generation combining user features with theme.

    Args:
        features: Feature description from VLM (e.g., "person with glasses and beard")
        theme: Selected theme (superhero, cyberpunk, fantasy, professional)

    Returns:
        Combined prompt string
    """
    theme_config = THEME_PROMPTS[theme]

    # Strip any mention of "glasses" from features so the image generator
    # never sees the word — diffusion models treat "no glasses" as "glasses".
    cleaned_features = re.sub(r',?\s*\b\w*\s*glasses\b', '', features, flags=re.IGNORECASE).strip()
    cleaned_features = re.sub(r'\s{2,}', ' ', cleaned_features)

    prompt_parts = [
        theme_config["base"],
        cleaned_features,
        "in",
        theme_config["style"],
    ]
    return ", ".join(prompt_parts)
