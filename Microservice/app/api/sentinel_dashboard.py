"""
Resource history dashboard API for Sentinel.

Provides endpoints for viewing system metrics history.
"""

from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/sentinel/metrics/history")
async def get_metrics_history(
    hours: int = Query(default=24, description="Hours of history to retrieve"),
    metric: str = Query(default="all", description="Metric type: cpu, memory, temperature, disk, network, or all"),
    user_id: str = Query(default="default", description="User ID for filtering")
):
    """Get historical metrics data."""
    try:
        from app.agents.sentinel.sentinel_daemon import get_sentinel_daemon
        
        daemon = get_sentinel_daemon()
        
        # Get history from daemon
        history = list(daemon.metrics_history)
        
        # Filter by time
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_history = [
            m for m in history 
            if m.timestamp >= cutoff_time
        ]
        
        # Format response
        result = {
            "user_id": user_id,
            "metric": metric,
            "hours": hours,
            "data_points": len(filtered_history),
            "data": []
        }
        
        for metrics in filtered_history:
            point = {
                "timestamp": metrics.timestamp.isoformat(),
                "cpu": metrics.cpu_percent,
                "memory": metrics.memory_percent,
                "temperature": metrics.temperature,
                "disk_usage": metrics.disk_usage,
                "network_io": metrics.network_io
            }
            
            # Filter by specific metric if requested
            if metric != "all":
                point = {k: v for k, v in point.items() if k == metric or k == "timestamp"}
            
            result["data"].append(point)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get metrics history: {e}")
        return {"error": str(e), "data": []}


@router.get("/api/sentinel/alerts/history")
async def get_alerts_history(
    hours: int = Query(default=24, description="Hours of alerts to retrieve"),
    severity: str = Query(default="all", description="Filter by severity: warning, critical, or all"),
    user_id: str = Query(default="default", description="User ID for filtering")
):
    """Get historical alerts."""
    try:
        from app.agents.sentinel.sentinel_daemon import get_sentinel_daemon
        
        daemon = get_sentinel_daemon()
        
        # Get alerts from daemon
        alerts = list(daemon.active_alerts.values())
        
        # Filter by time and severity
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_alerts = [
            alert for alert in alerts 
            if alert.timestamp >= cutoff_time
            and (severity == "all" or alert.severity == severity)
        ]
        
        # Sort by timestamp
        filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Format response
        result = {
            "user_id": user_id,
            "hours": hours,
            "severity": severity,
            "total_alerts": len(filtered_alerts),
            "alerts": []
        }
        
        for alert in filtered_alerts:
            alert_data = {
                "id": alert.id,
                "type": alert.type,
                "severity": alert.severity,
                "message": alert.message,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat(),
                "suggestions": alert.suggestions,
                "processes": alert.processes
            }
            
            result["alerts"].append(alert_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get alerts history: {e}")
        return {"error": str(e), "alerts": []}


@router.get("/api/sentinel/status")
async def get_sentinel_status():
    """Get current Sentinel daemon status."""
    try:
        from app.agents.sentinel.sentinel_daemon import get_sentinel_daemon
        
        daemon = get_sentinel_daemon()
        
        # Get basic status
        status = daemon.get_status()
        
        # Add gaming mode status if available
        if daemon.gaming_detector:
            status["gaming_mode"] = daemon.gaming_detector.get_gaming_status()
        
        # Add predictive analytics status if available
        if daemon.predictive_analyzer:
            status["predictive_analytics"] = {
                "enabled": True,
                "trends": daemon.predictive_analyzer.get_performance_trends()
            }
        
        # Add event monitor status if available
        if daemon.event_monitor:
            try:
                status["event_monitor"] = {
                    "enabled": True,
                    "recent_events": daemon.event_monitor.get_recent_events(hours=1)
                }
            except:
                status["event_monitor"] = {"enabled": True, "recent_events": []}
        
        # Add maintenance status if available
        if daemon.scheduled_maintenance:
            status["scheduled_maintenance"] = daemon.scheduled_maintenance.get_maintenance_status()
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get Sentinel status: {e}")
        return {"error": str(e), "running": False}


@router.post("/api/sentinel/gaming/process")
async def add_gaming_process(
    process_name: str = Query(..., description="Process name to add to gaming list")
):
    """Add a custom gaming process."""
    try:
        from app.agents.sentinel.sentinel_daemon import get_sentinel_daemon
        
        daemon = get_sentinel_daemon()
        
        if daemon.gaming_detector:
            daemon.gaming_detector.add_gaming_process(process_name)
            return {"success": True, "message": f"Added {process_name} to gaming processes"}
        else:
            return {"success": False, "error": "Gaming detector not available"}
            
    except Exception as e:
        logger.error(f"Failed to add gaming process: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/api/sentinel/gaming/process")
async def remove_gaming_process(
    process_name: str = Query(..., description="Process name to remove from gaming list")
):
    """Remove a gaming process."""
    try:
        from app.agents.sentinel.sentinel_daemon import get_sentinel_daemon
        
        daemon = get_sentinel_daemon()
        
        if daemon.gaming_detector:
            daemon.gaming_detector.remove_gaming_process(process_name)
            return {"success": True, "message": f"Removed {process_name} from gaming processes"}
        else:
            return {"success": False, "error": "Gaming detector not available"}
            
    except Exception as e:
        logger.error(f"Failed to remove gaming process: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/sentinel/predictions")
async def get_predictions():
    """Get current resource exhaustion predictions."""
    try:
        from app.agents.sentinel.sentinel_daemon import get_sentinel_daemon
        
        daemon = get_sentinel_daemon()
        
        if not daemon.predictive_analyzer:
            return {"error": "Predictive analyzer not available"}
        
        # Get current metrics
        metrics = await daemon._collect_metrics()
        
        # Get predictions
        predictions = daemon.predictive_analyzer.predict_resource_exhaustion()
        
        # Get anomalies
        anomalies = daemon.predictive_analyzer.detect_anomalies(metrics)
        
        return {
            "predictions": predictions,
            "anomalies": anomalies,
            "trends": daemon.predictive_analyzer.get_performance_trends()
        }
        
    except Exception as e:
        logger.error(f"Failed to get predictions: {e}")
        return {"error": str(e), "predictions": [], "anomalies": []}
