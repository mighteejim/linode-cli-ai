# Implementation Summary: BuildWatch as Optional Capability

## Overview

Successfully converted BuildWatch from an automatically-installed feature to an optional capability that users explicitly declare in their template YAML files. This implementation follows the same pattern as other capabilities like `docker`, `gpu-nvidia`, and `redis`.

## Changes Made

### 1. Core Capability System (`linodecli_build/core/capabilities.py`)

#### BuildWatchCapability Class
- **Updated constructor** to accept optional configuration parameters:
  - `port` (default: 9090)
  - `log_retention_days` (default: 7)
  - `enable_metrics` (default: True)
- **Added validation** for all parameters:
  - `deployment_id` and `app_name` are required
  - Port must be 1024-65535
  - Log retention must be 1-365 days

#### CapabilityManager Class
- **Registered BuildWatch** in `_CAPABILITY_MAP`:
  ```python
  "buildwatch": lambda config: BuildWatchCapability(
      deployment_id=config.get("deployment_id"),
      app_name=config.get("app_name"),
      port=config.get("port", 9090),
      log_retention_days=config.get("log_retention_days", 7),
      enable_metrics=config.get("enable_metrics", True)
  )
  ```
- **Updated `add_from_config()`** to accept `deployment_id` and `app_name` parameters
- **Added special handling** for BuildWatch to inject deployment context
- **Removed `add_buildwatch()`** method (no longer needed)

#### create_capability_manager Function
- **Added parameters**: `deployment_id` and `app_name`
- **Updated signature**:
  ```python
  def create_capability_manager(
      template_data: Dict[str, Any], 
      deployment_id: str = None, 
      app_name: str = None
  ) -> Optional[CapabilityManager]
  ```

### 2. Deploy Command (`linodecli_build/commands/deploy.py`)

- **Updated capability manager creation** to pass deployment context:
  ```python
  capability_manager = capabilities.create_capability_manager(
      template.data,
      deployment_id=deployment_id,
      app_name=app_name
  )
  ```
- **Removed automatic BuildWatch addition**:
  - Deleted line: `capability_manager.add_buildwatch(deployment_id, app_name)`

### 3. Template Updates

#### Added BuildWatch to Templates
Updated the following templates to include BuildWatch:

**llm-api/template.yml**
```yaml
capabilities:
  runtime: docker
  features:
    - gpu-nvidia
    - docker-optimize
    - buildwatch  # NEW
```

**chat-agent/template.yml**
```yaml
capabilities:
  runtime: docker
  features:
    - buildwatch  # NEW
```

**ml-pipeline/template.yml**
```yaml
capabilities:
  runtime: docker
  features:
    - gpu-nvidia
    - docker-optimize
    - redis
    - buildwatch  # NEW
```

#### Left Without BuildWatch
**embeddings-python/template.yml** - Intentionally left without BuildWatch to demonstrate it's optional.

### 4. Documentation Updates

#### template-development.md
- **Added BuildWatch to capabilities table**
- **Added comprehensive BuildWatch section** including:
  - Basic usage example
  - Configuration options
  - Features list
  - API endpoints
  - When to use / when to skip guidance

#### template-quick-reference.md
- **Added buildwatch** to the features example

### 5. Migration Guide

Created **BUILDWATCH_OPTIONAL_CAPABILITY.md** with:
- Breaking change notice
- Before/after migration examples
- Configuration options documentation
- Updated templates list
- Benefits of the change
- When to use BuildWatch guidance
- Troubleshooting section

## Testing

Created and ran comprehensive tests verifying:
- ✅ Simple BuildWatch declaration (string in features list)
- ✅ Configured BuildWatch (dict with custom config)
- ✅ Parameter validation (port, retention, deployment_id)
- ✅ BuildWatch NOT added when not in features
- ✅ Cloud-init fragment generation
- ✅ Python syntax validation
- ✅ YAML syntax validation

All tests passed successfully.

## Usage Examples

### Simple (Default Config)

```yaml
capabilities:
  features:
    - buildwatch
```

### Advanced (Custom Config)

```yaml
capabilities:
  features:
    - name: buildwatch
      config:
        port: 9090
        log_retention_days: 14
        enable_metrics: true
```

## Breaking Changes

⚠️ **BREAKING CHANGE**: BuildWatch is no longer automatically installed.

### Migration Required
Users who want BuildWatch must now add it to their template's `capabilities.features` list.

### Backward Compatibility
None - this is a breaking change. However, the migration is straightforward:
1. Add `buildwatch` to features list
2. Redeploy

## Benefits

1. **User Control** - Users decide if they want monitoring
2. **Resource Efficiency** - No overhead for deployments that don't need it
3. **Consistent Pattern** - Follows same pattern as other capabilities
4. **Configurable** - Users can customize port, retention, metrics
5. **Explicit** - Template clearly shows what's installed
6. **Discoverable** - Feature visible in template YAML
7. **Testable** - Easier to test with/without BuildWatch

## Files Modified

```
 docs/template-development.md                       | 53 +++++++++++++++
 docs/template-quick-reference.md                   |  1 +
 linodecli_build/commands/deploy.py                 | 11 ++--
 linodecli_build/core/capabilities.py               | 75 +++++++++++++++++-----
 linodecli_build/templates/chat-agent/template.yml  |  2 +
 linodecli_build/templates/llm-api/template.yml     |  1 +
 linodecli_build/templates/ml-pipeline/template.yml |  1 +
 7 files changed, 122 insertions(+), 22 deletions(-)
```

## Files Created

1. **BUILDWATCH_OPTIONAL_CAPABILITY.md** - Comprehensive migration guide

## Validation

All changes validated:
- ✅ Python syntax check (capabilities.py, deploy.py)
- ✅ YAML validation (all template files)
- ✅ Comprehensive functionality tests
- ✅ Git status clean (no unexpected files)

## API Compatibility

The changes maintain internal API compatibility for:
- Cloud-init generation
- Fragment assembly
- Capability validation

The only breaking change is the removal of automatic BuildWatch installation, which is intentional.

## Next Steps

1. ✅ Code changes implemented
2. ✅ Tests passed
3. ✅ Documentation updated
4. ✅ Migration guide created
5. Ready to commit and push

## Commit Message

```
feat: Make BuildWatch an optional capability

BREAKING CHANGE: BuildWatch is no longer automatically installed.
Users must explicitly add 'buildwatch' to capabilities.features in
their template YAML files.

Changes:
- Register BuildWatch in capability registry
- Add configuration options (port, log_retention_days, enable_metrics)
- Add validation for BuildWatch parameters
- Update capability manager to pass deployment context
- Remove automatic BuildWatch installation from deploy command
- Add buildwatch to llm-api, chat-agent, ml-pipeline templates
- Update documentation with BuildWatch usage
- Create migration guide (BUILDWATCH_OPTIONAL_CAPABILITY.md)

Benefits:
- User control over monitoring overhead
- Resource efficiency for simple deployments
- Consistent with other capabilities (gpu-nvidia, redis, etc.)
- Configurable monitoring parameters
- Explicit template declarations

Migration:
Add 'buildwatch' to capabilities.features in templates that need monitoring.

See BUILDWATCH_OPTIONAL_CAPABILITY.md for detailed migration guide.
```

## Implementation Complete

All tasks from the plan have been successfully implemented and tested:
- ✅ Capability registration and configuration
- ✅ Deploy command updates
- ✅ Template updates
- ✅ Documentation updates
- ✅ Migration guide
- ✅ Validation and testing

The implementation is production-ready and follows best practices for breaking changes with comprehensive documentation and clear migration paths.
