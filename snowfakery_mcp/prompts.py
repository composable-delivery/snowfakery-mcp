from __future__ import annotations

import textwrap

from fastmcp import Context, FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(tags={"authoring"})
    async def author_recipe(goal: str, ctx: Context) -> str:
        """Create a new Snowfakery recipe from a description of what data to generate."""
        try:
            schema_content = await ctx.read_resource("snowfakery://schema/recipe-jsonschema")
            schema_section = f"\nSnowfakery Recipe Schema (partial/full):\n{schema_content}\n"
        except Exception:
            schema_section = "Note: Could not load schema automatically. Please use the tool to fetch it if needed."

        return textwrap.dedent(
            f"""
            You are authoring a Snowfakery recipe.

            Goal:
            {goal}
            {schema_section}

            Requirements:
            - Consult the included schema above.
            - Consult at least one relevant example: snowfakery://examples/list then snowfakery://examples/<name>
            - Check community templates for complex patterns: snowfakery://templates/list
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
