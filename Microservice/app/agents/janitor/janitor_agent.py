"""
Janitor Agent - File system organization and cleanup specialist.

The Janitor Agent eliminates "Digital Entropy" through:
1. Staging Sweep - Organize Downloads and Desktop
2. Ghost Removal - Clear temp files, caches, recycle bin
3. Large File Sentinel - Find hidden large files
4. App Hunter - Identify unused software (future)

This is a HYBRID agent:
- CONTINUOUS: Can run in background triggered by system pulse
- ON_DEMAND: Can be triggered by user ("clean my desktop")
"""

import os
import logging
import asyncio
from typing import Optional
from datetime import datetime

from app.agents.base_agent import (
    BaseAgent,
    AgentType,
    AgentTrigger,
    AnalysisResult,
    ActionPlan,
    ExecutionResult,
)
from app.agents.janitor.file_categorizer import (
    categorize_file,
    FileCategory,
    get_destination_path,
    is_old_file,
    get_file_age_days,
)
from app.agents.janitor.cleaning_plan import CleaningPlan, CleaningAction
from app.agents.janitor.janitor_tools import (
    scan_folder,
    find_large_files,
    get_temp_folders,
    get_folder_size,
    safe_move,
    safe_delete,
    is_protected_path,
    FileInfo,
)
from app.agents.janitor.parallel_processor import get_parallel_processor, parallel_scan_and_analyze
from app.agents.janitor.smart_cache import get_smart_cache
from app.agents.janitor.capabilities.ml_classifier import MLFileClassifierCapability
from app.agents.janitor.capabilities.smart_renamer import SmartRenamerCapability

logger = logging.getLogger(__name__)


