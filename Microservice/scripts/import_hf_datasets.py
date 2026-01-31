#!/usr/bin/env python3
"""
Import PC automation datasets from Hugging Face for Gemma fine-tuning.

Supported datasets:
- AgentTrek/AgentTrek-ToolBench (GUI automation)
- xlangai/spider (SQL/command parsing)
- gorilla-llm/Berkeley-Function-Call (function calling)
- glaiveai/glaive-function-calling-v2 (function calling)
- Custom desktop automation datasets

Usage:
    python import_hf_datasets.py --dataset agentTrek --output training_data/
    python import_hf_datasets.py --all --output training_data/
"""

import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from datasets import load_dataset, Dataset
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("Warning: datasets library not installed. Run: pip install datasets")


@dataclass
class TrainingExample:
    """Standardized training example format for Gemma."""
    instruction: str
    input: str
    output: str
    source: str
    category: str
    confidence: float = 1.0


# Dataset configurations
DATASET_CONFIGS = {
    "agent-trek": {
        "name": "AgentTrek/AgentTrek-ToolBench",
        "split": "train",
        "description": "GUI automation trajectories",
        "converter": "convert_agent_trek"
    },
    "glaive-function": {
        "name": "glaiveai/glaive-function-calling-v2",
        "split": "train", 
        "description": "Function calling examples",
        "converter": "convert_glaive_function"
    },
    "berkeley-function": {
        "name": "gorilla-llm/Berkeley-Function-Calling-Leaderboard",
        "split": "train",
        "description": "Berkeley function calling benchmark",
        "converter": "convert_berkeley_function"
    },
    "mind2web": {
        "name": "osunlp/Mind2Web",
        "split": "train",
        "description": "Web automation dataset",
        "converter": "convert_mind2web"
    },
    "aitw": {
        "name": "google/android-in-the-wild",
        "split": "train",
        "description": "Android UI automation",
        "converter": "convert_aitw"
    },
    "gui-odyssey": {
        "name": "showlab/GUI-Odyssey",
        "split": "train",
        "description": "Cross-app GUI navigation",
        "converter": "convert_gui_odyssey"
    },
    "toolbench": {
        "name": "ToolBench/ToolBench",
        "split": "train",
        "description": "Tool usage dataset",
        "converter": "convert_toolbench"
    },
    "os-world": {
        "name": "xlangai/OSWorld",
        "split": "train",
        "description": "OS-level automation tasks",
        "converter": "convert_osworld"
    }
}


# System prompt for Gemma interpreter
SYSTEM_PROMPT = """You are a desktop automation interpreter. Parse user commands into structured JSON with:
- intent: The action type (OPEN_APP, CLICK_UI, TYPE_TEXT, WEB_SEARCH, FILE_OP, SYSTEM_CONTROL, MULTI_ACTION)
- entities: Extracted parameters (app, target, text, url, path, etc.)
- capabilities_needed: Required automation capabilities
- confidence: Your confidence 0.0-1.0
- risk: low|medium|high

Return ONLY valid JSON."""


def convert_agent_trek(example: Dict) -> Optional[TrainingExample]:
    """Convert AgentTrek dataset format."""
    try:
        # AgentTrek has task descriptions and action sequences
        task = example.get("task", example.get("instruction", ""))
        actions = example.get("actions", example.get("trajectory", []))
        
        if not task:
            return None
        
        # Convert actions to our format
        if isinstance(actions, list) and len(actions) > 0:
            first_action = actions[0] if isinstance(actions[0], dict) else {"action": str(actions[0])}
            intent = map_action_to_intent(first_action.get("action", "click"))
            entities = extract_entities_from_action(first_action)
        else:
            intent = "MULTI_ACTION"
            entities = {"task": task}
        
        output = {
            "intent": intent,
            "entities": entities,
            "capabilities_needed": infer_capabilities(intent, entities),
            "confidence": 0.9,
            "risk": "low"
        }
        
        return TrainingExample(
            instruction=SYSTEM_PROMPT,
            input=task,
            output=json.dumps(output, ensure_ascii=False),
            source="agent-trek",
            category="gui_automation"
        )
    except Exception as e:
        print(f"Error converting AgentTrek example: {e}")
        return None


