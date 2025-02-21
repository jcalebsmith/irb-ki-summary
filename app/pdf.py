import pypdf

from dataclasses import dataclass

@dataclass
class PDFPages:
    texts: list[str]
    labels: list[str]

def read_pdf(f) -> PDFPages:
    pdf = pypdf.PdfReader(f)

    texts = []
    labels = []

    for idx, page in enumerate(pdf.pages):
        text = page.extract_text()
        label = pdf.page_labels[idx]

        texts.append(text)
        labels.append(label)

    return PDFPages(texts, labels)
