# Buildhelper CLI

Buildhelper is a Click-powered command line façade that unifies multiple developer workflows (SCM, analysis, and code review) behind a single, backend-agnostic interface. Projects pick their desired tooling through configuration and buildhelper wires commands to the appropriate backend implementation while keeping session state in Click's context store.

## Architecture overview

### Command groups
- **`scm`**: Source control lifecycle (sync, status, submit).
- **`analysis`**: Static analysis and reporting (scan, report).
- **`review`**: Code review actions (create, comment, approve).
- **`workflow`**: Orchestrated, reusable command sequences defined in configuration.

Commands are defined in `cli.py` as Click subcommands. Each command emits a human-readable banner (e.g., `[scm] Executing sync`) to verify invocation even when backends are silent.

### Context store and session management
- The top-level `cli` command initializes a shared context dictionary containing configuration, environment, session cache, selected runner, workflow state, and verbosity settings.
- The `ensure_session` decorator guarantees that a backend instance is connected before any domain command runs. It resolves the backend name from configuration (`backends.<domain>`), instantiates it via `backends.get_backend`, and calls `connect()` once per context lifetime.
- Connected backends live in `ctx.obj["sessions"]`, so repeated invocations reuse the same session.

### Backend registry
- Abstract interfaces live in `backends.py` (`SCMBackend`, `AnalysisBackend`, `ReviewBackend`).
- Concrete backends register themselves with `register_backend(domain, name, backend_cls)`.
- `get_backend(domain, name, config, env)` retrieves the registered class, merges base and environment-specific settings (`backend_configs` plus `envs.<env>.backend_configs`), and instantiates the backend.
- Plugin discovery loads external registrations via the `buildhelper.plugins` entry-point group, enabling third-party packages to add backends or commands without modifying core code.

### Runner abstraction
- `runners.py` defines a `Runner` interface for executing shell commands in different environments.
- Implementations: `LocalRunner`, `DockerRunner`, and `K8sRunner`.
- `get_runner(env, config)` selects the proper runner using `envs.<env>.runner` overrides, defaulting to local execution.
- The runner instance is stored in the context for any backend or workflow step needing shell access.

### Workflows
- Configuration can define workflows as ordered step lists. Each step is a command string or argument array, executed via `cli.invoke` while sharing the same context (and therefore the same sessions/runner/state).
- Workflow execution announces its start, counts steps, and stops on first failure unless `--continue-on-error` is provided. Failures are aggregated for a final status message.
- Telemetry captures per-step timing so you can inspect slow or failing workflow stages.

### Logging
- `logging_utils.py` centralizes logging configuration. The `--verbose` and `--quiet` flags map to DEBUG/ERROR levels respectively and are mutually exclusive to avoid conflicting settings, ensuring consistent log output across commands.

### Context typing and session caching
- `context_state.py` wraps Click's `ctx.obj` in a typed `ContextState` so shared fields (config, env, runner, telemetry, cache) remain discoverable and uniform.
- `session_cache.py` persists backend session metadata (e.g., tokens) to `~/.buildhelper/sessions.yaml` or a configured path, allowing backends to restore state across CLI runs via optional `restore_session`/`export_session` hooks.

### Telemetry
- `telemetry.py` records command durations and statuses through a decorator (`@telemetry_event`) and a context manager (`TelemetryCollector.track`).
- Workflow steps automatically emit telemetry, and individual commands record success or failure timing.

## Configuration format

Example `config.yaml`:

```yaml
env: local
backends:
  scm: git
  analysis: sonar
  review: bitbucket
backend_configs:
  git:
    url: https://git.example.com
    token: ${GIT_TOKEN}
  sonar:
    host: https://sonarqube.example.com
    token: ${SONAR_TOKEN}
  bitbucket:
    host: https://bitbucket.example.com
    user: ci
    app_password: ${BB_APP_PASSWORD}
envs:
  docker:
    runner:
      type: docker
      container: ci-tools
  k8s:
    runner:
      type: k8s
      namespace: tooling
      pod: ci-runner
workflows:
  full-check:
    - "scm sync"
    - ["analysis", "scan"]
    - ["analysis", "report", "--format", "json"]
    - ["review", "create", "--subject", "Automated review"]
```

