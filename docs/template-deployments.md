# Template Deployment Workflow

This plugin assumes a simple, repeatable project layout. Every project created
via `linode-cli ai init <template>` contains:

1. **`ai.linode.yml`** – Manifest describing which template is in use plus
   default deploy settings (region, Linode type, app/env names, env file path).
2. **`.env`** – User-provided environment variables that will be injected into
   the container.
3. **Template README** – Quickstart notes specific to the chosen template.

## Lifecycle

1. Scaffold the project:
   ```bash
   linode-cli ai init chat-agent --directory chat-demo
   cd chat-demo
   cp .env.example .env  # populate values
   ```
2. Deploy:
   ```bash
   linode-cli ai deploy --region us-chi --linode-type g6-standard-2 --wait
   ```
3. Inspect:
   ```bash
   linode-cli ai status
   ```
4. Tear down when finished:
   ```bash
   linode-cli ai destroy --app chat-agent --env default
   ```

## `ai.linode.yml`

Example manifest:

```yaml
template:
  name: chat-agent
  version: 0.1.0
deploy:
  region: us-chi
  linode_type: g6-standard-2
  app_name: chat-agent
  env: default
env:
  file: .env
```

- `template`: Identifies which template definition should be loaded.
- `deploy.region` and `deploy.linode_type`: Defaults that can be overridden at
  deploy time (`--region`, `--linode-type`).
- `deploy.app_name`/`deploy.env`: Tags recorded in the registry and added as
  Linode tags.
- `env.file`: Relative path to the environment file that will be parsed.

## `.env` Files

The plugin reads `.env` (or the file specified in `env.file`). Format is
standard `KEY=VALUE` lines. Comments begin with `#`.

- Required variables are validated per-template; deployment fails if any are
  missing.
- Optional variables may be left blank (or omitted) if the template supports
  sensible defaults.
- Values are injected into `/etc/build-ai.env` on the Linode and passed to
  Docker via `--env-file`.

See the docs under `linodecli_ai/templates/<template>/docs/` for a full list of
supported variables and template-specific usage tips.
