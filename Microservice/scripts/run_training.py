#!/usr/bin/env python3
"""
Quick launcher script to run the full Gemma training pipeline.

Usage:
    python run_training.py              # Default: import data + train
    python run_training.py --import-only  # Just import datasets
    python run_training.py --train-only   # Just train (data must exist)
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add scripts to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


def run_command(cmd: list, cwd: str = None) -> int:
    """Run a command and stream output."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print("="*60 + "\n")
    
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    for line in process.stdout:
        print(line, end="")
    
    process.wait()
    return process.returncode


def check_dependencies():
    """Check and install required dependencies."""
    print("Checking dependencies...")
    
    required = [
        "torch",
        "transformers",
        "peft",
        "datasets",
        "accelerate",
        "bitsandbytes"
    ]
    
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            *missing, "-q"
        ])
    else:
        print("All dependencies installed ✓")


def main():
    parser = argparse.ArgumentParser(description="Gemma Training Pipeline Launcher")
    
    # Pipeline control
    parser.add_argument("--import-only", action="store_true",
                       help="Only import datasets, don't train")
    parser.add_argument("--train-only", action="store_true", 
                       help="Only train (datasets must exist)")
    
    # Dataset options
    parser.add_argument("--datasets", "-d", type=str, 
                       default="osworld,mind2web,glaive-function",
                       help="Datasets to import (comma-separated)")
    parser.add_argument("--max-examples", "-m", type=int, default=5000,
                       help="Max examples per dataset")
    
    # Training options
    parser.add_argument("--model", type=str, default="google/gemma-2b",
                       help="Base model to fine-tune")
    parser.add_argument("--epochs", "-e", type=int, default=3,
                       help="Training epochs")
    parser.add_argument("--batch-size", "-b", type=int, default=4,
                       help="Batch size")
    parser.add_argument("--use-unsloth", action="store_true",
                       help="Use Unsloth for faster training")
    
    # Output
    parser.add_argument("--output", "-o", type=str, 
                       default="models/gemma-interpreter",
                       help="Output directory for trained model")
    
    args = parser.parse_args()
    
    # Paths
    data_dir = SCRIPT_DIR.parent / "training_data"
    training_data = data_dir / "gemma_training_combined.jsonl"
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           🧠 Gemma Training Pipeline for Kernal Agent          ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Check dependencies
    check_dependencies()
    
    # Step 1: Import datasets
    if not args.train_only:
        print("\n📦 Step 1: Importing HuggingFace datasets...")
        
        import_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "import_hf_datasets.py"),
            "--dataset", args.datasets,
            "--max-examples", str(args.max_examples),
            "--output", str(data_dir),
            "--format", "all"
        ]
        
        result = run_command(import_cmd)
        
        if result != 0:
            print("❌ Dataset import failed!")
            return 1
        
        if args.import_only:
            print(f"\n✅ Import complete! Data saved to {data_dir}")
            return 0
    
    # Step 2: Verify training data exists
    if not training_data.exists():
        print(f"❌ Training data not found: {training_data}")
        print("   Run with --import-only first, or remove --train-only")
        return 1
    
    # Count examples
    with open(training_data, "r") as f:
        num_examples = sum(1 for _ in f)
    print(f"\n📊 Found {num_examples} training examples")
    
    if num_examples < 100:
        print("⚠️  Warning: Very few training examples. Consider importing more data.")
    
    # Step 3: Train the model
    print("\n🚀 Step 2: Training Gemma with LoRA...")
    
    train_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "train_gemma_lora.py"),
        "--data", str(training_data),
        "--model", args.model,
        "--output", args.output,
        "--epochs", str(args.epochs),
        "--batch-size", str(args.batch_size),
        "--create-modelfile"
    ]
    
    if args.use_unsloth:
        train_cmd.append("--use-unsloth")
    
    result = run_command(train_cmd)
    
    if result != 0:
        print("❌ Training failed!")
        return 1
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    ✅ Pipeline Complete!                       ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Your fine-tuned Gemma model is ready!                        ║
║                                                               ║
║  Next steps:                                                  ║
║  1. Test the model:                                           ║
║     python scripts/test_finetuned_model.py --model <path>     ║
║                                                               ║
║  2. Deploy to Ollama:                                         ║
║     ollama create gemma-interpreter -f Modelfile              ║
║                                                               ║
║  3. Update Microservice .env:                                 ║
║     GEMMA_HTTP_URL=http://localhost:11434                     ║
║     GEMMA_MODEL=gemma-interpreter                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
