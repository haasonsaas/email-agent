"""Performance monitoring and optimization for Email Agent."""

import logging
import time
import asyncio
import psutil
import gc
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Tracks and manages performance metrics."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics = defaultdict(lambda: deque(maxlen=max_history))
        self.counters = defaultdict(int)
        self.timers = {}
        self.start_time = datetime.now()
    
    def record_metric(self, name: str, value: float, timestamp: Optional[datetime] = None):
        """Record a performance metric."""
        timestamp = timestamp or datetime.now()
        self.metrics[name].append({
            "value": value,
            "timestamp": timestamp
        })
    
    def increment_counter(self, name: str, amount: int = 1):
        """Increment a counter metric."""
        self.counters[name] += amount
    
    def get_metric_stats(self, name: str, window_minutes: int = 60) -> Dict[str, Any]:
        """Get statistics for a metric within a time window."""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        values = [
            entry["value"] for entry in self.metrics[name]
            if entry["timestamp"] >= cutoff
        ]
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else None,
            "window_minutes": window_minutes
        }
    
    def get_counter_value(self, name: str) -> int:
        """Get current counter value."""
        return self.counters[name]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics summary."""
        return {
            "counters": dict(self.counters),
            "recent_metrics": {
                name: self.get_metric_stats(name, 10)  # Last 10 minutes
                for name in self.metrics.keys()
            },
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        }


class PerformanceMonitor:
    """Comprehensive performance monitoring system."""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.monitoring_active = False
        self.monitoring_task = None
        self.alert_thresholds = {
            "memory_usage_percent": 80.0,
            "cpu_usage_percent": 85.0,
            "response_time_ms": 5000.0,
            "error_rate_percent": 10.0
        }
        self.optimization_suggestions = []
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous performance monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Performance monitoring started (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self):
        """Stop performance monitoring."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._collect_system_metrics()
                await self._check_alerts()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(interval_seconds)
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.record_metric("cpu_usage_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.metrics.record_metric("memory_usage_percent", memory.percent)
            self.metrics.record_metric("memory_used_mb", memory.used / 1024 / 1024)
            self.metrics.record_metric("memory_available_mb", memory.available / 1024 / 1024)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.metrics.record_metric("disk_usage_percent", (disk.used / disk.total) * 100)
            
            # Process-specific metrics
            process = psutil.Process()
            self.metrics.record_metric("process_cpu_percent", process.cpu_percent())
            self.metrics.record_metric("process_memory_mb", process.memory_info().rss / 1024 / 1024)
            self.metrics.record_metric("process_threads", process.num_threads())
            
            # Python-specific metrics
            self.metrics.record_metric("gc_objects", len(gc.get_objects()))
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {str(e)}")
    
    async def _check_alerts(self):
        """Check for performance alerts."""
        alerts = []
        
        for metric_name, threshold in self.alert_thresholds.items():
            stats = self.metrics.get_metric_stats(metric_name, 5)  # Last 5 minutes
            if stats and stats.get("avg", 0) > threshold:
                alerts.append({
                    "metric": metric_name,
                    "current_value": stats["avg"],
                    "threshold": threshold,
                    "severity": "warning" if stats["avg"] < threshold * 1.2 else "critical"
                })
        
        if alerts:
            await self._handle_alerts(alerts)
    
    async def _handle_alerts(self, alerts: List[Dict[str, Any]]):
        """Handle performance alerts."""
        for alert in alerts:
            logger.warning(
                f"Performance alert: {alert['metric']} = {alert['current_value']:.2f} "
                f"(threshold: {alert['threshold']:.2f})"
            )
            
            # Generate optimization suggestions
            await self._generate_optimization_suggestions(alert)
    
    async def _generate_optimization_suggestions(self, alert: Dict[str, Any]):
        """Generate optimization suggestions based on alerts."""
        metric = alert["metric"]
        suggestions = []
        
        if metric == "memory_usage_percent":
            suggestions.extend([
                "Consider reducing email batch sizes",
                "Implement email caching with LRU eviction",
                "Run garbage collection more frequently",
                "Optimize email model memory usage"
            ])
        elif metric == "cpu_usage_percent":
            suggestions.extend([
                "Reduce AI processing frequency",
                "Implement async processing for heavy operations",
                "Consider caching AI results",
                "Optimize database queries"
            ])
        elif metric == "response_time_ms":
            suggestions.extend([
                "Implement response caching",
                "Optimize database indexing",
                "Reduce AI model complexity",
                "Use connection pooling"
            ])
        
        # Add unique suggestions
        for suggestion in suggestions:
            if suggestion not in self.optimization_suggestions:
                self.optimization_suggestions.append(suggestion)
                logger.info(f"Optimization suggestion: {suggestion}")
    
    def time_operation(self, operation_name: str):
        """Decorator to time operations."""
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        self.metrics.increment_counter(f"{operation_name}_success")
                        return result
                    except Exception as e:
                        self.metrics.increment_counter(f"{operation_name}_error")
                        raise
                    finally:
                        duration_ms = (time.time() - start_time) * 1000
                        self.metrics.record_metric(f"{operation_name}_duration_ms", duration_ms)
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        self.metrics.increment_counter(f"{operation_name}_success")
                        return result
                    except Exception as e:
                        self.metrics.increment_counter(f"{operation_name}_error")
                        raise
                    finally:
                        duration_ms = (time.time() - start_time) * 1000
                        self.metrics.record_metric(f"{operation_name}_duration_ms", duration_ms)
                return sync_wrapper
        return decorator
    
    @asynccontextmanager
    async def measure_operation(self, operation_name: str):
        """Context manager to measure operation performance."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            yield
            self.metrics.increment_counter(f"{operation_name}_success")
        except Exception as e:
            self.metrics.increment_counter(f"{operation_name}_error")
            raise
        finally:
            # Record duration
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_metric(f"{operation_name}_duration_ms", duration_ms)
            
            # Record memory delta
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_delta = end_memory - start_memory
            self.metrics.record_metric(f"{operation_name}_memory_delta_mb", memory_delta)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        all_metrics = self.metrics.get_all_metrics()
        
        # Calculate key performance indicators
        kpis = {}
        
        # Response times
        for metric_name in self.metrics.metrics.keys():
            if "duration_ms" in metric_name:
                stats = self.metrics.get_metric_stats(metric_name, 60)
                if stats:
                    kpis[f"{metric_name}_avg"] = stats["avg"]
        
        # Error rates
        for counter_name in self.metrics.counters.keys():
            if "error" in counter_name:
                operation = counter_name.replace("_error", "")
                total_ops = (
                    self.metrics.get_counter_value(f"{operation}_success") +
                    self.metrics.get_counter_value(f"{operation}_error")
                )
                if total_ops > 0:
                    error_rate = (self.metrics.get_counter_value(counter_name) / total_ops) * 100
                    kpis[f"{operation}_error_rate_percent"] = error_rate
        
        # System health score (0-100)
        health_score = self._calculate_health_score()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_score": health_score,
            "kpis": kpis,
            "system_metrics": all_metrics,
            "alerts": self._get_current_alerts(),
            "optimization_suggestions": self.optimization_suggestions[-10:],  # Last 10
            "monitoring_status": "active" if self.monitoring_active else "inactive"
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        scores = []
        
        # CPU health (inverse of usage)
        cpu_stats = self.metrics.get_metric_stats("cpu_usage_percent", 10)
        if cpu_stats:
            cpu_score = max(0, 100 - cpu_stats["avg"])
            scores.append(cpu_score)
        
        # Memory health
        memory_stats = self.metrics.get_metric_stats("memory_usage_percent", 10)
        if memory_stats:
            memory_score = max(0, 100 - memory_stats["avg"])
            scores.append(memory_score)
        
        # Error rate health
        total_operations = sum(
            count for name, count in self.metrics.counters.items()
            if "success" in name or "error" in name
        )
        
        if total_operations > 0:
            total_errors = sum(
                count for name, count in self.metrics.counters.items()
                if "error" in name
            )
            error_rate = (total_errors / total_operations) * 100
            error_score = max(0, 100 - (error_rate * 10))  # Penalize errors heavily
            scores.append(error_score)
        
        return sum(scores) / len(scores) if scores else 100.0
    
    def _get_current_alerts(self) -> List[Dict[str, Any]]:
        """Get current active alerts."""
        alerts = []
        
        for metric_name, threshold in self.alert_thresholds.items():
            stats = self.metrics.get_metric_stats(metric_name, 5)
            if stats and stats.get("avg", 0) > threshold:
                alerts.append({
                    "metric": metric_name,
                    "current_value": stats["avg"],
                    "threshold": threshold,
                    "status": "active"
                })
        
        return alerts
    
    def optimize_memory(self):
        """Perform memory optimization."""
        logger.info("Running memory optimization...")
        
        # Force garbage collection
        before_objects = len(gc.get_objects())
        gc.collect()
        after_objects = len(gc.get_objects())
        
        objects_freed = before_objects - after_objects
        logger.info(f"Memory optimization completed: {objects_freed} objects freed")
        
        self.metrics.record_metric("memory_optimization_objects_freed", objects_freed)
        return objects_freed
    
    async def run_performance_test(self, test_name: str, test_func: Callable, 
                                 iterations: int = 100) -> Dict[str, Any]:
        """Run performance test and collect metrics."""
        logger.info(f"Running performance test: {test_name} ({iterations} iterations)")
        
        durations = []
        errors = 0
        
        for i in range(iterations):
            try:
                start_time = time.time()
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
                duration = (time.time() - start_time) * 1000
                durations.append(duration)
            except Exception as e:
                errors += 1
                logger.error(f"Test iteration {i} failed: {str(e)}")
        
        if durations:
            results = {
                "test_name": test_name,
                "iterations": iterations,
                "successful_iterations": len(durations),
                "errors": errors,
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "success_rate": (len(durations) / iterations) * 100
            }
        else:
            results = {
                "test_name": test_name,
                "iterations": iterations,
                "successful_iterations": 0,
                "errors": errors,
                "success_rate": 0
            }
        
        logger.info(f"Performance test completed: {results}")
        return results


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str):
    """Decorator for monitoring function performance."""
    return performance_monitor.time_operation(operation_name)


async def start_performance_monitoring():
    """Start global performance monitoring."""
    await performance_monitor.start_monitoring()


async def stop_performance_monitoring():
    """Stop global performance monitoring."""
    await performance_monitor.stop_monitoring()


def get_performance_report() -> Dict[str, Any]:
    """Get global performance report."""
    return performance_monitor.get_performance_report()
