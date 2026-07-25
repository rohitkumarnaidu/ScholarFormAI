"""Load testing script for AMF API using locust."""

from locust import HttpUser, task, between


class AMFUser(HttpUser):
    """Simulates a typical AMF API user with weighted endpoint access."""

    wait_time = between(1, 3)

    @task(3)
    def list_styles(self):
        self.client.get("/api/v1/styles")

    @task(1)
    def get_style_apa(self):
        self.client.get("/api/v1/styles/apa")

    @task(1)
    def get_style_mla(self):
        self.client.get("/api/v1/styles/mla")

    @task(1)
    def validate_manuscript(self):
        self.client.post(
            "/api/v1/validate",
            json={
                "manuscript": {
                    "title": "Test Title for Validation",
                    "authors": [
                        {"first_name": "Jane", "last_name": "Smith", "affiliation": "Test University"}
                    ],
                    "abstract": "This is a test abstract for load testing validation endpoint.",
                    "keywords": ["test", "load", "validation"],
                    "sections": [
                        {
                            "heading": "Introduction",
                            "level": 1,
                            "content": [{"text": "This is the introduction paragraph for load testing."}],
                        }
                    ],
                    "references": [
                        {
                            "authors": [{"first_name": "Test", "last_name": "Author"}],
                            "year": "2024",
                            "title": "Test Reference for Load Testing",
                            "journal": "Journal of Testing",
                            "volume": "10",
                            "issue": "2",
                            "pages": "100-110",
                        }
                    ],
                },
                "style_id": "apa",
            },
        )

    @task(1)
    def format_manuscript(self):
        self.client.post(
            "/api/v1/format",
            json={
                "manuscript": {
                    "title": "Load Test Manuscript",
                    "authors": [
                        {"first_name": "Jane", "last_name": "Smith", "affiliation": "Test University"}
                    ],
                    "abstract": "This abstract is for load testing the format endpoint with a substantial amount of text.",
                    "keywords": ["load", "test", "format", "performance"],
                    "sections": [
                        {
                            "heading": "Introduction",
                            "level": 1,
                            "content": [{"text": "Test content " * 50}],
                        },
                        {
                            "heading": "Methodology",
                            "level": 1,
                            "content": [{"text": "Methodology content " * 50}],
                        },
                        {
                            "heading": "Results",
                            "level": 1,
                            "content": [{"text": "Results content " * 50}],
                        },
                    ],
                    "references": [
                        {
                            "authors": [{"first_name": "Ref", "last_name": "One"}],
                            "year": "2023",
                            "title": "First Reference for Load Testing",
                            "journal": "Journal A",
                            "volume": "5",
                            "pages": "1-10",
                        },
                        {
                            "authors": [{"first_name": "Ref", "last_name": "Two"}],
                            "year": "2024",
                            "title": "Second Reference for Load Testing",
                            "journal": "Journal B",
                            "volume": "8",
                            "issue": "3",
                            "pages": "50-60",
                        },
                    ],
                },
                "style_id": "apa",
            },
        )

    @task(1)
    def preview_manuscript(self):
        self.client.post(
            "/api/v1/preview",
            json={
                "manuscript": {
                    "title": "Preview Load Test",
                    "sections": [
                        {
                            "heading": "Introduction",
                            "level": 1,
                            "content": [{"text": "Preview content for load testing."}],
                        }
                    ],
                },
                "style_id": "mla",
            },
        )

    @task(1)
    def health_check(self):
        self.client.get("/health")


class HeavyAMFUser(HttpUser):
    """Simulates a power user submitting larger manuscripts."""

    wait_time = between(5, 15)

    @task(1)
    def format_large_manuscript(self):
        sections = []
        for i in range(5):
            sections.append({
                "heading": f"Section {i+1}",
                "level": 1,
                "content": [{"text": f"Detailed content for section {i+1}. " * 200}],
            })
        self.client.post(
            "/api/v1/format",
            json={
                "manuscript": {
                    "title": "Large Load Test Manuscript",
                    "authors": [
                        {"first_name": "Heavy", "last_name": "User"},
                        {"first_name": "Load", "last_name": "Tester"},
                    ],
                    "abstract": "This is a large manuscript abstract for load testing. " * 10,
                    "keywords": ["large", "load", "test", "performance", "heavy"],
                    "sections": sections,
                },
                "style_id": "apa",
            },
        )

    @task(2)
    def validate_large_manuscript(self):
        sections = []
        for i in range(3):
            sections.append({
                "heading": f"Section {i+1}",
                "level": 1,
                "content": [{"text": f"Validation content for section {i+1}. " * 100}],
            })
        self.client.post(
            "/api/v1/validate",
            json={
                "manuscript": {
                    "title": "Large Validation Test",
                    "authors": [{"first_name": "Heavy", "last_name": "User"}],
                    "sections": sections,
                },
                "style_id": "chicago",
            },
        )