def convert_glaive_function(example: Dict) -> Optional[TrainingExample]:
    """Convert Glaive function calling dataset."""
    try:
        # Glaive has system, user, and assistant messages
        messages = example.get("conversations", example.get("messages", []))
        
        user_msg = ""
        assistant_msg = ""
        
        for msg in messages:
            role = msg.get("role", msg.get("from", ""))
            content = msg.get("content", msg.get("value", ""))
            
            if role in ["user", "human"]:
                user_msg = content
            elif role in ["assistant", "gpt", "function_call"]:
                assistant_msg = content
        
        if not user_msg:
            return None
        
        # Parse function call if present
        try:
            if "function_call" in assistant_msg or "{" in assistant_msg:
                parsed = json.loads(assistant_msg) if assistant_msg.startswith("{") else {"response": assistant_msg}
                intent = parsed.get("name", parsed.get("function", "FUNCTION_CALL"))
                entities = parsed.get("arguments", parsed.get("parameters", {}))
            else:
                intent = "RESPONSE"
                entities = {"response": assistant_msg}
        except:
            intent = "RESPONSE"
            entities = {"response": assistant_msg[:200]}
        
        output = {
            "intent": map_function_to_intent(intent),
            "entities": entities if isinstance(entities, dict) else {"value": str(entities)},
            "capabilities_needed": ["function_calling"],
            "confidence": 0.85,
            "risk": "low"
        }
        
        return TrainingExample(
            instruction=SYSTEM_PROMPT,
            input=user_msg,
            output=json.dumps(output, ensure_ascii=False),
            source="glaive-function",
            category="function_calling"
        )
    except Exception as e:
        print(f"Error converting Glaive example: {e}")
        return None


def convert_berkeley_function(example: Dict) -> Optional[TrainingExample]:
    """Convert Berkeley function calling dataset."""
    try:
        question = example.get("question", example.get("prompt", ""))
        ground_truth = example.get("ground_truth", example.get("answer", ""))
        
        if not question:
            return None
        
        # Parse the ground truth function call
        try:
            if isinstance(ground_truth, str) and ground_truth.startswith("["):
                calls = json.loads(ground_truth)
                if calls and isinstance(calls, list):
                    first_call = calls[0]
                    intent = first_call.get("name", "FUNCTION_CALL")
                    entities = first_call.get("arguments", {})
                else:
                    intent = "FUNCTION_CALL"
                    entities = {}
            else:
                intent = "FUNCTION_CALL"
                entities = {"raw": str(ground_truth)[:200]}
        except:
            intent = "FUNCTION_CALL"
            entities = {}
        
        output = {
            "intent": map_function_to_intent(intent),
            "entities": entities,
            "capabilities_needed": ["function_calling"],
            "confidence": 0.9,
            "risk": "low"
        }
        
        return TrainingExample(
            instruction=SYSTEM_PROMPT,
            input=question,
            output=json.dumps(output, ensure_ascii=False),
            source="berkeley-function",
            category="function_calling"
        )
    except Exception as e:
        print(f"Error converting Berkeley example: {e}")
        return None


def convert_mind2web(example: Dict) -> Optional[TrainingExample]:
    """Convert Mind2Web web automation dataset."""
    try:
        task = example.get("confirmed_task", example.get("task", ""))
        action_seq = example.get("action_reprs", example.get("actions", []))
        
        if not task:
            return None
        
        # Extract first action details
        if action_seq and len(action_seq) > 0:
            first_action = action_seq[0] if isinstance(action_seq[0], str) else str(action_seq[0])
            if "click" in first_action.lower():
                intent = "CLICK_UI"
            elif "type" in first_action.lower():
                intent = "TYPE_TEXT"
            else:
                intent = "WEB_ACTION"
            entities = {"action_description": first_action, "website": example.get("website", "")}
        else:
            intent = "WEB_ACTION"
            entities = {"task": task}
        
        output = {
            "intent": intent,
            "entities": entities,
            "capabilities_needed": ["web_automation", "ui_interaction"],
            "confidence": 0.85,
            "risk": "low"
        }
        
        return TrainingExample(
            instruction=SYSTEM_PROMPT,
            input=task,
            output=json.dumps(output, ensure_ascii=False),
            source="mind2web",
            category="web_automation"
        )
    except Exception as e:
        print(f"Error converting Mind2Web example: {e}")
        return None


