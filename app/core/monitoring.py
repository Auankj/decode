"""
Production monitoring and metrics collection for Cookie Licking Detector.
Includes Prometheus metrics, health checks, and performance monitoring.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, List, Optional
from contextlib import asynccontextmanager

import psutil
from prometheus_client import (
    Counter, Histogram, Gauge, Info, CollectorRegistry, 
    multiprocess, generate_latest, CONTENT_TYPE_LATEST
)
from fastapi import Request, Response
import redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger, PerformanceTimer
from app.db.database import get_async_session

settings = get_settings()
logger = get_logger(__name__)

# Prometheus metrics registry
if settings.ENABLE_METRICS:
    registry = CollectorRegistry()
    
    # Set up multiprocess collector with proper directory
    import os
    prometheus_multiproc_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'prometheus_multiproc')
    
    # Ensure the directory exists and is accessible
    if not os.path.exists(prometheus_multiproc_dir):
        os.makedirs(prometheus_multiproc_dir, exist_ok=True)
    
    # Set environment variable for multiprocess collector
    os.environ['PROMETHEUS_MULTIPROC_DIR'] = prometheus_multiproc_dir
    
    # Try to enable multiprocess collector
    try:
        if os.path.isdir(prometheus_multiproc_dir) and os.access(prometheus_multiproc_dir, os.W_OK):
            multiprocess.MultiProcessCollector(registry)
            logger.info(f"Multiprocess Prometheus collector enabled using {prometheus_multiproc_dir}")
        else:
            raise Exception(f"Directory {prometheus_multiproc_dir} is not writable")
    except Exception as e:
        logger.info(f"Using single-process Prometheus metrics: {e}")

    # Application metrics
    REQUEST_COUNT = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status_code'],
        registry=registry
    )

    REQUEST_DURATION = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint'],
        registry=registry
    )

    ACTIVE_CONNECTIONS = Gauge(
        'active_connections',
        'Number of active connections',
        registry=registry
    )

    DATABASE_CONNECTIONS = Gauge(
        'database_connections_active',
        'Number of active database connections',
        registry=registry
    )

    REDIS_CONNECTIONS = Gauge(
        'redis_connections_active',
        'Number of active Redis connections',
        registry=registry
    )

    CELERY_TASK_COUNT = Counter(
        'celery_tasks_total',
        'Total Celery tasks executed',
        ['task_name', 'status'],
        registry=registry
    )

    CELERY_TASK_DURATION = Histogram(
        'celery_task_duration_seconds',
        'Celery task execution duration in seconds',
        ['task_name'],
        registry=registry
    )

    QUEUE_SIZE = Gauge(
        'queue_size',
        'Size of message queues',
        ['queue_name'],
        registry=registry
    )

    # Business metrics
    CLAIMS_DETECTED = Counter(
        'claims_detected_total',
        'Total claims detected',
        ['confidence_level'],
        registry=registry
    )

    NOTIFICATIONS_SENT = Counter(
        'notifications_sent_total',
        'Total notifications sent',
        ['type', 'status'],
        registry=registry
    )

    GITHUB_API_CALLS = Counter(
        'github_api_calls_total',
        'Total GitHub API calls',
        ['endpoint', 'status_code'],
        registry=registry
    )

    ECOSYSTEMS_API_CALLS = Counter(
        'ecosystems_api_calls_total',
        'Total Ecosyste.ms API calls',
        ['endpoint', 'status_code'],
        registry=registry
    )

    # System metrics
    SYSTEM_INFO = Info(
        'system_info',
        'System information',
        registry=registry
    )

    CPU_USAGE = Gauge(
        'cpu_usage_percent',
        'CPU usage percentage',
        registry=registry
    )

    MEMORY_USAGE = Gauge(
        'memory_usage_bytes',
        'Memory usage in bytes',
        registry=registry
    )

    DISK_USAGE = Gauge(
        'disk_usage_bytes',
        'Disk usage in bytes',
        ['device'],
        registry=registry
    )

else:
    # Dummy objects when metrics are disabled
    class DummyMetric:
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass

    REQUEST_COUNT = DummyMetric()
    REQUEST_DURATION = DummyMetric()
    ACTIVE_CONNECTIONS = DummyMetric()
    DATABASE_CONNECTIONS = DummyMetric()
    REDIS_CONNECTIONS = DummyMetric()
    CELERY_TASK_COUNT = DummyMetric()
    CELERY_TASK_DURATION = DummyMetric()
    QUEUE_SIZE = DummyMetric()
    CLAIMS_DETECTED = DummyMetric()
    NOTIFICATIONS_SENT = DummyMetric()
    GITHUB_API_CALLS = DummyMetric()
    ECOSYSTEMS_API_CALLS = DummyMetric()
    SYSTEM_INFO = DummyMetric()
    CPU_USAGE = DummyMetric()
    MEMORY_USAGE = DummyMetric()
    DISK_USAGE = DummyMetric()


class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self._redis_client: Optional[redis.Redis] = None
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function."""
        self.checks[name] = check_func
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            async_session_gen = get_async_session()
            session = await anext(async_session_gen)
            
            try:
                result = await session.execute(text("SELECT 1"))
                row = result.fetchone()
                duration = time.time() - start_time
                
                if row and row[0] == 1:
                    return {
                        'status': 'healthy',
                        'response_time_ms': duration * 1000,
                        'message': 'Database connection successful'
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'message': 'Database query returned unexpected result'
                    }
            finally:
                await session.close()
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': f'Database connection failed: {str(e)}'
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            if not self._redis_client:
                self._redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True
                )
            
            start_time = time.time()
            pong = self._redis_client.ping()
            duration = time.time() - start_time
            
            if pong:
                return {
                    'status': 'healthy',
                    'response_time_ms': duration * 1000,
                    'message': 'Redis connection successful'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'Redis ping failed'
                }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': f'Redis connection failed: {str(e)}'
            }
    
    async def check_github_api(self) -> Dict[str, Any]:
        """Check GitHub API connectivity."""
        try:
            import httpx
            
            start_time = time.time()
            headers = {
                "User-Agent": "Cookie-Licking-Detector/1.0",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Add auth header only if token is available
            if settings.GITHUB_TOKEN:
                headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/rate_limit",
                    headers=headers,
                    timeout=settings.HEALTH_CHECK_TIMEOUT
                )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                auth_status = "authenticated" if settings.GITHUB_TOKEN else "unauthenticated"
                return {
                    'status': 'healthy',
                    'response_time_ms': duration * 1000,
                    'rate_limit_remaining': data.get('rate', {}).get('remaining'),
                    'message': f'GitHub API accessible ({auth_status})'
                }
            elif response.status_code == 401 and not settings.GITHUB_TOKEN:
                # 401 is expected without auth token, but API is still reachable
                return {
                    'status': 'healthy',
                    'response_time_ms': duration * 1000,
                    'message': 'GitHub API accessible (unauthenticated)'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': f'GitHub API returned status {response.status_code}'
                }
        except Exception as e:
            logger.error(f"GitHub API health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': f'GitHub API check failed: {str(e)}'
            }
    
    async def check_ecosystems_api(self) -> Dict[str, Any]:
        """Check Ecosyste.ms API connectivity."""
        try:
            import httpx
            
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                # Use the main ecosyste.ms site for health check instead of API endpoint
                response = await client.get(
                    "https://ecosyste.ms",
                    timeout=settings.HEALTH_CHECK_TIMEOUT,
                    headers={
                        'User-Agent': 'Cookie-Licking-Detector/1.0 Health-Check'
                    }
                )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'response_time_ms': duration * 1000,
                    'message': 'Ecosyste.ms service accessible'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': f'Ecosyste.ms returned status {response.status_code}'
                }
        except Exception as e:
            logger.error(f"Ecosyste.ms health check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': f'Ecosyste.ms check failed: {str(e)}'
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Update Prometheus metrics
            CPU_USAGE.set(cpu_percent)
            MEMORY_USAGE.set(memory.used)
            DISK_USAGE.labels(device='root').set(disk.used)
            
            status = 'healthy'
            warnings = []
            
            if cpu_percent > 90:
                status = 'degraded'
                warnings.append(f'High CPU usage: {cpu_percent}%')
            
            if memory.percent > 90:
                status = 'degraded'
                warnings.append(f'High memory usage: {memory.percent}%')
            
            if disk.percent > 90:
                status = 'degraded'
                warnings.append(f'High disk usage: {disk.percent}%')
            
            return {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'warnings': warnings,
                'message': 'System resources checked'
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                'status': 'unhealthy',
                'message': f'System resource check failed: {str(e)}'
            }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        overall_status = 'healthy'
        
        # Define critical vs optional checks
        critical_checks = {
            'database': self.check_database,
            'redis': self.check_redis,
            'system_resources': self.check_system_resources,
        }
        
        optional_checks = {
            'github_api': self.check_github_api,
            'ecosystems_api': self.check_ecosystems_api,
        }
        
        # Combine all checks
        all_checks = {**critical_checks, **optional_checks}
        all_checks.update(self.checks)  # Add any custom checks
        
        # Run all checks concurrently
        check_tasks = []
        for name, check_func in all_checks.items():
            if asyncio.iscoroutinefunction(check_func):
                check_tasks.append((name, check_func()))
            else:
                # Wrap sync functions
                check_tasks.append((name, asyncio.create_task(
                    asyncio.to_thread(check_func)
                )))
        
        critical_failures = 0
        optional_failures = 0
        
        for name, task in check_tasks:
            try:
                if hasattr(task, '__await__'):
                    result = await task
                else:
                    result = task
                results[name] = result
                
                # Only count critical checks for overall status
                if result.get('status') in ['unhealthy', 'degraded']:
                    if name in critical_checks:
                        critical_failures += 1
                        if result.get('status') == 'degraded':
                            overall_status = 'degraded' if overall_status == 'healthy' else overall_status
                        else:
                            overall_status = 'unhealthy'
                    else:
                        optional_failures += 1
                        
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                results[name] = {
                    'status': 'unhealthy',
                    'message': f'Check failed: {str(e)}'
                }
                if name in critical_checks:
                    critical_failures += 1
                    overall_status = 'unhealthy'
                else:
                    optional_failures += 1
        
        # Add summary information
        total_checks = len(all_checks)
        healthy_checks = total_checks - critical_failures - optional_failures
        
        return {
            'status': overall_status,
            'timestamp': time.time(),
            'summary': {
                'total_checks': total_checks,
                'healthy_checks': healthy_checks,
                'critical_failures': critical_failures,
                'optional_failures': optional_failures,
                'message': f'{healthy_checks}/{total_checks} services healthy'
            },
            'checks': results
        }


# Global health checker instance
health_checker = HealthChecker()


def track_request_metrics(request: Request, response: Response, process_time: float):
    """Track HTTP request metrics."""
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)


