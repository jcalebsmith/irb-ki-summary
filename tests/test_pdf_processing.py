from pathlib import Path

from app.pdf import read_pdf


def test_read_pdf_returns_texts_and_labels():
    pdf_path = Path("test_data") / "HUM00173014.pdf"
    with pdf_path.open("rb") as handle:
        pages = read_pdf(handle)

    assert len(pages.texts) == len(pages.labels)
    assert len(pages.texts) > 0
    assert all(isinstance(text, str) for text in pages.texts)
