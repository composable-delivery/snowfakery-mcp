# Publish MCP Registry (composite action)

This composite action publishes an MCP server to the MCP Registry.

- Default auth: **GitHub OIDC** (no repository secret required)
- Optional auth: **GitHub PAT** via `github-token`

## Required workflow permissions

Your workflow/job must include:

- `permissions: id-token: write` (required for OIDC)
- `permissions: contents: read`

## Inputs

- `version` (required): Version to set in `server.json` (and `manifest.json` if present)
- `github-token` (optional): PAT with `read:org` and `read:user` scopes; if omitted, uses OIDC
- `python-version` (optional, default `3.12`)
- `server-json-path` (optional, default `server.json`)
- `manifest-json-path` (optional, default `manifest.json`)

## Example

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v6

      - uses: ./.github/actions/publish-mcp-registry
        with:
          version: "0.2.0"
          # github-token: ${{ secrets.MCP_GITHUB_TOKEN }} # optional
```

## Notes

- `server.json` is treated as required.
- `manifest.json` is updated if present.
- If you supply `github-token`, the action uses PAT auth; otherwise it uses OIDC.
