#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Kernal Agent Automation System

This script thoroughly tests all the new automation enhancements:
- Agent imports and registration
- Workflow engine functionality
- Scheduling system
- Notification system
- Voice control system
- Integration points
"""

import sys
import os
import asyncio
import traceback
import logging
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all new modules can be imported successfully."""
    logger.info("🧪 Testing module imports...")
    
    try:
        # Test agent imports
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.janitor.janitor_tools import FileAnalyzer, safe_move, safe_delete
        logger.info("✅ JanitorAgent imports successful")
        
        from app.agents.productivity.productivity_agent import ProductivityAgent
        logger.info("✅ ProductivityAgent imports successful")
        
        from app.agents.security.security_agent import SecurityAgent
        logger.info("✅ SecurityAgent imports successful")
        
        # Test core system imports
        from app.agents.agent_registry import get_registry
        logger.info("✅ Agent registry imports successful")
        
        from app.automation.scheduler import SmartScheduler, CronParser, get_scheduler
        logger.info("✅ Scheduler imports successful")
        
        from app.notifications.notification_manager import get_notification_manager, NotificationPriority
        logger.info("✅ Notification system imports successful")
        
        from app.voice.enhanced_voice_control import get_voice_control, VoiceCommand, ConversationState
        logger.info("✅ Voice control imports successful")
        
        # Test enhanced planner
        from app.reasoning.llm_planner import WorkflowEngine
        logger.info("✅ Enhanced planner imports successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_agent_creation():
    """Test that agents can be created and configured properly."""
    logger.info("🤖 Testing agent creation...")
    
    try:
        # Create agents
        janitor = JanitorAgent()
        productivity = ProductivityAgent()
        security = SecurityAgent()
        
        # Test basic properties
        assert janitor.name == "JANITOR_AGENT"
        assert productivity.name == "PRODUCTIVITY_AGENT"
        assert security.name == "SECURITY_AGENT"
        
        # Test that they have required methods
        assert hasattr(janitor, 'analyze')
        assert hasattr(janitor, 'plan')
        assert hasattr(janitor, 'execute')
        assert hasattr(janitor, 'get_triggers')
        
        logger.info("✅ Agent creation successful")
        return True, [janitor, productivity, security]
        
    except Exception as e:
        logger.error(f"❌ Agent creation failed: {e}")
        logger.error(traceback.format_exc())
        return False, []

def test_agent_registry():
    """Test agent registration system."""
    logger.info("📋 Testing agent registry...")
    
    try:
        from app.agents.agent_registry import get_registry
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.productivity.productivity_agent import ProductivityAgent
        from app.agents.security.security_agent import SecurityAgent
        
        registry = get_registry()
        
        # Clear any existing registrations for clean test
        registry._agents = {}
        registry._by_type = {agent_type: [] for agent_type in registry._by_type}
        
        # Register agents
        agents = [JanitorAgent(), ProductivityAgent(), SecurityAgent()]
        for agent in agents:
            registry.register(agent)
        
        # Test retrieval
        assert len(registry.get_all()) == 3
        assert registry.get("JANITOR_AGENT") is not None
        assert registry.get("PRODUCTIVITY_AGENT") is not None
        assert registry.get("SECURITY_AGENT") is not None
        
        # Test type-based retrieval
        continuous_agents = registry.get_continuous_agents()
        on_demand_agents = registry.get_on_demand_agents()
        
        logger.info(f"✅ Agent registry successful - {len(registry.get_all())} agents registered")
        logger.info(f"   Continuous: {len(continuous_agents)}, On-demand: {len(on_demand_agents)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent registry test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_agent_functionality():
    """Test basic agent functionality."""
    logger.info("⚡ Testing agent functionality...")
    
    try:
        from app.agents.janitor.janitor_agent import JanitorAgent
        
        # Test JanitorAgent analyze method
        janitor = JanitorAgent()
        
        test_context = {
            "intent": "clean up my desktop files",
            "current_directory": "C:\\Users\\anime\\Desktop"
        }
        
        analysis = await janitor.analyze(test_context)
        assert analysis is not None
        assert hasattr(analysis, 'findings')
        assert hasattr(analysis, 'recommendations')
        
        # Test plan generation
        if analysis.recommendations:
            plan = await janitor.plan(analysis)
            assert plan is not None
            assert hasattr(plan, 'actions')
            
            logger.info(f"✅ Agent functionality test passed - {len(plan.actions)} actions planned")
        else:
            logger.info("✅ Agent functionality test passed - no actions needed")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent functionality test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_scheduler_system():
    """Test the intelligent scheduling system."""
    logger.info("⏰ Testing scheduler system...")
    
    try:
        from app.automation.scheduler import SmartScheduler, CronParser, ScheduledTask, TriggerType
        from datetime import datetime, timedelta
        
        # Test CronParser
        parser = CronParser()
        
        # Test parsing basic cron expression
        next_run = parser.parse_cron("0 9 * * *")  # 9 AM daily
        assert next_run is not None
        
        # Test SmartScheduler
        scheduler = SmartScheduler()
        
        # Test adding a scheduled task
        task = ScheduledTask(
            task_id="test_task",
            agent_name="JANITOR_AGENT",
            trigger_type=TriggerType.CRON,
            trigger_value="0 */6 * * *",  # Every 6 hours
            action_params={"action": "cleanup"}
        )
        
        scheduler.add_task(task)
        assert len(scheduler.tasks) == 1
        assert scheduler.tasks[0].task_id == "test_task"
        
        logger.info("✅ Scheduler system test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Scheduler system test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_notification_system():
    """Test the notification system."""
    logger.info("🔔 Testing notification system...")
    
    try:
        from app.notifications.notification_manager import get_notification_manager, NotificationPriority
        
        manager = get_notification_manager()
        
        # Test notification creation
        notification_id = await manager.create_notification(
            title="Test Notification",
            message="This is a test notification",
            priority=NotificationPriority.MEDIUM,
            agent_name="TEST_AGENT"
        )
        
        assert notification_id is not None
        
        # Test notification retrieval
        notification = manager.get_notification(notification_id)
        assert notification is not None
        assert notification.title == "Test Notification"
        
        # Test template-based notification
        template_vars = {
            "agent_name": "JANITOR_AGENT",
            "action_count": 5,
            "summary": "cleaned 5 files"
        }
        
        template_notification_id = await manager.create_from_template(
            "agent_action_complete",
            template_vars
        )
        
        assert template_notification_id is not None
        
        logger.info("✅ Notification system test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Notification system test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_voice_control_system():
    """Test the enhanced voice control system."""
    logger.info("🗣️ Testing voice control system...")
    
    try:
        from app.voice.enhanced_voice_control import get_voice_control, VoiceCommand, ConversationState
        
        voice_control = get_voice_control()
        
        # Test voice control initialization
        assert voice_control is not None
        assert hasattr(voice_control, 'conversation_contexts')
        assert hasattr(voice_control, 'intent_patterns')
        
        # Test intent pattern matching
        assert "open_application" in voice_control.intent_patterns
        assert "security_scan" in voice_control.intent_patterns
        assert "create_task" in voice_control.intent_patterns
        
        # Test response templates
        assert "action_confirm" in voice_control.response_templates
        assert "not_understood" in voice_control.response_templates
        
        logger.info("✅ Voice control system test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Voice control system test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_workflow_engine():
    """Test the enhanced workflow engine."""
    logger.info("🔧 Testing workflow engine...")
    
    try:
        from app.reasoning.llm_planner import WorkflowEngine
        
        engine = WorkflowEngine()
        
        # Test workflow detection
        test_plan = {
            "steps": [
                {"action": "CLICK", "target": "file"},
                {"action": "IF", "condition": "file_selected", "then": [{"action": "DELETE"}]},
                {"action": "WAIT", "duration": 1000}
            ]
        }
        
        has_workflow = engine._has_workflow_features(test_plan)
        assert has_workflow == True
        
        logger.info("✅ Workflow engine test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Workflow engine test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def test_integration():
    """Test integration between different systems."""
    logger.info("🔗 Testing system integration...")
    
    try:
        # Test agent-notification integration
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.notifications.notification_manager import get_notification_manager
        
        janitor = JanitorAgent()
        notification_manager = get_notification_manager()
        
        # Simulate agent completing work and sending notification
        notification_id = await notification_manager.create_from_template(
            "agent_action_complete",
            {
                "agent_name": janitor.name,
                "action_count": 3,
                "summary": "organized 15 files"
            }
        )
        
        assert notification_id is not None
        
        # Test scheduler-agent integration
        from app.automation.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        assert scheduler is not None
        
        logger.info("✅ System integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ System integration test failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_file_operations():
    """Test file operation tools safely."""
    logger.info("📁 Testing file operations...")
    
    try:
        from app.agents.janitor.janitor_tools import FileAnalyzer, FileOperation
        import tempfile
        import os
        
        # Create temporary test files
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.txt")
            with open(test_file, "w") as f:
                f.write("Test content")
            
            # Test file analyzer
            analyzer = FileAnalyzer()
            category = analyzer.get_file_category(test_file)
            assert category in ["documents", "unknown"]  # txt could be either
            
            # Test file operation creation
            operation = FileOperation(
                operation_type="move",
                source_path=test_file,
                destination_path=os.path.join(temp_dir, "moved_file.txt"),
                timestamp=datetime.now(),
                file_size=os.path.getsize(test_file)
            )
            
            assert operation.operation_type == "move"
            assert operation.file_size > 0
        
        logger.info("✅ File operations test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ File operations test failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def main():
    """Run all comprehensive tests."""
    logger.info("🚀 Starting comprehensive test suite for Kernal Agent automation enhancements")
    logger.info("=" * 80)
    
    test_results = {}
    
    # Run all tests
    tests = [
        ("Module Imports", test_imports, False),
        ("Agent Creation", test_agent_creation, False),
        ("Agent Registry", test_agent_registry, False),
        ("Agent Functionality", test_agent_functionality, True),
        ("Scheduler System", test_scheduler_system, False),
        ("Notification System", test_notification_system, True),
        ("Voice Control", test_voice_control_system, False),
        ("Workflow Engine", test_workflow_engine, False),
        ("System Integration", test_integration, True),
        ("File Operations", test_file_operations, False)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func, is_async in tests:
        logger.info(f"\n--- Running: {test_name} ---")
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
                if isinstance(result, tuple):
                    result = result[0]  # Take first element for agent creation test
            
            if result:
                test_results[test_name] = "✅ PASSED"
                passed += 1
            else:
                test_results[test_name] = "❌ FAILED"
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            test_results[test_name] = "❌ CRASHED"
            failed += 1
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 80)
    
    for test_name, result in test_results.items():
        logger.info(f"{result} {test_name}")
    
    logger.info(f"\n🎯 Total: {passed + failed} tests")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    
    if failed == 0:
        logger.info("\n🎉 ALL TESTS PASSED! The enhanced automation system is working correctly.")
        return True
    else:
        logger.error(f"\n⚠️  {failed} tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n⛔ Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n💥 Test suite crashed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
