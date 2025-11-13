# Implementation Checklist

Track Phase 1 tasks for the `linode-cli ai` plugin. Update the checkboxes as functionality lands.

## Foundation
- [x] Create Python package `linodecli_ai` with commands/core/templates directories.
- [x] Implement plugin entrypoint `populate(subparsers, config)` wiring top-level `ai` command.
- [x] Configure packaging metadata (`pyproject.toml` or equivalent) so the plugin can be installed.

## Template Assets
- [x] Add `templates/index.yml` plus at least the `chat-agent/template.yml` definition.
- [x] Provide any auxiliary files needed by templates (`ai.linode.yml`, `.env.example`, etc.).

## Core Helpers
- [x] `core/templates.py`: load/index template metadata.
- [x] `core/cloud_init.py`: render cloud-init scripts for Docker install + container run.
- [x] `core/registry.py`: manage `~/.config/linode-cli/ai-deployments.json`.
- [x] `core/linode_api.py`: thin wrapper for Linode instance CRUD.
- [x] `core/env.py`: handle env var file loading/validation.

## Commands
- [x] `ai templates list` (table output from template index).
- [x] `ai templates show <name>` (detailed view).
- [x] `ai init <template>` (generate project files from template).
- [x] `ai deploy` (parse env, render cloud-init, call Linode API, update registry).
- [x] `ai status [--app --env]` (report deployment states).
- [x] `ai destroy --app --env` (delete Linode + remove registry entry).

## Deployment Tracking & Status
- [x] Persist deployment metadata (id, template, region, linode id, IP/hostname, health, timestamps).
- [x] Update registry with provisioning/running/failed states.
- [x] Derive default hostname `ip.linodeusercontent.com` if API response omits it.

## Validation & Docs
- [ ] Manual test flow: templates → init → deploy → status → destroy.
- [x] Add README.md usage section for the plugin (install, register, commands overview).
- [x] Ensure plugin help text matches UX requirements from Phase 1 plan.
