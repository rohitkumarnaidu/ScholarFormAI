import logging
import os
import threading
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


class Counter:
    """Thread-safe counter metric."""

    def __init__(self, name: str, help_text: str, label_names: list[str] | None = None):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self._values: dict[tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        label_values = tuple(labels.get(k, "") for k in self.label_names) if labels else ()
        with self._lock:
            self._values[label_values] += value

    def get(self, labels: dict[str, str] | None = None) -> float:
        label_values = tuple(labels.get(k, "") for k in self.label_names) if labels else ()
        with self._lock:
            return self._values.get(label_values, 0.0)

    def reset(self) -> None:
        with self._lock:
            self._values.clear()

    def collect(self) -> list[str]:
        with self._lock:
            if not self._values:
                return [
                    f"# HELP {self.name} {self.help_text}",
                    f"# TYPE {self.name} counter",
                    f"{self.name} 0",
                ]
            lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} counter"]
            for label_values, value in self._values.items():
                if self.label_names:
                    labels_str = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, label_values, strict=False))
                    lines.append(f"{self.name}{{{labels_str}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
            return lines


class Histogram:
    """Thread-safe histogram metric with configurable buckets."""

    def __init__(
        self,
        name: str,
        help_text: str,
        label_names: list[str] | None = None,
        buckets: list[float] | None = None,
    ):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self.buckets = sorted(buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
        self._values: dict[tuple[str, ...], dict[str, float]] = defaultdict(
            lambda: {"sum": 0.0, "count": 0, **{str(b): 0 for b in self.buckets}}
        )
        self._lock = threading.Lock()

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        label_values = tuple(labels.get(k, "") for k in self.label_names) if labels else ()
        with self._lock:
            entry = self._values[label_values]
            entry["sum"] += value
            entry["count"] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    entry[str(bucket)] += 1

    def collect(self) -> list[str]:
        with self._lock:
            lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} histogram"]
            if not self._values:
                lines.append(f"{self.name}_count 0")
                lines.append(f"{self.name}_sum 0")
                return lines
            for label_values, entry in self._values.items():
                labels_str = ""
                if self.label_names:
                    labels_str = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, label_values, strict=False))
                bucket_name = self.name
                if labels_str:
                    bucket_name = f"{self.name}{{{labels_str}}}"
                for bucket in self.buckets:
                    lines.append(f'{bucket_name}_bucket{{le="{bucket}"}} {int(entry[str(bucket)])}')
                lines.append(f'{bucket_name}_bucket{{le="+Inf"}} {int(entry["count"])}')
                lines.append(f"{bucket_name}_count {int(entry['count'])}")
                lines.append(f"{bucket_name}_sum {entry['sum']}")
            return lines


