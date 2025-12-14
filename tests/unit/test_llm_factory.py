"""
Tests for LLM factory.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bharatrag.core.config import Settings
from bharatrag.services.llm.extractive_llm import ExtractiveLLM
from bharatrag.services.llm.llm_factory import create_llm
from bharatrag.services.llm.local_llm import LocalLLM


def test_factory_creates_extractive_llm_by_default():
    """Test factory creates ExtractiveLLM when backend is 'extractive'."""
    settings = Settings(llm_backend="extractive")
    llm = create_llm(settings)
    
    assert isinstance(llm, ExtractiveLLM)


def test_factory_creates_local_llm_when_configured():
    """Test factory creates LocalLLM when backend is 'local'."""
    settings = Settings(
        llm_backend="local",
        llm_model_name="gpt2",
        llm_device="cpu",
    )
    
    with patch("bharatrag.services.llm.llm_factory.LocalLLM") as mock_local_llm:
        mock_local_llm.return_value = MagicMock()
        llm = create_llm(settings)
        
        assert isinstance(llm, type(mock_local_llm.return_value))
        mock_local_llm.assert_called_once_with(
            model_name="gpt2",
            device="cpu",
            max_length=512,
            temperature=0.7,
        )


def test_factory_falls_back_to_extractive_on_error():
    """Test factory falls back to ExtractiveLLM when LocalLLM fails to initialize."""
    settings = Settings(
        llm_backend="local",
        llm_model_name="gpt2",
    )
    
    with patch("bharatrag.services.llm.llm_factory.LocalLLM") as mock_local_llm:
        mock_local_llm.side_effect = Exception("Failed to load model")
        
        llm = create_llm(settings)
        
        assert isinstance(llm, ExtractiveLLM)


def test_factory_uses_custom_settings():
    """Test factory respects custom settings."""
    settings = Settings(
        llm_backend="local",
        llm_model_name="microsoft/DialoGPT-small",
        llm_device="cuda",
        llm_max_length=256,
        llm_temperature=0.9,
    )
    
    with patch("bharatrag.services.llm.llm_factory.LocalLLM") as mock_local_llm:
        mock_local_llm.return_value = MagicMock()
        create_llm(settings)
        
        mock_local_llm.assert_called_once_with(
            model_name="microsoft/DialoGPT-small",
            device="cuda",
            max_length=256,
            temperature=0.9,
        )


def test_factory_uses_get_settings_when_none_provided():
    """Test factory uses get_settings() when settings is None."""
    with patch("bharatrag.services.llm.llm_factory.get_settings") as mock_get_settings:
        mock_settings = Settings(llm_backend="extractive")
        mock_get_settings.return_value = mock_settings
        
        llm = create_llm(None)
        
        assert isinstance(llm, ExtractiveLLM)
        mock_get_settings.assert_called_once()

