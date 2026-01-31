"""
Security Agent - "The Digital Guardian"

Specializes in system security monitoring, threat detection, and security automation.
Handles suspicious activity monitoring, password auditing, security updates, and privacy protection.

Capabilities:
- Suspicious activity monitoring
- Password security audits
- Automatic security updates
- Backup verification
- Privacy scanning and protection
- Threat detection and response
"""

import logging
import os
import hashlib
import asyncio
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import psutil
import re

from app.agents.base_agent import BaseAgent, AgentType, AnalysisResult, ActionPlan, AgentTrigger, ExecutionResult

logger = logging.getLogger(__name__)


class SecurityAgent(BaseAgent):
    """Agent for security monitoring and automated protection."""
    
    def __init__(self):
        self.name = "SECURITY_AGENT"
        self.agent_type = AgentType.CONTINUOUS
        self.specialization = "security_monitoring"
        self.last_scan_time = None
        self.suspicious_events = []
        super().__init__()
    
    async def analyze(self, context: dict) -> AnalysisResult:
        """Analyze system security status and threats."""
        intent = context.get("intent", "").lower()
        findings = {
            "security_threats": [],
            "security_score": 100,
            "recommendations": [],
            "vulnerability_count": 0
        }
        
        recommendations = []
        security_issues = []
        
        # Perform security scans based on intent or continuous monitoring
        if any(keyword in intent for keyword in ["security", "scan", "check", "threat", "virus"]):
            # Full security scan
            threat_scan = await self._scan_for_threats()
            password_audit = await self._audit_passwords()
            system_scan = await self._scan_system_security()
            
            security_issues.extend(threat_scan["threats"])
            security_issues.extend(password_audit["issues"])
            security_issues.extend(system_scan["vulnerabilities"])
            
        elif any(keyword in intent for keyword in ["password", "credential", "login"]):
            # Focus on password security
            password_audit = await self._audit_passwords()
            security_issues.extend(password_audit["issues"])
            
        elif any(keyword in intent for keyword in ["backup", "restore", "data"]):
            # Focus on backup security
            backup_check = await self._verify_backups()
            security_issues.extend(backup_check["issues"])
            
        elif any(keyword in intent for keyword in ["privacy", "tracking", "data"]):
            # Focus on privacy protection
            privacy_scan = await self._scan_privacy_threats()
            security_issues.extend(privacy_scan["threats"])
            
        else:
            # Continuous monitoring
            threat_scan = await self._scan_for_threats()
            system_scan = await self._scan_system_security()
            
            security_issues.extend(threat_scan["threats"])
            security_issues.extend(system_scan["vulnerabilities"])
        
        # Calculate security score
        findings["vulnerability_count"] = len(security_issues)
        findings["security_score"] = max(0, 100 - (len(security_issues) * 10))
        findings["security_threats"] = security_issues
        
        # Generate recommendations based on findings
        for issue in security_issues:
            if issue["type"] == "weak_password":
                recommendations.append("Update weak passwords immediately")
            elif issue["type"] == "outdated_software":
                recommendations.append("Install security updates")
            elif issue["type"] == "suspicious_process":
                recommendations.append("Investigate suspicious processes")
            elif issue["type"] == "open_ports":
                recommendations.append("Close unnecessary network ports")
            elif issue["type"] == "backup_failure":
                recommendations.append("Fix backup configuration")
            elif issue["type"] == "privacy_leak":
                recommendations.append("Block privacy-invasive tracking")
        
        findings["recommendations"] = list(set(recommendations))  # Remove duplicates
        
        # Determine severity
        severity = "info"
        if findings["vulnerability_count"] > 3:
            severity = "warning"
        elif findings["vulnerability_count"] > 5 or any(issue["severity"] == "critical" for issue in security_issues):
            severity = "critical"
        
        return AnalysisResult(
            agent_name=self.name,
            findings=findings,
            recommendations=recommendations,
            severity=severity
        )
    
    async def plan(self, analysis: AnalysisResult) -> ActionPlan:
        """Create security remediation plan."""
        threats = analysis.findings.get("security_threats", [])
        actions = []
        
        for threat in threats:
            if threat["type"] == "weak_password":
                actions.extend(self._create_password_actions(threat))
            elif threat["type"] == "outdated_software":
                actions.extend(self._create_update_actions(threat))
            elif threat["type"] == "suspicious_process":
                actions.extend(self._create_process_actions(threat))
            elif threat["type"] == "open_ports":
                actions.extend(self._create_network_actions(threat))
            elif threat["type"] == "backup_failure":
                actions.extend(self._create_backup_actions(threat))
            elif threat["type"] == "privacy_leak":
                actions.extend(self._create_privacy_actions(threat))
        
        # Always include monitoring actions for continuous security
        actions.append({
            "tool": "enable_monitoring",
            "parameters": {"monitoring_type": "continuous"},
            "description": "Enable continuous security monitoring"
        })
        
        vulnerability_count = analysis.findings.get("vulnerability_count", 0)
        estimated_impact = f"Address {vulnerability_count} security issues"
        
        return ActionPlan(
            agent_name=self.name,
            analysis_id=analysis.analysis_id,
            actions=actions,
            estimated_impact=estimated_impact,
            requires_approval=True
        )
    
    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """Execute the security remediation plan."""
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
                
                if tool == "update_passwords":
                    action_result = await self._execute_update_passwords(params)
                elif tool == "install_updates":
                    action_result = await self._execute_install_updates(params)
                elif tool == "terminate_process":
                    action_result = await self._execute_terminate_process(params)
                elif tool == "close_ports":
                    action_result = await self._execute_close_ports(params)
                elif tool == "fix_backup":
                    action_result = await self._execute_fix_backup(params)
                elif tool == "block_tracking":
                    action_result = await self._execute_block_tracking(params)
                elif tool == "enable_monitoring":
                    action_result = await self._execute_enable_monitoring(params)
                
                if action_result and action_result.get("success", False):
                    result.actions_completed += 1
                    
                    # Update security metrics
                    if tool == "update_passwords":
                        result.metrics["passwords_updated"] = result.metrics.get("passwords_updated", 0) + 1
                    elif tool == "install_updates":
                        result.metrics["updates_installed"] = action_result.get("updates_installed", 0)
                    elif tool == "terminate_process":
                        result.metrics["threats_mitigated"] = result.metrics.get("threats_mitigated", 0) + 1
                    
                else:
                    result.actions_failed += 1
                    error_msg = action_result.get("error", "Unknown error") if action_result else "No result"
                    result.errors.append(f"{tool} failed: {error_msg}")
                    
            except Exception as e:
                result.actions_failed += 1
                result.errors.append(f"Security action {i+1} failed: {str(e)}")
                logger.error(f"Security action failed: {e}")
        
        # Determine final status
        if result.actions_failed == 0:
            result.status = "success"
        elif result.actions_completed > 0:
            result.status = "partial"
        else:
            result.status = "failed"
        
        return result
    
    def get_triggers(self) -> List[AgentTrigger]:
        """Return conditions that trigger the Security agent."""
        return [
            AgentTrigger(
                trigger_type="user_intent",
                condition="security scan check virus malware threat",
                priority=10
            ),
            AgentTrigger(
                trigger_type="user_intent", 
                condition="password credential login authenticate",
                priority=9
            ),
            AgentTrigger(
                trigger_type="scheduled",
                condition="daily_security_scan",
                priority=8
            ),
            AgentTrigger(
                trigger_type="system_event",
                condition="suspicious_process_detected",
                priority=10
            ),
            AgentTrigger(
                trigger_type="system_event",
                condition="failed_login_attempt",
                priority=9
            ),
            AgentTrigger(
                trigger_type="system_event",
                condition="network_anomaly",
                priority=8
            )
        ]
    
    # ===== Analysis Methods =====
    
    async def _scan_for_threats(self) -> dict:
        """Scan for security threats and suspicious activity."""
        threats = []
        
        try:
            # Check running processes for suspicious activity
            suspicious_processes = await self._check_suspicious_processes()
            threats.extend(suspicious_processes)
            
            # Check network connections
            network_threats = await self._check_network_security()
            threats.extend(network_threats)
            
            # Check for malware signatures (simplified)
            malware_scan = await self._scan_for_malware()
            threats.extend(malware_scan)
            
        except Exception as e:
            logger.error(f"Threat scan failed: {e}")
            threats.append({
                "type": "scan_error",
                "description": f"Threat scan failed: {str(e)}",
                "severity": "medium"
            })
        
        return {"threats": threats}
    
    async def _check_suspicious_processes(self) -> List[dict]:
        """Check for suspicious running processes."""
        suspicious = []
        
        try:
            # Known suspicious process patterns
            suspicious_patterns = [
                r'.*keylog.*',
                r'.*trojan.*',
                r'.*backdoor.*',
                r'.*cryptominer.*',
                r'.*bitcoin.*',
                r'.*mining.*'
            ]
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_name = proc.info['name'].lower()
                    
                    # Check against suspicious patterns
                    for pattern in suspicious_patterns:
                        if re.match(pattern, proc_name, re.IGNORECASE):
                            suspicious.append({
                                "type": "suspicious_process",
                                "process_name": proc.info['name'],
                                "process_id": proc.info['pid'],
                                "cpu_usage": proc.info['cpu_percent'],
                                "memory_usage": proc.info['memory_percent'],
                                "description": f"Suspicious process detected: {proc.info['name']}",
                                "severity": "critical"
                            })
                    
                    # Check for high resource usage
                    if proc.info['cpu_percent'] > 80 and proc.info['memory_percent'] > 50:
                        suspicious.append({
                            "type": "suspicious_process",
                            "process_name": proc.info['name'],
                            "process_id": proc.info['pid'],
                            "cpu_usage": proc.info['cpu_percent'],
                            "memory_usage": proc.info['memory_percent'],
                            "description": f"Process using high resources: {proc.info['name']}",
                            "severity": "medium"
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Process scan failed: {e}")
        
        return suspicious
    
    async def _check_network_security(self) -> List[dict]:
        """Check network connections for security issues."""
        network_issues = []
        
        try:
            # Check for open ports
            connections = psutil.net_connections(kind='inet')
            
            # Common dangerous ports
            dangerous_ports = [23, 135, 139, 445, 1433, 1521, 3389, 5900]
            
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN:
                    port = conn.laddr.port
                    
                    if port in dangerous_ports:
                        network_issues.append({
                            "type": "open_ports",
                            "port": port,
                            "address": conn.laddr.ip,
                            "description": f"Dangerous port {port} is open",
                            "severity": "high"
                        })
                    
                    # Check for unusual high ports
                    elif port > 10000 and port not in [8000, 8080, 3000, 5000]:
                        network_issues.append({
                            "type": "open_ports", 
                            "port": port,
                            "address": conn.laddr.ip,
                            "description": f"Unusual high port {port} is open",
                            "severity": "medium"
                        })
                        
        except Exception as e:
            logger.error(f"Network scan failed: {e}")
        
        return network_issues
    
    async def _scan_for_malware(self) -> List[dict]:
        """Simple malware detection scan."""
        malware_indicators = []
        
        try:
            # Check common malware locations (simplified)
            suspicious_dirs = [
                os.path.expanduser("~\\AppData\\Roaming"),
                os.path.expanduser("~\\AppData\\Local\\Temp"),
                "C:\\Windows\\Temp"
            ]
            
            for directory in suspicious_dirs:
                if os.path.exists(directory):
                    try:
                        for root, dirs, files in os.walk(directory):
                            for file in files:
                                if file.lower().endswith(('.exe', '.scr', '.bat', '.cmd')):
                                    filepath = os.path.join(root, file)
                                    file_size = os.path.getsize(filepath)
                                    
                                    # Flag unusually large executable files in temp directories
                                    if file_size > 10 * 1024 * 1024:  # 10MB
                                        malware_indicators.append({
                                            "type": "suspicious_file",
                                            "file_path": filepath,
                                            "file_size": file_size,
                                            "description": f"Large executable in temp directory: {file}",
                                            "severity": "medium"
                                        })
                                        
                    except (PermissionError, OSError):
                        continue
                        
        except Exception as e:
            logger.error(f"Malware scan failed: {e}")
        
        return malware_indicators
    
    async def _audit_passwords(self) -> dict:
        """Audit password security (simulated)."""
        issues = []
        
        try:
            # Simulate password strength checking
            # In real implementation, this would integrate with password managers
            
            weak_passwords_found = 3  # Simulated
            reused_passwords_found = 2  # Simulated
            old_passwords_found = 5  # Simulated
            
            if weak_passwords_found > 0:
                issues.append({
                    "type": "weak_password",
                    "count": weak_passwords_found,
                    "description": f"Found {weak_passwords_found} weak passwords",
                    "severity": "high"
                })
            
            if reused_passwords_found > 0:
                issues.append({
                    "type": "password_reuse",
                    "count": reused_passwords_found,
                    "description": f"Found {reused_passwords_found} reused passwords",
                    "severity": "medium"
                })
            
            if old_passwords_found > 0:
                issues.append({
                    "type": "old_password",
                    "count": old_passwords_found,
                    "description": f"Found {old_passwords_found} old passwords (>90 days)",
                    "severity": "low"
                })
                
        except Exception as e:
            logger.error(f"Password audit failed: {e}")
        
        return {"issues": issues}
    
    async def _scan_system_security(self) -> dict:
        """Scan system security configuration."""
        vulnerabilities = []
        
        try:
            # Check Windows security features
            security_checks = [
                ("Windows Defender", self._check_windows_defender()),
                ("Firewall", self._check_firewall_status()),
                ("Updates", self._check_windows_updates()),
                ("UAC", self._check_uac_status())
            ]
            
            for check_name, check_result in security_checks:
                if not check_result.get("enabled", False):
                    vulnerabilities.append({
                        "type": "security_feature_disabled",
                        "feature": check_name,
                        "description": f"{check_name} is disabled or not functioning",
                        "severity": "high"
                    })
                    
        except Exception as e:
            logger.error(f"System security scan failed: {e}")
        
        return {"vulnerabilities": vulnerabilities}
    
    async def _verify_backups(self) -> dict:
        """Verify backup integrity and availability."""
        issues = []
        
        try:
            # Check common backup locations
            backup_locations = [
                os.path.expanduser("~\\Documents\\Backups"),
                "D:\\Backups",
                "E:\\Backups"
            ]
            
            backup_found = False
            for location in backup_locations:
                if os.path.exists(location):
                    backup_found = True
                    
                    # Check if backups are recent (within 7 days)
                    recent_backup = False
                    for root, dirs, files in os.walk(location):
                        for file in files:
                            filepath = os.path.join(root, file)
                            mod_time = os.path.getmtime(filepath)
                            if datetime.now().timestamp() - mod_time < 7 * 24 * 3600:  # 7 days
                                recent_backup = True
                                break
                        if recent_backup:
                            break
                    
                    if not recent_backup:
                        issues.append({
                            "type": "backup_failure",
                            "location": location,
                            "description": "No recent backups found (older than 7 days)",
                            "severity": "medium"
                        })
            
            if not backup_found:
                issues.append({
                    "type": "backup_failure",
                    "description": "No backup system configured",
                    "severity": "high"
                })
                
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
        
        return {"issues": issues}
    
    async def _scan_privacy_threats(self) -> dict:
        """Scan for privacy and tracking threats."""
        threats = []
        
        try:
            # Check browser for tracking cookies and privacy issues
            privacy_issues = await self._check_browser_privacy()
            threats.extend(privacy_issues)
            
            # Check for data collection software
            tracking_software = await self._check_tracking_software()
            threats.extend(tracking_software)
            
        except Exception as e:
            logger.error(f"Privacy scan failed: {e}")
        
        return {"threats": threats}
    
    async def _check_browser_privacy(self) -> List[dict]:
        """Check browser privacy settings."""
        privacy_issues = []
        
        try:
            # Simulate browser privacy checking
            # In real implementation, would check browser data
            
            tracking_cookies = 150  # Simulated
            fingerprinting_scripts = 25  # Simulated
            
            if tracking_cookies > 100:
                privacy_issues.append({
                    "type": "privacy_leak",
                    "subtype": "tracking_cookies",
                    "count": tracking_cookies,
                    "description": f"Found {tracking_cookies} tracking cookies",
                    "severity": "medium"
                })
            
            if fingerprinting_scripts > 10:
                privacy_issues.append({
                    "type": "privacy_leak",
                    "subtype": "fingerprinting",
                    "count": fingerprinting_scripts,
                    "description": f"Found {fingerprinting_scripts} fingerprinting attempts",
                    "severity": "medium"
                })
                
        except Exception as e:
            logger.error(f"Browser privacy check failed: {e}")
        
        return privacy_issues
    
    async def _check_tracking_software(self) -> List[dict]:
        """Check for installed tracking/spyware."""
        tracking_software = []
        
        try:
            # Check for known tracking software patterns
            tracking_patterns = [
                'analytics',
                'tracker',
                'monitor',
                'spy',
                'keylogger'
            ]
            
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    for pattern in tracking_patterns:
                        if pattern in proc_name:
                            tracking_software.append({
                                "type": "privacy_leak",
                                "subtype": "tracking_software",
                                "software_name": proc.info['name'],
                                "description": f"Potential tracking software: {proc.info['name']}",
                                "severity": "high"
                            })
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Tracking software check failed: {e}")
        
        return tracking_software
    
    # ===== Security Check Methods =====
    
    def _check_windows_defender(self) -> dict:
        """Check Windows Defender status."""
        try:
            # Simplified check - in real implementation would use WMI
            return {"enabled": True, "updated": True}
        except:
            return {"enabled": False, "updated": False}
    
    def _check_firewall_status(self) -> dict:
        """Check Windows Firewall status."""
        try:
            # Simplified check
            return {"enabled": True}
        except:
            return {"enabled": False}
    
    def _check_windows_updates(self) -> dict:
        """Check Windows Update status."""
        try:
            # Simplified check
            return {"enabled": True, "pending_updates": 0}
        except:
            return {"enabled": False, "pending_updates": 5}
    
    def _check_uac_status(self) -> dict:
        """Check UAC (User Account Control) status."""
        try:
            # Simplified check
            return {"enabled": True}
        except:
            return {"enabled": False}
    
    # ===== Action Creation Methods =====
    
    def _create_password_actions(self, threat: dict) -> List[dict]:
        """Create actions for password security issues."""
        actions = []
        
        if threat["type"] == "weak_password":
            actions.append({
                "tool": "update_passwords",
                "parameters": {
                    "action": "strengthen_weak",
                    "count": threat.get("count", 1)
                },
                "description": f"Update {threat.get('count', 1)} weak passwords"
            })
        
        return actions
    
    def _create_update_actions(self, threat: dict) -> List[dict]:
        """Create actions for software updates."""
        actions = []
        
        actions.append({
            "tool": "install_updates",
            "parameters": {
                "update_type": "security"
            },
            "description": "Install security updates"
        })
        
        return actions
    
    def _create_process_actions(self, threat: dict) -> List[dict]:
        """Create actions for suspicious processes."""
        actions = []
        
        if threat.get("severity") == "critical":
            actions.append({
                "tool": "terminate_process",
                "parameters": {
                    "process_id": threat.get("process_id"),
                    "process_name": threat.get("process_name")
                },
                "description": f"Terminate suspicious process: {threat.get('process_name')}"
            })
        
        return actions
    
    def _create_network_actions(self, threat: dict) -> List[dict]:
        """Create actions for network security issues."""
        actions = []
        
        if threat["type"] == "open_ports":
            actions.append({
                "tool": "close_ports",
                "parameters": {
                    "port": threat.get("port")
                },
                "description": f"Close potentially dangerous port {threat.get('port')}"
            })
        
        return actions
    
    def _create_backup_actions(self, threat: dict) -> List[dict]:
        """Create actions for backup issues."""
        actions = []
        
        actions.append({
            "tool": "fix_backup",
            "parameters": {
                "issue_type": threat["type"]
            },
            "description": "Configure and verify backup system"
        })
        
        return actions
    
    def _create_privacy_actions(self, threat: dict) -> List[dict]:
        """Create actions for privacy protection."""
        actions = []
        
        if threat.get("subtype") == "tracking_cookies":
            actions.append({
                "tool": "block_tracking",
                "parameters": {
                    "action": "clear_cookies",
                    "cookie_count": threat.get("count", 0)
                },
                "description": f"Clear {threat.get('count', 0)} tracking cookies"
            })
        
        return actions
    
    # ===== Execution Methods =====
    
    async def _execute_update_passwords(self, params: dict) -> dict:
        """Execute password security improvements."""
        action = params.get("action", "strengthen_weak")
        count = params.get("count", 1)
        
        try:
            # This would integrate with password managers
            # For now, simulate password updates
            
            return {
                "success": True,
                "passwords_updated": count,
                "message": f"Updated {count} passwords for better security"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_install_updates(self, params: dict) -> dict:
        """Execute security updates installation."""
        update_type = params.get("update_type", "security")
        
        try:
            # This would trigger actual Windows Update process
            # For now, simulate update installation
            
            updates_installed = 3  # Simulated
            
            return {
                "success": True,
                "updates_installed": updates_installed,
                "message": f"Installed {updates_installed} security updates"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_terminate_process(self, params: dict) -> dict:
        """Execute suspicious process termination."""
        process_id = params.get("process_id")
        process_name = params.get("process_name", "unknown")
        
        try:
            if process_id:
                # Terminate the suspicious process
                proc = psutil.Process(process_id)
                proc.terminate()
                
                return {
                    "success": True,
                    "process_terminated": process_name,
                    "message": f"Terminated suspicious process: {process_name}"
                }
            else:
                return {
                    "success": False,
                    "error": "No process ID provided"
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            return {
                "success": False,
                "error": f"Failed to terminate process: {str(e)}"
            }
    
    async def _execute_close_ports(self, params: dict) -> dict:
        """Execute port closure for security."""
        port = params.get("port")
        
        try:
            # This would use firewall rules to close ports
            # For now, simulate port closure
            
            return {
                "success": True,
                "port_closed": port,
                "message": f"Closed potentially dangerous port {port}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_fix_backup(self, params: dict) -> dict:
        """Execute backup system fixes."""
        issue_type = params.get("issue_type", "general")
        
        try:
            # This would configure backup software
            # For now, simulate backup configuration
            
            return {
                "success": True,
                "backup_configured": True,
                "message": "Backup system configured and verified"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_block_tracking(self, params: dict) -> dict:
        """Execute privacy protection actions."""
        action = params.get("action", "clear_cookies")
        cookie_count = params.get("cookie_count", 0)
        
        try:
            # This would clear browser data and configure privacy settings
            # For now, simulate privacy protection
            
            return {
                "success": True,
                "cookies_cleared": cookie_count,
                "tracking_blocked": True,
                "message": f"Cleared {cookie_count} tracking cookies and enabled privacy protection"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _execute_enable_monitoring(self, params: dict) -> dict:
        """Execute continuous security monitoring."""
        monitoring_type = params.get("monitoring_type", "continuous")
        
        try:
            # Enable continuous security monitoring
            self.last_scan_time = datetime.now()
            
            return {
                "success": True,
                "monitoring_enabled": True,
                "monitoring_type": monitoring_type,
                "message": f"Enabled {monitoring_type} security monitoring"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }