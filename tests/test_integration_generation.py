import asyncio
from pathlib import Path

from app.main import framework
from app.pdf import read_pdf
from app.core.document_models import Document


def test_informed_consent_generation_success(sample_document):
    result = asyncio.run(
        framework.generate(
            document_type="informed-consent-ki",
            parameters={},
            document=sample_document,
        )
    )

    assert result.success is True
    assert "Section 1" in result.content
    assert "6 months" in result.content
    assert result.metadata["plugin_id"] == "informed-consent-ki"
    assert result.metadata["template_used"].endswith("ki-summary.j2")


def test_supported_document_types_lists_plugin():
    supported = framework.list_supported_document_types()
    assert "informed-consent" in supported
    assert "consent-form" in supported


def test_get_plugin_info_exposes_metadata():
    info = framework.get_plugin_info("informed-consent-ki")
    assert info is not None
    assert info["name"] == "Informed Consent Key Information Summary"
    assert "features" in info


def test_generate_with_unknown_document_type_returns_error(sample_document):
    result = asyncio.run(
        framework.generate(
            document_type="non-existent-plugin",
            parameters={},
            document=sample_document,
        )
    )

    assert result.success is False
    assert result.error_message == "No plugin found for document type: non-existent-plugin"


def test_informed_consent_generation_from_pdf():
    pdf_path = Path("test_data") / "HUM00173014.pdf"
    with pdf_path.open("rb") as handle:
        pages = read_pdf(handle)

    document = Document(
        text="\n\n".join(filter(None, pages.texts)),
        metadata={"source": pdf_path.name, "page_labels": pages.labels},
    )

    result = asyncio.run(
        framework.generate(
            document_type="informed-consent-ki",
            parameters={},
            document=document,
        )
    )

    assert result.success is True
    assert "Section 1" in result.content
    assert result.metadata["plugin_id"] == "informed-consent-ki"
