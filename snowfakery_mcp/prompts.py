from __future__ import annotations

import textwrap

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(tags={"authoring"})
    def author_recipe(goal: str) -> str:
        """Create a new Snowfakery recipe from a description of what data to generate."""
        return textwrap.dedent(
            f"""
            You are authoring a Snowfakery recipe.

            Goal:
            {goal}

            Requirements:
            - Consult the Snowfakery schema resource: snowfakery://schema/recipe-jsonschema
            - Consult at least one relevant example: snowfakery://examples/list then snowfakery://examples/<name>
            - Use snowfakery_version: 3
            - Prefer options (option/default) + --option for tunable parameters
            - Validate with validate_recipe before presenting the final recipe

            Output:
            - Return a complete YAML recipe.
            """
        ).strip()

    @mcp.prompt(tags={"debugging"})
    def debug_recipe(recipe_yaml: str, error: str) -> str:
        """Debug and fix a failing Snowfakery recipe given the error output."""
        return textwrap.dedent(
            f"""
            Debug this Snowfakery recipe.

            Recipe:
            {recipe_yaml}

            Error output:
            {error}

            Instructions:
            - Identify the failing construct and the minimal fix.
            - Keep changes as small as possible.
            - If the error mentions a filename/line, focus on that location.

            Output:
            - Provide a patched YAML recipe.
            - Explain the fix briefly.
            """
        ).strip()
