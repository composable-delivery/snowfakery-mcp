"""Discovery resources for Snowfakery capabilities (providers, plugins, formats).

These functions are registered via FastMCP decorators, so they may appear
"unused" to static analyzers even though they are invoked at runtime.
"""

# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
from typing import Any

from faker import Faker
from mcp.server.fastmcp import FastMCP


def register_discovery_resources(mcp: FastMCP) -> None:
    """Register read-only resources for discovering Snowfakery capabilities."""

    @mcp.resource("snowfakery://providers/list")
    def fake_providers_resource() -> str:
        """List available Faker providers and their methods for generating fake data."""
        locale = "en_US"
        try:
            fake = Faker(locale)
        except (TypeError, ValueError):
            fake = Faker("en_US")

        providers_info: dict[str, list[dict[str, str]]] = {}

        # Get all providers from Faker
        for provider_class in fake.providers:
            provider_module = provider_class.__module__
            provider_name = provider_class.__name__

            # Categorize by standard Faker providers
            if "person" in provider_module:
                category = "person"
            elif "address" in provider_module:
                category = "address"
            elif "company" in provider_module:
                category = "company"
            elif "internet" in provider_module:
                category = "internet"
            elif "date_time" in provider_module:
                category = "date_time"
            elif "lorem" in provider_module:
                category = "lorem"
            elif "file" in provider_module:
                category = "file"
            elif "job" in provider_module:
                category = "job"
            elif "phone_number" in provider_module:
                category = "phone_number"
            elif "bank" in provider_module:
                category = "bank"
            elif "credit_card" in provider_module:
                category = "credit_card"
            else:
                category = "other"

            if category not in providers_info:
                providers_info[category] = []

            # Get methods from provider
            methods = [
                method
                for method in dir(provider_class)
                if not method.startswith("_") and callable(getattr(provider_class, method))
            ]

            for method in methods:
                providers_info[category].append(
                    {
                        "name": method,
                        "provider": provider_name,
                        "usage": f"fake: {method}",
                    }
                )

        # Remove duplicates and sort
        for category in providers_info:
            seen: set[str] = set()
            unique_methods: list[dict[str, str]] = []
            for item in providers_info[category]:
                if item["name"] not in seen:
                    unique_methods.append(item)
                    seen.add(item["name"])
            providers_info[category] = sorted(unique_methods, key=lambda x: x["name"])

        result: dict[str, Any] = {
            "locale": locale,
            "provider_count": sum(len(v) for v in providers_info.values()),
            "categories": providers_info,
        }
        return json.dumps(result, indent=2)

    @mcp.resource("snowfakery://plugins/list")
    def plugins_list_resource() -> str:
        """List built-in Snowfakery plugins and their capabilities."""
        plugins_info: dict[str, dict[str, Any]] = {
            "Math": {
                "module": "snowfakery.standard_plugins.Math",
                "description": "Mathematical functions: sqrt, sin, cos, pi, min, max, round, etc.",
                "methods": [
                    "sqrt",
                    "sin",
                    "cos",
                    "tan",
                    "pi",
                    "e",
                    "min",
                    "max",
                    "round",
                    "floor",
                    "ceil",
                    "log",
                    "exp",
                ],
                "example": "Math.sqrt: 144",
            },
            "Counters": {
                "module": "snowfakery.standard_plugins.Counters",
                "description": "Generate incrementing or decrementing counters (numeric or date-based).",
                "methods": [
                    "NumberCounter",
                    "DateCounter",
                ],
                "parameters": {
                    "NumberCounter": [
                        {"name": "start", "type": "int", "description": "Starting value"},
                        {
                            "name": "step",
                            "type": "int",
                            "description": "Increment step (default: 1)",
                        },
                        {"name": "name", "type": "str", "description": "Counter identifier"},
                    ],
                    "DateCounter": [
                        {
                            "name": "start_date",
                            "type": "str",
                            "description": "Starting date (YYYY-MM-DD)",
                        },
                        {
                            "name": "step",
                            "type": "str",
                            "description": "Increment step (e.g., '+1d')",
                        },
                        {"name": "name", "type": "str", "description": "Counter identifier"},
                    ],
                },
                "example": "Counters.NumberCounter: {start: 1, name: counter1}",
            },
            "UniqueId": {
                "module": "snowfakery.standard_plugins.UniqueId",
                "description": "Generate unique IDs with custom alphabets and formats.",
                "methods": [
                    "AlphaCodeGenerator",
                ],
                "parameters": {
                    "AlphaCodeGenerator": [
                        {
                            "name": "alphabet",
                            "type": "str",
                            "description": "Custom alphabet for code generation",
                        },
                    ],
                },
                "example": "UniqueId.AlphaCodeGenerator: {alphabet: ACGT}",
            },
            "Salesforce": {
                "module": "snowfakery.standard_plugins.Salesforce",
                "description": "Salesforce-specific integration (SOQL queries, org access when embedded in CumulusCI).",
                "methods": [
                    "soql_query",
                ],
                "example": "Uses SOQL for data retrieval",
            },
            "Schedule": {
                "module": "snowfakery.standard_plugins.Schedule",
                "description": "Generate scheduled events and recurring dates.",
                "methods": [
                    "get_schedule",
                ],
                "example": "Schedule-based data generation",
            },
            "Datasets": {
                "module": "snowfakery.standard_plugins.datasets",
                "description": "Load external datasets and reference data.",
                "methods": [
                    "load_dataset",
                ],
                "example": "Load CSV or JSON data",
            },
        }

        result: dict[str, Any] = {
            "plugin_count": len(plugins_info),
            "plugins": plugins_info,
            "note": "To use a plugin, add it to your recipe: - plugin: snowfakery.standard_plugins.PluginName",
        }
        return json.dumps(result, indent=2)

    @mcp.resource("snowfakery://formats/info")
    def formats_info_resource() -> str:
        """Describe Snowfakery's output formats with configuration options."""
        formats_info: dict[str, dict[str, Any]] = {
            "txt": {
                "name": "Text (Debug Output)",
                "extension": ".txt",
                "description": "Human-readable debug output showing generated records.",
                "use_case": "Quick testing, development, debugging",
                "parameters": [],
                "example": "Person(id=1, name=John, age=30)",
                "default": True,
            },
            "json": {
                "name": "JSON",
                "extension": ".json",
                "description": "Structured JSON representation of generated data.",
                "use_case": "Data import, APIs, machine-readable output",
                "parameters": [],
                "example": '{"tables": {"Person": [{"id": 1, "name": "John", "age": 30}]}}',
                "dependencies": [],
            },
            "csv": {
                "name": "CSV (Comma-Separated Values)",
                "extension": "csv/",
                "description": "Directory with one CSV file per table plus CSVW metadata file.",
                "use_case": "Spreadsheet import, databases, data warehouses",
                "parameters": [
                    {
                        "name": "output_folder",
                        "type": "path",
                        "description": "Directory to write CSV files and metadata",
                    }
                ],
                "example": "Person.csv, Account.csv, csvw_metadata.json",
                "note": "Includes CSVW (Comma-Separated Values on the Web) metadata",
            },
            "sql": {
                "name": "SQL",
                "extension": ".sql",
                "description": "SQL DDL and INSERT statements for database import.",
                "use_case": "Database seeding, script export, documentation",
                "parameters": [],
                "example": "CREATE TABLE Person (id TEXT, name TEXT); INSERT INTO Person VALUES ...",
                "dependencies": [],
            },
            "dot": {
                "name": "Graphviz DOT",
                "extension": ".dot",
                "description": "Graph description format for visualizing data relationships.",
                "use_case": "Schema visualization, relationship mapping",
                "parameters": [],
                "example": "digraph { Person -> Account [label=owns]; }",
                "tools": ["graphviz (optional for rendering)"],
            },
            "svg": {
                "name": "SVG (Scalable Vector Graphics)",
                "extension": ".svg",
                "description": "Vector diagram showing table relationships.",
                "use_case": "Web display, documentation, reports",
                "parameters": [],
                "dependencies": ["graphviz"],
                "note": "Requires graphviz to be installed",
            },
            "svgz": {
                "name": "Compressed SVG",
                "extension": ".svgz",
                "description": "Gzip-compressed SVG for smaller file size.",
                "use_case": "Web display with compression, bandwidth optimization",
                "parameters": [],
                "dependencies": ["graphviz"],
            },
            "png": {
                "name": "PNG (Portable Network Graphics)",
                "extension": ".png",
                "description": "Raster image showing table relationships.",
                "use_case": "Documentation, slides, reports",
                "parameters": [],
                "dependencies": ["graphviz"],
                "note": "Requires graphviz to be installed",
            },
            "jpeg": {
                "name": "JPEG",
                "extension": ".jpg",
                "description": "Compressed raster image of relationship diagram.",
                "use_case": "Email-friendly format, lightweight sharing",
                "parameters": [],
                "dependencies": ["graphviz"],
            },
            "ps": {
                "name": "PostScript",
                "extension": ".ps",
                "description": "PostScript format for printing or archival.",
                "use_case": "Print-ready output, PostScript workflows",
                "parameters": [],
                "dependencies": ["graphviz"],
            },
        }

        result: dict[str, Any] = {
            "total_formats": len(formats_info),
            "formats": formats_info,
            "graphviz_note": "Image formats (SVG, PNG, JPEG, PS) require graphviz to be installed: https://graphviz.org/download/",
            "usage": "Use --output-format=<format> with snowfakery command",
        }
        return json.dumps(result, indent=2)