def convert_aitw(example: Dict) -> Optional[TrainingExample]:
    """Convert Android in the Wild dataset."""
    try:
        goal = example.get("goal", example.get("instruction", ""))
        
        if not goal:
            return None
        
        output = {
            "intent": "MOBILE_ACTION",
            "entities": {"goal": goal, "platform": "android"},
            "capabilities_needed": ["mobile_automation"],
            "confidence": 0.8,
            "risk": "low"
        }
        
        return TrainingExample(
            instruction=SYSTEM_PROMPT,
            input=goal,
            output=json.dumps(output, ensure_ascii=False),
            source="aitw",
            category="mobile_automation"
        )
    except Exception as e:
        print(f"Error converting AITW example: {e}")
        return None


def convert_gui_odyssey(example: Dict) -> Optional[TrainingExample]:
    """Convert GUI-Odyssey cross-app navigation dataset."""
    try:
        task = example.get("task", example.get("instruction", ""))
        
        if not task:
            return None
        
        output = {
            "intent": "MULTI_ACTION",
            "entities": {"task": task},
            "capabilities_needed": ["gui_navigation", "cross_app"],
            "confidence": 0.85,
            "risk": "low"
        }
        
        return TrainingExample(
            instruction=SYSTEM_PROMPT,
            input=task,
            output=json.dumps(output, ensure_ascii=False),
            source="gui-odyssey",
            category="gui_automation"
        )
    except Exception as e:
        print(f"Error converting GUI-Odyssey example: {e}")
        return None


def convert_toolbench(example: Dict) -> Optional[TrainingExample]:
    """Convert ToolBench dataset."""
    try:
        query = example.get("query", example.get("instruction", ""))
        api_name = example.get("api_name", "")
        
        if not query:
            return None
        
        output = {
            "intent": "API_CALL",
            "entities": {"query": query, "api": api_name},
            "capabilities_needed": ["api_calling"],
            "confidence": 0.85,
            "risk": "low"
        }
        
        return TrainingExample(
            instruction=SYSTEM_PROMPT,
            input=query,
            output=json.dumps(output, ensure_ascii=False),
            source="toolbench",
            category="api_calling"
        )
    except Exception as e:
        print(f"Error converting ToolBench example: {e}")
        return None


def convert_osworld(example: Dict) -> Optional[TrainingExample]:
    """Convert OSWorld dataset for OS-level automation."""
    try:
        task = example.get("instruction", example.get("task", ""))
        
        if not task:
            return None
        
        # Detect intent from task description
        task_lower = task.lower()
        if "open" in task_lower:
            intent = "OPEN_APP"
        elif "click" in task_lower:
            intent = "CLICK_UI"
        elif "type" in task_lower or "write" in task_lower:
            intent = "TYPE_TEXT"
        elif "file" in task_lower or "folder" in task_lower:
            intent = "FILE_OP"
        else:
            intent = "SYSTEM_CONTROL"
        
        output = {
            "intent": intent,
            "entities": extract_entities_from_text(task),
            "capabilities_needed": infer_capabilities(intent, {}),
            "confidence": 0.85,
            "risk": assess_risk(task)
        }
        
        return TrainingExample(
            instruction=SYSTEM_PROMPT,
            input=task,
            output=json.dumps(output, ensure_ascii=False),
            source="osworld",
            category="os_automation"
        )
    except Exception as e:
        print(f"Error converting OSWorld example: {e}")
        return None


# Helper functions
def map_action_to_intent(action: str) -> str:
    """Map action types to our intent categories."""
    action_lower = action.lower()
    
    if "click" in action_lower or "tap" in action_lower:
        return "CLICK_UI"
    elif "type" in action_lower or "input" in action_lower or "enter" in action_lower:
        return "TYPE_TEXT"
    elif "open" in action_lower or "launch" in action_lower:
        return "OPEN_APP"
    elif "scroll" in action_lower:
        return "SCROLL"
    elif "navigate" in action_lower or "go to" in action_lower:
        return "WEB_NAVIGATE"
    elif "search" in action_lower:
        return "WEB_SEARCH"
    elif "file" in action_lower or "save" in action_lower or "copy" in action_lower:
        return "FILE_OP"
    else:
        return "MULTI_ACTION"


def map_function_to_intent(func_name: str) -> str:
    """Map function names to our intent categories."""
    func_lower = func_name.lower()
    
    intent_mapping = {
        "search": "WEB_SEARCH",
        "open": "OPEN_APP",
        "click": "CLICK_UI",
        "type": "TYPE_TEXT",
        "file": "FILE_OP",
        "send": "COMMUNICATION",
        "get": "API_CALL",
        "set": "SYSTEM_CONTROL",
        "play": "MEDIA_CONTROL",
        "volume": "VOLUME_CONTROL",
    }
    
    for key, intent in intent_mapping.items():
        if key in func_lower:
            return intent
    
    return "FUNCTION_CALL"


