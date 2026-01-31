#!/usr/bin/env python3
"""
Fine-tune Gemma for desktop automation command interpretation using LoRA.

This script trains a Gemma model to understand user commands and output
structured JSON with intent, entities, and capabilities.

Requirements:
    pip install torch transformers peft datasets accelerate bitsandbytes

Usage:
    # Basic training
    python train_gemma_lora.py --data training_data/gemma_training_combined.jsonl
    
    # With custom settings
    python train_gemma_lora.py \
        --data training_data/gemma_training_combined.jsonl \
        --model google/gemma-2b \
        --output models/gemma-interpreter-v1 \
        --epochs 3 \
        --batch-size 4 \
        --lora-r 16

    # Using Unsloth for 2x faster training (if installed)
    python train_gemma_lora.py --data training_data/gemma_training_combined.jsonl --use-unsloth
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import torch

# Check for available libraries
try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
        BitsAndBytesConfig
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False

try:
    from datasets import Dataset, load_dataset
    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False

try:
    from unsloth import FastLanguageModel
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_CONFIG = {
    "model_name": "google/gemma-2b",
    "output_dir": "models/gemma-interpreter",
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    "epochs": 3,
    "batch_size": 4,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-4,
    "max_seq_length": 1024,
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,
    "logging_steps": 10,
    "save_steps": 100,
    "eval_steps": 100,
    "fp16": True,
    "bf16": False,
    "gradient_checkpointing": True,
    "use_4bit": True,
    "cpu_only": False,
}

# CPU-optimized configuration (smaller, faster)
CPU_CONFIG = {
    "model_name": "google/gemma-2b",  # Smallest Gemma
    "output_dir": "models/gemma-interpreter-cpu",
    "lora_r": 8,  # Smaller rank for CPU
    "lora_alpha": 16,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "v_proj"],  # Fewer modules
    "epochs": 2,
    "batch_size": 1,  # Small batch for memory
    "gradient_accumulation_steps": 8,  # Accumulate for effective batch
    "learning_rate": 1e-4,
    "max_seq_length": 512,  # Shorter sequences
    "warmup_ratio": 0.03,
    "weight_decay": 0.01,
    "logging_steps": 5,
    "save_steps": 50,
    "eval_steps": 50,
    "fp16": False,  # CPU doesn't support fp16 well
    "bf16": False,
    "gradient_checkpointing": True,
    "use_4bit": False,  # No quantization on CPU
    "cpu_only": True,
}


def check_requirements():
    """Check if all required libraries are installed."""
    missing = []
    
    if not TRANSFORMERS_AVAILABLE:
        missing.append("transformers")
    if not PEFT_AVAILABLE:
        missing.append("peft")
    if not DATASETS_AVAILABLE:
        missing.append("datasets")
    
    if missing:
        raise RuntimeError(
            f"Missing required libraries: {', '.join(missing)}\n"
            f"Install with: pip install {' '.join(missing)} accelerate bitsandbytes"
        )


def load_training_data(data_path: str, format: str = "auto") -> Dataset:
    """Load training data from various formats."""
    logger.info(f"Loading training data from {data_path}")
    
    path = Path(data_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Training data not found: {data_path}")
    
    # Auto-detect format
    if format == "auto":
        if path.suffix == ".json":
            format = "alpaca"
        else:
            format = "jsonl"
    
    if format == "alpaca":
        # Alpaca format: [{"instruction": ..., "input": ..., "output": ...}, ...]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Dataset.from_list(data)
    
    elif format == "jsonl":
        # JSONL format: one JSON per line
        examples = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    examples.append(json.loads(line))
        return Dataset.from_list(examples)
    
    elif format == "chatml":
        # ChatML format: {"messages": [{"role": ..., "content": ...}, ...]}
        examples = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    messages = obj.get("messages", [])
                    instruction = ""
                    input_text = ""
                    output_text = ""
                    
                    for msg in messages:
                        if msg["role"] == "system":
                            instruction = msg["content"]
                        elif msg["role"] == "user":
                            input_text = msg["content"]
                        elif msg["role"] == "assistant":
                            output_text = msg["content"]
                    
                    examples.append({
                        "instruction": instruction,
                        "input": input_text,
                        "output": output_text
                    })
        return Dataset.from_list(examples)
    
    else:
        raise ValueError(f"Unknown format: {format}")


def format_prompt(example: Dict[str, str], tokenizer) -> str:
    """Format a single example as a prompt for training."""
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output_text = example.get("output", "")
    
    # Gemma chat template
    prompt = f"""<start_of_turn>user
{instruction}

