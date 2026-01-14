# Community Guide

This project welcomes contributions and conversations at any level. This document explains where to ask questions, how to report bugs, and how maintainers triage and track work.

Discussions
- Enable GitHub Discussions in the repository settings to provide a low-friction place for:
  - Questions & Answers (usage help)
  - How-to guides and examples
  - Design proposals and RFC-style conversations
  - Show-and-tell: community examples and integrations

Suggested Discussion categories and quick prompts
- Q&A: "How do I generate 100 Accounts with related Contacts?"
- How-to: "How to write a macro for reusable address blocks"
- Ideas: "Proposal: add a `--preview` mode to the server"
- Show-and-tell: "Example: Snowfakery recipe for a product catalog"

Issues
- Use Issues for reproducible bugs and scoped feature requests. Include:
  - Expected vs actual behaviour
  - Minimal reproduction (recipe snippet)
  - Environment (OS, Python)
  - Whether you ran from a release or from source

Maintainer triage flow
1. New Discussions are read by maintainers and optionally converted to Issues when actionable.
2. Issues are labeled and prioritized by maintainers.
3. Accepted Issues are added to the project board and assigned an owner or milestone.

Pull requests
- Keep PRs small and focused. Link to the Issue they address. Add tests where applicable.

Repository templates
You can add the following files under `.github/` to improve contributor experience:

- ISSUE_TEMPLATE/bug.yml — fields for reproduction steps, env, expected/actual
- ISSUE_TEMPLATE/feature_request.yml — short form to capture motivation and acceptance
- PULL_REQUEST_TEMPLATE.md — checklist for tests and changelog notes
- DISCUSSION_TEMPLATES/* — optional discussion starters

Enabling Discussions
- Only a repository admin can enable Discussions. To enable:
  1. Go to the repository Settings → Features
  2. Check "Discussions"
  3. Add categories and any templates you want to expose

If you'd like, I can open a PR adding suggested `.github/ISSUE_TEMPLATE` and `.github/PULL_REQUEST_TEMPLATE.md` files and sample Discussion templates.
