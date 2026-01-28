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
        # Import safely
        from app.agents.sentinel.sentinel_daemon import get_sentinel_daemon
        
        # Get daemon safely
        try:
            daemon = get_sentinel_daemon()
        except Exception as e:
            logger.error(f"[Sentinel] Failed to get daemon: {e}")
            return {
                "running": False,
                "error": f"Daemon initialization failed: {str(e)}",
                "components": {}
            }
        
        # Build minimal safe status
        status = {
            "running": getattr(daemon, 'running', False),
            "clients": len(getattr(daemon, 'clients', set())),
            "active_alerts": len(getattr(daemon, 'active_alerts', {})),
            "metrics_history": len(getattr(daemon, 'metrics_history', [])),
            "process_reputation": len(getattr(daemon, 'process_reputation', {})),
            "last_check": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Test each component individually and safely
        component_tests = [
            ("predictive_analytics", lambda: {
                "enabled": hasattr(daemon, 'predictive_analyzer') and daemon.predictive_analyzer is not None,
                "data_points": {
                    "cpu": len(getattr(daemon.predictive_analyzer, 'prediction_history', {}).get("cpu", [])) if hasattr(daemon, 'predictive_analyzer') and daemon.predictive_analyzer else 0,
                    "memory": len(getattr(daemon.predictive_analyzer, 'prediction_history', {}).get("memory", [])) if hasattr(daemon, 'predictive_analyzer') and daemon.predictive_analyzer else 0,
                    "temperature": len(getattr(daemon.predictive_analyzer, 'prediction_history', {}).get("temperature", [])) if hasattr(daemon, 'predictive_analyzer') and daemon.predictive_analyzer else 0
                }
            }),
            ("gaming_mode", lambda: {
                "enabled": hasattr(daemon, 'gaming_detector') and daemon.gaming_detector is not None
            }),
            ("event_monitor", lambda: {
                "enabled": hasattr(daemon, 'event_monitor') and daemon.event_monitor is not None
            }),
            ("scheduled_maintenance", lambda: {
                "enabled": hasattr(daemon, 'scheduled_maintenance') and daemon.scheduled_maintenance is not None
            })
        ]
        
        for component_name, component_func in component_tests:
            try:
                status["components"][component_name] = component_func()
            except Exception as e:
                logger.debug(f"[Sentinel] Component {component_name} failed: {e}")
                status["components"][component_name] = {"enabled": False, "error": str(e)}
        
        logger.info(f"[Sentinel] Status generated successfully - running: {status['running']}")
        return status
        
    except Exception as e:
        logger.error(f"[Sentinel] Critical status failure: {e}")
        import traceback
        logger.error(f"[Sentinel] Full traceback: {traceback.format_exc()}")
        
        # Return absolute fallback
        return {
            "running": False,
            "error": f"Critical failure: {str(e)}",
            "components": {
                "predictive_analytics": {"enabled": False},
                "gaming_mode": {"enabled": False},
                "event_monitor": {"enabled": False},
                "scheduled_maintenance": {"enabled": False}
            },
            "fallback": True
        }


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
            logger.warning("[Sentinel] Predictive analyzer not available")
            return {"error": "Predictive analyzer not available", "predictions": [], "anomalies": [], "trends": {}}
        
        # Get current metrics
        metrics = await daemon._collect_metrics()
        logger.info(f"[Sentinel] Current metrics: CPU={metrics.cpu_percent}%, RAM={metrics.memory_percent}%, Temp={metrics.temperature}")
        
        # Check if we have enough data for predictions
        has_cpu_data = len(daemon.predictive_analyzer.prediction_history["cpu"]) >= 30
        has_memory_data = len(daemon.predictive_analyzer.prediction_history["memory"]) >= 30
        has_temp_data = len(daemon.predictive_analyzer.prediction_history["temperature"]) >= 30
        
        logger.info(f"[Sentinel] Data availability: CPU={has_cpu_data}, Memory={has_memory_data}, Temp={has_temp_data}")
        
        # Get predictions
        predictions = daemon.predictive_analyzer.predict_resource_exhaustion()
        logger.info(f"[Sentinel] Generated {len(predictions)} predictions")
        
        # Get anomalies
        anomalies = daemon.predictive_analyzer.detect_anomalies(metrics)
        logger.info(f"[Sentinel] Detected {len(anomalies)} anomalies")
        
        # Get trends
        trends = daemon.predictive_analyzer.get_performance_trends()
        
        # If no predictions due to insufficient data, provide mock data for testing
        if not predictions and not has_cpu_data and not has_memory_data:
            logger.warning("[Sentinel] Insufficient historical data, providing mock predictions")
            mock_predictions = [
                {
                    "type": "cpu_exhaustion",
                    "predicted_time": (datetime.utcnow() + timedelta(minutes=45)).isoformat(),
                    "current_value": metrics.cpu_percent,
                    "predicted_value": 95,
                    "trend": 0.5,
                    "confidence": 0.8,
                    "time_to_exhaustion": 2700,
                    "severity": "warning",
                    "mock": True
                },
                {
                    "type": "memory_exhaustion", 
                    "predicted_time": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
                    "current_value": metrics.memory_percent,
                    "predicted_value": 98,
                    "trend": 0.3,
                    "confidence": 0.7,
                    "time_to_exhaustion": 1800,
                    "severity": "warning",
                    "mock": True
                }
            ]
            predictions = mock_predictions
        
        return {
            "predictions": predictions,
            "anomalies": anomalies,
            "trends": trends,
            "data_status": {
                "cpu_data_points": len(daemon.predictive_analyzer.prediction_history["cpu"]),
                "memory_data_points": len(daemon.predictive_analyzer.prediction_history["memory"]),
                "temperature_data_points": len(daemon.predictive_analyzer.prediction_history["temperature"]),
                "daemon_running": daemon.running,
                "current_metrics": {
                    "cpu": metrics.cpu_percent,
                    "memory": metrics.memory_percent,
                    "temperature": metrics.temperature
                }
            }
        }
        
    except Exception as e:
        logger.error(f"[Sentinel] Failed to get predictions: {e}")
        import traceback
        logger.error(f"[Sentinel] Traceback: {traceback.format_exc()}")
        return {"error": str(e), "predictions": [], "anomalies": [], "trends": {}}