class Gauge:
    """Thread-safe gauge metric."""

    def __init__(self, name: str, help_text: str, label_names: list[str] | None = None):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self._values: dict[tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, value: float, labels: dict[str, str] | None = None) -> None:
        label_values = tuple(labels.get(k, "") for k in self.label_names) if labels else ()
        with self._lock:
            self._values[label_values] = value

    def inc(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        label_values = tuple(labels.get(k, "") for k in self.label_names) if labels else ()
        with self._lock:
            self._values[label_values] += value

    def dec(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        label_values = tuple(labels.get(k, "") for k in self.label_names) if labels else ()
        with self._lock:
            self._values[label_values] -= value

    def get(self, labels: dict[str, str] | None = None) -> float:
        label_values = tuple(labels.get(k, "") for k in self.label_names) if labels else ()
        with self._lock:
            return self._values.get(label_values, 0.0)

    def collect(self) -> list[str]:
        with self._lock:
            lines = [f"# HELP {self.name} {self.help_text}", f"# TYPE {self.name} gauge"]
            if not self._values:
                lines.append(f"{self.name} 0")
                return lines
            for label_values, value in self._values.items():
                if self.label_names:
                    labels_str = ",".join(f'{k}="{v}"' for k, v in zip(self.label_names, label_values, strict=False))
                    lines.append(f"{self.name}{{{labels_str}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
            return lines


class MetricsCollector:
    """Central metrics registry with Prometheus text format output."""

    def __init__(self, namespace: str = "amf"):
        self.namespace = namespace
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._gauges: dict[str, Gauge] = {}
        self._lock = threading.Lock()
        self._system_metrics_enabled = False

        self._setup_default_metrics()

    def _setup_default_metrics(self) -> None:
        self.create_counter(
            "http_requests_total",
            "Total number of HTTP requests",
            label_names=["method", "endpoint", "status"],
        )
        self.create_histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            label_names=["method", "endpoint"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )
        self.create_gauge("http_requests_active", "Number of active HTTP requests")
        self.create_counter("errors_total", "Total number of errors", label_names=["type", "endpoint"])
        self.create_counter(
            "http_request_size_bytes",
            "Total request size in bytes",
            label_names=["method", "endpoint"],
        )
        self.create_counter(
            "http_response_size_bytes",
            "Total response size in bytes",
            label_names=["method", "endpoint"],
        )
        self.create_gauge("up", "Service up status")

    def create_counter(self, name: str, help_text: str, label_names: list[str] | None = None) -> Counter:
        full_name = f"{self.namespace}_{name}"
        with self._lock:
            if full_name in self._counters:
                return self._counters[full_name]
            counter = Counter(full_name, help_text, label_names)
            self._counters[full_name] = counter
            return counter

    def create_histogram(
        self,
        name: str,
        help_text: str,
        label_names: list[str] | None = None,
        buckets: list[float] | None = None,
    ) -> Histogram:
        full_name = f"{self.namespace}_{name}"
        with self._lock:
            if full_name in self._histograms:
                return self._histograms[full_name]
            histogram = Histogram(full_name, help_text, label_names, buckets)
            self._histograms[full_name] = histogram
            return histogram

    def create_gauge(self, name: str, help_text: str, label_names: list[str] | None = None) -> Gauge:
        full_name = f"{self.namespace}_{name}"
        with self._lock:
            if full_name in self._gauges:
                return self._gauges[full_name]
            gauge = Gauge(full_name, help_text, label_names)
            self._gauges[full_name] = gauge
            return gauge

    def get_counter(self, name: str) -> Counter | None:
        return self._counters.get(f"{self.namespace}_{name}")

    def get_histogram(self, name: str) -> Histogram | None:
        return self._histograms.get(f"{self.namespace}_{name}")

    def get_gauge(self, name: str) -> Gauge | None:
        return self._gauges.get(f"{self.namespace}_{name}")

    def enable_system_metrics(self, interval_seconds: int = 15) -> None:
        if self._system_metrics_enabled:
            return
        self._system_metrics_enabled = True
        self.create_gauge("system_memory_usage_bytes", "Current memory usage in bytes")
        self.create_gauge("system_memory_total_bytes", "Total system memory in bytes")
        self.create_gauge("system_cpu_percent", "Current CPU usage percentage")
        self.create_gauge("system_disk_usage_bytes", "Disk usage in bytes")
        self.create_gauge("system_disk_free_bytes", "Disk free space in bytes")

        def _collect_loop():
            while self._system_metrics_enabled:
                try:
                    import psutil

                    proc = psutil.Process()
                    mem = proc.memory_info()
                    self.get_gauge("system_memory_usage_bytes").set(mem.rss)
                    self.get_gauge("system_cpu_percent").set(proc.cpu_percent(interval=1))

                    mem_total = getattr(psutil.virtual_memory(), "total", 0)
                    self.get_gauge("system_memory_total_bytes").set(mem_total)

                    disk = psutil.disk_usage(os.path.abspath(os.sep))
                    self.get_gauge("system_disk_usage_bytes").set(disk.used)
                    self.get_gauge("system_disk_free_bytes").set(disk.free)
                except ImportError:
                    pass  # intentionally ignored
                except Exception as exc:
                    logger.debug("System metrics collection error: %s", exc)
                time.sleep(interval_seconds)

        thread = threading.Thread(target=_collect_loop, daemon=True, name="system-metrics")
        thread.start()
        logger.info("System metrics collection enabled (interval=%ds)", interval_seconds)

    def disable_system_metrics(self) -> None:
        self._system_metrics_enabled = False

    def observe_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        status_group = f"{status_code // 100}xx"
        self.get_counter("http_requests_total").inc(
            labels={"method": method, "endpoint": endpoint, "status": status_group}
        )
        self.get_histogram("http_request_duration_seconds").observe(
            duration, labels={"method": method, "endpoint": endpoint}
        )

    def generate_prometheus_text(self) -> str:
        lines = []
        self.get_gauge("up").set(1.0)
        with self._lock:
            for counter in self._counters.values():
                lines.extend(counter.collect())
            for histogram in self._histograms.values():
                lines.extend(histogram.collect())
            for gauge in self._gauges.values():
                lines.extend(gauge.collect())
        lines.append("")
        return "\n".join(lines)

    def reset(self) -> None:
        with self._lock:
            for counter in self._counters.values():
                counter.reset()
            for histogram in self._histograms.values():
                histogram._values.clear()
            for gauge in self._gauges.values():
                gauge._values.clear()


metrics = MetricsCollector()
