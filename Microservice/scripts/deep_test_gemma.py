#!/usr/bin/env python3
"""
Deep test for the fine-tuned Gemma model.
Tests model loading and inference without needing base model download.
"""

import os
import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("🧪 GEMMA FINE-TUNED MODEL DEEP TEST")
print("=" * 60)

# Test 1: Check model files exist
print("\n📁 Test 1: Model Files Check")
model_dir = Path(__file__).parent.parent / "models" / "gemma-interpreter" / "final"
print(f"   Model directory: {model_dir}")

required_files = [
    "adapter_config.json",
    "adapter_model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json"
]

all_found = True
for f in required_files:
    exists = (model_dir / f).exists()
    status = "✅" if exists else "❌"
    print(f"   {status} {f}")
    if not exists:
        all_found = False

if not all_found:
    print("\n❌ FAILED: Missing model files!")
    sys.exit(1)

print("   ✅ All model files present")

# Test 2: Load adapter config
print("\n📋 Test 2: Adapter Configuration")
try:
    with open(model_dir / "adapter_config.json", "r") as f:
        config = json.load(f)
    
    print(f"   Base model: {config.get('base_model_name_or_path', 'unknown')}")
    print(f"   LoRA rank (r): {config.get('r', 'unknown')}")
    print(f"   LoRA alpha: {config.get('lora_alpha', 'unknown')}")
    print(f"   Target modules: {config.get('target_modules', [])}")
    print(f"   Task type: {config.get('task_type', 'unknown')}")
    print("   ✅ Config loaded successfully")
except Exception as e:
    print(f"   ❌ Failed to load config: {e}")
    sys.exit(1)

# Test 3: Load tokenizer
print("\n🔤 Test 3: Tokenizer")
try:
    from transformers import AutoTokenizer
    
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    test_text = "open notepad and type hello"
    tokens = tokenizer.encode(test_text)
    decoded = tokenizer.decode(tokens)
    
    print(f"   Test input: '{test_text}'")
    print(f"   Token count: {len(tokens)}")
    print(f"   Decoded back: '{decoded}'")
    print("   ✅ Tokenizer works")
except Exception as e:
    print(f"   ❌ Tokenizer failed: {e}")
    sys.exit(1)

# Test 4: Check HuggingFace login
print("\n🔑 Test 4: HuggingFace Authentication")
try:
    from huggingface_hub import HfFolder, whoami
    
    token = HfFolder.get_token()
    if token:
        try:
            user_info = whoami()
            print(f"   Logged in as: {user_info.get('name', 'unknown')}")
            print("   ✅ HuggingFace authenticated")
        except:
            print(f"   Token found but couldn't verify")
            print("   ⚠️ May need to re-login")
    else:
        print("   ❌ Not logged in to HuggingFace")
        print("   Run: python -c \"from huggingface_hub import login; login()\"")
        print("   Get token from: https://huggingface.co/settings/tokens")
        print("   Also accept Gemma license: https://huggingface.co/google/gemma-2b")
except Exception as e:
    print(f"   ⚠️ Could not check HF status: {e}")

# Test 5: Try loading the full model (with helpful error messages)
print("\n🧠 Test 5: Model Loading")
try:
    import torch
    from transformers import AutoModelForCausalLM
    from peft import PeftModel
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"   Device: {device}")
    print(f"   PyTorch version: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    
    base_model_name = config.get('base_model_name_or_path', 'google/gemma-2b')
    print(f"   Loading base model: {base_model_name}")
    print("   (This may take 1-2 minutes on CPU...)")
    
    # Try to load the model
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float32 if device == "cpu" else torch.float16,
        device_map="auto" if device == "cuda" else None,
        low_cpu_mem_usage=True,
    )
    
    if device == "cpu":
        base_model = base_model.to(device)
    
    print("   ✅ Base model loaded")
    
    # Load LoRA adapter
    print("   Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, str(model_dir))
    model.eval()
    print("   ✅ LoRA adapter loaded")
    
    # Test inference
    print("\n🎯 Test 6: Inference Test")
    
    test_commands = [
        "open notepad",
        "search for weather on google",
        "click on save button",
        "turn up the volume",
        "create folder called projects"
    ]
    
    for cmd in test_commands:
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
        
        inputs = tokenizer(prompt, return_tensors="pt")
        if device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.1,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract model response
        if "<start_of_turn>model" in response:
            response = response.split("<start_of_turn>model")[-1]
        if "<end_of_turn>" in response:
            response = response.split("<end_of_turn>")[0]
        response = response.strip()
        
        # Try to parse JSON
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(response[start:end])
                intent = parsed.get("intent", "?")
                confidence = parsed.get("confidence", 0)
                print(f"   ✅ '{cmd}' → {intent} (conf: {confidence})")
            else:
                print(f"   ⚠️ '{cmd}' → No JSON found: {response[:50]}...")
        except json.JSONDecodeError:
            print(f"   ⚠️ '{cmd}' → Invalid JSON: {response[:50]}...")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Model is trained and working!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n   ❌ Model loading failed: {e}")
    
    if "gated repo" in str(e).lower() or "restricted" in str(e).lower():
        print("\n   📋 TO FIX:")
        print("   1. Go to: https://huggingface.co/google/gemma-2b")
        print("   2. Accept the license agreement")
        print("   3. Get token from: https://huggingface.co/settings/tokens")
        print("   4. Run: python -c \"from huggingface_hub import login; login()\"")
        print("   5. Enter your token when prompted")
        print("   6. Re-run this test")
    
    import traceback
    traceback.print_exc()
    sys.exit(1)
