"""
LLM Content Analyzer - Uses AI to analyze file contents for smart categorization.

Features:
- Read PDF first page to determine Work vs Personal
- Analyze document names with context
- Detect invoice, receipt, contract patterns
- Content-aware organization
"""

import os
import logging
from typing import Optional
from pathlib import Path

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult
from app.agents.janitor.file_categorizer import FileCategory

logger = logging.getLogger(__name__)


class LLMContentAnalyzerCapability(BaseCapability):
    """Uses LLM to analyze file contents for smart categorization."""
    
    name = "llm_content_analyzer"
    description = "AI-powered content analysis for smart file categorization"
    
    def __init__(self):
        self._supported_extensions = [".pdf", ".docx", ".doc", ".txt", ".xlsx"]
        self._gemini = None
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Analyze file content to determine category.
        
        Uses filename + content preview for LLM analysis.
        """
        extension = file_info.get("extension", "").lower()
        filename = file_info.get("filename", "")
        
        # Only analyze supported document types
        if extension not in self._supported_extensions:
            return CapabilityResult(capability=self.name, action_required=False)
        
        # Analyze with LLM
        try:
            category, confidence, reason = await self._analyze_with_llm(file_path, filename)
            
            if category and confidence > 0.7:
                return CapabilityResult(
                    capability=self.name,
                    action_required=True,
                    action_type="categorize",
                    confidence=confidence,
                    suggestion=f"🧠 AI detected: {category} ({reason})",
                    requires_permission=False,  # Auto-categorize
                    metadata={
                        "category": category,
                        "reason": reason,
                        "destination": self._get_destination(category),
                    }
                )
        except Exception as e:
            logger.debug(f"[LLMAnalyzer] Analysis failed: {e}")
        
        return CapabilityResult(capability=self.name, action_required=False)
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Move file to categorized location."""
        destination = result.metadata.get("destination")
        
        if not destination:
            return True
        
        try:
            import shutil
            os.makedirs(destination, exist_ok=True)
            
            filename = os.path.basename(file_path)
            dest_path = os.path.join(destination, filename)
            
            # Handle conflicts
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(destination, f"{base}_{counter}{ext}")
                    counter += 1
            
            shutil.move(file_path, dest_path)
            logger.info(f"[LLMAnalyzer] Moved to {result.metadata.get('category')}: {dest_path}")
            return True
        except Exception as e:
            logger.error(f"[LLMAnalyzer] Move failed: {e}")
            return False
    
    async def _analyze_with_llm(self, file_path: str, filename: str) -> tuple[Optional[str], float, str]:
        """
        Use LLM to analyze and categorize the file.
        
        Returns: (category, confidence, reason)
        """
        # First, try heuristic analysis (fast path)
        category, confidence, reason = self._heuristic_analysis(filename)
        
        if confidence > 0.8:
            return category, confidence, reason
        
        # Try LLM analysis for ambiguous cases
        try:
            content_preview = await self._get_content_preview(file_path)
            
            if content_preview:
                # Use Gemini for analysis
                from app.core.gemini_layer import get_gemini_layer
                gemini = get_gemini_layer()
                
                if gemini and gemini.enabled:
                    prompt = f"""Analyze this document and categorize it.

Filename: {filename}
Content Preview: {content_preview[:500]}

Categories:
- WORK_INVOICE: Work invoices, bills from vendors
- WORK_CONTRACT: Contracts, agreements, legal docs
- WORK_REPORT: Reports, presentations, meeting notes
- PERSONAL_RECEIPT: Personal receipts, shopping
- PERSONAL_TRAVEL: Travel tickets, reservations
- PERSONAL_FINANCE: Bank statements, tax docs
- PERSONAL_OTHER: Personal misc

Respond in format: CATEGORY|CONFIDENCE|REASON
Example: WORK_INVOICE|0.95|Contains invoice number and billing address"""

                    response = await gemini.generate_content_async(prompt)
                    
                    if response and "|" in response:
                        parts = response.strip().split("|")
                        if len(parts) >= 3:
                            return parts[0], float(parts[1]), parts[2]
        
        except Exception as e:
            logger.debug(f"[LLMAnalyzer] LLM analysis failed: {e}")
        
        return category, confidence, reason
    
    def _heuristic_analysis(self, filename: str) -> tuple[Optional[str], float, str]:
        """Fast heuristic categorization based on filename."""
        filename_lower = filename.lower()
        
        # Work patterns
        if any(word in filename_lower for word in ["invoice", "bill", "payment due"]):
            return "WORK_INVOICE", 0.9, "Invoice keyword detected"
        
        if any(word in filename_lower for word in ["contract", "agreement", "nda", "terms"]):
            return "WORK_CONTRACT", 0.9, "Contract keyword detected"
        
        if any(word in filename_lower for word in ["report", "presentation", "meeting", "quarterly"]):
            return "WORK_REPORT", 0.85, "Report keyword detected"
        
        if any(word in filename_lower for word in ["resume", "cv", "cover letter"]):
            return "WORK_RESUME", 0.9, "Resume keyword detected"
        
        # Personal patterns
        if any(word in filename_lower for word in ["receipt", "order confirmation", "purchase"]):
            return "PERSONAL_RECEIPT", 0.85, "Receipt keyword detected"
        
        if any(word in filename_lower for word in ["ticket", "boarding", "reservation", "itinerary"]):
            return "PERSONAL_TRAVEL", 0.9, "Travel keyword detected"
        
        if any(word in filename_lower for word in ["bank statement", "tax", "1099", "w2"]):
            return "PERSONAL_FINANCE", 0.9, "Finance keyword detected"
        
        return None, 0.0, ""
    
    async def _get_content_preview(self, file_path: str) -> Optional[str]:
        """Extract text preview from file."""
        ext = Path(file_path).suffix.lower()
        
        try:
            if ext == ".txt":
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(1000)
            
            elif ext == ".pdf":
                # Try PyPDF2
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        if reader.pages:
                            return reader.pages[0].extract_text()[:1000]
                except ImportError:
                    pass
            
            # Add more formats as needed (docx, xlsx)
            
        except Exception as e:
            logger.debug(f"[LLMAnalyzer] Content extraction failed: {e}")
        
        return None
    
    def _get_destination(self, category: str) -> str:
        """Get destination folder for category."""
        home = os.path.expanduser("~")
        
        destinations = {
            "WORK_INVOICE": os.path.join(home, "Documents", "Work", "Invoices"),
            "WORK_CONTRACT": os.path.join(home, "Documents", "Work", "Contracts"),
            "WORK_REPORT": os.path.join(home, "Documents", "Work", "Reports"),
            "WORK_RESUME": os.path.join(home, "Documents", "Work", "Career"),
            "PERSONAL_RECEIPT": os.path.join(home, "Documents", "Personal", "Receipts"),
            "PERSONAL_TRAVEL": os.path.join(home, "Documents", "Personal", "Travel"),
            "PERSONAL_FINANCE": os.path.join(home, "Documents", "Personal", "Finance"),
            "PERSONAL_OTHER": os.path.join(home, "Documents", "Personal", "Misc"),
        }
        
        return destinations.get(category, os.path.join(home, "Documents", "Unsorted"))
