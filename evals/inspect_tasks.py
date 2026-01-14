from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, NamedTuple

from inspect_ai import Task, task
from inspect_ai import eval as inspect_eval
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, Scorer, scorer
from inspect_ai.solver import basic_agent, system_message, use_tools
from inspect_ai.tool import mcp_server_stdio, mcp_tools
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class SnowfakeryCase(NamedTuple):
    id: str
    title: str
    task: str
    must_contain: list[str]
    must_call_tools: list[str]
    must_output_substrings: list[str]


CASES: list[SnowfakeryCase] = [
    SnowfakeryCase(
        id="debug_broken_reference",
        title="Debug broken reference",
        task=(
            "You are given a Snowfakery recipe that fails. Use available tools to debug it, "
            "then submit a corrected recipe YAML.\n\n"
            "Broken recipe:\n"
            "- snowfakery_version: 3\n"
            "- object: Account\n"
            "  fields:\n"
            "    Name: ACME\n"
            "- object: Contact\n"
            "  fields:\n"
            "    FirstName: Buster\n"
            "    AccountId:\n"
            "      reference: Accounts\n"
        ),
        must_contain=["Account", "Contact"],
        must_call_tools=["validate_recipe", "run_recipe"],
        must_output_substrings=["Account(", "Contact(", "AccountId="],
    ),
    SnowfakeryCase(
        id="use_examples_then_author",
        title="Use examples to author",
        task=(
            "Use tools to consult at least one example, then author a Snowfakery recipe "
            "(snowfakery_version: 3) that generates 2 Person rows with a literal 'name' field. "
            "Then validate and run it, and submit the final recipe YAML."
        ),
        must_contain=["Person"],
        must_call_tools=[
            "list_examples",
            "get_example",
            "validate_recipe",
            "run_recipe",
        ],
        must_output_substrings=["Person("],
    ),
    SnowfakeryCase(
        id="generate_mapping",
        title="Generate mapping",
        task=(
            "Author a Snowfakery recipe that generates an Account and a Contact referencing it. "
            "Call generate_mapping and then submit the recipe YAML."
        ),
        must_contain=["Account", "Contact"],
        must_call_tools=["generate_mapping", "validate_recipe", "run_recipe"],
        must_output_substrings=["Account(", "Contact(", "AccountId="],
    ),
    SnowfakeryCase(
        id="salesforce_standard_objects",
        title="Salesforce standard objects (field casing + references)",
        task=(
            "Create a Snowfakery recipe that uses Salesforce standard objects and standard field names "
            "with correct casing (e.g., Account.Name, Contact.FirstName, Contact.LastName).\n\n"
            "Requirements:\n"
            "- Create exactly one Account with Name = 'The Account' (use just_once: True).\n"
            "- Create exactly one Contact with FirstName='Da' and LastName='Boss' referencing that Account via AccountId.\n"
            "- Create exactly one Campaign with Name='The Campaign'.\n"
            "- Create one CampaignMember referencing the Campaign and Contact (CampaignId + ContactId) and a Status value.\n\n"
            "Use tools to validate and run. Then output ONLY the final Snowfakery recipe YAML."
        ),
        must_contain=["Account", "Contact", "Campaign", "CampaignMember"],
        must_call_tools=["validate_recipe", "run_recipe"],
        must_output_substrings=[
            "Name=The Account",
            "FirstName=Da",
            "LastName=Boss",
            "AccountId=Account(1)",
            "Name=The Campaign",
            "CampaignId=Campaign(1)",
            "ContactId=Contact(1)",
        ],
    ),
]


