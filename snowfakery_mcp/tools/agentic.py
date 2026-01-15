from __future__ import annotations

from fastmcp import Context, FastMCP
from mcp.types import SamplingMessage, TextContent

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.validate import validate_recipe_logic


def register_agentic_tools(mcp: FastMCP, paths: WorkspacePaths, config: Config) -> None:
    @mcp.tool(tags={"authoring", "agentic"})
    async def iterative_recipe_gen(
        goal: str,
        max_iterations: int = 3,
        ctx: Context | None = None,
    ) -> str:
        """Create a recipe iteratively with validation.

        This tool uses the LLM (via sampling) to draft a Snowfakery recipe,
        validates it, and if it fails, asks the LLM to fix it.
        Returns the final valid recipe or the last attempt.
        """
        return await _iterative_recipe_gen_impl(goal, max_iterations, ctx, paths, config)


async def _iterative_recipe_gen_impl(
    goal: str,
    max_iterations: int,
    ctx: Context | None,
    paths: WorkspacePaths,
    config: Config,
) -> str:
    if ctx is None:
        return "Error: Context is required for this tool to function."

    messages = [
        SamplingMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"Write a Snowfakery recipe for: {goal}.\nReturn ONLY the YAML content.",
            ),
        )
    ]

    # Fetch schema to provide context
    try:
        schema = await ctx.read_resource("snowfakery://schema/recipe-jsonschema")
        first_content = messages[0].content
        if isinstance(first_content, TextContent):
            first_content.text += f"\n\nSchema Context:\n{schema}"[:2000]  # Truncate if too long
    except Exception:
        pass

    current_recipe = ""

    for _i in range(max_iterations):
        try:
            # Call the client LLM to generate the recipe
            # Note: This assumes the client supports sampling (CreateMessageRequest)
            # We use a large max_tokens to ensure complete recipes
            result = await ctx.sample(
                messages=messages,
                max_tokens=4000,
                system_prompt="You are a Snowfakery expert. Output only valid YAML.",
            )

            # Extract text content (simplistic extraction)
            # result is likely CreateMessageResult
            content = getattr(result, "content", None)
            if content is None:
                # Fallback if result is just a string (some fastmcp versions might do this?)
                content = str(result)

            # Normalize content to string
            if hasattr(content, "text"):
                current_recipe = content.text
            elif isinstance(content, list):  # List of content blocks
                current_recipe = "\n".join([c.text for c in content if hasattr(c, "text")])
            elif isinstance(content, str):
                current_recipe = content
            else:
                current_recipe = str(content)

            # Strip markdown blocks if present
            if current_recipe.strip().startswith("```"):
                lines = current_recipe.strip().splitlines()
                # Remove first line if it's ```yaml or ```
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                current_recipe = "\n".join(lines)

            current_recipe = current_recipe.strip()

            # Validate
            validation = validate_recipe_logic(
                paths=paths, config=config, recipe_text=current_recipe
            )

            if validation["valid"]:
                return current_recipe

            # If invalid, feed error back to LLM
            errors = "\n".join(
                [
                    f"{e['kind']}: {e['message']} (Line {e.get('line', 'Unknown')})"
                    for e in validation.get("errors", [])
                ]
            )
            messages.append(
                SamplingMessage(
                    role="assistant",
                    content=TextContent(type="text", text=current_recipe),
                )
            )
            messages.append(
                SamplingMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"The recipe is invalid. Errors:\n{errors}\n\nPlease fix the recipe and return the full fixed YAML.",
                    ),
                )
            )

        except Exception as e:
            # Fallback if sampling fails or client doesn't support it
            return f"Error during generation: {str(e)}\nLast attempt:\n{current_recipe}"

    return f"Failed to generate valid recipe after {max_iterations} attempts.\nLast attempt:\n{current_recipe}"
