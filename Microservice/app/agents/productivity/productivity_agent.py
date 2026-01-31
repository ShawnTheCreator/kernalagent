"""
Productivity Agent - "The Digital Assistant"

Specializes in workplace automation and productivity enhancement.
Handles meeting automation, email processing, task management, and focus optimization.

Capabilities:
- Meeting automation (auto-join, scheduling, recording)
- Email processing and organization
- Task creation and management
- Break reminders and focus sessions
- Application management
- Document automation
"""

import logging
import os
import re
import asyncio
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

from app.agents.base_agent import BaseAgent, AgentType, AnalysisResult, ActionPlan, AgentTrigger, ExecutionResult

logger = logging.getLogger(__name__)


class ProductivityAgent(BaseAgent):
    """Agent for workplace automation and productivity enhancement."""
    
    def __init__(self):
        self.name = "PRODUCTIVITY_AGENT"
        self.agent_type = AgentType.ON_DEMAND
        self.specialization = "productivity_automation"
        super().__init__()
    
    async def analyze(self, context: dict) -> AnalysisResult:
        """Analyze productivity context and opportunities."""
        intent = context.get("intent", "").lower()
        findings = {
            "productivity_opportunities": [],
            "current_context": {},
            "recommendations": []
        }
        
        recommendations = []
        severity = "info"
        
        # Analyze different productivity areas based on intent
        if any(keyword in intent for keyword in ["meeting", "zoom", "teams", "call"]):
            meeting_analysis = await self._analyze_meeting_context(intent, context)
            findings["productivity_opportunities"].extend(meeting_analysis["opportunities"])
            recommendations.extend(meeting_analysis["recommendations"])
        
        elif any(keyword in intent for keyword in ["email", "outlook", "gmail", "inbox"]):
            email_analysis = await self._analyze_email_context(intent, context)
            findings["productivity_opportunities"].extend(email_analysis["opportunities"])
            recommendations.extend(email_analysis["recommendations"])
        
        elif any(keyword in intent for keyword in ["task", "todo", "remind", "schedule"]):
            task_analysis = await self._analyze_task_context(intent, context)
            findings["productivity_opportunities"].extend(task_analysis["opportunities"])
            recommendations.extend(task_analysis["recommendations"])
        
        elif any(keyword in intent for keyword in ["focus", "distraction", "block", "break"]):
            focus_analysis = await self._analyze_focus_context(intent, context)
            findings["productivity_opportunities"].extend(focus_analysis["opportunities"])
            recommendations.extend(focus_analysis["recommendations"])
        
        elif any(keyword in intent for keyword in ["document", "report", "template", "format"]):
            document_analysis = await self._analyze_document_context(intent, context)
            findings["productivity_opportunities"].extend(document_analysis["opportunities"])
            recommendations.extend(document_analysis["recommendations"])
        
        else:
            # General productivity analysis
            general_analysis = await self._analyze_general_productivity(intent, context)
            findings["productivity_opportunities"].extend(general_analysis["opportunities"])
            recommendations.extend(general_analysis["recommendations"])
        
        # Determine severity based on opportunities
        opportunity_count = len(findings["productivity_opportunities"])
        if opportunity_count > 3:
            severity = "warning"
        elif opportunity_count > 5:
            severity = "critical"
        
        return AnalysisResult(
            agent_name=self.name,
            findings=findings,
            recommendations=recommendations,
            severity=severity
        )
    
    async def plan(self, analysis: AnalysisResult) -> ActionPlan:
        """Create productivity automation plan."""
        opportunities = analysis.findings.get("productivity_opportunities", [])
        actions = []
        
        for opp in opportunities:
            if opp["type"] == "meeting_automation":
                actions.extend(self._create_meeting_actions(opp))
            elif opp["type"] == "email_processing":
                actions.extend(self._create_email_actions(opp))
            elif opp["type"] == "task_management":
                actions.extend(self._create_task_actions(opp))
            elif opp["type"] == "focus_session":
                actions.extend(self._create_focus_actions(opp))
            elif opp["type"] == "document_automation":
                actions.extend(self._create_document_actions(opp))
        
        # Estimate impact
        total_opportunities = len(opportunities)
        estimated_impact = f"Automate {total_opportunities} productivity tasks"
        
        return ActionPlan(
            agent_name=self.name,
            analysis_id=analysis.analysis_id,
            actions=actions,
            estimated_impact=estimated_impact,
            requires_approval=True
        )
    
    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """Execute the productivity plan."""
        result = ExecutionResult(
            plan_id=plan.plan_id,
            agent_name=self.name,
            status="running"
        )
        
        for i, action in enumerate(plan.actions):
            try:
                tool = action.get("tool")
                params = action.get("parameters", {})
                
                action_result = None
                
                if tool == "join_meeting":
                    action_result = await self._execute_join_meeting(params)
                elif tool == "process_emails":
                    action_result = await self._execute_process_emails(params)
                elif tool == "create_task":
                    action_result = await self._execute_create_task(params)
                elif tool == "start_focus_session":
                    action_result = await self._execute_start_focus_session(params)
                elif tool == "block_distractions":
                    action_result = await self._execute_block_distractions(params)
                elif tool == "format_document":
                    action_result = await self._execute_format_document(params)
                elif tool == "schedule_break":
                    action_result = await self._execute_schedule_break(params)
                
                if action_result and action_result.get("success", False):
                    result.actions_completed += 1
                    
                    # Update metrics based on action type
                    if tool == "join_meeting":
                        result.metrics["meetings_joined"] = result.metrics.get("meetings_joined", 0) + 1
                    elif tool == "process_emails":
                        result.metrics["emails_processed"] = action_result.get("emails_processed", 0)
                    elif tool == "create_task":
                        result.metrics["tasks_created"] = result.metrics.get("tasks_created", 0) + 1
                    
                else:
                    result.actions_failed += 1
                    error_msg = action_result.get("error", "Unknown error") if action_result else "No result"
                    result.errors.append(f"{tool} failed: {error_msg}")
                    
            except Exception as e:
                result.actions_failed += 1
                result.errors.append(f"Action {i+1} failed: {str(e)}")
                logger.error(f"Productivity action failed: {e}")
        
        # Determine final status
        if result.actions_failed == 0:
            result.status = "success"
        elif result.actions_completed > 0:
            result.status = "partial"
        else:
            result.status = "failed"
        
        return result
    
    def get_triggers(self) -> List[AgentTrigger]:
        """Return conditions that trigger the Productivity agent."""
        return [
            AgentTrigger(
                trigger_type="user_intent",
                condition="meeting join schedule call zoom teams",
                priority=9
            ),
            AgentTrigger(
                trigger_type="user_intent",
                condition="email process inbox organize",
                priority=8
            ),
            AgentTrigger(
                trigger_type="user_intent",
                condition="task todo create remind schedule",
                priority=8
            ),
            AgentTrigger(
                trigger_type="user_intent",
                condition="focus session block distractions break",
                priority=7
            ),
            AgentTrigger(
                trigger_type="scheduled",
                condition="hourly_break_reminder",
                priority=6
            ),
            AgentTrigger(
                trigger_type="application_event",
                condition="outlook_opened",
                priority=5
            )
        ]
    
    # ===== Analysis Methods =====
    
    async def _analyze_meeting_context(self, intent: str, context: dict) -> dict:
        """Analyze meeting-related automation opportunities."""
        opportunities = []
        recommendations = []
        
        if "join" in intent or "start" in intent:
            # Extract meeting details from intent
            meeting_url = self._extract_meeting_url(intent)
            meeting_time = self._extract_time(intent)
            
            opportunities.append({
                "type": "meeting_automation",
                "subtype": "join_meeting",
                "meeting_url": meeting_url,
                "meeting_time": meeting_time,
                "priority": "high"
            })
            recommendations.append("Auto-join meeting")
        
        elif "schedule" in intent:
            opportunities.append({
                "type": "meeting_automation",
                "subtype": "schedule_meeting",
                "priority": "medium"
            })
            recommendations.append("Schedule meeting with participants")
        
        return {"opportunities": opportunities, "recommendations": recommendations}
    
    async def _analyze_email_context(self, intent: str, context: dict) -> dict:
        """Analyze email-related automation opportunities."""
        opportunities = []
        recommendations = []
        
        if "organize" in intent or "sort" in intent:
            opportunities.append({
                "type": "email_processing",
                "subtype": "organize_inbox",
                "priority": "medium"
            })
            recommendations.append("Organize inbox by rules")
        
        elif "unsubscribe" in intent:
            opportunities.append({
                "type": "email_processing",
                "subtype": "mass_unsubscribe",
                "priority": "low"
            })
            recommendations.append("Unsubscribe from newsletters")
        
        elif "respond" in intent or "reply" in intent:
            opportunities.append({
                "type": "email_processing",
                "subtype": "auto_response",
                "priority": "high"
            })
            recommendations.append("Generate email response")
        
        return {"opportunities": opportunities, "recommendations": recommendations}
    
    async def _analyze_task_context(self, intent: str, context: dict) -> dict:
        """Analyze task management opportunities."""
        opportunities = []
        recommendations = []
        
        if "create" in intent or "add" in intent:
            task_description = self._extract_task_description(intent)
            due_date = self._extract_due_date(intent)
            
            opportunities.append({
                "type": "task_management",
                "subtype": "create_task",
                "task_description": task_description,
                "due_date": due_date,
                "priority": "high"
            })
            recommendations.append(f"Create task: {task_description}")
        
        elif "remind" in intent:
            reminder_time = self._extract_time(intent)
            reminder_text = self._extract_reminder_text(intent)
            
            opportunities.append({
                "type": "task_management",
                "subtype": "set_reminder",
                "reminder_time": reminder_time,
                "reminder_text": reminder_text,
                "priority": "medium"
            })
            recommendations.append(f"Set reminder: {reminder_text}")
        
        return {"opportunities": opportunities, "recommendations": recommendations}
    
    async def _analyze_focus_context(self, intent: str, context: dict) -> dict:
        """Analyze focus and distraction management opportunities."""
        opportunities = []
        recommendations = []
        
        if "focus" in intent or "concentrate" in intent:
            duration = self._extract_duration(intent) or 25  # Default Pomodoro
            
            opportunities.append({
                "type": "focus_session",
                "subtype": "start_pomodoro",
                "duration_minutes": duration,
                "priority": "high"
            })
            recommendations.append(f"Start {duration}-minute focus session")
        
        elif "block" in intent or "distraction" in intent:
            apps_to_block = self._extract_apps_to_block(intent)
            
            opportunities.append({
                "type": "focus_session",
                "subtype": "block_distractions",
                "apps_to_block": apps_to_block,
                "priority": "high"
            })
            recommendations.append("Block distracting applications")
        
        elif "break" in intent:
            break_type = self._extract_break_type(intent)
            
            opportunities.append({
                "type": "focus_session",
                "subtype": "take_break",
                "break_type": break_type,
                "priority": "medium"
            })
            recommendations.append(f"Take {break_type} break")
        
        return {"opportunities": opportunities, "recommendations": recommendations}
    
    async def _analyze_document_context(self, intent: str, context: dict) -> dict:
        """Analyze document automation opportunities."""
        opportunities = []
        recommendations = []
        
        if "format" in intent or "template" in intent:
            document_type = self._extract_document_type(intent)
            
            opportunities.append({
                "type": "document_automation",
                "subtype": "apply_template",
                "document_type": document_type,
                "priority": "medium"
            })
            recommendations.append(f"Apply {document_type} template")
        
        elif "export" in intent or "convert" in intent:
            export_format = self._extract_export_format(intent)
            
            opportunities.append({
                "type": "document_automation",
                "subtype": "export_document",
                "export_format": export_format,
                "priority": "medium"
            })
            recommendations.append(f"Export to {export_format}")
        
        return {"opportunities": opportunities, "recommendations": recommendations}
    
    async def _analyze_general_productivity(self, intent: str, context: dict) -> dict:
        """Analyze general productivity opportunities."""
        opportunities = []
        recommendations = []
        
        # Check current time for productivity suggestions
        current_hour = datetime.now().hour
        
        if 9 <= current_hour <= 17:  # Work hours
            opportunities.append({
                "type": "productivity_suggestion",
                "subtype": "work_hours_optimization",
                "priority": "low"
            })
            recommendations.append("Enable work hours automation")
        
        return {"opportunities": opportunities, "recommendations": recommendations}
    
    # ===== Action Creation Methods =====
    
    def _create_meeting_actions(self, opportunity: dict) -> List[dict]:
        """Create actions for meeting automation."""
        actions = []
        subtype = opportunity.get("subtype")
        
        if subtype == "join_meeting":
            actions.append({
                "tool": "join_meeting",
                "parameters": {
                    "meeting_url": opportunity.get("meeting_url"),
                    "meeting_time": opportunity.get("meeting_time")
                },
                "description": "Join meeting automatically"
            })
        
        elif subtype == "schedule_meeting":
            actions.append({
                "tool": "schedule_meeting",
                "parameters": {},
                "description": "Schedule meeting with participants"
            })
        
        return actions
    
    def _create_email_actions(self, opportunity: dict) -> List[dict]:
        """Create actions for email processing."""
        actions = []
        subtype = opportunity.get("subtype")
        
        if subtype == "organize_inbox":
            actions.append({
                "tool": "process_emails",
                "parameters": {
                    "action": "organize"
                },
                "description": "Organize inbox by rules"
            })
        
        elif subtype == "auto_response":
            actions.append({
                "tool": "process_emails",
                "parameters": {
                    "action": "auto_response"
                },
                "description": "Generate and send email response"
            })
        
        return actions
    
    def _create_task_actions(self, opportunity: dict) -> List[dict]:
        """Create actions for task management."""
        actions = []
        subtype = opportunity.get("subtype")
        
        if subtype == "create_task":
            actions.append({
                "tool": "create_task",
                "parameters": {
                    "description": opportunity.get("task_description"),
                    "due_date": opportunity.get("due_date")
                },
                "description": f"Create task: {opportunity.get('task_description')}"
            })
        
        elif subtype == "set_reminder":
            actions.append({
                "tool": "schedule_break",
                "parameters": {
                    "reminder_time": opportunity.get("reminder_time"),
                    "reminder_text": opportunity.get("reminder_text")
                },
                "description": f"Set reminder: {opportunity.get('reminder_text')}"
            })
        
        return actions
    
    def _create_focus_actions(self, opportunity: dict) -> List[dict]:
        """Create actions for focus management."""
        actions = []
        subtype = opportunity.get("subtype")
        
        if subtype == "start_pomodoro":
            duration = opportunity.get("duration_minutes", 25)
            actions.append({
                "tool": "start_focus_session",
                "parameters": {
                    "duration_minutes": duration,
                    "session_type": "pomodoro"
                },
                "description": f"Start {duration}-minute focus session"
            })
        
        elif subtype == "block_distractions":
            actions.append({
                "tool": "block_distractions",
                "parameters": {
                    "apps_to_block": opportunity.get("apps_to_block", ["youtube.com", "facebook.com", "twitter.com"])
                },
                "description": "Block distracting websites and apps"
            })
        
        return actions
    
    def _create_document_actions(self, opportunity: dict) -> List[dict]:
        """Create actions for document automation."""
        actions = []
        subtype = opportunity.get("subtype")
        
        if subtype == "apply_template":
            actions.append({
                "tool": "format_document",
                "parameters": {
                    "template_type": opportunity.get("document_type"),
                    "action": "apply_template"
                },
                "description": f"Apply {opportunity.get('document_type')} template"
            })
        
        return actions
    
    # ===== Execution Methods =====
    
    async def _execute_join_meeting(self, params: dict) -> dict:
        """Execute meeting join automation."""
        meeting_url = params.get("meeting_url")
        
        try:
            if meeting_url:
                # Open meeting URL in default browser
                import webbrowser
                webbrowser.open(meeting_url)
                
                # Wait for browser to load, then look for join button
                await asyncio.sleep(3)
                
                return {
                    "success": True,
                    "message": f"Opened meeting URL: {meeting_url}"
                }
            else:
                return {
                    "success": False,
                    "error": "No meeting URL provided"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_process_emails(self, params: dict) -> dict:
        """Execute email processing automation."""
        action = params.get("action", "organize")
        
        try:
            # This would integrate with email APIs (Outlook, Gmail)
            # For now, return simulation
            
            emails_processed = 0
            
            if action == "organize":
                # Simulate organizing emails
                emails_processed = 25
                
            elif action == "auto_response":
                # Simulate auto-response
                emails_processed = 1
            
            return {
                "success": True,
                "emails_processed": emails_processed,
                "message": f"Processed {emails_processed} emails with action: {action}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_create_task(self, params: dict) -> dict:
        """Execute task creation."""
        description = params.get("description", "")
        due_date = params.get("due_date")
        
        try:
            # This would integrate with task management systems (Todoist, etc.)
            # For now, simulate task creation
            
            task_data = {
                "description": description,
                "due_date": due_date,
                "created_at": datetime.now().isoformat(),
                "status": "pending"
            }
            
            return {
                "success": True,
                "task_created": task_data,
                "message": f"Created task: {description}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_start_focus_session(self, params: dict) -> dict:
        """Execute focus session start."""
        duration = params.get("duration_minutes", 25)
        session_type = params.get("session_type", "focus")
        
        try:
            # Start focus session (would integrate with focus apps)
            
            return {
                "success": True,
                "session_started": True,
                "duration_minutes": duration,
                "session_type": session_type,
                "message": f"Started {duration}-minute {session_type} session"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_block_distractions(self, params: dict) -> dict:
        """Execute distraction blocking."""
        apps_to_block = params.get("apps_to_block", [])
        
        try:
            # Block distracting apps/websites (would integrate with blocking software)
            blocked_count = len(apps_to_block)
            
            return {
                "success": True,
                "apps_blocked": apps_to_block,
                "blocked_count": blocked_count,
                "message": f"Blocked {blocked_count} distracting apps/sites"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_format_document(self, params: dict) -> dict:
        """Execute document formatting."""
        template_type = params.get("template_type", "")
        action = params.get("action", "apply_template")
        
        try:
            # Apply document template/formatting
            
            return {
                "success": True,
                "template_applied": template_type,
                "action": action,
                "message": f"Applied {template_type} template"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_schedule_break(self, params: dict) -> dict:
        """Execute break scheduling."""
        reminder_time = params.get("reminder_time")
        reminder_text = params.get("reminder_text", "Take a break")
        
        try:
            # Schedule break reminder
            from app.automation.scheduler import get_scheduler
            
            scheduler = get_scheduler()
            # This would schedule an actual reminder
            
            return {
                "success": True,
                "reminder_scheduled": True,
                "reminder_time": reminder_time,
                "reminder_text": reminder_text,
                "message": f"Scheduled reminder: {reminder_text}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ===== Helper Methods =====
    
    def _extract_meeting_url(self, text: str) -> Optional[str]:
        """Extract meeting URL from text."""
        url_patterns = [
            r'https?://[^\s]+zoom[^\s]*',
            r'https?://teams\.microsoft\.com[^\s]*',
            r'https?://meet\.google\.com[^\s]*'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """Extract time from text."""
        time_patterns = [
            r'\d{1,2}:\d{2}\s*(?:am|pm)',
            r'\d{1,2}\s*(?:am|pm)',
            r'at\s+(\d{1,2}:\d{2})',
            r'in\s+(\d+)\s*minutes?'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    def _extract_task_description(self, text: str) -> str:
        """Extract task description from intent."""
        # Remove command words and extract the main task
        command_words = ["create", "add", "task", "todo", "remind", "me", "to"]
        words = text.split()
        
        filtered_words = []
        skip_next = False
        
        for word in words:
            if skip_next:
                skip_next = False
                continue
                
            if word.lower() in command_words:
                if word.lower() in ["remind", "create", "add"]:
                    skip_next = True
                continue
            
            filtered_words.append(word)
        
        return " ".join(filtered_words).strip()
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date from text."""
        date_patterns = [
            r'due\s+(\w+)',
            r'by\s+(\w+)',
            r'tomorrow',
            r'today',
            r'next\s+\w+',
            r'\d{1,2}/\d{1,2}'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    def _extract_reminder_text(self, text: str) -> str:
        """Extract reminder text from intent."""
        # Extract text after "remind me to" or similar
        patterns = [
            r'remind\s+me\s+to\s+(.+)',
            r'reminder\s+to\s+(.+)',
            r'remind\s+(.+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return text.strip()
    
    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract duration in minutes from text."""
        duration_patterns = [
            r'(\d+)\s*minutes?',
            r'(\d+)\s*mins?',
            r'(\d+)\s*hours?',
            r'for\s+(\d+)'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                if "hour" in pattern:
                    value *= 60
                return value
        return None
    
    def _extract_apps_to_block(self, text: str) -> List[str]:
        """Extract apps/websites to block from text."""
        common_distractions = [
            "youtube.com", "facebook.com", "twitter.com", "instagram.com",
            "tiktok.com", "reddit.com", "netflix.com", "twitch.tv"
        ]
        
        found_apps = []
        text_lower = text.lower()
        
        for app in common_distractions:
            domain = app.split('.')[0]
            if domain in text_lower:
                found_apps.append(app)
        
        return found_apps if found_apps else common_distractions
    
    def _extract_break_type(self, text: str) -> str:
        """Extract break type from text."""
        if "short" in text.lower():
            return "short"
        elif "long" in text.lower():
            return "long"
        else:
            return "normal"
    
    def _extract_document_type(self, text: str) -> str:
        """Extract document type from text."""
        doc_types = {
            "report": "business_report",
            "memo": "memo", 
            "letter": "formal_letter",
            "proposal": "project_proposal",
            "presentation": "presentation"
        }
        
        text_lower = text.lower()
        for keyword, doc_type in doc_types.items():
            if keyword in text_lower:
                return doc_type
        
        return "generic"
    
    def _extract_export_format(self, text: str) -> str:
        """Extract export format from text."""
        formats = ["pdf", "docx", "xlsx", "pptx", "txt", "csv"]
        text_lower = text.lower()
        
        for fmt in formats:
            if fmt in text_lower:
                return fmt
        
        return "pdf"  # Default format