async def _call_mcp_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]

    # Keep tool responses small enough for small-context models.
    max_capture_chars = os.environ.get("SNOWFAKERY_MCP_MAX_CAPTURE_CHARS", "800")

    params = StdioServerParameters(
        command="uv",
        args=["run", "snowfakery-mcp"],
        cwd=str(root),
        env={
            "SNOWFAKERY_MCP_WORKSPACE_ROOT": str(root),
            "SNOWFAKERY_MCP_MAX_REPS": os.environ.get("SNOWFAKERY_MCP_MAX_REPS", "5"),
            "SNOWFAKERY_MCP_MAX_TARGET_COUNT": os.environ.get(
                "SNOWFAKERY_MCP_MAX_TARGET_COUNT", "50"
            ),
            "SNOWFAKERY_MCP_MAX_CAPTURE_CHARS": max_capture_chars,
        },
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            out = await session.call_tool(name, arguments)

    if not out.content:
        return {"_parse_error": "tool_result_empty"}

    content0 = out.content[0]
    text = getattr(content0, "text", None)
    if not isinstance(text, str):
        return {"_parse_error": "tool_result_not_text"}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_parse_error": "tool_result_not_json", "_raw_text": text[:4000]}


async def _read_mcp_resource(uri: str) -> str:
    root = Path(__file__).resolve().parents[1]

    # Keep resource reads small enough for small-context models.
    max_capture_chars = os.environ.get("SNOWFAKERY_MCP_MAX_CAPTURE_CHARS", "800")

    params = StdioServerParameters(
        command="uv",
        args=["run", "snowfakery-mcp"],
        cwd=str(root),
        env={
            "SNOWFAKERY_MCP_WORKSPACE_ROOT": str(root),
            "SNOWFAKERY_MCP_MAX_REPS": os.environ.get("SNOWFAKERY_MCP_MAX_REPS", "5"),
            "SNOWFAKERY_MCP_MAX_TARGET_COUNT": os.environ.get(
                "SNOWFAKERY_MCP_MAX_TARGET_COUNT", "50"
            ),
            "SNOWFAKERY_MCP_MAX_CAPTURE_CHARS": max_capture_chars,
        },
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.read_resource(uri)

    if not getattr(result, "contents", None):
        return ""

    content0 = result.contents[0]
    text = getattr(content0, "text", None)
    return text if isinstance(text, str) else ""


@scorer(metrics=[], name="snowfakery_mcp_recipe")
def snowfakery_mcp_recipe_scorer() -> Scorer:
    async def score(state, target) -> Score:
        _ = target

        case_meta = state.metadata or {}
        must_contain = [str(x) for x in (case_meta.get("must_contain") or [])]
        must_call_tools = [str(x) for x in (case_meta.get("must_call_tools") or [])]
        must_output_substrings = [str(x) for x in (case_meta.get("must_output_substrings") or [])]

        completion = (state.output.completion if state.output is not None else "").strip()
        if not completion:
            return Score(value=False, explanation="No submission / empty output")

        # Inspect records tool results as tool-role messages (ChatMessageTool.function).
        tool_messages = [m for m in state.messages if getattr(m, "role", None) == "tool"]
        tool_names = [
            str(getattr(m, "function", "")) for m in tool_messages if getattr(m, "function", None)
        ]
        missing_required_calls = [t for t in must_call_tools if t not in tool_names]
        if missing_required_calls:
            return Score(
                value=False,
                explanation=f"Missing required tool calls: {missing_required_calls}",
                metadata={
                    "missing_tool_calls": missing_required_calls,
                    "tool_calls": tool_names,
                },
            )

        validate_payload = await _call_mcp_tool(
            "validate_recipe",
            {"recipe_text": completion, "strict_mode": True},
        )
        if not validate_payload.get("valid"):
            return Score(
                value=False,
                explanation="Recipe did not validate",
                metadata={"validate": validate_payload},
            )

        run_payload = await _call_mcp_tool(
            "run_recipe",
            {
                "recipe_text": completion,
                "reps": 1,
                "output_format": "txt",
                "capture_output": True,
                "strict_mode": True,
            },
        )
        if not run_payload.get("ok"):
            return Score(
                value=False,
                explanation="Recipe failed to run",
                metadata={"run": run_payload},
            )

        stdout_text = str(run_payload.get("stdout_text", ""))
        resources = run_payload.get("resources")
        resource_uris: list[str] = (
            [str(u) for u in resources] if isinstance(resources, list) else []
        )
        output_uri = next((u for u in resource_uris if u.endswith("/output.txt")), None)

        artifact_text = ""
        if output_uri is not None:
            artifact_text = await _read_mcp_resource(output_uri)

        # Prefer the artifact text for scoring (it reflects the real run output).
        text_for_checks = artifact_text or stdout_text

        missing_markers = [m for m in must_contain if m not in text_for_checks]
        if missing_markers:
            return Score(
                value=False,
                explanation=f"Run output missing markers: {missing_markers}",
                metadata={
                    "missing_markers": missing_markers,
                    "output_uri": output_uri,
                    "stdout_text": stdout_text[:2000],
                    "artifact_text": artifact_text[:2000],
                },
            )

        missing_substrings = [s for s in must_output_substrings if s not in text_for_checks]
        if missing_substrings:
            return Score(
                value=False,
                explanation=f"Run output missing required substrings: {missing_substrings}",
                metadata={
                    "missing_output_substrings": missing_substrings,
                    "output_uri": output_uri,
                    "stdout_text": stdout_text[:2000],
                    "artifact_text": artifact_text[:2000],
                },
            )

        # Require some tool usage beyond the scorer's internal validate/run calls.
        if len(tool_messages) < 2:
            return Score(
                value=False,
                explanation="Not enough tool interaction recorded (need >=2 tool messages)",
                metadata={"tool_calls": tool_names},
            )

        return Score(
            value=True,
            explanation="Validated and ran successfully",
            metadata={
                "tool_calls": tool_names,
                "run_id": run_payload.get("run_id"),
                "output_uri": output_uri,
            },
        )

    return score


@task
def snowfakery_mcp_agentic() -> Task:
    """Agentic eval: model must use MCP tools and adapt based on results."""

    root = Path(__file__).resolve().parents[1]

    server = mcp_server_stdio(
        name="snowfakery",
        command="uv",
        args=["run", "snowfakery-mcp"],
        cwd=root,
        env={
            "SNOWFAKERY_MCP_WORKSPACE_ROOT": str(root),
            "SNOWFAKERY_MCP_MAX_REPS": os.environ.get("SNOWFAKERY_MCP_MAX_REPS", "5"),
            "SNOWFAKERY_MCP_MAX_TARGET_COUNT": os.environ.get(
                "SNOWFAKERY_MCP_MAX_TARGET_COUNT", "50"
            ),
            # Keep tool outputs and captured stdout small enough to fit
            # within model context windows (e.g. GitHub Models gpt-5-mini).
            "SNOWFAKERY_MCP_MAX_CAPTURE_CHARS": os.environ.get(
                "SNOWFAKERY_MCP_MAX_CAPTURE_CHARS", "800"
            ),
        },
    )

    # Only expose the tools the cases actually need (reduces tool schema tokens).
    tool_source = mcp_tools(
        server,
        tools=[
            "validate_recipe",
            "run_recipe",
            "analyze_recipe",
            "generate_mapping",
            "list_examples",
            "get_example",
        ],
    )

    samples: list[Sample] = []
    for c in CASES:
        samples.append(
            Sample(
                id=c.id,
                input=(
                    f"TASK: {c.title}\n\n"
                    f"{c.task}\n\n"
                    "Requirements:\n"
                    "- Use available tools/resources to debug/iterate.\n"
                    "- When ready, output ONLY the final Snowfakery recipe YAML.\n"
                ),
                metadata={
                    "must_contain": c.must_contain,
                    "must_call_tools": c.must_call_tools,
                    "must_output_substrings": c.must_output_substrings,
                },
            )
        )

    init = system_message(
        """You are solving Snowfakery recipe tasks.

Use the available tools sparingly to validate, debug, and iterate.
- Keep messages short and avoid pasting large tool outputs.
- Prefer targeted tool calls over broad searches.
- Try to finish in ~3 tool calls.
- Before submitting, you MUST call validate_recipe and run_recipe at least once.
- When ready, call {submit} and provide ONLY the final Snowfakery recipe YAML.
""",
        submit="submit",
    )

    solver = basic_agent(
        init=init,
        tools=use_tools(tool_source),
        max_attempts=1,
        message_limit=14,
        # Truncate tool output included in the chat history.
        max_tool_output=600,
    )

    return Task(
        dataset=samples,
        solver=solver,
        scorer=snowfakery_mcp_recipe_scorer(),
    )


def _print_usage() -> None:
    print("This file defines inspect-ai tasks; running it directly does not execute evals.")
    print()
    print("Run with inspect-ai CLI:")
    print(
        "  uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model <api>/<model_name>"
    )
    print()
    print("Examples:")
    print(
        "  uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model openai/gpt-4o-mini"
    )
    print(
        "  OPENAI_API_KEY=$GITHUB_TOKEN INSPECT_EVAL_MODEL_BASE_URL=https://models.inference.ai.azure.com \\"
    )
    print(
        "  uv run inspect eval evals/inspect_tasks.py@snowfakery_mcp_agentic --model openai/gpt-4o-mini"
    )
    print()
    print("Optional programmatic run:")
    print("  uv run python evals/inspect_tasks.py --model openai/gpt-4o-mini")


def _main(argv: list[str]) -> int:
    if any(a in argv for a in ("-h", "--help")):
        _print_usage()
        return 0

    model: str | None = None
    model_base_url: str | None = None
    display: str | None = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--model" and i + 1 < len(argv):
            model = argv[i + 1]
            i += 2
            continue
        if arg == "--model-base-url" and i + 1 < len(argv):
            model_base_url = argv[i + 1]
            i += 2
            continue
        if arg == "--display" and i + 1 < len(argv):
            display = argv[i + 1]
            i += 2
            continue
        i += 1

    if model is None:
        _print_usage()
        return 0

    inspect_eval(
        "evals/inspect_tasks.py@snowfakery_mcp_agentic",
        model=model,
        model_base_url=model_base_url,
        display=display or "plain",
    )
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
