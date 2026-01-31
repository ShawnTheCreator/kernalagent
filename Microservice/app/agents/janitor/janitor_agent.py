"""
Janitor Agent - "The Digital Housekeeper"

Specializes in autonomous file management and system cleanup.
Monitors Downloads, Desktop, and user directories for organization opportunities.

Capabilities:
- Smart file organization by category
- Duplicate file detection and cleanup
- Large file compression
- Empty folder removal
- Scheduled cleanup automation
- Safe operations with transaction logging
"""

import logging
import os
from typing import Any, Optional, Dict, List
from datetime import datetime

from app.agents.base_agent import BaseAgent, AgentType, AnalysisResult, ActionPlan, AgentTrigger, ExecutionResult
from app.agents.janitor.janitor_tools import (
    FileAnalyzer, organize_by_category, compress_large_files, 
    find_duplicates, clean_empty_folders, safe_move, safe_delete
)

logger = logging.getLogger(__name__)


class JanitorAgent(BaseAgent):
    """Agent for autonomous file organization and system cleanup."""
    
    def __init__(self):
        self.name = "JANITOR_AGENT"
        self.agent_type = AgentType.CONTINUOUS
        self.specialization = "file_organization"
        super().__init__()
    
    async def analyze(self, context: dict) -> AnalysisResult:
        """Analyze directories for cleanup opportunities."""
        intent = context.get("intent", "").lower()
        target_dirs = self._get_target_directories(context, intent)
        
        findings = {
            "directories_analyzed": len(target_dirs),
            "total_files": 0,
            "total_size_mb": 0,
            "cleanup_opportunities": []
        }
        
        recommendations = []
        severity = "info"
        
        for directory in target_dirs:
            if not os.path.exists(directory):
                continue
                
            analysis = FileAnalyzer.analyze_directory(directory)
            
            if "error" in analysis:
                logger.warning(f"Failed to analyze {directory}: {analysis['error']}")
                continue
            
            findings["total_files"] += analysis["total_files"]
            findings["total_size_mb"] += analysis["total_size_mb"]
            
            # Analyze cleanup opportunities
            opportunities = []
            
            # File organization opportunity
            if analysis["total_files"] > 10:
                categories = len(analysis["categories"])
                if categories > 1:
                    opportunities.append({
                        "type": "organize_by_category",
                        "directory": directory,
                        "impact": f"Organize {analysis['total_files']} files into {categories} categories",
                        "priority": "medium"
                    })
            
            # Large files compression
            if analysis["large_files"]:
                total_large_size = sum(f["size_mb"] for f in analysis["large_files"])
                opportunities.append({
                    "type": "compress_large_files",
                    "directory": directory,
                    "impact": f"Compress {len(analysis['large_files'])} large files ({total_large_size:.1f}MB)",
                    "priority": "low"
                })
            
            # Empty folders cleanup
            if analysis["empty_folders"]:
                opportunities.append({
                    "type": "clean_empty_folders",
                    "directory": directory,
                    "impact": f"Remove {len(analysis['empty_folders'])} empty folders",
                    "priority": "low"
                })
            
            # Old files archival
            if analysis["old_files"]:
                old_size = sum(os.path.getsize(f["path"]) for f in analysis["old_files"] 
                             if os.path.exists(f["path"])) / (1024 * 1024)
                opportunities.append({
                    "type": "archive_old_files",
                    "directory": directory,
                    "impact": f"Archive {len(analysis['old_files'])} old files ({old_size:.1f}MB)",
                    "priority": "low"
                })
            
            if opportunities:
                findings["cleanup_opportunities"].extend(opportunities)
                
                # Generate recommendations
                for opp in opportunities:
                    if opp["type"] == "organize_by_category":
                        recommendations.append(f"Organize files in {os.path.basename(directory)}")
                    elif opp["type"] == "compress_large_files":
                        recommendations.append(f"Compress large files in {os.path.basename(directory)}")
                    elif opp["type"] == "clean_empty_folders":
                        recommendations.append(f"Clean empty folders in {os.path.basename(directory)}")
                    elif opp["type"] == "archive_old_files":
                        recommendations.append(f"Archive old files in {os.path.basename(directory)}")
        
        # Determine severity based on findings
        total_opportunities = len(findings["cleanup_opportunities"])
        if total_opportunities > 5:
            severity = "warning"
        elif total_opportunities > 10:
            severity = "critical"
        
        return AnalysisResult(
            agent_name=self.name,
            findings=findings,
            recommendations=recommendations,
            severity=severity
        )
    
    async def plan(self, analysis: AnalysisResult) -> ActionPlan:
        """Create cleanup plan based on analysis."""
        opportunities = analysis.findings.get("cleanup_opportunities", [])
        actions = []
        
        # Sort opportunities by priority
        priority_order = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        opportunities.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 0), reverse=True)
        
        for opp in opportunities:
            action = {
                "tool": opp["type"],
                "parameters": {
                    "directory": opp["directory"]
                },
                "description": opp["impact"],
                "priority": opp["priority"]
            }
            
            # Add specific parameters based on action type
            if opp["type"] == "compress_large_files":
                action["parameters"]["size_threshold_mb"] = 100
            
            actions.append(action)
        
        # Estimate impact
        total_files = analysis.findings.get("total_files", 0)
        total_size = analysis.findings.get("total_size_mb", 0)
        estimated_impact = f"Process {total_files} files ({total_size:.1f}MB) across {len(opportunities)} operations"
        
        return ActionPlan(
            agent_name=self.name,
            analysis_id=analysis.analysis_id,
            actions=actions,
            estimated_impact=estimated_impact,
            requires_approval=True  # File operations require approval
        )
    
    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """Execute the cleanup plan."""
        result = ExecutionResult(
            plan_id=plan.plan_id,
            agent_name=self.name,
            status="running"
        )
        
        for i, action in enumerate(plan.actions):
            try:
                tool = action.get("tool")
                params = action.get("parameters", {})
                directory = params.get("directory")
                
                if not directory or not os.path.exists(directory):
                    result.actions_failed += 1
                    result.errors.append(f"Directory not found: {directory}")
                    continue
                
                action_result = None
                
                if tool == "organize_by_category":
                    action_result = await organize_by_category(directory)
                    
                elif tool == "compress_large_files":
                    size_threshold = params.get("size_threshold_mb", 100)
                    action_result = await compress_large_files(directory, size_threshold)
                    
                elif tool == "clean_empty_folders":
                    action_result = await clean_empty_folders(directory)
                    
                elif tool == "find_duplicates":
                    action_result = await find_duplicates(directory)
                    
                elif tool == "archive_old_files":
                    # Create archive directory and move old files
                    archive_dir = os.path.join(directory, "Archive")
                    os.makedirs(archive_dir, exist_ok=True)
                    
                    # This is a placeholder - would need more sophisticated archival logic
                    action_result = {"archived_files": [], "total_archived": 0}
                
                if action_result and "error" not in action_result:
                    result.actions_completed += 1
                    
                    # Update metrics
                    if tool == "organize_by_category":
                        result.metrics["files_organized"] = action_result.get("total_processed", 0)
                    elif tool == "compress_large_files":
                        result.metrics["space_saved_mb"] = action_result.get("space_saved_mb", 0)
                        result.metrics["files_compressed"] = len(action_result.get("files_compressed", []))
                    elif tool == "clean_empty_folders":
                        result.metrics["folders_removed"] = action_result.get("total_removed", 0)
                    elif tool == "find_duplicates":
                        result.metrics["duplicates_found"] = action_result.get("total_duplicates", 0)
                        result.metrics["potential_space_saved_mb"] = action_result.get("potential_space_saved_mb", 0)
                else:
                    result.actions_failed += 1
                    error_msg = action_result.get("error", "Unknown error") if action_result else "No result"
                    result.errors.append(f"{tool} failed: {error_msg}")
                    
            except Exception as e:
                result.actions_failed += 1
                result.errors.append(f"Action {i+1} failed: {str(e)}")
                logger.error(f"Janitor action failed: {e}")
        
        # Determine final status
        if result.actions_failed == 0:
            result.status = "success"
        elif result.actions_completed > 0:
            result.status = "partial"
        else:
            result.status = "failed"
        
        return result
    
    def get_triggers(self) -> List[AgentTrigger]:
        """Return conditions that trigger the Janitor agent."""
        return [
            AgentTrigger(
                trigger_type="system_pulse",
                condition="downloads > 50 files",
                priority=7
            ),
            AgentTrigger(
                trigger_type="system_pulse", 
                condition="desktop > 30 files",
                priority=6
            ),
            AgentTrigger(
                trigger_type="system_pulse",
                condition="disk_usage > 85%",
                priority=8
            ),
            AgentTrigger(
                trigger_type="scheduled",
                condition="daily_at_2am",
                priority=5
            ),
            AgentTrigger(
                trigger_type="user_intent",
                condition="clean organize tidy files downloads desktop",
                priority=9
            )
        ]
    
    def _get_target_directories(self, context: dict, intent: str) -> List[str]:
        """Determine which directories to analyze based on context and intent."""
        default_dirs = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents")
        ]
        
        # Check for specific directory requests in intent
        if "downloads" in intent:
            return [os.path.expanduser("~/Downloads")]
        elif "desktop" in intent:
            return [os.path.expanduser("~/Desktop")]
        elif "documents" in intent:
            return [os.path.expanduser("~/Documents")]
        
        # Check context for specific paths
        target_path = context.get("target_path")
        if target_path and os.path.exists(target_path):
            return [target_path]
        
        # Return all default directories
        return [d for d in default_dirs if os.path.exists(d)]


# Capability functions for direct invocation
async def organize_downloads() -> dict:
    """Quick function to organize downloads folder."""
    downloads_dir = os.path.expanduser("~/Downloads")
    return await organize_by_category(downloads_dir)


async def compress_large_downloads() -> dict:
    """Quick function to compress large files in downloads."""
    downloads_dir = os.path.expanduser("~/Downloads") 
    return await compress_large_files(downloads_dir)


async def clean_desktop() -> dict:
    """Quick function to clean up desktop."""
    desktop_dir = os.path.expanduser("~/Desktop")
    
    # Organize files
    organize_result = await organize_by_category(desktop_dir)
    
    # Clean empty folders
    clean_result = await clean_empty_folders(desktop_dir)
    
    return {
        "organized": organize_result,
        "cleaned": clean_result
    }


async def find_desktop_duplicates() -> dict:
    """Quick function to find duplicates on desktop."""
    desktop_dir = os.path.expanduser("~/Desktop")
    return await find_duplicates(desktop_dir)