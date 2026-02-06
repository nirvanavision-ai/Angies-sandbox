"""Tests for niche classification."""

from trendbot.models import Niche
from trendbot.ranking.niche_classifier import classify_niche


class TestNicheClassifier:
    def test_ai_niche(self):
        assert classify_niche("Building a ChatGPT Clone with LLMs") == Niche.AI

    def test_coding_niche(self):
        assert classify_niche("Python Web Development Tutorial for Beginners") == Niche.CODING

    def test_finance_niche(self):
        assert classify_niche("How to Start Investing in Stocks for Passive Income") == Niche.FINANCE

    def test_ai_music_niche(self):
        assert classify_niche("How to Use Suno AI to Create Music") == Niche.AI_MUSIC

    def test_ai_agents_niche(self):
        assert classify_niche("Build an AI Agent with LangChain and Tool Use") == Niche.AI_AGENTS

    def test_graphic_design_niche(self):
        assert classify_niche("Figma UI Design Tutorial for Logo Design") == Niche.GRAPHIC_DESIGN

    def test_unknown_returns_other(self):
        assert classify_niche("Random unrelated content about cooking") == Niche.OTHER

    def test_uses_description_for_classification(self):
        result = classify_niche(
            "Getting Started",
            "This tutorial covers machine learning and deep learning concepts"
        )
        assert result == Niche.AI