User command: {input_text}<end_of_turn>
<start_of_turn>model
{output_text}<end_of_turn>"""
    
    return prompt


def tokenize_dataset(dataset: Dataset, tokenizer, max_length: int) -> Dataset:
    """Tokenize the dataset for training."""
    
    def tokenize_function(examples):
        prompts = []
        for i in range(len(examples["input"])):
            example = {
                "instruction": examples["instruction"][i] if "instruction" in examples else "",
                "input": examples["input"][i],
                "output": examples["output"][i]
            }
            prompts.append(format_prompt(example, tokenizer))
        
        tokenized = tokenizer(
            prompts,
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_tensors=None
        )
        
        # Set labels equal to input_ids for causal LM training
        tokenized["labels"] = tokenized["input_ids"].copy()
        
        return tokenized
    
    return dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names,
        desc="Tokenizing dataset"
    )


def train_with_transformers(
    data_path: str,
    config: Dict[str, Any]
) -> str:
    """Train using HuggingFace Transformers + PEFT."""
    
    check_requirements()
    
    logger.info(f"Loading model: {config['model_name']}")
    
    # Check if CPU-only mode
    cpu_only = config.get("cpu_only", False) or not torch.cuda.is_available()
    
    if cpu_only:
        logger.info("🖥️ Running in CPU-only mode (this will be slower)")
        device_map = "cpu"
        torch_dtype = torch.float32
        bnb_config = None
    else:
        device_map = "auto"
        torch_dtype = torch.bfloat16 if config["bf16"] else torch.float16
        
        # Quantization config for 4-bit training (GPU only)
        bnb_config = None
        if config["use_4bit"]:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch_dtype,
                bnb_4bit_use_double_quant=True,
            )
    
    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        config["model_name"],
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        config["model_name"],
        trust_remote_code=True
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # Prepare model for training
    if config["use_4bit"] and not cpu_only:
        model = prepare_model_for_kbit_training(model)
    
    # Configure LoRA
    lora_config = LoraConfig(
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        target_modules=config["target_modules"],
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load and prepare dataset
    dataset = load_training_data(data_path)
    logger.info(f"Loaded {len(dataset)} training examples")
    
    # Split into train/eval
    split = dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = tokenize_dataset(split["train"], tokenizer, config["max_seq_length"])
    eval_dataset = tokenize_dataset(split["test"], tokenizer, config["max_seq_length"])
    
    logger.info(f"Train size: {len(train_dataset)}, Eval size: {len(eval_dataset)}")
    
    # Training arguments
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Adjust settings for CPU
    if cpu_only:
        optim = "adamw_torch"
        fp16 = False
        bf16 = False
    else:
        optim = "paged_adamw_8bit" if config["use_4bit"] else "adamw_torch"
        fp16 = config["fp16"]
        bf16 = config["bf16"]
    
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=config["epochs"],
        per_device_train_batch_size=config["batch_size"],
        per_device_eval_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        learning_rate=config["learning_rate"],
        warmup_ratio=config["warmup_ratio"],
        weight_decay=config["weight_decay"],
        logging_steps=config["logging_steps"],
        save_steps=config["save_steps"],
        eval_steps=config["eval_steps"],
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        fp16=fp16,
        bf16=bf16,
        gradient_checkpointing=config["gradient_checkpointing"],
        report_to="none",  # Disable wandb etc
        optim=optim,
        lr_scheduler_type="cosine",
        seed=42,
        use_cpu=cpu_only,
        no_cuda=cpu_only,
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )
    
    # Train!
    logger.info("🚀 Starting training...")
    trainer.train()
    
    # Save the final model
    final_path = output_dir / "final"
    model.save_pretrained(str(final_path))
    tokenizer.save_pretrained(str(final_path))
    
    logger.info(f"✅ Model saved to {final_path}")
    
    return str(final_path)


def train_with_unsloth(
    data_path: str,
    config: Dict[str, Any]
) -> str:
    """Train using Unsloth for 2x faster training."""
    
    if not UNSLOTH_AVAILABLE:
        raise RuntimeError("Unsloth not installed. Run: pip install unsloth")
    
    logger.info(f"Loading model with Unsloth: {config['model_name']}")
    
    # Load model with Unsloth
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config["model_name"],
        max_seq_length=config["max_seq_length"],
        dtype=None,  # Auto-detect
        load_in_4bit=config["use_4bit"],
    )
    
    # Apply LoRA
    model = FastLanguageModel.get_peft_model(
        model,
        r=config["lora_r"],
        target_modules=config["target_modules"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    
    # Load dataset
    dataset = load_training_data(data_path)
    logger.info(f"Loaded {len(dataset)} training examples")
    
    # Format for Unsloth
    def formatting_prompts_func(examples):
        prompts = []
        for i in range(len(examples["input"])):
            example = {
                "instruction": examples.get("instruction", [""])[i],
                "input": examples["input"][i],
                "output": examples["output"][i]
            }
            prompts.append(format_prompt(example, tokenizer))
        return {"text": prompts}
    
    dataset = dataset.map(formatting_prompts_func, batched=True)
    
    # Training with Unsloth
    from trl import SFTTrainer
    
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=config["max_seq_length"],
        dataset_num_proc=2,
        packing=False,
        args=TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=config["epochs"],
            per_device_train_batch_size=config["batch_size"],
            gradient_accumulation_steps=config["gradient_accumulation_steps"],
            learning_rate=config["learning_rate"],
            warmup_ratio=config["warmup_ratio"],
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=config["logging_steps"],
            save_steps=config["save_steps"],
            optim="adamw_8bit",
            seed=42,
        ),
    )
    
    logger.info("🚀 Starting training with Unsloth...")
    trainer.train()
    
    # Save
    final_path = output_dir / "final"
    model.save_pretrained(str(final_path))
    tokenizer.save_pretrained(str(final_path))
    
    logger.info(f"✅ Model saved to {final_path}")
    
    return str(final_path)


def export_to_gguf(model_path: str, output_path: str, quantization: str = "q4_k_m"):
    """Export the model to GGUF format for Ollama."""
    logger.info(f"Exporting to GGUF: {output_path}")
    
    # This requires llama.cpp's convert script
    # For now, provide instructions
    print(f"""
    
