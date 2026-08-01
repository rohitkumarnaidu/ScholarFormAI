import pytest

from amf_sdk.models import Author, Manuscript, Paragraph, Section


@pytest.fixture
def sample_manuscript():
    return Manuscript(
        title="Test Manuscript",
        authors=[Author(first_name="Jane", last_name="Smith")],
        abstract="This is a test abstract.",
        keywords=["test", "sdk"],
        sections=[
            Section(
                heading="Introduction",
                level=1,
                content=[Paragraph(text="Test paragraph.")],
            ),
        ],
    )