class JanitorAgent(BaseAgent):
    """
    Janitor Agent - Eliminates Digital Entropy.
    
    Success Metrics:
    - Disk space recovered (MB)
    - Files organized
    - Reduction in staging area clutter
    """
    
    name = "JANITOR_AGENT"
    specialization = "File system organization, cache clearing, and temporary file management"
    agent_type = AgentType.HYBRID  # Both continuous and on-demand
    
    def __init__(self):
        super().__init__()
        self._user_home = os.path.expanduser("~")
        self._staging_paths = [
            os.path.join(self._user_home, "Downloads"),
            os.path.join(self._user_home, "Desktop"),
        ]
        self._metrics = {
            "files_analyzed": 0,
            "files_organized": 0,
            "files_deleted": 0,
            "space_recovered_mb": 0.0,
        }
        
        # Initialize enhanced components
        self._parallel_processor = get_parallel_processor()
        self._smart_cache = get_smart_cache()
        self._ml_classifier = MLFileClassifierCapability()
        self._smart_renamer = SmartRenamerCapability()
        
        logger.info("[Janitor] Enhanced agent initialized with ML, parallel processing, and smart caching")
    
    def get_triggers(self) -> list[AgentTrigger]:
        """Define what triggers this agent."""
        return [
            # System pulse triggers (for Control Tower)
            AgentTrigger(
                trigger_type="system_pulse",
                condition="disk_usage > 85%",
                priority=7
            ),
            AgentTrigger(
                trigger_type="system_pulse",
                condition="downloads clutter > 50 files",
                priority=5
            ),
            AgentTrigger(
                trigger_type="system_pulse",
                condition="desktop clutter > 30 files",
                priority=5
            ),
            AgentTrigger(
                trigger_type="system_pulse",
                condition="user idle > 30 minutes",
                priority=3
            ),
            
            # User intent triggers (for LLM Planner)
            AgentTrigger(
                trigger_type="user_intent",
                condition="clean organize downloads desktop files mess clutter",
                priority=8
            ),
        ]
    
    async def analyze(self, context: dict) -> AnalysisResult:
        """
        Enhanced analysis using parallel processing and smart caching.
        
        Scans:
        - Downloads folder
        - Desktop folder
        - Temp folders
        - Large file search (optional)
        
        Uses:
        - Parallel processing for faster scanning
        - Smart caching for incremental updates
        - ML classification for intelligent categorization
        """
        logger.info(f"[Janitor] Starting enhanced analysis...")
        self._status.current_task = "Analyzing file system with ML and parallel processing"
        
        findings = {
            "staging_areas": {},
            "temp_files": {},
            "large_files": [],
            "ml_insights": {},
            "cache_stats": self._smart_cache.get_cache_stats(),
            "mode": context.get("mode")
        }
        recommendations = []
        total_reclaimable = 0
        
        # Use parallel scanning for staging areas
        async def progress_callback(completed, total, current_item):
            if completed % 50 == 0 or completed == total:
                logger.info(f"[Janitor] Scanned {completed}/{total} files")
        
        # Enhanced parallel scan with smart caching
        scan_results = await parallel_scan_and_analyze(
            paths=self._staging_paths,
            progress_callback=progress_callback
        )
        
        # Process staging areas with enhanced analysis
        for path in self._staging_paths:
            if not os.path.exists(path):
                continue
            
            folder_name = os.path.basename(path)
            
            # Use smart cache for incremental scanning with limit and timeout
            try:
                cached_files = await asyncio.wait_for(
                    self._smart_cache.scan_directory_incremental(path, max_files=500),
                    timeout=30.0  # 30 second timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"[Janitor] Scan timeout for {path}, skipping...")
                cached_files = []
            
            categorized = {}
            for cache_entry in cached_files:
                # Use ML classification for better categorization
                ml_result = await self._ml_classifier.analyze(
                    cache_entry.path,
                    {
                        "filename": cache_entry.name,
                        "extension": cache_entry.extension,
                        "size_bytes": cache_entry.size_bytes,
                    }
                )
                
                # Use ML category if confidence is high
                if ml_result.action_required and ml_result.confidence > 0.7:
                    category = ml_result.metadata.get('predicted_category', 'UNKNOWN')
                else:
                    category = categorize_file(cache_entry.path).value
                
                if category not in categorized:
                    categorized[category] = []
                
                categorized[category].append({
                    "path": cache_entry.path,
                    "name": cache_entry.name,
                    "size_bytes": cache_entry.size_bytes,
                    "age_days": (datetime.now() - cache_entry.modified_at).days,
                    "ml_confidence": ml_result.confidence if ml_result.action_required else 0.0,
                    "ml_suggestion": ml_result.suggestion if ml_result.action_required else None,
                })
                
                self._metrics["files_analyzed"] += 1
            
            findings["staging_areas"][folder_name] = {
                "path": path,
                "total_files": len(cached_files),
                "categories": categorized,
                "cache_hit_rate": findings["cache_stats"]["hit_rate"],
            }
            
            # Enhanced recommendations
            total_files = len(cached_files)
            if total_files > 20:
                recommendations.append(
                    f"Organize {folder_name}: {total_files} files need sorting (ML-enhanced)"
                )
            
            # Check for files that need renaming
            rename_needed = sum(1 for cat_files in categorized.values() 
                             for file_info in cat_files 
                             if file_info.get("ml_suggestion") and "rename" in file_info["ml_suggestion"].lower())
            if rename_needed > 0:
                recommendations.append(f"Rename {rename_needed} poorly named files in {folder_name}")
        
        # Analyze temp folders
        for temp_path in get_temp_folders():
            try:
                size = await get_folder_size(temp_path)
                size_mb = size / (1024 * 1024)
                findings["temp_files"][temp_path] = {
                    "size_mb": round(size_mb, 2),
                }
                total_reclaimable += size
                
                if size_mb > 100:
                    recommendations.append(
                        f"Clear temp folder: {round(size_mb)} MB in {temp_path}"
                    )
            except Exception as e:
                logger.warning(f"Could not analyze temp: {e}")
        
        # Find large hidden files using parallel processing
        if context.get("deep_scan", False) or context.get("mode") == "disk_pressure":
            large = await find_large_files(self._user_home, min_size_mb=500)
            for f in large[:10]:  # Limit to top 10
                findings["large_files"].append({
                    "path": f.path,
                    "name": f.name,
                    "size_mb": round(f.size_bytes / (1024 * 1024), 2),
                })
            
            if large:
                recommendations.append(
                    f"Found {len(large)} large files (>500MB) that may be candidates for cleanup"
                )
        
        # Add ML insights
        findings["ml_insights"] = {
            "ml_model_available": self._ml_classifier.classifier.model is not None,
            "training_samples": len(self._ml_classifier.classifier.training_data),
            "image_processing_available": IMAGE_PROCESSING_AVAILABLE if 'IMAGE_PROCESSING_AVAILABLE' in globals() else False,
        }
        
        # Determine severity
        severity = "info"
        if total_reclaimable > 1024 * 1024 * 1024:  # > 1GB
            severity = "warning"
        if total_reclaimable > 5 * 1024 * 1024 * 1024:  # > 5GB
            severity = "critical"
        
        logger.info(f"[Janitor] Enhanced analysis complete: {self._metrics['files_analyzed']} files processed")
        
        return AnalysisResult(
            agent_name=self.name,
            findings=findings,
            recommendations=recommendations,
            severity=severity,
        )
    
    async def plan(self, analysis: AnalysisResult) -> ActionPlan:
        """
        Create a cleaning plan based on analysis.
        
        The plan is a JSON manifest that requires user approval.
        """
        logger.info("[Janitor] Creating cleaning plan...")
        self._status.current_task = "Creating cleaning plan"
        
        plan = CleaningPlan(agent=self.name)
        
        findings = analysis.findings
        mode = findings.get("mode")
        
        # 1. Plan staging area organization
        for folder_name, data in findings.get("staging_areas", {}).items():
            categories = data.get("categories", {})
            
            for category_str, files in categories.items():
                try:
                    category = FileCategory(category_str)
                except ValueError:
                    category = FileCategory.UNKNOWN
                
                for file_info in files:
                    file_path = file_info["path"]
                    size = file_info["size_bytes"]
                    age = file_info.get("age_days", 0)
                    
                    # Determine action
                    if category == FileCategory.TRASH:
                        # Delete trash files
                        plan.add_action(CleaningAction(
                            action="DELETE",
                            source=file_path,
                            reason=f"Temporary/cache file ({category_str})",
                            category=category_str,
                            size_bytes=size,
                            age_days=age,
                        ))
                    elif category == FileCategory.INSTALLERS and (age > 30 or mode == "disk_pressure"):
                        # Old installers → suggest delete
                        plan.add_action(CleaningAction(
                            action="DELETE",
                            source=file_path,
                            reason=f"Old installer ({age} days old)",
                            category=category_str,
                            size_bytes=size,
                            age_days=age,
                        ))
                    elif category != FileCategory.UNKNOWN:
                        # Move to appropriate folder
                        dest = get_destination_path(category, self._user_home)
                        if dest:
                            dest_file = os.path.join(dest, os.path.basename(file_path))
                            plan.add_action(CleaningAction(
                                action="MOVE",
                                source=file_path,
                                destination=dest_file,
                                reason=f"Organize {category_str} file",
                                category=category_str,
                                size_bytes=size,
                                age_days=age,
                            ))
        
        # 2. Plan temp file cleanup
        for temp_path, data in findings.get("temp_files", {}).items():
            size_mb = data.get("size_mb", 0)
            if size_mb > 50 or mode in ["disk_pressure", "memory_pressure"]:
                # Scan for old temp files
                old_files = await scan_folder(
                    temp_path,
                    min_age_days=3 if mode in ["disk_pressure", "memory_pressure"] else 7,
                    extensions=[".tmp", ".temp", ".log", ".cache"]
                )
                for f in old_files:
                    if not is_protected_path(f.path):
                        plan.add_action(CleaningAction(
                            action="DELETE",
                            source=f.path,
                            reason="Old temporary file",
                            category="TRASH",
                            size_bytes=f.size_bytes,
                            age_days=get_file_age_days(f.path),
                        ))

        # 3. Pressure-mode large file candidates
        if mode == "disk_pressure":
            for lf in findings.get("large_files", [])[:10]:
                try:
                    file_path = lf.get("path")
                    if not file_path or is_protected_path(file_path):
                        continue
                    if not os.path.exists(file_path):
                        continue
                    age_days = get_file_age_days(file_path)
                    if age_days < 7:
                        continue
                    plan.add_action(CleaningAction(
                        action="DELETE",
                        source=file_path,
                        reason=f"Large file candidate ({age_days} days old)",
                        category="LARGE_FILE",
                        size_bytes=os.path.getsize(file_path),
                        age_days=age_days,
                    ))
                except Exception:
                    continue
        
        logger.info(f"[Janitor] Plan created: {plan.total_files} actions")
        
        return ActionPlan(
            agent_name=self.name,
            analysis_id=analysis.analysis_id,
            actions=[a.model_dump() for a in plan.actions],
            requires_approval=True,
            estimated_impact=f"{plan.space_recoverable_bytes / (1024*1024):.1f} MB recoverable"
        )
    
    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """
        Execute an approved cleaning plan using parallel processing.
        
        Only runs if plan.approved == True.
        Uses parallel batch operations for improved performance.
        """
        if not plan.approved:
            return ExecutionResult(
                plan_id=plan.plan_id,
                agent_name=self.name,
                status="failed",
                errors=["Plan not approved"]
            )
        
        logger.info(f"[Janitor] Executing plan {plan.plan_id} with parallel processing...")
        self._status.current_task = "Executing cleaning plan with parallel operations"
        
        # Prepare operations for parallel execution
        operations = []
        for action_dict in plan.actions:
            action_type = action_dict.get("action")
            source = action_dict.get("source")
            destination = action_dict.get("destination")
            
            operations.append({
                "type": action_type.lower(),
                "source": source,
                "destination": destination,
                "size_bytes": action_dict.get("size_bytes", 0)
            })
        
        # Execute operations in parallel batches
        async def progress_callback(completed, total, result):
            if completed % 10 == 0 or completed == total:
                logger.info(f"[Janitor] Executed {completed}/{total} operations")
        
        summary = await self._parallel_processor.parallel_batch_operations(
            operations=operations,
            progress_callback=progress_callback
        )
        
        # Update metrics
        completed = summary["successful"]
        failed = summary["failed"]
        space_recovered = sum(op["size_bytes"] for op in operations if op["type"] == "delete")
        
        self._metrics["space_recovered_mb"] += space_recovered / (1024 * 1024)
        self._metrics["files_organized"] += sum(1 for op in operations if op["type"] == "move")
        self._metrics["files_deleted"] += sum(1 for op in operations if op["type"] == "delete")
        
        status = "success" if failed == 0 else "partial" if completed > 0 else "failed"
        
        logger.info(f"[Janitor] Parallel execution complete: {completed} done, {failed} failed")
        
        return ExecutionResult(
            plan_id=plan.plan_id,
            agent_name=self.name,
            status=status,
            actions_completed=completed,
            actions_failed=failed,
            metrics={
                "space_recovered_mb": round(space_recovered / (1024 * 1024), 2),
                "files_organized": self._metrics["files_organized"],
                "files_deleted": self._metrics["files_deleted"],
                "parallel_performance": {
                    "throughput": summary["throughput"],
                    "average_duration": summary["average_duration"],
                    "total_duration": summary["total_duration"]
                }
            },
            errors=[],
        )
    
    async def quick_scan(self) -> dict:
        """
        Quick scan for API endpoint - returns summary without full analysis.
        """
        logger.info("[Janitor] Starting quick scan...")
        
        result = {
            "downloads": {"files": 0, "size_mb": 0, "path": ""},
            "desktop": {"files": 0, "size_mb": 0, "path": ""},
            "temp_size_mb": 0,
            "recommendations": [],
            "errors": [],
            "scan_status": "started"
        }
        
        try:
            # Downloads
            downloads = os.path.join(self._user_home, "Downloads")
            result["downloads"]["path"] = downloads
            logger.info(f"[Janitor] Scanning Downloads: {downloads}")
            
            if os.path.exists(downloads):
                try:
                    files = await scan_folder(downloads)
                    result["downloads"]["files"] = len(files)
                    result["downloads"]["size_mb"] = round(
                        sum(f.size_bytes for f in files) / (1024*1024), 2
                    )
                    logger.info(f"[Janitor] Downloads: {len(files)} files, {result['downloads']['size_mb']} MB")
                except Exception as e:
                    logger.error(f"[Janitor] Failed to scan Downloads: {e}")
                    result["errors"].append(f"Downloads scan failed: {str(e)}")
            else:
                logger.warning(f"[Janitor] Downloads folder does not exist: {downloads}")
                result["errors"].append(f"Downloads folder not found: {downloads}")
            
            # Desktop
            desktop = os.path.join(self._user_home, "Desktop")
            result["desktop"]["path"] = desktop
            logger.info(f"[Janitor] Scanning Desktop: {desktop}")
            
            if os.path.exists(desktop):
                try:
                    files = await scan_folder(desktop)
                    result["desktop"]["files"] = len(files)
                    result["desktop"]["size_mb"] = round(
                        sum(f.size_bytes for f in files) / (1024*1024), 2
                    )
                    logger.info(f"[Janitor] Desktop: {len(files)} files, {result['desktop']['size_mb']} MB")
                except Exception as e:
                    logger.error(f"[Janitor] Failed to scan Desktop: {e}")
                    result["errors"].append(f"Desktop scan failed: {str(e)}")
            else:
                logger.warning(f"[Janitor] Desktop folder does not exist: {desktop}")
                result["errors"].append(f"Desktop folder not found: {desktop}")
            
            # Temp
            logger.info("[Janitor] Scanning temp folders...")
            temp_folders = get_temp_folders()
            logger.info(f"[Janitor] Found {len(temp_folders)} temp folders")
            
            for temp in temp_folders:
                try:
                    if os.path.exists(temp):
                        temp_size = await get_folder_size(temp)
                        result["temp_size_mb"] += round(temp_size / (1024*1024), 2)
                        logger.info(f"[Janitor] Temp {temp}: {temp_size / (1024*1024):.2f} MB")
                    else:
                        logger.debug(f"[Janitor] Temp folder does not exist: {temp}")
                except Exception as e:
                    logger.warning(f"[Janitor] Failed to scan temp folder {temp}: {e}")
            
            # Quick recommendations
            if result["downloads"]["files"] > 30:
                result["recommendations"].append(
                    f"Downloads has {result['downloads']['files']} files - needs organization"
                )
            if result["desktop"]["files"] > 20:
                result["recommendations"].append(
                    f"Desktop has {result['desktop']['files']} files - declutter recommended"
                )
            if result["temp_size_mb"] > 500:
                result["recommendations"].append(
                    f"Temp folders have {result['temp_size_mb']:.0f} MB - cleanup available"
                )
            
            # If no files found, provide mock data for testing
            if result["downloads"]["files"] == 0 and result["desktop"]["files"] == 0 and result["temp_size_mb"] == 0:
                logger.warning("[Janitor] No files found, providing mock data for testing")
                result["mock_data"] = True
                result["downloads"] = {"files": 15, "size_mb": 125.7, "path": downloads}
                result["desktop"] = {"files": 8, "size_mb": 45.2, "path": desktop}
                result["temp_size_mb"] = 234.1
                result["recommendations"] = [
                    "Mock data provided for testing - no actual files found",
                    f"Consider creating test folders at: {downloads}",
                    f"Consider creating test folders at: {desktop}"
                ]
            
            result["scan_status"] = "completed"
            logger.info(f"[Janitor] Quick scan completed: {len(result['recommendations'])} recommendations, {len(result['errors'])} errors")
            
        except Exception as e:
            logger.error(f"[Janitor] Quick scan failed: {e}")
            import traceback
            logger.error(f"[Janitor] Traceback: {traceback.format_exc()}")
            result["scan_status"] = "failed"
            result["errors"].append(f"Quick scan failed: {str(e)}")
        
        return result
    
    def get_metrics(self) -> dict:
        """Get current performance metrics."""
        return self._metrics.copy()
