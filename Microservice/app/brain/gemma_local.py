"""
Local Gemma interpreter using the fine-tuned LoRA adapter.
This loads the trained model directly for inference.

NOTE: This module is designed to be imported independently without
triggering the main brain import chain.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Model paths - use absolute path resolution
_SCRIPT_DIR = Path(__file__).parent.resolve()
MODEL_DIR = _SCRIPT_DIR.parent.parent / "models" / "gemma-interpreter" / "final"
BASE_MODEL = "google/gemma-2b"

# Lazy loading
_model = None
_tokenizer = None

SYSTEM_PROMPT = """You are a desktop automation interpreter. Parse user commands into structured JSON with:
- intent: The action type (OPEN_APP, CLICK_UI, TYPE_TEXT, WEB_SEARCH, FILE_OP, SYSTEM_CONTROL, MULTI_ACTION)
- entities: Extracted parameters (app, target, text, url, path, etc.)
- capabilities_needed: Required automation capabilities
- confidence: Your confidence 0.0-1.0
- risk: low|medium|high

Return ONLY valid JSON."""


def is_model_available() -> bool:
    """Check if the fine-tuned model is available."""
    return MODEL_DIR.exists() and (MODEL_DIR / "adapter_config.json").exists()


def load_model():
    """Load the fine-tuned Gemma model with LoRA adapter."""
    global _model, _tokenizer
    
    if _model is not None:
        return _model, _tokenizer
    
    if not is_model_available():
        logger.warning(f"Fine-tuned model not found at {MODEL_DIR}")
        return None, None
    
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        from huggingface_hub import try_to_load_from_cache
        
        # Check if base model is already cached - skip if not to avoid blocking startup
        cached_config = try_to_load_from_cache(BASE_MODEL, "config.json")
        if cached_config is None:
            logger.info("ℹ️ Gemma base model not cached, skipping to avoid blocking startup")
            logger.info("   Run 'huggingface-cli download google/gemma-2b' to download it")
            return None, None
        
        logger.info(f"Loading fine-tuned Gemma from {MODEL_DIR}")
        
        # Check for GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        
        logger.info(f"Using device: {device}")
        
        # Load tokenizer
        _tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
        
        # Load base model (from cache only, no download)
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            torch_dtype=dtype,
            device_map="auto" if device == "cuda" else None,
            low_cpu_mem_usage=True,
            local_files_only=True,  # Don't download, use cached only
        )
        
        if device == "cpu":
            base_model = base_model.to(device)
        
        # Load LoRA adapter
        _model = PeftModel.from_pretrained(base_model, str(MODEL_DIR))
        _model.eval()
        
        logger.info("✅ Fine-tuned Gemma model loaded successfully")
        return _model, _tokenizer
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None, None


def interpret_command(command: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Interpret a user command using the fine-tuned Gemma model.
    
    Args:
        command: The user's natural language command
        context: Optional context (active window, etc.)
        
    Returns:
        Parsed interpretation with intent, entities, capabilities, confidence, risk
    """
    model, tokenizer = load_model()
    
    if model is None or tokenizer is None:
        logger.warning("Model not loaded, returning None")
        return None
    
    try:
        import torch
        
        # Format prompt
        context_str = ""
        if context:
            if "active_window" in context:
                context_str = f"\nActive window: {context['active_window']}"
        
        prompt = f"""<start_of_turn>user
{SYSTEM_PROMPT}{context_str}

User command: {command}<end_of_turn>
<start_of_turn>model
"""
        
        # Tokenize
        inputs = tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.1,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        # Decode response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract model output
        if "<start_of_turn>model" in response:
            response = response.split("<start_of_turn>model")[-1]
        if "<end_of_turn>" in response:
            response = response.split("<end_of_turn>")[0]
        
        response = response.strip()
        
        # Parse JSON
        try:
            # Find JSON in response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Validate required fields
                if "intent" not in result:
                    result["intent"] = "UNKNOWN"
                if "entities" not in result:
                    result["entities"] = {}
                if "capabilities_needed" not in result:
                    result["capabilities_needed"] = []
                if "confidence" not in result:
                    result["confidence"] = 0.7
                if "risk" not in result:
                    result["risk"] = "low"
                
                return result
            else:
                logger.warning(f"No JSON found in response: {response[:200]}")
                return None
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}, response: {response[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"Error during interpretation: {e}")
        return None


def batch_interpret(commands: list, context: Optional[Dict[str, Any]] = None) -> list:
    """Interpret multiple commands."""
    return [interpret_command(cmd, context) for cmd in commands]


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if not is_model_available():
        print("❌ Model not found. Please ensure the model is extracted to:")
        print(f"   {MODEL_DIR}")
        exit(1)
    
    test_commands = [
        "open notepad",
        "search for python tutorials on google",
        "click on the save button",
        "turn up the volume",
    ]
    
    print("\n🧪 Testing fine-tuned Gemma interpreter:\n")
    
    for cmd in test_commands:
        print(f"Command: {cmd}")
        result = interpret_command(cmd)
        if result:
            print(f"  Intent: {result.get('intent')}")
            print(f"  Entities: {result.get('entities')}")
            print(f"  Confidence: {result.get('confidence')}")
        else:
            print("  ❌ Failed to interpret")
        print()