To export to GGUF for Ollama:

1. Install llama.cpp:
   git clone https://github.com/ggerganov/llama.cpp
   cd llama.cpp && make

2. Convert the model:
   python llama.cpp/convert_hf_to_gguf.py {model_path} --outfile {output_path} --outtype {quantization}

3. Create Ollama model:
   ollama create gemma-interpreter -f Modelfile

4. Update your .env:
   GEMMA_MODEL=gemma-interpreter
""")


def create_ollama_modelfile(model_path: str, output_path: str = "Modelfile"):
    """Create an Ollama Modelfile for the trained model."""
    
    modelfile_content = f'''# Gemma Interpreter - Fine-tuned for desktop automation
FROM {model_path}

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_predict 512
PARAMETER stop "<end_of_turn>"

SYSTEM """You are a desktop automation interpreter. Parse user commands into structured JSON with:
- intent: The action type (OPEN_APP, CLICK_UI, TYPE_TEXT, WEB_SEARCH, FILE_OP, SYSTEM_CONTROL, MULTI_ACTION)
- entities: Extracted parameters (app, target, text, url, path, etc.)
- capabilities_needed: Required automation capabilities
- confidence: Your confidence 0.0-1.0
- risk: low|medium|high

Return ONLY valid JSON."""
'''
    
    with open(output_path, "w") as f:
        f.write(modelfile_content)
    
    logger.info(f"Created Ollama Modelfile at {output_path}")
    print(f"\nTo create Ollama model:\n  ollama create gemma-interpreter -f {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Gemma for desktop automation")
    
    # Required
    parser.add_argument("--data", "-d", type=str, required=True,
                       help="Path to training data (JSONL or Alpaca JSON)")
    
    # Model settings
    parser.add_argument("--model", "-m", type=str, default=DEFAULT_CONFIG["model_name"],
                       help=f"Base model (default: {DEFAULT_CONFIG['model_name']})")
    parser.add_argument("--output", "-o", type=str, default=DEFAULT_CONFIG["output_dir"],
                       help=f"Output directory (default: {DEFAULT_CONFIG['output_dir']})")
    
    # LoRA settings
    parser.add_argument("--lora-r", type=int, default=DEFAULT_CONFIG["lora_r"],
                       help=f"LoRA rank (default: {DEFAULT_CONFIG['lora_r']})")
    parser.add_argument("--lora-alpha", type=int, default=DEFAULT_CONFIG["lora_alpha"],
                       help=f"LoRA alpha (default: {DEFAULT_CONFIG['lora_alpha']})")
    
    # Training settings
    parser.add_argument("--epochs", "-e", type=int, default=DEFAULT_CONFIG["epochs"],
                       help=f"Training epochs (default: {DEFAULT_CONFIG['epochs']})")
    parser.add_argument("--batch-size", "-b", type=int, default=DEFAULT_CONFIG["batch_size"],
                       help=f"Batch size (default: {DEFAULT_CONFIG['batch_size']})")
    parser.add_argument("--lr", type=float, default=DEFAULT_CONFIG["learning_rate"],
                       help=f"Learning rate (default: {DEFAULT_CONFIG['learning_rate']})")
    parser.add_argument("--max-length", type=int, default=DEFAULT_CONFIG["max_seq_length"],
                       help=f"Max sequence length (default: {DEFAULT_CONFIG['max_seq_length']})")
    
    # Optimization
    parser.add_argument("--use-unsloth", action="store_true",
                       help="Use Unsloth for 2x faster training")
    parser.add_argument("--no-4bit", action="store_true",
                       help="Disable 4-bit quantization")
    parser.add_argument("--bf16", action="store_true",
                       help="Use bfloat16 instead of float16")
    parser.add_argument("--cpu", action="store_true",
                       help="Force CPU-only training (slower but works without GPU)")
    
    # Export
    parser.add_argument("--export-gguf", action="store_true",
                       help="Export to GGUF format for Ollama")
    parser.add_argument("--create-modelfile", action="store_true",
                       help="Create Ollama Modelfile")
    
    args = parser.parse_args()
    
    # Use CPU config if --cpu flag or no GPU detected
    if args.cpu or not torch.cuda.is_available():
        logger.info("Using CPU-optimized configuration")
        config = CPU_CONFIG.copy()
    else:
        config = DEFAULT_CONFIG.copy()
    
    # Override with command line args
    config.update({
        "model_name": args.model,
        "output_dir": args.output,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "max_seq_length": args.max_length,
        "use_4bit": not args.no_4bit and not args.cpu and torch.cuda.is_available(),
        "bf16": args.bf16 and not args.cpu,
        "fp16": not args.bf16 and not args.cpu,
        "cpu_only": args.cpu or not torch.cuda.is_available(),
    })
    
    # Add timestamp to output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config["output_dir"] = f"{config['output_dir']}_{timestamp}"
    
    logger.info("=" * 60)
    logger.info("Gemma Fine-Tuning for Desktop Automation")
    logger.info("=" * 60)
    logger.info(f"Model: {config['model_name']}")
    logger.info(f"Data: {args.data}")
    logger.info(f"Output: {config['output_dir']}")
    logger.info(f"LoRA r={config['lora_r']}, alpha={config['lora_alpha']}")
    logger.info(f"Epochs: {config['epochs']}, Batch: {config['batch_size']}")
    logger.info(f"4-bit: {config['use_4bit']}, Unsloth: {args.use_unsloth}, CPU-only: {config['cpu_only']}")
    logger.info("=" * 60)
    
    if config["cpu_only"]:
        logger.info("⚠️  CPU training is slow. Consider using Google Colab (free GPU) for faster training.")
        logger.info("   See: https://colab.research.google.com/")
    
    # Train
    if args.use_unsloth:
        model_path = train_with_unsloth(args.data, config)
    else:
        model_path = train_with_transformers(args.data, config)
    
    # Export options
    if args.create_modelfile:
        create_ollama_modelfile(model_path)
    
    if args.export_gguf:
        export_to_gguf(model_path, f"{model_path}.gguf")
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
║  ✅ Training Complete!                                      ║
╠════════════════════════════════════════════════════════════╣
║  Model saved to: {model_path:<40} ║
║                                                            ║
║  Next steps:                                               ║
║  1. Test locally:                                          ║
║     python test_finetuned_model.py --model {model_path}    ║
║                                                            ║
║  2. Convert for Ollama:                                    ║
║     python train_gemma_lora.py --create-modelfile          ║
║     ollama create gemma-interpreter -f Modelfile           ║
║                                                            ║
║  3. Update Microservice .env:                              ║
║     GEMMA_MODEL=gemma-interpreter                          ║
╚════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