def track_celery_task(task_name: str, status: str, duration: float):
    """Track Celery task metrics."""
    CELERY_TASK_COUNT.labels(
        task_name=task_name,
        status=status
    ).inc()
    
    CELERY_TASK_DURATION.labels(
        task_name=task_name
    ).observe(duration)


def track_claim_detection(confidence_level: str):
    """Track claim detection metrics."""
    CLAIMS_DETECTED.labels(
        confidence_level=confidence_level
    ).inc()


def track_notification(notification_type: str, status: str):
    """Track notification metrics."""
    NOTIFICATIONS_SENT.labels(
        type=notification_type,
        status=status
    ).inc()


def track_api_call(service: str, endpoint: str, status_code: int):
    """Track external API call metrics."""
    if service == 'github':
        GITHUB_API_CALLS.labels(
            endpoint=endpoint,
            status_code=status_code
        ).inc()
    elif service == 'ecosystems':
        ECOSYSTEMS_API_CALLS.labels(
            endpoint=endpoint,
            status_code=status_code
        ).inc()


def monitor_performance(operation_name: str):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                with PerformanceTimer(operation_name, logger):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with PerformanceTimer(operation_name, logger):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator


@asynccontextmanager
async def monitor_queue_sizes():
    """Context manager to monitor queue sizes."""
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Monitor common queue names
        queue_names = [
            'comment_analysis',
            'nudge_check', 
            'progress_check',
            'auto_release_check',
            'dead_letter'
        ]
        
        while True:
            for queue_name in queue_names:
                try:
                    size = redis_client.llen(f"celery:{queue_name}")
                    QUEUE_SIZE.labels(queue_name=queue_name).set(size)
                except Exception as e:
                    logger.warning(f"Failed to get queue size for {queue_name}: {e}")
            
            await asyncio.sleep(30)  # Update every 30 seconds
            
    except Exception as e:
        logger.error(f"Queue monitoring failed: {e}")
    finally:
        yield


def initialize_system_info():
    """Initialize system information metrics."""
    if not settings.ENABLE_METRICS:
        return
    
    try:
        import platform
        
        SYSTEM_INFO.info({
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'application': 'cookie-licking-detector',
            'environment': settings.ENVIRONMENT
        })
    except Exception as e:
        logger.error(f"Failed to initialize system info: {e}")


def get_metrics() -> str:
    """Get Prometheus metrics in text format."""
    if not settings.ENABLE_METRICS:
        return "# Metrics disabled\n"
    
    try:
        return generate_latest(registry).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return f"# Error generating metrics: {e}\n"


# Initialize system info on module import
initialize_system_info()