"""Locust load testing configuration for AMF API.

Usage:
    locust -f locustfile.py --host=http://localhost:8000
    locust -f locustfile.py --host=http://localhost:8000 --csv=results --headless -u 50 -r 10 -t 5m
"""

import random
import string

from locust import HttpUser, between, constant_pacing, task

# ------------------------------------------------------------------ #
#  Test data factories                                                #
# ------------------------------------------------------------------ #


def random_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def make_manuscript(section_count: int = 3, para_words: int = 50, ref_count: int = 5) -> dict:
    sections = []
    for i in range(section_count):
        sections.append({
            "heading": f"Section {i+1}: {random_string(8)}",
            "level": min(i + 1, 4),
            "content": [{"text": f"Paragraph content for section {i+1}. " * para_words}],
        })
    references = []
    for i in range(ref_count):
        references.append({
            "authors": [{"first_name": random_string(6), "last_name": random_string(8)}],
            "year": str(random.randint(1990, 2024)),
            "title": f"Reference title {i+1}: {random_string(12)}",
            "journal": f"Journal of {random_string(10)}",
            "volume": str(random.randint(1, 50)),
            "issue": str(random.randint(1, 12)),
            "pages": f"{random.randint(1, 100)}-{random.randint(101, 200)}",
            "doi": f"10.1000/{random_string(8)}",
        })
    return {
        "title": f"Load Test Manuscript {random_string(6)}",
        "authors": [
            {"first_name": "Jane", "last_name": "Smith", "affiliation": "University of Testing"},
            {"first_name": "John", "last_name": "Doe", "affiliation": "Institute of Load"},
        ],
        "abstract": "This is a test abstract for load testing purposes. " * 5,
        "keywords": ["load", "test", random_string(6), random_string(8)],
        "sections": sections,
        "references": references,
    }


# ------------------------------------------------------------------ #
#  User classes                                                       #
# ------------------------------------------------------------------ #

class BrowsingUser(HttpUser):
    """Lightweight user that browses styles and occasionally validates."""

    wait_time = between(2, 5)

    @task(5)
    def list_styles(self):
        self.client.get("/api/v1/styles")

    @task(3)
    def get_random_style(self):
        style = random.choice(["apa", "mla", "chicago", "ieee", "harvard", "vancouver", "turabian", "acs", "ama"])
        self.client.get(f"/api/v1/styles/{style}")

    @task(1)
    def health(self):
        self.client.get("/health")

    @task(1)
    def quick_validate(self):
        ms = {
            "title": "Quick Validation",
            "authors": [{"first_name": "Test", "last_name": "User"}],
            "sections": [{"heading": "Intro", "level": 1, "content": [{"text": "Test."}]}],
        }
        self.client.post("/api/v1/validate", json={"manuscript": ms, "style_id": "apa"})


class SubmittingUser(HttpUser):
    """Primary user that performs the core format/preview/validate workflows."""

    wait_time = between(3, 8)

    @task(3)
    def validate(self):
        ms = make_manuscript(section_count=2, para_words=20)
        style = random.choice(["apa", "mla", "chicago", "ieee"])
        self.client.post("/api/v1/validate", json={"manuscript": ms, "style_id": style})

    @task(2)
    def format(self):
        ms = make_manuscript(section_count=3, para_words=30, ref_count=3)
        style = random.choice(["apa", "mla", "chicago"])
        self.client.post("/api/v1/format", json={"manuscript": ms, "style_id": style})

    @task(1)
    def preview(self):
        ms = make_manuscript(section_count=1, para_words=10, ref_count=0)
        style = random.choice(["mla", "apa", "chicago"])
        self.client.post("/api/v1/preview", json={"manuscript": ms, "style_id": style})

    @task(1)
    def health(self):
        self.client.get("/health")

    @task(1)
    def list_styles(self):
        self.client.get("/api/v1/styles")


class HeavySubmittingUser(HttpUser):
    """Stress-test user that submits large manuscripts."""

    wait_time = between(10, 30)

    @task(1)
    def format_large(self):
        ms = make_manuscript(section_count=8, para_words=200, ref_count=20)
        self.client.post(
            "/api/v1/format",
            json={"manuscript": ms, "style_id": "apa"},
            name="/api/v1/format [large]",
        )

    @task(2)
    def validate_large(self):
        ms = make_manuscript(section_count=5, para_words=100, ref_count=10)
        self.client.post(
            "/api/v1/validate",
            json={"manuscript": ms, "style_id": "chicago"},
            name="/api/v1/validate [large]",
        )

    @task(1)
    def preview_large(self):
        ms = make_manuscript(section_count=4, para_words=80, ref_count=0)
        self.client.post(
            "/api/v1/preview",
            json={"manuscript": ms, "style_id": "ieee"},
            name="/api/v1/preview [large]",
        )


class SteadyPacingUser(HttpUser):
    """User with constant pacing for precise throughput measurement."""

    wait_time = constant_pacing(2)

    @task(1)
    def steady_validate(self):
        ms = make_manuscript(section_count=2, para_words=30)
        self.client.post("/api/v1/validate", json={"manuscript": ms, "style_id": "harvard"})

    @task(1)
    def steady_format(self):
        ms = make_manuscript(section_count=2, para_words=20, ref_count=2)
        self.client.post("/api/v1/format", json={"manuscript": ms, "style_id": "vancouver"})

    @task(1)
    def steady_styles(self):
        self.client.get("/api/v1/styles")

    @task(1)
    def steady_preview(self):
        ms = make_manuscript(section_count=1, para_words=15, ref_count=0)
        self.client.post("/api/v1/preview", json={"manuscript": ms, "style_id": "turabian"})
