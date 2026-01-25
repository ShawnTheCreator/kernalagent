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
        Survey the dirty zones and gather data.
        
        Scans:
        - Downloads folder
        - Desktop folder
        - Temp folders
        - Large file search (optional)
        """
        logger.info(f"[Janitor] Starting analysis...")
        self._status.current_task = "Analyzing file system"
        
        findings = {
            "staging_areas": {},
            "temp_files": {},
            "large_files": [],
        }
        recommendations = []
        total_reclaimable = 0
        
        # 1. Analyze staging areas (Downloads, Desktop)
        for path in self._staging_paths:
            if not os.path.exists(path):
                continue
            
            folder_name = os.path.basename(path)
            files = await scan_folder(path)
            
            categorized = {}
            for f in files:
                cat = categorize_file(f.path)
                if cat.value not in categorized:
                    categorized[cat.value] = []
                categorized[cat.value].append({
                    "path": f.path,
                    "name": f.name,
                    "size_bytes": f.size_bytes,
                    "age_days": get_file_age_days(f.path),
                })
                self._metrics["files_analyzed"] += 1
            
            findings["staging_areas"][folder_name] = {
                "path": path,
                "total_files": len(files),
                "categories": categorized,
            }
            
            if len(files) > 20:
                recommendations.append(
                    f"Organize {folder_name}: {len(files)} files need sorting"
                )
        
        # 2. Analyze temp folders
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
        
        # 3. Find large hidden files (optional, slower)
        if context.get("deep_scan", False):
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
        
        # Determine severity
        severity = "info"
        if total_reclaimable > 1024 * 1024 * 1024:  # > 1GB
            severity = "warning"
        if total_reclaimable > 5 * 1024 * 1024 * 1024:  # > 5GB
            severity = "critical"
        
        logger.info(f"[Janitor] Analysis complete: {self._metrics['files_analyzed']} files")
        
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
                    elif category == FileCategory.INSTALLERS and age > 30:
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
            if size_mb > 50:  # Only if > 50MB
                # Scan for old temp files
                old_files = await scan_folder(
                    temp_path,
                    min_age_days=7,
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
        Execute an approved cleaning plan.
        
        Only runs if plan.approved == True.
        """
        if not plan.approved:
            return ExecutionResult(
                plan_id=plan.plan_id,
                agent_name=self.name,
                status="failed",
                errors=["Plan not approved"]
            )
        
        logger.info(f"[Janitor] Executing plan {plan.plan_id}...")
        self._status.current_task = "Executing cleaning plan"
        
        completed = 0
        failed = 0
        errors = []
        space_recovered = 0
        
        for action_dict in plan.actions:
            action_type = action_dict.get("action")
            source = action_dict.get("source")
            destination = action_dict.get("destination")
            size = action_dict.get("size_bytes", 0)
            
            try:
                if action_type == "MOVE":
                    result = await safe_move(source, destination)
                    if result.success:
                        completed += 1
                        self._metrics["files_organized"] += 1
                    else:
                        failed += 1
                        errors.append(f"Move failed: {result.error}")
                        
                elif action_type == "DELETE":
                    result = await safe_delete(source, to_recycle=True)
                    if result.success:
                        completed += 1
                        space_recovered += size
                        self._metrics["files_deleted"] += 1
                    else:
                        failed += 1
                        errors.append(f"Delete failed: {result.error}")
                        
            except Exception as e:
                failed += 1
                errors.append(f"Error: {str(e)}")
        
        self._metrics["space_recovered_mb"] += space_recovered / (1024 * 1024)
        
        status = "success" if failed == 0 else "partial" if completed > 0 else "failed"
        
        logger.info(f"[Janitor] Execution complete: {completed} done, {failed} failed")
        
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
            },
            errors=errors[:10],  # Limit errors
        )
    
    async def quick_scan(self) -> dict:
        """
        Quick scan for API endpoint - returns summary without full analysis.
        """
        result = {
            "downloads": {"files": 0, "size_mb": 0},
            "desktop": {"files": 0, "size_mb": 0},
            "temp_size_mb": 0,
            "recommendations": [],
        }
        
        # Downloads
        downloads = os.path.join(self._user_home, "Downloads")
        if os.path.exists(downloads):
            files = await scan_folder(downloads)
            result["downloads"]["files"] = len(files)
            result["downloads"]["size_mb"] = round(
                sum(f.size_bytes for f in files) / (1024*1024), 2
            )
        
        # Desktop
        desktop = os.path.join(self._user_home, "Desktop")
        if os.path.exists(desktop):
            files = await scan_folder(desktop)
            result["desktop"]["files"] = len(files)
            result["desktop"]["size_mb"] = round(
                sum(f.size_bytes for f in files) / (1024*1024), 2
            )
        
        # Temp
        for temp in get_temp_folders():
            result["temp_size_mb"] += round(await get_folder_size(temp) / (1024*1024), 2)
        
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
        
        return result
    
    def get_metrics(self) -> dict:
        """Get current performance metrics."""
        return self._metrics.copy()