def extract_entities_from_action(action: Dict) -> Dict[str, Any]:
    """Extract entities from action dict."""
    entities = {}
    
    for key in ["target", "element", "text", "value", "selector", "coordinates", "url", "app", "file"]:
        if key in action:
            entities[key] = action[key]
    
    return entities if entities else {"raw": str(action)[:100]}


def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """Extract entities from natural language text."""
    entities = {}
    text_lower = text.lower()
    
    # Common app names
    apps = ["chrome", "firefox", "notepad", "word", "excel", "powerpoint", "outlook", 
            "spotify", "discord", "slack", "vscode", "terminal", "explorer", "settings"]
    for app in apps:
        if app in text_lower:
            entities["app"] = app
            break
    
    # Look for quoted strings
    import re
    quotes = re.findall(r'"([^"]*)"', text)
    if quotes:
        entities["text"] = quotes[0]
    
    # Look for URLs
    urls = re.findall(r'https?://\S+', text)
    if urls:
        entities["url"] = urls[0]
    
    return entities if entities else {"raw": text[:100]}


def infer_capabilities(intent: str, entities: Dict) -> List[str]:
    """Infer required capabilities from intent and entities."""
    capability_map = {
        "OPEN_APP": ["app_launcher"],
        "CLICK_UI": ["ui_automation", "vision_targeting"],
        "TYPE_TEXT": ["text_input", "keyboard"],
        "WEB_SEARCH": ["web_navigation", "app_launcher"],
        "WEB_NAVIGATE": ["web_navigation"],
        "FILE_OP": ["file_system"],
        "SYSTEM_CONTROL": ["system_control"],
        "MEDIA_CONTROL": ["media_control"],
        "VOLUME_CONTROL": ["volume_control"],
        "MULTI_ACTION": ["multi_step_execution"],
        "FUNCTION_CALL": ["function_calling"],
        "API_CALL": ["api_calling"],
    }
    
    return capability_map.get(intent, ["general_automation"])


def assess_risk(text: str) -> str:
    """Assess risk level of an action."""
    text_lower = text.lower()
    
    high_risk = ["delete", "remove", "format", "shutdown", "restart", "password", "admin"]
    medium_risk = ["install", "uninstall", "modify", "change settings", "system"]
    
    for word in high_risk:
        if word in text_lower:
            return "high"
    
    for word in medium_risk:
        if word in text_lower:
            return "medium"
    
    return "low"


def load_and_convert_dataset(
    dataset_key: str,
    max_examples: int = 5000,
    output_dir: str = "training_data"
) -> List[TrainingExample]:
    """Load a HuggingFace dataset and convert to training format."""
    
    if not HF_AVAILABLE:
        raise RuntimeError("datasets library not available. Run: pip install datasets")
    
    config = DATASET_CONFIGS.get(dataset_key)
    if not config:
        raise ValueError(f"Unknown dataset: {dataset_key}. Available: {list(DATASET_CONFIGS.keys())}")
    
    print(f"\n📦 Loading {config['name']}...")
    print(f"   Description: {config['description']}")
    
    try:
        # Try loading with streaming for large datasets
        dataset = load_dataset(
            config["name"],
            split=config["split"],
            streaming=True,
            trust_remote_code=True
        )
    except Exception as e:
        print(f"   ⚠️ Streaming failed, trying direct load: {e}")
        try:
            dataset = load_dataset(
                config["name"],
                split=config["split"],
                trust_remote_code=True
            )
        except Exception as e2:
            print(f"   ❌ Failed to load dataset: {e2}")
            return []
    
    # Get converter function
    converter_name = config["converter"]
    converter = globals().get(converter_name)
    if not converter:
        print(f"   ❌ Converter {converter_name} not found")
        return []
    
    # Convert examples
    examples = []
    skipped = 0
    
    print(f"   Converting examples (max {max_examples})...")
    
    for i, example in enumerate(dataset):
        if i >= max_examples:
            break
        
        converted = converter(example)
        if converted:
            examples.append(converted)
        else:
            skipped += 1
        
        if (i + 1) % 500 == 0:
            print(f"   Processed {i + 1} examples, converted {len(examples)}, skipped {skipped}")
    
    print(f"   ✅ Converted {len(examples)} examples from {dataset_key}")
    return examples


