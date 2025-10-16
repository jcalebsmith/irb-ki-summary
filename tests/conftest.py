import os

# Ensure offline extraction is enabled before the application imports plugins.
os.environ.setdefault("USE_OFFLINE_KI_EXTRACTOR", "1")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.document_models import Document


@pytest.fixture(scope="session", autouse=True)
def use_offline_extractor():
    """Restore the offline flag after the test session completes."""
    previous = os.environ.get("USE_OFFLINE_KI_EXTRACTOR", "1")
    os.environ["USE_OFFLINE_KI_EXTRACTOR"] = "1"
    try:
        yield
    finally:
        os.environ["USE_OFFLINE_KI_EXTRACTOR"] = previous


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_document():
    content = "\n".join(
        [
            "STUDY_TYPE: studying",
            "ARTICLE: a ",
            "STUDY_OBJECT: inhaler therapy",
            "POPULATION: children",
            "STUDY_PURPOSE: improve asthma control in children",
            "STUDY_GOALS: reduce asthma attacks quickly",
            "HAS_RANDOMIZATION: yes",
            "REQUIRES_WASHOUT: no",
            "KEY_RISKS: coughing and mild headache",
            "HAS_DIRECT_BENEFITS: yes",
            "BENEFIT_DESCRIPTION: breathing more easily",
            "STUDY_DURATION: 6 months",
            "AFFECTS_TREATMENT: yes",
            "ALTERNATIVE_OPTIONS: continue usual inhaler therapy",
            "COLLECTS_BIOSPECIMENS: yes",
            "BIOSPECIMEN_DETAILS: blood sample each visit",
            "IS_PEDIATRIC: true",
        ]
    )
    return Document(text=content, metadata={"source": "synthetic-consent"})
