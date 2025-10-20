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
import time
from pathlib import Path
from typing import Any, Dict, List

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
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to repeat the request for consistency testing (default: %(default)s).",
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


def _print_response(resp: requests.Response, run_number: int = None) -> None:
    if run_number is not None:
        print(f"\n{'='*60}")
        print(f"Run {run_number} - Status: {resp.status_code}")
        print(f"{'='*60}")
    else:
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


def _make_request(args, pdf_path: Path) -> requests.Response:
    """Make a single request to the endpoint."""
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

    return response


def _extract_generated_content(response_json: Dict[str, Any]) -> str:
    """Extract generated content from response for consistency tracking."""
    # Try to get the rendered_summary or generated_text field
    if "rendered_summary" in response_json:
        return response_json["rendered_summary"]
    elif "generated_text" in response_json:
        return response_json["generated_text"]
    elif "content" in response_json:
        return response_json["content"]
    else:
        # Fall back to the entire JSON as string
        return json.dumps(response_json, ensure_ascii=False)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    pdf_path: Path = args.pdf
    if not pdf_path.exists():
        raise SystemExit(f"PDF does not exist: {pdf_path}")

    repeat_count = args.repeat

    if repeat_count > 1:
        print(f"\n{'='*60}")
        print(f"Running consistency test with {repeat_count} iterations")
        print(f"{'='*60}")

    # Import ConsistencyTracker for multi-run analysis
    from app.core.validators import ConsistencyTracker

    tracker = ConsistencyTracker()
    responses: List[Dict[str, Any]] = []
    all_success = True

    for run in range(1, repeat_count + 1):
        if repeat_count > 1:
            print(f"\nExecuting run {run}/{repeat_count}...")
            time.sleep(0.5)  # Small delay between runs

        response = _make_request(args, pdf_path)

        # Parse response
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                response_json = response.json()
                responses.append(response_json)

                # Extract generated content for tracking
                generated_content = _extract_generated_content(response_json)
                tracker.track(generated_content, args.plugin_id)

            except ValueError:
                print(f"Run {run}: Failed to parse JSON response")
                all_success = False
        else:
            print(f"Run {run}: Non-JSON response received")
            all_success = False

        _print_response(response, run if repeat_count > 1 else None)

        if not response.ok:
            all_success = False

    # Generate consistency report if multiple runs
    if repeat_count > 1:
        consistency_report = tracker.get_report(args.plugin_id)

        # Add metadata
        report_with_metadata = {
            "test_metadata": {
                "pdf_file": str(pdf_path),
                "plugin_id": args.plugin_id,
                "template_id": args.template_id,
                "repeat_count": repeat_count,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "consistency_metrics": consistency_report,
            "all_responses": responses
        }

        # Save to file
        report_path = Path("consistency_report.json")
        with open(report_path, "w") as f:
            json.dump(report_with_metadata, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"Consistency Report Generated: {report_path}")
        print(f"{'='*60}")
        print("\nSummary:")

        metrics = consistency_report.get("by_document_type", {}).get(args.plugin_id, {})
        if metrics:
            print(f"  Runs Analyzed: {metrics.get('runs', 0)}")
            print(f"  Coefficient of Variation: {metrics.get('cv', 0):.2f}%")
            print(f"  Structural Consistency: {metrics.get('structural_consistency', 0):.2%}")
            print(f"  Mean Word Count: {metrics.get('mean_word_count', 0):.1f}")
            print(f"  Unique Outputs: {metrics.get('unique_outputs', 0)}")

            cv = metrics.get('cv', 0)
            if cv < 15.0:
                print(f"  ✓ Target achieved (CV < 15%)")
            else:
                print(f"  ✗ Target not achieved (CV >= 15%)")

    if not all_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
