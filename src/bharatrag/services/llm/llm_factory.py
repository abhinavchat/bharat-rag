"""
Factory for creating LLM instances based on configuration.

Provides a single point for LLM creation with fallback mechanisms.
"""
from __future__ import annotations

import logging

from bharatrag.core.config import Settings, get_settings
from bharatrag.ports.llm import LLM
from bharatrag.services.llm.extractive_llm import ExtractiveLLM
from bharatrag.services.llm.local_llm import LocalLLM

logger = logging.getLogger(__name__)


def create_llm(settings: Settings | None = None) -> LLM:
    """
    Factory function to create LLM instance based on configuration.
    
    Args:
        settings: Settings instance (uses get_settings() if None)
        
    Returns:
        LLM instance (LocalLLM or ExtractiveLLM as fallback)
    """
    if settings is None:
        settings = get_settings()
    
    if settings.llm_backend == "local":
        try:
            logger.info(
                "Initializing local LLM",
                extra={
                    "model_name": settings.llm_model_name,
                    "device": settings.llm_device,
                },
            )
            
            llm = LocalLLM(
                model_name=settings.llm_model_name,
                device=settings.llm_device,
                max_length=settings.llm_max_length,
                temperature=settings.llm_temperature,
            )
            
            logger.info("Local LLM initialized successfully")
            return llm
            
        except Exception as e:
            logger.warning(
                "Failed to initialize local LLM, falling back to extractive",
                extra={
                    "error": str(e),
                    "model": settings.llm_model_name,
                },
            )
            return ExtractiveLLM()
    else:
        logger.info("Using extractive LLM backend")
        return ExtractiveLLM()

