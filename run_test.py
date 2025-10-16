"""
Simple helper script to hit the local /generate/ endpoint with a real PDF.

Usage:
    python run_test.py --pdf test_data/HUM00173014.pdf

Assumes uvicorn is already running, e.g.
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import requests


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Submit a PDF to the KI summary endpoint and print the response.",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/generate/",
        help="Target /generate/ endpoint (default: %(default)s)",
    )
    parser.add_argument(
        "--pdf",
        required=True,
        type=Path,
        help="Path to the PDF file to upload.",
    )
    parser.add_argument(
        "--plugin-id",
        default="informed-consent-ki",
        help="Plugin identifier to submit with the request (default: %(default)s).",
    )
    parser.add_argument(
        "--template-id",
        help="Optional template_id form field value.",
    )
    parser.add_argument(
        "--params",
        type=Path,
        help="Optional JSON file containing additional parameters to send in the form field `parameters`.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds (default: %(default)s).",
    )
    return parser


def _load_params(path: Path | None) -> str:
    if not path:
        return "{}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Failed to load parameters JSON from {path}: {exc}") from exc
    return json.dumps(data)


def _print_response(resp: requests.Response) -> None:
    print(f"Status: {resp.status_code}")
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload: Dict[str, Any] = resp.json()
        except ValueError:
            print(resp.text)
            return
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(resp.text)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    pdf_path: Path = args.pdf
    if not pdf_path.exists():
        raise SystemExit(f"PDF does not exist: {pdf_path}")

    form_data = {"plugin_id": args.plugin_id}
    if args.template_id:
        form_data["template_id"] = args.template_id
    form_data["parameters"] = _load_params(args.params)

    with pdf_path.open("rb") as pdf_handle:
        files = {
            "file": (pdf_path.name, pdf_handle, "application/pdf"),
        }
        try:
            response = requests.post(
                args.url,
                data=form_data,
                files=files,
                timeout=args.timeout,
            )
        except requests.RequestException as exc:
            raise SystemExit(f"Request failed: {exc}") from exc

    _print_response(response)
    if not response.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
