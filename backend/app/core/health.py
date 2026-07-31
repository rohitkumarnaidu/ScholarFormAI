import logging
import os
import platform
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app import __title__, __version__

logger = logging.getLogger(__name__)

_START_TIME: float = time.time()


@dataclass
class HealthComponent:
    name: str
    status: str = "healthy"
    message: str = ""
    details: dict[str, Any] | None = None
    critical: bool = True

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "critical": self.critical,
        }
        if self.message:
            result["message"] = self.message
        if self.details:
            result["details"] = self.details
        return result


class HealthChecker:
    """Comprehensive health check with component-level status reporting."""

    def __init__(self):
        self._components: dict[str, HealthComponent] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._components["app"] = HealthComponent(
            name="Application",
            status="healthy",
            details={
                "version": __version__,
                "title": __title__,
                "python_version": platform.python_version(),
                "platform": platform.platform(),
            },
        )
        self._components["disk"] = HealthComponent(
            name="Disk Space",
            status="healthy",
            critical=False,
        )

    def register_component(self, component: HealthComponent) -> None:
        self._components[component.name.lower()] = component

    def get_component(self, name: str) -> HealthComponent | None:
        return self._components.get(name.lower())

    def check_database(self, db_url: str = "") -> HealthComponent:
        component = HealthComponent(name="Database", status="healthy", critical=True)
        if not db_url:
            component.status = "skipped"
            component.message = "No database configured"
            return component
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(db_url, connect_args={"connect_timeout": 3})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            component.details = {"database_url": db_url.split("@")[-1] if "@" in db_url else "configured"}
            logger.debug("Database health check passed")
        except ImportError:
            component.status = "skipped"
            component.message = "sqlalchemy not installed"
        except Exception as exc:
            component.status = "unhealthy"
            component.message = str(exc)
            logger.warning("Database health check failed: %s", exc)
        return component

    def check_redis(self, redis_url: str = "") -> HealthComponent:
        component = HealthComponent(name="Redis", status="healthy", critical=False)
        if not redis_url:
            component.status = "skipped"
            component.message = "No Redis configured"
            return component
        try:
            import redis as sync_redis

            client = sync_redis.from_url(
                redis_url,
                socket_connect_timeout=2,
                socket_timeout=3,
            )
            client.ping()
            info = client.info()
            component.details = {
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "total_connections_received": info.get("total_connections_received", 0),
                "connected_clients": info.get("connected_clients", 0),
            }
            client.close()
            logger.debug("Redis health check passed")
        except ImportError:
            component.status = "skipped"
            component.message = "redis not installed"
        except Exception as exc:
            component.status = "unhealthy"
            component.message = str(exc)
            logger.warning("Redis health check failed: %s", exc)
        return component

    def check_disk_usage(self, path: str | None = None) -> HealthComponent:
        component = self._components.get("disk", HealthComponent(name="Disk Space", critical=False))
        try:
            target_path = path or os.path.abspath(os.sep)
            usage = os.statvfs(target_path) if hasattr(os, "statvfs") else None
            if usage:
                total = usage.f_frsize * usage.f_blocks
                free = usage.f_frsize * usage.f_bfree
                used = total - free
                percent = (used / total) * 100
                component.details = {
                    "path": target_path,
                    "total_bytes": total,
                    "free_bytes": free,
                    "used_bytes": used,
                    "used_percent": round(percent, 2),
                }
                if percent > 90:
                    component.status = "degraded"
                    component.message = f"Disk usage at {percent:.1f}%"
                elif percent > 95:
                    component.status = "unhealthy"
                    component.message = f"Critical disk usage at {percent:.1f}%"
                else:
                    component.status = "healthy"
            else:
                import shutil

                total, used, free = shutil.disk_usage(target_path)
                percent = (used / total) * 100
                component.details = {
                    "path": target_path,
                    "total_bytes": total,
                    "free_bytes": free,
                    "used_bytes": used,
                    "used_percent": round(percent, 2),
                }
                if percent > 90:
                    component.status = "degraded"
                    component.message = f"Disk usage at {percent:.1f}%"
                elif percent > 95:
                    component.status = "unhealthy"
                else:
                    component.status = "healthy"
        except Exception as exc:
            component.status = "degraded"
            component.message = f"Could not check disk: {exc}"
        self._components["disk"] = component
        return component

    def liveness(self) -> dict[str, Any]:
        self._components.get("app", HealthComponent(name="Application"))
        return {
            "status": "alive",
            "version": __version__,
            "service": __title__,
            "uptime_seconds": round(time.time() - _START_TIME, 2),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def readiness(self) -> dict[str, Any]:
        self.check_disk_usage()
        components = [c.to_dict() for c in self._components.values()]
        critical_healthy = all(c.status in ("healthy", "skipped") for c in self._components.values() if c.critical)
        overall_status = "ready" if critical_healthy else "not_ready"
        degraded = any(c.status == "degraded" and not c.critical for c in self._components.values())
        if critical_healthy and degraded:
            overall_status = "ready_degraded"
        return {
            "status": overall_status,
            "version": __version__,
            "service": __title__,
            "uptime_seconds": round(time.time() - _START_TIME, 2),
            "timestamp": datetime.now(UTC).isoformat(),
            "components": components,
        }

    def detailed(self) -> dict[str, Any]:
        self.check_disk_usage()
        return {
            "status": "healthy",
            "version": __version__,
            "service": __title__,
            "uptime_seconds": round(time.time() - _START_TIME, 2),
            "start_time": datetime.fromtimestamp(_START_TIME, tz=UTC).isoformat(),
            "timestamp": datetime.now(UTC).isoformat(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "hostname": platform.node(),
            "components": [c.to_dict() for c in self._components.values()],
            "environment": {
                "python_version": platform.python_version(),
                "architecture": platform.machine(),
            },
        }


health_checker = HealthChecker()
