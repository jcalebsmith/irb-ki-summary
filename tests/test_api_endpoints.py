from pathlib import Path


def test_list_plugins_endpoint(client):
    response = client.get("/plugins/")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] >= 1
    plugin_ids = {plugin["plugin_id"] for plugin in payload["plugins"]}
    assert "informed-consent" in plugin_ids
    assert any(item["info"]["id"] == "informed-consent-ki" for item in payload["plugins"])


def test_get_plugin_info_not_found_returns_404(client):
    response = client.get("/plugins/non-existent/")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_root_healthcheck(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World3"}


def test_generate_endpoint_with_pdf(client):
    pdf_path = Path("test_data") / "HUM00173014.pdf"
    with pdf_path.open("rb") as handle:
        response = client.post(
            "/generate/",
            data={"plugin_id": "informed-consent-ki"},
            files={"file": (pdf_path.name, handle, "application/pdf")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert any(section.startswith("Section") for section in payload["sections"])
    assert payload["sections"][-1] == "Total Summary"
    assert len(payload["texts"][-1]) > 0
