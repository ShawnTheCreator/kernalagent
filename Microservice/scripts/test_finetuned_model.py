#!/usr/bin/env python3
"""
Test a fine-tuned Gemma model for desktop automation interpretation.

Usage:
    python test_finetuned_model.py --model models/gemma-interpreter_*/final
    python test_finetuned_model.py --model gemma-interpreter --ollama
"""

import json
import argparse
from typing import Dict, Any, Optional

# Test cases for desktop automation
TEST_COMMANDS = [
    # App launching
    "open notepad",
    "launch chrome",
    "start spotify and play some music",
    "close all browser windows",
    
    # Web actions
    "search for python tutorials on google",
    "go to github.com",
    "open youtube and search for coding tutorials",
    
    # File operations
    "create a new folder called projects on desktop",
    "rename the file report.docx to final_report.docx",
    "move all pdf files to the Documents folder",
    "delete temporary files",
    
    # System control
    "turn up the volume",
    "set brightness to 50%",
    "mute the computer",
    "take a screenshot",
    
    # UI interactions  
    "click on the save button",
    "scroll down",
    "press enter",
    "type hello world",
    
    # Complex multi-step
    "open word, create a new document, and save it as notes.docx",
    "minimize all windows and open file explorer",
    "switch to the next tab in chrome",
]


def test_with_transformers(model_path: str, commands: list) -> Dict[str, Any]:
    """Test model loaded via transformers."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch
    
    print(f"Loading model from {model_path}...")
    
    # Check if it's a LoRA adapter or full model
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto"
        )
    except:
        # Try loading as LoRA adapter
        print("Loading as LoRA adapter...")
        base_model_name = "google/gemma-2b"
        tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        model = PeftModel.from_pretrained(base_model, model_path)
    
    model.eval()
    
    results = []
    
    for cmd in commands:
        prompt = f"""<start_of_turn>user
You are a desktop automation interpreter. Parse user commands into structured JSON with:
- intent: The action type (OPEN_APP, CLICK_UI, TYPE_TEXT, WEB_SEARCH, FILE_OP, SYSTEM_CONTROL, MULTI_ACTION)
- entities: Extracted parameters (app, target, text, url, path, etc.)
- capabilities_needed: Required automation capabilities
- confidence: Your confidence 0.0-1.0
- risk: low|medium|high

Return ONLY valid JSON.

User command: {cmd}<end_of_turn>
<start_of_turn>model
"""
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.1,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the model's response
        if "<start_of_turn>model" in response:
            response = response.split("<start_of_turn>model")[-1].strip()
        if "<end_of_turn>" in response:
            response = response.split("<end_of_turn>")[0].strip()
        
        # Try to parse JSON
        try:
            parsed = json.loads(response)
            valid_json = True
        except:
            parsed = {"raw": response}
            valid_json = False
        
        results.append({
            "command": cmd,
            "response": response,
            "parsed": parsed,
            "valid_json": valid_json
        })
        
        print(f"\n{'='*60}")
        print(f"Command: {cmd}")
        print(f"Response: {response[:200]}...")
        print(f"Valid JSON: {valid_json}")
    
    return {"results": results, "model_path": model_path}


def test_with_ollama(model_name: str, commands: list) -> Dict[str, Any]:
    """Test model via Ollama API."""
    import requests
    
    ollama_url = "http://localhost:11434/api/generate"
    
    results = []
    
    for cmd in commands:
        prompt = f"""You are a desktop automation interpreter. Parse user commands into structured JSON with:
- intent: The action type (OPEN_APP, CLICK_UI, TYPE_TEXT, WEB_SEARCH, FILE_OP, SYSTEM_CONTROL, MULTI_ACTION)
- entities: Extracted parameters (app, target, text, url, path, etc.)
- capabilities_needed: Required automation capabilities
- confidence: Your confidence 0.0-1.0
- risk: low|medium|high

Return ONLY valid JSON.

User command: {cmd}"""
        
        try:
            resp = requests.post(
                ollama_url,
                json={"model": model_name, "prompt": prompt, "stream": False},
                timeout=30
            )
            resp.raise_for_status()
            response = resp.json().get("response", "")
        except Exception as e:
            response = f"Error: {e}"
        
        # Try to parse JSON
        try:
            parsed = json.loads(response)
            valid_json = True
        except:
            parsed = {"raw": response}
            valid_json = False
        
        results.append({
            "command": cmd,
            "response": response,
            "parsed": parsed,
            "valid_json": valid_json
        })
        
        print(f"\n{'='*60}")
        print(f"Command: {cmd}")
        print(f"Response: {response[:200]}...")
        print(f"Valid JSON: {valid_json}")
    
    return {"results": results, "model_name": model_name}


def evaluate_results(results: Dict[str, Any]) -> Dict[str, float]:
    """Evaluate test results."""
    all_results = results["results"]
    
    total = len(all_results)
    valid_json = sum(1 for r in all_results if r["valid_json"])
    
    # Check for expected fields
    has_intent = 0
    has_entities = 0
    has_confidence = 0
    
    for r in all_results:
        if r["valid_json"]:
            parsed = r["parsed"]
            if "intent" in parsed:
                has_intent += 1
            if "entities" in parsed:
                has_entities += 1
            if "confidence" in parsed:
                has_confidence += 1
    
    metrics = {
        "total_commands": total,
        "valid_json_rate": valid_json / total * 100,
        "has_intent_rate": has_intent / total * 100,
        "has_entities_rate": has_entities / total * 100,
        "has_confidence_rate": has_confidence / total * 100,
    }
    
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    for k, v in metrics.items():
        if "rate" in k:
            print(f"{k}: {v:.1f}%")
        else:
            print(f"{k}: {v}")
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Test fine-tuned Gemma model")
    parser.add_argument("--model", "-m", type=str, required=True,
                       help="Model path or Ollama model name")
    parser.add_argument("--ollama", action="store_true",
                       help="Use Ollama API instead of local model")
    parser.add_argument("--commands", "-c", type=str,
                       help="Custom commands file (one per line)")
    parser.add_argument("--output", "-o", type=str,
                       help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Load custom commands if provided
    commands = TEST_COMMANDS
    if args.commands:
        with open(args.commands, "r") as f:
            commands = [line.strip() for line in f if line.strip()]
    
    print(f"Testing with {len(commands)} commands...")
    
    # Run tests
    if args.ollama:
        results = test_with_ollama(args.model, commands)
    else:
        results = test_with_transformers(args.model, commands)
    
    # Evaluate
    metrics = evaluate_results(results)
    results["metrics"] = metrics
    
    # Save if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