def export_to_jsonl(examples: List[TrainingExample], output_path: str):
    """Export examples to JSONL format."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(asdict(ex), ensure_ascii=False) + "\n")
    
    print(f"   💾 Saved {len(examples)} examples to {output_path}")


def export_to_alpaca(examples: List[TrainingExample], output_path: str):
    """Export examples to Alpaca format for fine-tuning."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    alpaca_examples = []
    for ex in examples:
        alpaca_examples.append({
            "instruction": ex.instruction,
            "input": ex.input,
            "output": ex.output
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(alpaca_examples, f, indent=2, ensure_ascii=False)
    
    print(f"   💾 Saved {len(alpaca_examples)} examples to {output_path} (Alpaca format)")


def export_to_chatml(examples: List[TrainingExample], output_path: str):
    """Export examples to ChatML format."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    chatml_examples = []
    for ex in examples:
        chatml_examples.append({
            "messages": [
                {"role": "system", "content": ex.instruction},
                {"role": "user", "content": ex.input},
                {"role": "assistant", "content": ex.output}
            ]
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in chatml_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    print(f"   💾 Saved {len(chatml_examples)} examples to {output_path} (ChatML format)")


def main():
    parser = argparse.ArgumentParser(description="Import HuggingFace datasets for Gemma training")
    parser.add_argument("--dataset", "-d", type=str, help="Dataset to import (see DATASET_CONFIGS)")
    parser.add_argument("--all", action="store_true", help="Import all available datasets")
    parser.add_argument("--output", "-o", type=str, default="training_data", help="Output directory")
    parser.add_argument("--max-examples", "-m", type=int, default=5000, help="Max examples per dataset")
    parser.add_argument("--format", "-f", type=str, default="all", 
                       choices=["jsonl", "alpaca", "chatml", "all"], help="Output format")
    parser.add_argument("--list", "-l", action="store_true", help="List available datasets")
    
    args = parser.parse_args()
    
    if args.list:
        print("\n📚 Available datasets:\n")
        for key, config in DATASET_CONFIGS.items():
            print(f"  {key:20} - {config['description']}")
            print(f"                       HuggingFace: {config['name']}")
        print("\n")
        return
    
    if not args.dataset and not args.all:
        # Default: import recommended datasets for desktop automation
        args.dataset = "osworld,mind2web,glaive-function"
        print(f"No dataset specified. Using recommended: {args.dataset}")
    
    datasets_to_import = []
    if args.all:
        datasets_to_import = list(DATASET_CONFIGS.keys())
    elif args.dataset:
        datasets_to_import = [d.strip() for d in args.dataset.split(",")]
    
    all_examples = []
    
    print(f"\n🚀 Importing {len(datasets_to_import)} dataset(s)...\n")
    
    for dataset_key in datasets_to_import:
        try:
            examples = load_and_convert_dataset(
                dataset_key,
                max_examples=args.max_examples,
                output_dir=args.output
            )
            all_examples.extend(examples)
        except Exception as e:
            print(f"   ❌ Error loading {dataset_key}: {e}")
    
    if not all_examples:
        print("\n❌ No examples collected. Check dataset availability and network.")
        return
    
    # Deduplicate by input
    seen = set()
    unique_examples = []
    for ex in all_examples:
        if ex.input not in seen:
            seen.add(ex.input)
            unique_examples.append(ex)
    
    print(f"\n📊 Total: {len(all_examples)} → {len(unique_examples)} unique examples")
    
    # Export in requested formats
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.format in ["jsonl", "all"]:
        export_to_jsonl(unique_examples, str(output_dir / f"gemma_train_{timestamp}.jsonl"))
    
    if args.format in ["alpaca", "all"]:
        export_to_alpaca(unique_examples, str(output_dir / f"gemma_train_{timestamp}_alpaca.json"))
    
    if args.format in ["chatml", "all"]:
        export_to_chatml(unique_examples, str(output_dir / f"gemma_train_{timestamp}_chatml.jsonl"))
    
    # Also save combined file
    export_to_jsonl(unique_examples, str(output_dir / "gemma_training_combined.jsonl"))
    
    print(f"\n✅ Done! Training data saved to {output_dir}/")
    print(f"   Next step: python train_gemma_lora.py --data {output_dir}/gemma_training_combined.jsonl")


if __name__ == "__main__":
    main()
