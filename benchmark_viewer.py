#!/usr/bin/env python3
"""
Benchmark Viewer - Web interface to view Mindy benchmark results
"""

from flask import Flask, render_template, jsonify
import json
from pathlib import Path

app = Flask(__name__, template_folder="templates")

RESULTS_FILE = Path(__file__).parent / "benchmark" / "benchmark_results.json"


def load_results():
    """Load benchmark results from JSON file."""
    if not RESULTS_FILE.exists():
        return None

    with open(RESULTS_FILE, 'r') as f:
        return json.load(f)


@app.route("/")
def index():
    """Main benchmark viewer page."""
    results = load_results()
    if results is None:
        return render_template("benchmark_viewer.html", error="No benchmark results found. Run the benchmark first.")

    return render_template("benchmark_viewer.html", results=results)


@app.route("/api/results")
def api_results():
    """API endpoint to get benchmark results as JSON."""
    results = load_results()
    if results is None:
        return jsonify({"error": "No results found"}), 404

    return jsonify(results)


if __name__ == "__main__":
    print("=" * 70)
    print("MINDY BENCHMARK VIEWER")
    print("=" * 70)
    print(f"\nResults file: {RESULTS_FILE}")
    print("\nStarting server at http://localhost:5001")
    print("Press Ctrl+C to stop\n")

    app.run(port=5001, debug=True)
