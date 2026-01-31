#!/usr/bin/env python3
"""
Test Enhanced Agent System Integration

This test verifies the enhanced agent system integrates properly
with the existing Kernal Agent infrastructure.
"""

import pytest
import sys
import os
import asyncio
from unittest.mock import Mock, patch

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestEnhancedAgentSystem:
    """Test enhanced agent system integration."""
    
    def test_agent_imports(self):
        """Test that all enhanced agents can be imported."""
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent  
        from app.agents.security.security_agent import SecurityAgent
        
        assert JanitorAgent is not None
        assert ProductivityAgent is not None
        assert SecurityAgent is not None
    
    def test_agent_creation(self):
        """Test that enhanced agents can be created."""
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent
        from app.agents.security.security_agent import SecurityAgent
        
        janitor = JanitorAgent()
        productivity = ProductivityAgent()
        security = SecurityAgent()
        
        assert janitor.name == "JANITOR_AGENT"
        assert productivity.name == "PRODUCTIVITY_AGENT" 
        assert security.name == "SECURITY_AGENT"
        
        # Test required methods exist
        for agent in [janitor, productivity, security]:
            assert hasattr(agent, 'analyze')
            assert hasattr(agent, 'plan')
            assert hasattr(agent, 'execute')
            assert hasattr(agent, 'get_triggers')
    
    def test_agent_registry_integration(self):
        """Test that agents integrate with the registry."""
        from app.agents.agent_registry import get_registry
        from app.agents.janitor.janitor_agent import JanitorAgent
        
        registry = get_registry()
        janitor = JanitorAgent()
        
        # Clear registry for clean test
        original_agents = registry._agents.copy()
        registry._agents = {}
        registry._by_type = {agent_type: [] for agent_type in registry._by_type}
        
        try:
            registry.register(janitor)
            assert len(registry.get_all()) == 1
            assert registry.get("JANITOR_AGENT") is not None
            
            # Test intent matching
            matches = registry.find_by_intent("clean up files")
            assert len(matches) > 0
            
        finally:
            # Restore original state
            registry._agents = original_agents
            registry._by_type = {agent_type: [] for agent_type in registry._by_type}
            for agent in original_agents.values():
                registry._by_type[agent.agent_type].append(agent.name)
    
    def test_scheduler_system(self):
        """Test the enhanced scheduler system."""
        from app.automation.scheduler import SmartScheduler, CronParser, ScheduledTask, TriggerType
        from datetime import datetime, timedelta
        
        scheduler = SmartScheduler()
        parser = CronParser()
        
        # Test cron parsing
        next_run = parser.parse_cron("0 9 * * *")  # 9 AM daily
        assert next_run is not None
        
        # Test task scheduling
        task = ScheduledTask(
            task_id="test_task",
            agent_name="JANITOR_AGENT",
            trigger_type=TriggerType.CRON,
            trigger_value="0 */6 * * *",
            action_params={"action": "test"}
        )
        
        scheduler.add_task(task)
        assert len(scheduler.tasks) == 1
        assert scheduler.tasks[0].task_id == "test_task"
    
    @pytest.mark.asyncio
    async def test_notification_system(self):
        """Test the notification system."""
        from app.notifications.notification_manager import get_notification_manager, NotificationPriority
        
        manager = get_notification_manager()
        
        # Clear any existing notifications for clean test
        manager.notifications = {}
        manager.delivery_queue = []
        
        # Test notification creation
        notification_id = await manager.create_notification(
            title="Test Notification",
            message="Test message", 
            priority=NotificationPriority.MEDIUM,
            agent_name="TEST_AGENT"
        )
        
        assert notification_id is not None
        
        notification = manager.get_notification(notification_id)
        assert notification is not None
        assert notification.title == "Test Notification"
        
        # Test template notification
        template_id = await manager.create_from_template(
            "agent_action_complete",
            {
                "agent_name": "JANITOR_AGENT",
                "action_count": 5,
                "summary": "test summary"
            }
        )
        
        assert template_id is not None
        template_notification = manager.get_notification(template_id)
        assert template_notification is not None
    
    def test_voice_control_system(self):
        """Test the enhanced voice control system."""
        from app.voice.enhanced_voice_control import get_voice_control
        
        voice_control = get_voice_control()
        
        assert voice_control is not None
        assert hasattr(voice_control, 'intent_patterns')
        assert hasattr(voice_control, 'response_templates')
        
        # Test intent patterns exist
        assert "open_application" in voice_control.intent_patterns
        assert "security_scan" in voice_control.intent_patterns
        assert "create_task" in voice_control.intent_patterns
        
        # Test response templates exist
        assert "action_confirm" in voice_control.response_templates
        assert "not_understood" in voice_control.response_templates
    
    @pytest.mark.asyncio
    async def test_agent_workflow(self):
        """Test basic agent workflow functionality."""
        from app.agents.janitor.janitor_agent import JanitorAgent
        
        agent = JanitorAgent()
        
        # Test analysis
        context = {
            "intent": "organize files",
            "target_directory": "/tmp"
        }
        
        analysis = await agent.analyze(context)
        assert analysis is not None
        assert hasattr(analysis, 'findings')
        assert hasattr(analysis, 'recommendations')
        
        # Test planning
        plan = await agent.plan(analysis)
        assert plan is not None
        assert hasattr(plan, 'actions')
    
    def test_workflow_engine(self):
        """Test the enhanced workflow engine."""
        from app.reasoning.llm_planner import WorkflowEngine
        
        engine = WorkflowEngine()
        
        # Test workflow detection
        workflow_plan = {
            "steps": [
                {"action": "CLICK", "target": "button"},
                {"action": "IF", "condition": "success", "then": [{"action": "DONE"}]},
                {"action": "WAIT", "duration": 1000}
            ]
        }
        
        has_workflow = engine._has_workflow_features(workflow_plan)
        assert has_workflow == True
        
        simple_plan = {
            "steps": [
                {"action": "CLICK", "target": "button"},
                {"action": "DONE"}
            ]
        }
        
        has_simple_workflow = engine._has_workflow_features(simple_plan)
        assert has_simple_workflow == False
    
    def test_main_app_imports(self):
        """Test that main app imports work with enhancements."""
        # This should import without errors
        from app.main import app
        assert app is not None
        
        # Test that the startup event exists
        assert hasattr(app, 'router')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])