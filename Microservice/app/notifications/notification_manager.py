"""
Enhanced Notification System

Provides comprehensive notification management for the Kernal Agent system.
Supports multiple notification types, channels, and priority levels.

Features:
- Multi-channel delivery (toast, email, webhook, desktop)
- Priority-based queuing and delivery
- Notification templates and customization
- User preference management
- Delivery confirmation and retry logic
- Rich formatting and action buttons
"""

import logging
import asyncio
import json
import os
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5


class NotificationChannel(Enum):
    """Available notification channels."""
    TOAST = "toast"           # Windows toast notifications
    DESKTOP = "desktop"       # Desktop app notifications
    EMAIL = "email"           # Email notifications
    WEBHOOK = "webhook"       # Webhook/API notifications
    VOICE = "voice"          # Voice announcements
    POPUP = "popup"          # Modal popup dialogs


class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


@dataclass
class NotificationAction:
    """Represents an action button in a notification."""
    id: str
    label: str
    action_type: str  # "callback", "url", "command"
    action_data: str  # Callback function, URL, or command
    style: str = "default"  # "default", "primary", "danger"


@dataclass
class NotificationTemplate:
    """Template for creating notifications."""
    template_id: str
    title_template: str
    message_template: str
    icon: Optional[str] = None
    default_priority: NotificationPriority = NotificationPriority.MEDIUM
    default_channels: List[NotificationChannel] = None
    actions: List[NotificationAction] = None
    expiry_minutes: int = 60


@dataclass
class Notification:
    """Represents a notification."""
    notification_id: str
    title: str
    message: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: NotificationStatus = NotificationStatus.PENDING
    agent_name: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    actions: List[NotificationAction] = None
    metadata: Dict[str, Any] = None
    retry_count: int = 0
    max_retries: int = 3
    delivery_attempts: List[Dict] = None