- `backends` maps each domain to a backend name.
- `backend_configs` stores backend-specific settings. Environment-specific overrides live under `envs.<env>.backend_configs.<name>`.
- `envs.<env>.runner` selects and configures the execution runner.
- `workflows` lists reusable sequences of commands.
- Configuration is validated for expected mapping shapes during startup to catch typos early.

## Usage

Initialize the CLI with a configuration file and optional environment:

```bash
python -m cli --config config.yaml --env docker --verbose scm sync
python -m cli --config config.yaml --env docker --quiet scm status
```

Common commands:
- `scm sync` / `scm status` / `scm submit --message "Ready"`
- `analysis scan` / `analysis report --format json`
- `review create --subject "Feature"` / `review comment --body "Looks good"` / `review approve --message "Ship it"`
- `workflow run <name> [--continue-on-error]`

Because commands print their invocation banners, you will always see output verifying that the right handler ran even if the backend returns nothing.

## Development and testing

- Install dependencies: `pip install -r requirements-dev.txt`
- Run tests: `pytest`
- Add new backends by subclassing the relevant interface in `backends.py` and registering the class with `register_backend`.
- When implementing commands, rely on the shared context for sessions, runners, and workflow state to keep behavior consistent across domains and workflows.

## Adding a new command group

Follow the pattern below to introduce a new domain (for example, **`deploy`**) and wire it to backends:

1. **Create a backend interface** in `backends.py` if the domain needs specific methods (e.g., `DeployBackend` with `plan`/`apply`).
2. **Implement concrete backends** in a module of your choice and register them:

   ```python
   from backends import register_backend, BaseBackend


   class DummyDeployBackend(BaseBackend):
       def connect(self):
           ...

       def plan(self):
           return "planned"

       def apply(self):
           return "applied"


   register_backend("deploy", "dummy", DummyDeployBackend)
   ```

3. **Declare a Click group** in `cli.py` and route commands through `ensure_session("deploy")` to reuse the standard session lifecycle:

   ```python
   @cli.group()
   @click.pass_context
   def deploy(ctx):
       ctx.ensure_object(dict)


   @deploy.command()
   @ensure_session("deploy")
   def plan(ctx):
       click.echo("[deploy] Planning")
       result = ctx.obj["sessions"]["deploy"].plan()
       if result is not None:
           click.echo(result)
   ```

4. **Expose the backend in configuration** by adding `deploy: dummy` under `backends:` and optional settings under `backend_configs.dummy` and `envs.<env>.backend_configs.dummy`.
5. **Extend workflows** with `deploy` steps so they participate in orchestrated runs.

This pattern keeps new domains consistent with existing ones and requires minimal boilerplate beyond defining the interface and commands specific to the domain.

## Optimization opportunities

Below are additional improvements that can make Buildhelper more robust and extensible:

1. **Plugin discovery**: load additional command groups and backends via Python entry points so external packages can extend the CLI without modifying `cli.py`.
2. **Schema-validated configuration**: enforce a JSON Schema or Pydantic model for `config.yaml` to provide early feedback on typos, missing sections, or invalid values.
3. **Connection pooling and caching**: cache authentication tokens or session handles across runs (optionally via a shared cache directory) to reduce repeated logins.
4. **Typed context objects**: wrap `ctx.obj` in lightweight dataclasses to improve type safety and editor auto-completion when commands consume shared state.
5. **Telemetry hooks**: instrument command durations and failures (with opt-in/opt-out) to highlight slow or error-prone workflows and guide future optimizations.

## Extensibility tips

- **New domains**: Add an interface, extend `BACKEND_REGISTRY`, and create a new Click group mirroring the existing ones.
- **Backends**: Keep `connect()` lightweight; it is invoked lazily via `ensure_session` the first time any command for that domain runs.
- **Workflows**: Use simple strings for most steps; supply explicit argument arrays when you need to pass flags without shell parsing ambiguity.
- **Runners**: Implement additional environment runners by subclassing `Runner` and updating `get_runner` to route to them.

