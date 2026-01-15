# Releasing `snowfakery-mcp`

This repo publishes releases via GitHub Actions.

- A **real release** (GitHub Release + attached artifacts + PyPI publish) happens on **pushing a git tag** matching `v*`.
- A **manual run from the GitHub UI** (`workflow_dispatch`) is supported as a **dry run build**: it builds + (optionally) tests and uploads build artifacts to the workflow run, but it does **not** create a GitHub Release or publish to PyPI.

## Prereqs (local)

- `uv` installed
- Submodule initialized (recommended for local dev/tests):
	- `git submodule update --init --recursive`

## Versioning + tags

- Source of truth version: `pyproject.toml` → `[project].version`
- Release tag format: `vX.Y.Z` (example: `v0.2.0`)
- The release workflow enforces: `tag version == pyproject.toml version`

## Standard release process (recommended)

1. **Update version**
	- Edit `pyproject.toml` and bump `[project].version`.

2. **Run tests locally**
	- `uv sync --all-groups`
	- `uv run pytest`

3. **Land the version bump on `main`**
	- Commit and push the change (PR preferred).

4. **Create and push a tag** (this triggers the release workflow)
	- Annotated tag (recommended):
		- `git tag -a vX.Y.Z -m "vX.Y.Z"`
		- `git push origin vX.Y.Z`
	- Lightweight tag also works:
		- `git tag vX.Y.Z`
		- `git push origin vX.Y.Z`

5. **Monitor GitHub Actions**
	- The `Release` workflow will:
		- checkout submodules
		- run tests
		- build wheel + sdist (`uv build`)
		- build a `.mcpb` bundle (via reusable `build-mcpb.yml` workflow)
		- attach `dist/*` + `release-assets/*` + `mcpb/*` to a GitHub Release (release notes auto-generated)
		- publish `dist/*.whl` + `dist/*.tar.gz` to PyPI via Trusted Publishing (tags only)
		- publish server metadata to MCP Registry (tags only)

## Can I release via the GitHub UI?

Yes — *as long as the UI action creates/pushes the git tag*.

Two common UI paths:

1) **Create a tag in the UI**

- Go to the repo → **Releases** → **Draft a new release**
- Enter a tag like `vX.Y.Z` and choose the target commit (usually `main`)
- Publish the release

This creates the git tag (`refs/tags/vX.Y.Z`), which should trigger the `on: push: tags: ["v*"]` workflow.

2) **Run the workflow manually (UI)**


- Go to **Actions** → **Release** → **Run workflow**

This is useful to verify that builds/tests pass on GitHub runners. It will upload build artifacts to the workflow run, but it will not create a GitHub Release nor publish to PyPI because those steps only run on tag pushes (`refs/tags/v*`).

## What artifacts are produced?

On tag releases, the GitHub Release will include:

- `dist/*.whl` (wheel)
- `dist/*.tar.gz` (sdist)
- `release-assets/*.mcpb` (experimental MCP bundle)

On workflow_dispatch dry runs, the workflow uploads artifacts to the run:

- `pypi-dist/` (wheel + sdist only)
- `release-assets/` (experimental `.mcpb`, `THIRD_PARTY_NOTICES.md`, SBOM)

## Troubleshooting

### Tag/version mismatch

If the workflow fails at “Check tag matches pyproject version”, update `pyproject.toml` to match the intended release version (or retag). The workflow requires exact equality.

### Fixing a broken release tag

If you pushed a bad tag and need to redo it:

- Delete the tag locally: `git tag -d vX.Y.Z`
- Delete the remote tag: `git push origin :refs/tags/vX.Y.Z`
- Fix the code/version, then recreate and push the tag.

(If a GitHub Release was created, delete it in the UI too.)

### PyPI Trusted Publishing setup

The publish job uses OIDC Trusted Publishing (`pypa/gh-action-pypi-publish`). If PyPI isn’t configured to trust this GitHub repo/environment yet, the publish step will fail.


### MCP Registry Publishing

The release workflow automatically publishes server metadata to the MCP Registry after a successful PyPI publish. This uses:

- **server.json**: Contains the MCP Registry metadata (name, description, packages, etc.)
- **manifest.json**: Contains the `mcpName` field that matches the server name in `server.json`
- **GitHub authentication**: Uses pre-authenticated credentials stored as a GitHub Actions secret

The server is published under the namespace `io.github.composable-delivery/snowfakery-mcp`, which is verified against the GitHub organization ownership.

#### Setting up MCP Registry Authentication

The `mcp-publisher` tool uses an interactive OAuth device flow for GitHub authentication, which doesn't work in CI/CD. To enable automated publishing:

1. **Authenticate locally** (one-time setup):
   ```bash
   mcp-publisher login github
   ```
   Follow the prompts to complete the OAuth device flow.

2. **Locate credentials file**:
   The credentials are typically stored in `~/.mcp-publisher/credentials.json` or `~/.config/mcp-publisher/credentials.json`

3. **Add to GitHub Actions secrets**:
   - Go to repository Settings → Secrets and variables → Actions
   - Create a new secret named `MCP_REGISTRY_CREDENTIALS`
   - Paste the contents of the credentials file

4. **Verify in workflow**:
   The release workflow will restore these credentials before publishing to the registry.
