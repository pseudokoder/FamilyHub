"""Reads docs/openapi.yaml and shapes it for the /apidocs page.

WHY SERVER-SIDE RENDERING instead of Swagger UI: the stock Swagger UI
injects inline styles, which our strict Content-Security-Policy (Ch. 19)
deliberately blocks. Rather than punch an 'unsafe-inline' hole in the CSP
for one developer page, we render the spec ourselves — it's a YAML file
and a for-loop. The raw spec at /openapi.yaml still works with any
external tool (paste it into editor.swagger.io).
"""

import os

import yaml
from flask import current_app


def spec_path():
    # <project root>/docs/openapi.yaml — current_app.root_path is app/.
    return os.path.join(
        os.path.dirname(current_app.root_path), "docs", "openapi.yaml"
    )


def load_spec():
    with open(spec_path(), encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def operations_by_tag(spec):
    """Reshape {path: {method: op}} into {tag: [op-rows]} for the template,
    preserving the spec's own tag order (it's the table of contents)."""
    grouped = {tag["name"]: [] for tag in spec.get("tags", [])}
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if method == "parameters":  # shared path params, not a verb
                continue
            tag = (operation.get("tags") or ["Other"])[0]
            grouped.setdefault(tag, []).append({
                "method": method.upper(),
                "path": path,
                "summary": operation.get("summary", ""),
            })
    return grouped
