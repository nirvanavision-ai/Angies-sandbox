"""Classify tutorials into niches based on keywords."""

from __future__ import annotations

import re

from trendbot.models import Niche


_NICHE_KEYWORDS: dict[Niche, list[str]] = {
    Niche.AI: [
        "artificial intelligence", "machine learning", "deep learning", "neural network",
        "llm", "large language model", "chatgpt", "gpt", "transformer", "ai tool",
    ],
    Niche.CODING: [
        "programming", "coding", "python", "javascript", "typescript", "react",
        "web dev", "backend", "frontend", "full stack", "api", "software",
    ],
    Niche.PERSONAL_DEV: [
        "personal development", "self improvement", "habit", "mindset",
        "motivation", "productivity hack", "morning routine", "journaling",
    ],
    Niche.AI_FILMMAKING: [
        "ai filmmaking", "ai video", "runway", "pika", "sora", "ai film",
        "ai movie", "text to video", "video generation",
    ],
    Niche.GRAPHIC_DESIGN: [
        "graphic design", "illustrator", "photoshop", "figma", "canva",
        "logo design", "branding", "typography", "ui design", "ux design",
    ],
    Niche.FINANCE: [
        "finance", "investing", "stock", "crypto", "trading", "budget",
        "passive income", "side hustle", "money", "wealth",
    ],
    Niche.IMAGE_TO_VIDEO: [
        "image to video", "img2vid", "animate image", "stable video",
        "video diffusion", "animate photo",
    ],
    Niche.AI_AGENTS: [
        "ai agent", "autonomous agent", "langchain", "autogpt", "crewai",
        "agentic", "tool use", "function calling", "mcp",
    ],
    Niche.AI_MUSIC: [
        "ai music", "suno", "udio", "music generation", "ai song",
        "text to music", "ai beat", "ai lyrics",
    ],
    Niche.PRODUCTIVITY: [
        "productivity", "notion", "obsidian", "time management",
        "workflow", "automation", "zapier", "make.com",
    ],
    Niche.NO_CODE: [
        "no code", "nocode", "low code", "bubble", "webflow",
        "airtable", "no-code",
    ],
    Niche.THREE_D: [
        "3d modeling", "blender", "3d print", "unreal engine",
        "unity", "3d animation", "cgi",
    ],
    Niche.MARKETING: [
        "marketing", "seo", "content marketing", "social media marketing",
        "email marketing", "growth hacking", "copywriting",
    ],
}


def classify_niche(title: str, description: str = "") -> Niche:
    """Classify a tutorial into the best-matching niche."""
    text = f"{title} {description}".lower()
    best_niche = Niche.OTHER
    best_count = 0

    for niche, keywords in _NICHE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_niche = niche

    return best_niche
