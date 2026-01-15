import html
import json
import sys
from pathlib import Path
from typing import Any


def _val_to_str(v: Any) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v, indent=2)
    return str(v)


def _render_messages(messages: list[dict[str, Any]]) -> str:
    out = []
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")

        # Handle content being a list (e.g. text + images, though rare here)
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                else:
                    text_parts.append(str(part))
            content = "\n".join(text_parts)

        content_str = str(content)

        # Specific styling for different roles
        style_class = f"msg-{role}"

        extra_info = ""
        if role == "tool":
            fn = m.get("function", "unknown")
            extra_info = f" <span class='tool-name'>({fn})</span>"

        # Simplify tool output if it's huge JSON
        if role == "tool" and len(content_str) > 1000:
            content_str = content_str[:1000] + "... (truncated)"

        # Escape HTML
        safe_content = html.escape(content_str)

        # Preserve newlines in pre tags
        out.append(f"""
        <div class="message {style_class}">
            <div class="header"><strong>{role.upper()}</strong>{extra_info}</div>
            <pre class="content">{safe_content}</pre>
        </div>
        """)
    return "\n".join(out)


def generate_report(log_path: Path, output_path: Path):
    data = json.loads(log_path.read_text(encoding="utf-8"))

    eval_meta = data.get("eval", {})
    model = eval_meta.get("model", "unknown")
    task = eval_meta.get("task", "unknown")

    samples = data.get("samples", [])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Snowfakery MCP Eval: {task}</title>
        <style>
            body {{ font-family: sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1, h2 {{ color: #333; }}
            .summary {{ margin-bottom: 20px; padding: 10px; background: #e9ecef; border-radius: 4px; }}
            .sample {{ margin-bottom: 30px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; }}
            .sample-header {{ padding: 10px; background: #f8f9fa; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }}
            .score-pass {{ color: green; font-weight: bold; }}
            .score-fail {{ color: red; font-weight: bold; }}
            .messages {{ padding: 10px; }}
            .message {{ margin-bottom: 10px; }}
            .msg-user {{ background-color: #e3f2fd; padding: 8px; border-radius: 4px; }}
            .msg-assistant {{ background-color: #f1f8e9; padding: 8px; border-radius: 4px; border-left: 4px solid #8bc34a; }}
            .msg-tool {{ background-color: #fff3e0; padding: 8px; border-radius: 4px; font-size: 0.9em; }}
            .header {{ font-size: 0.8em; color: #666; margin-bottom: 5px; }}
            .tool-name {{ font-family: monospace; color: #d84315; }}
            pre.content {{ margin: 0; white-space: pre-wrap; word-wrap: break-word; }}
            .metadata {{ font-size: 0.85em; color: #555; background: #eee; padding: 8px; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="summary">
                <h1>Eval Report</h1>
                <p><strong>Task:</strong> {task}</p>
                <p><strong>Model:</strong> {model}</p>
                <p><strong>Total Samples:</strong> {len(samples)}</p>
            </div>
    """

    for sample in samples:
        sid = sample.get("id")
        scores = sample.get("scores", {}).get("snowfakery_mcp_recipe", {})
        is_pass = scores.get("value")
        explanation = scores.get("explanation", "")
        metadata = scores.get("metadata", {})

        score_class = "score-pass" if is_pass else "score-fail"
        score_text = "PASS" if is_pass else "FAIL"

        messages_html = _render_messages(sample.get("messages", []))

        meta_html = ""
        if metadata:
            meta_json = json.dumps(metadata, indent=2)
            meta_html = f'<div class="metadata"><strong>Results Metadata:</strong><pre>{meta_json}</pre></div>'

        html_content += f"""
        <div class="sample">
            <div class="sample-header">
                <span><strong>ID:</strong> {sid}</span>
                <span class="{score_class}">{score_text}</span>
            </div>
            <div style="padding: 10px; border-bottom: 1px dashed #eee;">
                <strong>Explanation:</strong> {html.escape(str(explanation))}
            </div>
            <div class="messages">
                {messages_html}
            </div>
            {meta_html}
        </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """

    output_path.write_text(html_content, encoding="utf-8")
    print(f"Generated report: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python html_report.py <log_file.eval> <output_file.html>")
        sys.exit(1)

    log_file = Path(sys.argv[1])
    out_file = Path(sys.argv[2])
    generate_report(log_file, out_file)
