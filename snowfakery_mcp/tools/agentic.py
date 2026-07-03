from __future__ import annotations

from typing import cast

from fastmcp import Context, FastMCP
from fastmcp.tools import ToolResult
from mcp.types import SamplingMessage, TextContent, ToolAnnotations

from snowfakery_mcp.core.config import Config
from snowfakery_mcp.core.paths import WorkspacePaths
from snowfakery_mcp.core.validate import validate_recipe_logic


def register_agentic_tools(mcp: FastMCP, timeout_seconds: int) -> None:
    """Register ``iterative_recipe_gen``.

    ``timeout_seconds`` is the Phase-4 pre-lifespan carve-out (see
    ``server.create_app()``): ``@mcp.tool(timeout=...)`` is resolved at
    decoration time, before any lifespan/request context exists. Phase 5
    wires it straight into the decorator below, closing the gap that this
    tool previously had *zero* timeout coverage (unlike ``run_recipe``/
    ``generate_mapping``/``validate_recipe``, which at least wrapped their
    ``generate_data()`` call in the old SIGALRM-based ``time_limit()``).

    Unlike those three (plain ``def``, dispatched to a worker thread, where
    ``timeout=`` cannot actually preempt a stuck ``generate_data()`` call —
    see ``tools/run.py``'s docstring), ``iterative_recipe_gen`` is
    ``async def`` and runs directly on the event loop, so ``timeout=``
    *does* genuinely cancel it while it's awaiting the real checkpoint
    inside ``ctx.sample()`` (confirmed directly against fastmcp 3.4.2: a
    slow/unresponsive sampling round-trip is cancelled promptly at the
    configured deadline, surfacing as an ``McpError``-shaped tool failure
    instead of hanging indefinitely).

    ``annotations=ToolAnnotations(openWorldHint=True)`` (Phase 6) flags that
    this tool interacts with an "open world" entity (the client's LLM, via
    ``ctx.sample()``) rather than a closed, fully-modeled system. Its return
    type deliberately stays a bare ``str`` in this phase — introducing a
    typed ``RecipeGenResult`` is scoped as a separate, higher-risk follow-up
    PR (see ``FASTMCP3_REFACTOR_PLAN.md`` Phase 6, step 4) since any client
    pattern-matching on the current ``"Error during generation:"`` text
    prefix would need updating, unlike every other change in this phase.
    """

    @mcp.tool(
        tags={"authoring", "agentic"},
        annotations=ToolAnnotations(openWorldHint=True),
        timeout=timeout_seconds,
        version="1",
    )
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
        # `_iterative_recipe_gen_impl` itself is the source of truth for the
        # "ctx is None" error branch, checked before paths/config are ever
        # touched - so it's safe to source them from ctx.lifespan_context
        # (via a `cast`, since that dict access can't be typed precisely)
        # only when ctx is actually present.
        lifespan_context = ctx.lifespan_context if ctx is not None else {}
        paths = cast(WorkspacePaths, lifespan_context.get("paths"))
        config = cast(Config, lifespan_context.get("config"))
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
        schema_text = "\n".join(
            item.content if isinstance(item.content, str) else item.content.decode("utf-8")
            for item in schema.contents
        )
        first_content = messages[0].content
        if isinstance(first_content, TextContent):
            first_content.text += f"\n\nSchema Context:\n{schema_text}"[
                :2000
            ]  # Truncate if too long
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

            # Context.sample() returns a SamplingResult(.text/.result/.history).
            current_recipe = (result.text or "").strip()

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

            # Validate. validate_recipe_logic() returns a plain ValidateResult dict
            # on success but a ToolResult(is_error=True) on failure (Phase 3's
            # ToolResult(is_error=...) contract) — normalize both to a dict here.
            raw_validation = validate_recipe_logic(
                paths=paths, config=config, recipe_text=current_recipe
            )
            validation = (
                raw_validation.structured_content or {"valid": False, "errors": []}
                if isinstance(raw_validation, ToolResult)
                else raw_validation
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
