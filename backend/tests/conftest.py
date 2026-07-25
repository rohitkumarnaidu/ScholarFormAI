import pytest
from fastapi.testclient import TestClient

from app.api.models import Author, Manuscript, Paragraph, Reference, Section
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_manuscript():
    return Manuscript(
        title="The Impact of Artificial Intelligence on Modern Research Methodologies",
        authors=[
            Author(first_name="Jane", last_name="Smith", affiliation="University of Research", email="jane.smith@research.edu"),
            Author(first_name="John", last_name="Doe", affiliation="Institute of Technology", email="john.doe@tech.edu"),
        ],
        abstract="This study examines the transformative role of artificial intelligence in shaping contemporary research methodologies...",
        keywords=["artificial intelligence", "research methodology", "machine learning"],
        sections=[
            Section(
                heading="Introduction",
                level=1,
                content=[
                    Paragraph(text="Artificial intelligence (AI) has emerged as a transformative force in academic research."),
                    Paragraph(text="This paper explores the various ways AI technologies are reshaping research methodologies."),
                ],
            ),
            Section(
                heading="Methodology",
                level=1,
                content=[
                    Paragraph(text="We conducted a comprehensive literature review of AI applications in research."),
                ],
            ),
        ],
        references=[
            Reference(
                authors=[Author(first_name="Alan", last_name="Turing")],
                year="1950",
                title="Computing Machinery and Intelligence",
                journal="Mind",
                volume="59",
                issue="236",
                pages="433-460",
            ),
        ],
    )


@pytest.fixture
def sample_markdown():
    return """# The Impact of AI on Research

By Jane Smith, John Doe

## Abstract
This study examines AI's role in research methodologies.

Keywords: AI, research, methodology

## Introduction
Artificial intelligence has emerged as a transformative force.

## Conclusion
AI will continue to shape research methodologies.

## References
Turing, A. (1950). Computing Machinery and Intelligence. Mind, 59(236), 433-460.
"""
