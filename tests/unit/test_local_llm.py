"""
Tests for LocalLLM implementation.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from bharatrag.services.llm.local_llm import LocalLLM


def test_local_llm_initialization():
    """Test LocalLLM can be initialized."""
    with patch("bharatrag.services.llm.local_llm.AutoModelForCausalLM") as mock_model, \
         patch("bharatrag.services.llm.local_llm.AutoTokenizer") as mock_tokenizer:
        
        llm = LocalLLM(
            model_name="gpt2",
            device="cpu",
            max_length=256,
            temperature=0.8,
        )
        
        assert llm.model_name == "gpt2"
        assert llm.device == "cpu"
        assert llm.max_length == 256
        assert llm.temperature == 0.8
        assert not llm._loaded


def test_local_llm_missing_dependencies():
    """Test LocalLLM raises error when transformers is not installed."""
    with patch("bharatrag.services.llm.local_llm.AutoModelForCausalLM", None):
        with pytest.raises(ValueError, match="transformers library not installed"):
            LocalLLM()


def test_local_llm_lazy_loading():
    """Test that model is loaded lazily on first generate call."""
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    
    # Mock tokenizer behavior - create a proper mock tensor
    mock_inputs = MagicMock()
    mock_inputs.shape = [1, 10]  # Proper shape attribute
    mock_inputs.to.return_value = mock_inputs  # Chain the to() call
    
    mock_tokenizer.encode.return_value = mock_inputs
    mock_tokenizer.decode.return_value = "Test prompt Test response"
    mock_tokenizer.pad_token = None
    mock_tokenizer.eos_token = "<|endoftext|>"
    mock_tokenizer.pad_token_id = 50256
    mock_tokenizer.eos_token_id = 50256
    
    # Mock model behavior
    mock_model_instance = MagicMock()
    mock_model_instance.config.max_position_embeddings = 1024
    mock_output = MagicMock()
    mock_output.shape = [1, 20]
    mock_output.__getitem__.return_value = mock_output  # For outputs[0]
    mock_model_instance.generate.return_value = mock_output
    mock_model_instance.to.return_value = None
    mock_model_instance.eval.return_value = None
    
    mock_model.from_pretrained.return_value = mock_model_instance
    mock_tokenizer.from_pretrained.return_value = mock_tokenizer
    
    with patch("bharatrag.services.llm.local_llm.AutoModelForCausalLM", mock_model), \
         patch("bharatrag.services.llm.local_llm.AutoTokenizer", mock_tokenizer), \
         patch("bharatrag.services.llm.local_llm.torch") as mock_torch:
        
        mock_torch.float32 = "float32"
        mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
        mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=None)
        
        llm = LocalLLM(model_name="gpt2", device="cpu")
        
        # Model should not be loaded yet
        assert not llm._loaded
        
        # Generate should trigger loading
        result = llm.generate("Test prompt")
        
        # Model should now be loaded
        assert llm._loaded
        mock_model.from_pretrained.assert_called_once()
        mock_tokenizer.from_pretrained.assert_called_once()
        assert result is not None


def test_local_llm_generation():
    """Test text generation with LocalLLM."""
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    
    # Setup tokenizer - create proper mock tensor
    mock_inputs = MagicMock()
    mock_inputs.shape = [1, 10]  # Proper shape attribute
    mock_inputs.to.return_value = mock_inputs  # Chain the to() call
    
    mock_tokenizer.encode.return_value = mock_inputs
    mock_tokenizer.decode.return_value = "Test prompt Test response"
    mock_tokenizer.pad_token = None
    mock_tokenizer.eos_token = "<|endoftext|>"
    mock_tokenizer.pad_token_id = 50256
    mock_tokenizer.eos_token_id = 50256
    
    # Setup model
    mock_model_instance = MagicMock()
    mock_model_instance.config.max_position_embeddings = 1024
    mock_output = MagicMock()
    mock_output.shape = [1, 20]
    mock_output.__getitem__.return_value = mock_output  # For outputs[0]
    mock_model_instance.generate.return_value = mock_output
    mock_model_instance.to.return_value = None
    mock_model_instance.eval.return_value = None
    
    mock_model.from_pretrained.return_value = mock_model_instance
    mock_tokenizer.from_pretrained.return_value = mock_tokenizer
    
    with patch("bharatrag.services.llm.local_llm.AutoModelForCausalLM", mock_model), \
         patch("bharatrag.services.llm.local_llm.AutoTokenizer", mock_tokenizer), \
         patch("bharatrag.services.llm.local_llm.torch") as mock_torch:
        
        mock_torch.float32 = "float32"
        mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
        mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=None)
        
        llm = LocalLLM(model_name="gpt2", device="cpu", max_length=100)
        result = llm.generate("Test prompt")
        
        assert result is not None
        assert isinstance(result, str)
        mock_model_instance.generate.assert_called_once()


def test_local_llm_input_truncation():
    """Test that long inputs are truncated appropriately."""
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    
    # Mock very long input - create proper mock tensor
    long_input = MagicMock()
    long_input.shape = [1, 2000]  # Very long input
    long_input.to.return_value = long_input  # Chain the to() call
    # Mock slicing for truncation: inputs[:, -keep_length:]
    long_input.__getitem__.return_value = long_input
    
    mock_tokenizer.encode.return_value = long_input
    mock_tokenizer.decode.return_value = "Truncated response"
    mock_tokenizer.pad_token = None
    mock_tokenizer.eos_token = "<|endoftext|>"
    mock_tokenizer.pad_token_id = 50256
    mock_tokenizer.eos_token_id = 50256
    
    mock_model_instance = MagicMock()
    mock_model_instance.config.max_position_embeddings = 1024
    mock_output = MagicMock()
    mock_output.shape = [1, 20]
    mock_output.__getitem__.return_value = mock_output  # For outputs[0]
    mock_model_instance.generate.return_value = mock_output
    mock_model_instance.to.return_value = None
    mock_model_instance.eval.return_value = None
    
    mock_model.from_pretrained.return_value = mock_model_instance
    mock_tokenizer.from_pretrained.return_value = mock_tokenizer
    
    with patch("bharatrag.services.llm.local_llm.AutoModelForCausalLM", mock_model), \
         patch("bharatrag.services.llm.local_llm.AutoTokenizer", mock_tokenizer), \
         patch("bharatrag.services.llm.local_llm.torch") as mock_torch:
        
        mock_torch.float32 = "float32"
        mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
        mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=None)
        
        llm = LocalLLM(model_name="gpt2", device="cpu", max_length=100)
        
        # Should handle truncation gracefully
        result = llm.generate("A" * 10000)  # Very long prompt
        
        assert result is not None
        # Verify input was truncated (check that encode was called)
        mock_tokenizer.encode.assert_called()


def test_local_llm_error_handling():
    """Test error handling in LocalLLM."""
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    
    mock_model.from_pretrained.side_effect = Exception("Model load failed")
    mock_tokenizer.from_pretrained.return_value = mock_tokenizer
    
    with patch("bharatrag.services.llm.local_llm.AutoModelForCausalLM", mock_model), \
         patch("bharatrag.services.llm.local_llm.AutoTokenizer", mock_tokenizer):
        
        llm = LocalLLM(model_name="gpt2")
        
        with pytest.raises(ValueError, match="Failed to load model"):
            llm._load_model()