class NotificationManager:
    """Manages notifications across all channels and priorities."""
    
    def __init__(self):
        self.notifications: Dict[str, Notification] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.delivery_queue: List[str] = []
        self.active_channels: Dict[NotificationChannel, bool] = {
            NotificationChannel.TOAST: True,
            NotificationChannel.DESKTOP: True,
            NotificationChannel.EMAIL: False,
            NotificationChannel.WEBHOOK: False,
            NotificationChannel.VOICE: False,
            NotificationChannel.POPUP: True
        }
        self.delivery_handlers: Dict[NotificationChannel, callable] = {}
        self._setup_default_templates()
        self._setup_delivery_handlers()
    
    def _setup_default_templates(self):
        """Setup default notification templates."""
        templates = [
            NotificationTemplate(
                template_id="agent_action_complete",
                title_template="Action Complete - {agent_name}",
                message_template="{agent_name} has completed {action_count} actions: {summary}",
                icon="success",
                default_priority=NotificationPriority.MEDIUM,
                default_channels=[NotificationChannel.TOAST, NotificationChannel.DESKTOP],
                expiry_minutes=30
            ),
            NotificationTemplate(
                template_id="security_threat_detected",
                title_template="Security Alert - {threat_type}",
                message_template="Security threat detected: {threat_description}. Immediate action recommended.",
                icon="warning",
                default_priority=NotificationPriority.CRITICAL,
                default_channels=[NotificationChannel.TOAST, NotificationChannel.POPUP, NotificationChannel.VOICE],
                actions=[
                    NotificationAction(
                        id="fix_now",
                        label="Fix Now",
                        action_type="callback",
                        action_data="handle_security_fix",
                        style="primary"
                    ),
                    NotificationAction(
                        id="dismiss",
                        label="Dismiss",
                        action_type="callback",
                        action_data="dismiss_notification",
                        style="default"
                    )
                ],
                expiry_minutes=120
            ),
            NotificationTemplate(
                template_id="productivity_suggestion",
                title_template="Productivity Tip",
                message_template="Suggestion: {suggestion_text}",
                icon="lightbulb",
                default_priority=NotificationPriority.LOW,
                default_channels=[NotificationChannel.TOAST],
                actions=[
                    NotificationAction(
                        id="apply_suggestion",
                        label="Apply",
                        action_type="callback",
                        action_data="apply_productivity_suggestion",
                        style="primary"
                    )
                ],
                expiry_minutes=180
            ),
            NotificationTemplate(
                template_id="task_reminder",
                title_template="Task Reminder",
                message_template="Reminder: {task_description}",
                icon="clock",
                default_priority=NotificationPriority.MEDIUM,
                default_channels=[NotificationChannel.TOAST, NotificationChannel.VOICE],
                actions=[
                    NotificationAction(
                        id="complete_task",
                        label="Mark Complete",
                        action_type="callback",
                        action_data="complete_task",
                        style="primary"
                    ),
                    NotificationAction(
                        id="snooze",
                        label="Snooze 10min",
                        action_type="callback",
                        action_data="snooze_task",
                        style="default"
                    )
                ],
                expiry_minutes=60
            ),
            NotificationTemplate(
                template_id="system_maintenance",
                title_template="System Maintenance",
                message_template="System maintenance completed: {maintenance_summary}",
                icon="gear",
                default_priority=NotificationPriority.LOW,
                default_channels=[NotificationChannel.DESKTOP],
                expiry_minutes=45
            ),
            NotificationTemplate(
                template_id="focus_session_break",
                title_template="Break Time!",
                message_template="Your {session_duration} minute focus session is complete. Time for a {break_duration} minute break.",
                icon="coffee",
                default_priority=NotificationPriority.HIGH,
                default_channels=[NotificationChannel.POPUP, NotificationChannel.VOICE],
                actions=[
                    NotificationAction(
                        id="start_break",
                        label="Start Break",
                        action_type="callback",
                        action_data="start_break_timer",
                        style="primary"
                    ),
                    NotificationAction(
                        id="continue_working",
                        label="Continue Working",
                        action_type="callback", 
                        action_data="dismiss_notification",
                        style="default"
                    )
                ],
                expiry_minutes=15
            )
        ]
        
        for template in templates:
            self.templates[template.template_id] = template
    
    def _setup_delivery_handlers(self):
        """Setup delivery handlers for each channel."""
        self.delivery_handlers = {
            NotificationChannel.TOAST: self._deliver_toast_notification,
            NotificationChannel.DESKTOP: self._deliver_desktop_notification,
            NotificationChannel.EMAIL: self._deliver_email_notification,
            NotificationChannel.WEBHOOK: self._deliver_webhook_notification,
            NotificationChannel.VOICE: self._deliver_voice_notification,
            NotificationChannel.POPUP: self._deliver_popup_notification
        }
    
    async def create_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        channels: Optional[List[NotificationChannel]] = None,
        agent_name: Optional[str] = None,
        category: Optional[str] = None,
        actions: Optional[List[NotificationAction]] = None,
        expires_in_minutes: int = 60,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new notification."""
        notification_id = str(uuid.uuid4())
        
        # Use default channels based on priority if not specified
        if channels is None:
            channels = self._get_default_channels_for_priority(priority)
        
        # Filter channels based on user preferences and availability
        active_channels = [ch for ch in channels if self.active_channels.get(ch, False)]
        
        notification = Notification(
            notification_id=notification_id,
            title=title,
            message=message,
            priority=priority,
            channels=active_channels,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=expires_in_minutes),
            agent_name=agent_name,
            category=category,
            actions=actions or [],
            metadata=metadata or {},
            delivery_attempts=[]
        )
        
        self.notifications[notification_id] = notification
        await self._queue_notification(notification_id)
        
        logger.info(f"Created notification {notification_id}: {title}")
        return notification_id
    
    async def create_from_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        priority_override: Optional[NotificationPriority] = None,
        channels_override: Optional[List[NotificationChannel]] = None
    ) -> str:
        """Create a notification from a template."""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        
        # Substitute variables in title and message
        title = template.title_template.format(**variables)
        message = template.message_template.format(**variables)
        
        priority = priority_override or template.default_priority
        channels = channels_override or template.default_channels or []
        
        return await self.create_notification(
            title=title,
            message=message,
            priority=priority,
            channels=channels,
            agent_name=variables.get("agent_name"),
            category=variables.get("category"),
            actions=template.actions,
            expires_in_minutes=template.expiry_minutes,
            metadata=variables
        )
    
    async def _queue_notification(self, notification_id: str):
        """Queue notification for delivery."""
        notification = self.notifications[notification_id]
        
        # Insert into queue based on priority
        if notification.priority == NotificationPriority.URGENT:
            self.delivery_queue.insert(0, notification_id)
        elif notification.priority == NotificationPriority.CRITICAL:
            # Find position after other urgent notifications
            insert_pos = 0
            for i, queued_id in enumerate(self.delivery_queue):
                queued_notif = self.notifications[queued_id]
                if queued_notif.priority != NotificationPriority.URGENT:
                    insert_pos = i
                    break
            else:
                insert_pos = len(self.delivery_queue)
            self.delivery_queue.insert(insert_pos, notification_id)
        else:
            self.delivery_queue.append(notification_id)
        
        # Process queue
        await self._process_delivery_queue()
    
    async def _process_delivery_queue(self):
        """Process notifications in the delivery queue."""
        while self.delivery_queue:
            notification_id = self.delivery_queue[0]
            
            if notification_id not in self.notifications:
                self.delivery_queue.pop(0)
                continue
            
            notification = self.notifications[notification_id]
            
            # Check if notification has expired
            if notification.expires_at and datetime.now() > notification.expires_at:
                notification.status = NotificationStatus.EXPIRED
                self.delivery_queue.pop(0)
                logger.info(f"Notification {notification_id} expired")
                continue
            
            # Attempt delivery
            delivery_success = await self._deliver_notification(notification)
            
            if delivery_success:
                notification.status = NotificationStatus.SENT
                self.delivery_queue.pop(0)
                logger.info(f"Notification {notification_id} delivered successfully")
            else:
                notification.retry_count += 1
                
                if notification.retry_count >= notification.max_retries:
                    notification.status = NotificationStatus.FAILED
                    self.delivery_queue.pop(0)
                    logger.error(f"Notification {notification_id} failed after {notification.max_retries} attempts")
                else:
                    # Move to end of queue for retry
                    self.delivery_queue.pop(0)
                    self.delivery_queue.append(notification_id)
                    logger.warning(f"Notification {notification_id} delivery failed, will retry ({notification.retry_count}/{notification.max_retries})")
                    
                    # Wait before processing next notification to avoid spam
                    await asyncio.sleep(2)
            
            # Small delay between deliveries
            await asyncio.sleep(0.1)
    
    async def _deliver_notification(self, notification: Notification) -> bool:
        """Deliver a notification to all its channels."""
        delivery_results = []
        
        for channel in notification.channels:
            if channel in self.delivery_handlers:
                try:
                    result = await self.delivery_handlers[channel](notification)
                    delivery_results.append(result)
                    
                    # Record delivery attempt
                    attempt = {
                        "channel": channel.value,
                        "timestamp": datetime.now().isoformat(),
                        "success": result,
                        "attempt_number": notification.retry_count + 1
                    }
                    notification.delivery_attempts.append(attempt)
                    
                except Exception as e:
                    logger.error(f"Delivery failed for channel {channel.value}: {e}")
                    delivery_results.append(False)
        
        # Return True if at least one channel delivered successfully
        return any(delivery_results)
    
    def _get_default_channels_for_priority(self, priority: NotificationPriority) -> List[NotificationChannel]:
        """Get default channels based on notification priority."""
        if priority == NotificationPriority.URGENT:
            return [NotificationChannel.POPUP, NotificationChannel.VOICE, NotificationChannel.TOAST]
        elif priority == NotificationPriority.CRITICAL:
            return [NotificationChannel.POPUP, NotificationChannel.TOAST]
        elif priority == NotificationPriority.HIGH:
            return [NotificationChannel.TOAST, NotificationChannel.DESKTOP]
        elif priority == NotificationPriority.MEDIUM:
            return [NotificationChannel.TOAST]
        else:  # LOW
            return [NotificationChannel.DESKTOP]
    
    # ===== Delivery Handler Methods =====
    
    async def _deliver_toast_notification(self, notification: Notification) -> bool:
        """Deliver notification via Windows toast."""
        try:
            # This would integrate with Windows toast notification API
            # For now, simulate toast delivery
            
            toast_data = {
                "title": notification.title,
                "message": notification.message,
                "icon": notification.icon,
                "actions": [asdict(action) for action in notification.actions] if notification.actions else []
            }
            
            logger.info(f"Toast notification delivered: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Toast delivery failed: {e}")
            return False
    
    async def _deliver_desktop_notification(self, notification: Notification) -> bool:
        """Deliver notification to desktop app."""
        try:
            # This would send notification to desktop app via WebSocket or API
            # For now, simulate desktop delivery
            
            desktop_data = {
                "notification_id": notification.notification_id,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "agent_name": notification.agent_name,
                "actions": [asdict(action) for action in notification.actions] if notification.actions else []
            }
            
            logger.info(f"Desktop notification delivered: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Desktop delivery failed: {e}")
            return False
    
    async def _deliver_email_notification(self, notification: Notification) -> bool:
        """Deliver notification via email."""
        try:
            # This would integrate with email service (SMTP, SendGrid, etc.)
            # For now, simulate email delivery
            
            logger.info(f"Email notification delivered: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            return False
    
    async def _deliver_webhook_notification(self, notification: Notification) -> bool:
        """Deliver notification via webhook."""
        try:
            # This would send HTTP POST to configured webhook URLs
            # For now, simulate webhook delivery
            
            webhook_payload = {
                "notification_id": notification.notification_id,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "timestamp": notification.created_at.isoformat(),
                "agent_name": notification.agent_name,
                "metadata": notification.metadata
            }
            
            logger.info(f"Webhook notification delivered: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")
            return False
    
    async def _deliver_voice_notification(self, notification: Notification) -> bool:
        """Deliver notification via voice announcement."""
        try:
            # This would integrate with text-to-speech system
            # For now, simulate voice delivery
            
            voice_text = f"{notification.title}. {notification.message}"
            
            logger.info(f"Voice notification delivered: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Voice delivery failed: {e}")
            return False
    
    async def _deliver_popup_notification(self, notification: Notification) -> bool:
        """Deliver notification as popup dialog."""
        try:
            # This would show popup dialog in desktop app
            # For now, simulate popup delivery
            
            popup_data = {
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "actions": [asdict(action) for action in notification.actions] if notification.actions else [],
                "modal": notification.priority.value >= NotificationPriority.CRITICAL.value
            }
            
            logger.info(f"Popup notification delivered: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Popup delivery failed: {e}")
            return False
    
    # ===== Management Methods =====
    
    def dismiss_notification(self, notification_id: str) -> bool:
        """Dismiss a notification."""
        if notification_id in self.notifications:
            self.notifications[notification_id].status = NotificationStatus.DISMISSED
            
            # Remove from queue if still pending
            if notification_id in self.delivery_queue:
                self.delivery_queue.remove(notification_id)
            
            logger.info(f"Notification {notification_id} dismissed")
            return True
        return False
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        return self.notifications.get(notification_id)
    
    def get_active_notifications(self) -> List[Notification]:
        """Get all active (not dismissed/expired/failed) notifications."""
        active_statuses = [NotificationStatus.PENDING, NotificationStatus.SENT, NotificationStatus.DELIVERED]
        return [
            notif for notif in self.notifications.values()
            if notif.status in active_statuses and (
                notif.expires_at is None or datetime.now() < notif.expires_at
            )
        ]
    
    def get_notifications_by_agent(self, agent_name: str) -> List[Notification]:
        """Get notifications from a specific agent."""
        return [
            notif for notif in self.notifications.values()
            if notif.agent_name == agent_name
        ]
    
    def set_channel_active(self, channel: NotificationChannel, active: bool):
        """Enable or disable a notification channel."""
        self.active_channels[channel] = active
        logger.info(f"Channel {channel.value} set to {'active' if active else 'inactive'}")
    
    def update_user_preferences(self, preferences: Dict[str, Any]):
        """Update user notification preferences."""
        self.user_preferences.update(preferences)
        
        # Apply preferences to channel settings
        if "channels" in preferences:
            for channel_name, enabled in preferences["channels"].items():
                try:
                    channel = NotificationChannel(channel_name)
                    self.set_channel_active(channel, enabled)
                except ValueError:
                    logger.warning(f"Unknown channel in preferences: {channel_name}")
    
    def add_template(self, template: NotificationTemplate):
        """Add a new notification template."""
        self.templates[template.template_id] = template
        logger.info(f"Added notification template: {template.template_id}")
    
    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get a notification template by ID."""
        return self.templates.get(template_id)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics."""
        total_notifications = len(self.notifications)
        active_notifications = len(self.get_active_notifications())
        pending_in_queue = len(self.delivery_queue)
        
        status_counts = {}
        for status in NotificationStatus:
            count = sum(1 for notif in self.notifications.values() if notif.status == status)
            status_counts[status.value] = count
        
        return {
            "total_notifications": total_notifications,
            "active_notifications": active_notifications,
            "pending_in_queue": pending_in_queue,
            "status_counts": status_counts,
            "active_channels": {ch.value: active for ch, active in self.active_channels.items()}
        }


# Global notification manager instance
_notification_manager = None


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


async def notify(
    title: str,
    message: str,
    priority: NotificationPriority = NotificationPriority.MEDIUM,
    agent_name: Optional[str] = None,
    **kwargs
) -> str:
    """Quick function to create and send a notification."""
    manager = get_notification_manager()
    return await manager.create_notification(
        title=title,
        message=message,
        priority=priority,
        agent_name=agent_name,
        **kwargs
    )


async def notify_from_template(template_id: str, variables: Dict[str, Any]) -> str:
    """Quick function to create and send a notification from template."""
    manager = get_notification_manager()
    return await manager.create_from_template(template_id, variables)