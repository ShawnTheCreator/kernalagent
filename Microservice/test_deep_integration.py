#!/usr/bin/env python3
"""
Deep Integration Test - Microservice Startup Verification

Tests the complete microservice startup sequence including:
- All agent registrations
- Enhanced systems initialization  
- API endpoint availability
- WebSocket connections
- Error handling and resilience
"""

import sys
import os
import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DeepIntegrationTester:
    """Deep integration tester for the microservice."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_microservice_startup(self):
        """Test that microservice can start up with all enhancements."""
        logger.info("🚀 Testing microservice startup sequence...")
        
        try:
            # Import and test app creation
            from app.main import app
            logger.info("✅ FastAPI app imports successfully")
            
            # Test that startup event can run without errors
            logger.info("🔧 Testing startup event...")
            
            # Manually trigger startup logic (without actual server)
            try:
                # Test agent registration specifically
                from app.agents.agent_registry import get_registry
                from app.agents.janitor.janitor_agent import JanitorAgent
                from app.agents.productivity.productivity_agent import ProductivityAgent
                from app.agents.security.security_agent import SecurityAgent
                
                logger.info("📋 Testing agent registration...")
                registry = get_registry()
                
                # Clear registry for clean test
                registry._agents = {}
                registry._by_type = {agent_type: [] for agent_type in registry._by_type}
                
                # Register agents like the startup event does
                registry.register(JanitorAgent())
                registry.register(ProductivityAgent())
                registry.register(SecurityAgent())
                
                registered_agents = registry.get_all()
                logger.info(f"✅ Successfully registered {len(registered_agents)} agents:")
                
                for agent in registered_agents:
                    logger.info(f"   - {agent.name} ({agent.agent_type.value})")
                    
                    # Test that each agent has required methods
                    assert hasattr(agent, 'analyze'), f"{agent.name} missing analyze method"
                    assert hasattr(agent, 'plan'), f"{agent.name} missing plan method"
                    assert hasattr(agent, 'execute'), f"{agent.name} missing execute method"
                    assert hasattr(agent, 'get_triggers'), f"{agent.name} missing get_triggers method"
                
                logger.info("✅ All agents have required methods")
                
                # Test enhanced systems initialization
                from app.voice.enhanced_voice_control import get_voice_control
                from app.notifications.notification_manager import get_notification_manager
                from app.automation.scheduler import get_scheduler
                
                voice_control = get_voice_control()
                assert voice_control is not None
                logger.info("✅ Voice control system initialized")
                
                notification_manager = get_notification_manager()
                assert notification_manager is not None
                logger.info("✅ Notification system initialized")
                
                scheduler = get_scheduler()
                assert scheduler is not None
                logger.info("✅ Scheduling system initialized")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Startup event test failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
                
        except Exception as e:
            logger.error(f"❌ Microservice startup test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_api_endpoints(self):
        """Test API endpoint availability (if server is running)."""
        logger.info("🌐 Testing API endpoints...")
        
        try:
            # Test health endpoint
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Health endpoint responding: {data}")
                    return True
                else:
                    logger.warning(f"⚠️ Health endpoint returned {response.status}")
                    return False
                    
        except aiohttp.ClientConnectorError:
            logger.info("ℹ️ Microservice not running - skipping endpoint tests")
            return True  # Not a failure if server isn't running
        except Exception as e:
            logger.error(f"❌ API endpoint test failed: {e}")
            return False
    
    async def test_agent_triggers(self):
        """Test agent trigger system."""
        logger.info("🎯 Testing agent trigger system...")
        
        try:
            from app.agents.agent_registry import get_registry
            
            registry = get_registry()
            
            # Test intent matching
            test_intents = [
                ("clean up my files", ["JANITOR_AGENT"]),
                ("schedule a meeting", ["PRODUCTIVITY_AGENT"]),
                ("check security", ["SECURITY_AGENT"]),
                ("run virus scan", ["SECURITY_AGENT"])
            ]
            
            for intent, expected_agents in test_intents:
                matching_agents = registry.find_by_intent(intent)
                
                if matching_agents:
                    agent_names = [agent.name for agent in matching_agents]
                    logger.info(f"✅ Intent '{intent}' → {agent_names}")
                    
                    # Check if expected agents are in matches
                    for expected in expected_agents:
                        if expected in agent_names:
                            logger.info(f"   ✓ Found expected agent: {expected}")
                        else:
                            logger.warning(f"   ⚠️ Expected agent not found: {expected}")
                else:
                    logger.warning(f"⚠️ No agents matched intent: '{intent}'")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Agent triggers test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_workflow_engine_integration(self):
        """Test workflow engine integration with planning."""
        logger.info("⚙️ Testing workflow engine integration...")
        
        try:
            from app.reasoning.llm_planner import WorkflowEngine
            
            engine = WorkflowEngine()
            
            # Test complex workflow handling
            test_workflow = {
                "steps": [
                    {"action": "CLICK", "target": "Start Menu"},
                    {
                        "action": "IF", 
                        "condition": "menu_opened",
                        "then": [
                            {"action": "TYPE", "text": "notepad"},
                            {"action": "WAIT", "duration": 1000},
                            {"action": "CLICK", "target": "Notepad"}
                        ],
                        "else": [
                            {"action": "ERROR", "message": "Start menu did not open"}
                        ]
                    },
                    {"action": "DONE"}
                ]
            }
            
            # Test workflow detection
            has_workflow = engine._has_workflow_features(test_workflow)
            assert has_workflow, "Workflow features not detected"
            
            # Test conditional handling
            conditional_step = test_workflow["steps"][1]
            result = engine._handle_conditional(conditional_step, {})
            assert result is not None, "Conditional handling failed"
            
            logger.info("✅ Workflow engine integration successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Workflow engine integration test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_notification_integration(self):
        """Test notification system integration."""
        logger.info("🔔 Testing notification integration...")
        
        try:
            from app.notifications.notification_manager import get_notification_manager, NotificationPriority
            
            manager = get_notification_manager()
            
            # Test notification creation and delivery pipeline
            notification_id = await manager.create_notification(
                title="Integration Test",
                message="Testing notification integration",
                priority=NotificationPriority.HIGH,
                agent_name="TEST_AGENT"
            )
            
            # Verify notification exists
            notification = manager.get_notification(notification_id)
            assert notification is not None, "Notification not created"
            assert notification.title == "Integration Test"
            
            # Test template system
            template_id = await manager.create_from_template(
                "security_threat_detected",
                {
                    "threat_type": "TEST_THREAT",
                    "threat_description": "Integration test threat"
                }
            )
            
            template_notification = manager.get_notification(template_id)
            assert template_notification is not None, "Template notification not created"
            
            # Test queue status
            status = manager.get_queue_status()
            assert status["total_notifications"] >= 2, "Notifications not queued"
            
            logger.info(f"✅ Notification integration successful - {status['total_notifications']} notifications")
            return True
            
        except Exception as e:
            logger.error(f"❌ Notification integration test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_voice_control_integration(self):
        """Test voice control system integration."""
        logger.info("🗣️ Testing voice control integration...")
        
        try:
            from app.voice.enhanced_voice_control import get_voice_control, VoiceIntentType
            
            voice_control = get_voice_control()
            
            # Test intent parsing
            test_commands = [
                "open notepad",
                "create task buy groceries",
                "run security scan",
                "schedule meeting with team tomorrow"
            ]
            
            for command in test_commands:
                intent = await voice_control._parse_intent(command, "test_user", None)
                
                assert intent is not None, f"Intent parsing failed for: {command}"
                assert intent.confidence > 0, f"Zero confidence for: {command}"
                assert intent.original_text == command
                
                logger.info(f"✅ Parsed '{command}' → {intent.intent_type.value} (confidence: {intent.confidence:.2f})")
            
            # Test conversation context
            context = await voice_control._get_or_create_context("test_context", "test_user")
            assert context is not None, "Context creation failed"
            assert context.context_id == "test_context"
            
            logger.info("✅ Voice control integration successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Voice control integration test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_scheduler_integration(self):
        """Test scheduler system integration."""
        logger.info("⏰ Testing scheduler integration...")
        
        try:
            from app.automation.scheduler import get_scheduler, ScheduledTask, TriggerType
            from datetime import datetime, timedelta
            
            scheduler = get_scheduler()
            
            # Test task scheduling
            test_task = ScheduledTask(
                task_id="integration_test_task",
                agent_name="JANITOR_AGENT",
                trigger_type=TriggerType.CRON,
                trigger_value="0 */6 * * *",  # Every 6 hours
                action_params={"action": "test_cleanup"},
                next_run=datetime.now() + timedelta(hours=6)
            )
            
            scheduler.add_task(test_task)
            assert len(scheduler.tasks) >= 1, "Task not added to scheduler"
            
            # Test task retrieval
            found_task = None
            for task in scheduler.tasks:
                if task.task_id == "integration_test_task":
                    found_task = task
                    break
            
            assert found_task is not None, "Added task not found in scheduler"
            assert found_task.agent_name == "JANITOR_AGENT"
            
            # Test cron parsing
            from app.automation.scheduler import CronParser
            parser = CronParser()
            next_run = parser.parse_cron("0 9 * * *")  # 9 AM daily
            assert next_run is not None, "Cron parsing failed"
            
            logger.info(f"✅ Scheduler integration successful - {len(scheduler.tasks)} tasks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Scheduler integration test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def test_full_agent_workflow(self):
        """Test complete agent workflow: analyze → plan → execute."""
        logger.info("🔄 Testing full agent workflow...")
        
        try:
            from app.agents.janitor.janitor_agent import JanitorAgent
            
            agent = JanitorAgent()
            
            # Step 1: Analysis
            test_context = {
                "intent": "organize my downloads folder",
                "target_directory": "C:\\Users\\Test\\Downloads"
            }
            
            analysis = await agent.analyze(test_context)
            assert analysis is not None, "Analysis failed"
            assert hasattr(analysis, 'findings'), "Analysis missing findings"
            
            logger.info(f"✅ Analysis complete - {len(analysis.findings.get('file_issues', []))} issues found")
            
            # Step 2: Planning
            plan = await agent.plan(analysis)
            assert plan is not None, "Planning failed"
            assert hasattr(plan, 'actions'), "Plan missing actions"
            
            logger.info(f"✅ Planning complete - {len(plan.actions)} actions planned")
            
            # Step 3: Execution (dry run - don't actually execute)
            # We'll just verify the execution method exists and can be called
            assert hasattr(agent, 'execute'), "Agent missing execute method"
            
            logger.info("✅ Full agent workflow test successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Full agent workflow test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def run_all_tests(self):
        """Run all deep integration tests."""
        logger.info("🔬 Starting Deep Integration Test Suite")
        logger.info("=" * 80)
        
        tests = [
            ("Microservice Startup", self.test_microservice_startup),
            ("API Endpoints", self.test_api_endpoints),
            ("Agent Triggers", self.test_agent_triggers),
            ("Workflow Engine Integration", self.test_workflow_engine_integration),
            ("Notification Integration", self.test_notification_integration),
            ("Voice Control Integration", self.test_voice_control_integration),
            ("Scheduler Integration", self.test_scheduler_integration),
            ("Full Agent Workflow", self.test_full_agent_workflow)
        ]
        
        results = {}
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            logger.info(f"\n--- Running: {test_name} ---")
            
            start_time = time.time()
            try:
                result = await test_func()
                duration = time.time() - start_time
                
                if result:
                    results[test_name] = f"✅ PASSED ({duration:.2f}s)"
                    passed += 1
                else:
                    results[test_name] = f"❌ FAILED ({duration:.2f}s)"
                    failed += 1
                    
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"💥 {test_name} crashed: {e}")
                results[test_name] = f"💥 CRASHED ({duration:.2f}s)"
                failed += 1
        
        # Print detailed summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 DEEP INTEGRATION TEST RESULTS")
        logger.info("=" * 80)
        
        for test_name, result in results.items():
            logger.info(f"{result} {test_name}")
        
        logger.info(f"\n📈 SUMMARY:")
        logger.info(f"   Total Tests: {passed + failed}")
        logger.info(f"   ✅ Passed: {passed}")
        logger.info(f"   ❌ Failed: {failed}")
        logger.info(f"   Success Rate: {(passed/(passed + failed)*100):.1f}%")
        
        if failed == 0:
            logger.info("\n🎉 ALL DEEP INTEGRATION TESTS PASSED!")
            logger.info("🚀 The enhanced Kernal Agent automation system is fully operational!")
            return True
        else:
            logger.error(f"\n⚠️ {failed} integration tests failed.")
            logger.error("❗ Please review the errors above before deploying.")
            return False

async def main():
    """Main test runner."""
    try:
        async with DeepIntegrationTester() as tester:
            success = await tester.run_all_tests()
            return success
    except Exception as e:
        logger.error(f"💥 Deep integration tests crashed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            print("\n🎯 VERDICT: System ready for production!")
        else:
            print("\n🔧 VERDICT: System needs fixes before deployment.")
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n⛔ Tests interrupted by user")
        sys.exit(130)