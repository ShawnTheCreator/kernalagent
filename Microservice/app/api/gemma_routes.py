"""
API routes for the fine-tuned Gemma interpreter model.

Provides endpoints for:
- /api/gemma/interpret - Interpret a single command
- /api/gemma/batch - Interpret multiple commands
- /api/gemma/status - Check model status
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gemma", tags=["gemma"])


# Request/Response models
class InterpretRequest(BaseModel):
    command: str
    context: Optional[Dict[str, Any]] = None


class InterpretResponse(BaseModel):
    intent: str
    entities: Dict[str, Any] = {}
    capabilities_needed: List[str] = []
    confidence: float = 0.0
    risk: str = "low"
    success: bool = True
    error: Optional[str] = None


class BatchInterpretRequest(BaseModel):
    commands: List[str]
    context: Optional[Dict[str, Any]] = None


class BatchInterpretResponse(BaseModel):
    results: List[InterpretResponse]
    success_count: int
    total_count: int


class ModelStatus(BaseModel):
    available: bool
    model_path: str
    loaded: bool
    device: str = "unknown"


# Lazy import to avoid loading model on startup
_gemma_local = None

def get_gemma_local():
    """Lazy load the Gemma local module."""
    global _gemma_local
    if _gemma_local is None:
        try:
            from app.brain.gemma_local import interpret_command, is_model_available, load_model
            _gemma_local = {
                "interpret": interpret_command,
                "available": is_model_available,
                "load": load_model
            }
        except ImportError as e:
            logger.error(f"Failed to import gemma_local: {e}")
            _gemma_local = {"error": str(e)}
    return _gemma_local


@router.get("/status", response_model=ModelStatus)
async def get_model_status():
    """Check if the fine-tuned Gemma model is available."""
    try:
        from app.brain.gemma_local import is_model_available, MODEL_DIR, _model
        import torch
        
        available = is_model_available()
        loaded = _model is not None
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        return ModelStatus(
            available=available,
            model_path=str(MODEL_DIR),
            loaded=loaded,
            device=device
        )
    except Exception as e:
        logger.error(f"Error checking model status: {e}")
        return ModelStatus(
            available=False,
            model_path="unknown",
            loaded=False,
            device="error"
        )


@router.post("/interpret", response_model=InterpretResponse)
async def interpret_command_endpoint(request: InterpretRequest):
    """
    Interpret a user command using the fine-tuned Gemma model.
    
    Returns structured interpretation with intent, entities, capabilities.
    """
    gemma = get_gemma_local()
    
    if "error" in gemma:
        raise HTTPException(status_code=500, detail=f"Model not available: {gemma['error']}")
    
    if not gemma["available"]():
        raise HTTPException(
            status_code=503, 
            detail="Fine-tuned Gemma model not found. Please ensure the model is in Microservice/models/gemma-interpreter/final/"
        )
    
    try:
        result = gemma["interpret"](request.command, request.context)
        
        if result is None:
            return InterpretResponse(
                intent="UNKNOWN",
                entities={"raw_command": request.command},
                capabilities_needed=[],
                confidence=0.0,
                risk="low",
                success=False,
                error="Failed to interpret command"
            )
        
        return InterpretResponse(
            intent=result.get("intent", "UNKNOWN"),
            entities=result.get("entities", {}),
            capabilities_needed=result.get("capabilities_needed", []),
            confidence=result.get("confidence", 0.0),
            risk=result.get("risk", "low"),
            success=True
        )
        
    except Exception as e:
        logger.error(f"Error interpreting command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchInterpretResponse)
async def batch_interpret_endpoint(request: BatchInterpretRequest):
    """Interpret multiple commands in batch."""
    gemma = get_gemma_local()
    
    if "error" in gemma:
        raise HTTPException(status_code=500, detail=f"Model not available: {gemma['error']}")
    
    if not gemma["available"]():
        raise HTTPException(status_code=503, detail="Fine-tuned Gemma model not found")
    
    results = []
    success_count = 0
    
    for cmd in request.commands:
        try:
            result = gemma["interpret"](cmd, request.context)
            
            if result:
                results.append(InterpretResponse(
                    intent=result.get("intent", "UNKNOWN"),
                    entities=result.get("entities", {}),
                    capabilities_needed=result.get("capabilities_needed", []),
                    confidence=result.get("confidence", 0.0),
                    risk=result.get("risk", "low"),
                    success=True
                ))
                success_count += 1
            else:
                results.append(InterpretResponse(
                    intent="UNKNOWN",
                    entities={"raw_command": cmd},
                    success=False,
                    error="Failed to interpret"
                ))
        except Exception as e:
            results.append(InterpretResponse(
                intent="ERROR",
                entities={},
                success=False,
                error=str(e)
            ))
    
    return BatchInterpretResponse(
        results=results,
        success_count=success_count,
        total_count=len(request.commands)
    )


@router.post("/load")
async def load_model_endpoint():
    """Preload the Gemma model into memory."""
    try:
        from app.brain.gemma_local import load_model, is_model_available
        
        if not is_model_available():
            raise HTTPException(status_code=503, detail="Model files not found")
        
        model, tokenizer = load_model()
        
        if model is None:
            raise HTTPException(status_code=500, detail="Failed to load model")
        
        return {"status": "loaded", "message": "Model loaded successfully"}
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))
