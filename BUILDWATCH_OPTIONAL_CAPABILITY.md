# BuildWatch: Now an Optional Capability

## Summary

BuildWatch has been converted from an automatically-installed feature to an **optional capability** that users explicitly declare in their template YAML files. This change gives users control over monitoring overhead and follows the same pattern as other capabilities like `docker`, `gpu-nvidia`, and `redis`.

## Breaking Change Notice

⚠️ **BREAKING CHANGE**: BuildWatch is no longer automatically installed on every deployment.

If you want BuildWatch monitoring, you must now add it to your template's `capabilities.features` list.

## Migration Guide

### Before (Automatic)

Previously, BuildWatch was automatically added to every deployment:

```yaml
# deploy.yml or template.yml
capabilities:
  runtime: docker
  features:
    - gpu-nvidia
    - docker-optimize

# BuildWatch was automatically installed (no user control)
```

### After (Explicit)

Now, you must explicitly add `buildwatch` to enable monitoring:

```yaml
# deploy.yml or template.yml
capabilities:
  runtime: docker
  features:
    - gpu-nvidia
    - docker-optimize
    - buildwatch  # NEW: Explicitly enable BuildWatch
```

## Configuration Options

### Simple (Default Settings)

Just add `buildwatch` to use default configuration:

```yaml
capabilities:
  features:
    - buildwatch
```

**Defaults:**
- Port: 9090
- Log retention: 7 days
- Metrics: enabled

### Advanced (Custom Settings)

Configure BuildWatch with custom parameters:

```yaml
capabilities:
  features:
    - name: buildwatch
      config:
        port: 9090              # HTTP API port (default: 9090)
        log_retention_days: 14  # Keep logs for 2 weeks
        enable_metrics: true    # Resource metrics (default: true)
```

## Updated Templates

The bundled templates have been updated as follows:

### Templates WITH BuildWatch

These templates now explicitly include `buildwatch`:

- **llm-api** - GPU workload monitoring for vLLM inference
- **chat-agent** - Monitor Ollama chat service
- **ml-pipeline** - Track PyTorch pipeline jobs

Example (`llm-api/template.yml`):
```yaml
capabilities:
  runtime: docker
  features:
    - gpu-nvidia
    - docker-optimize
    - buildwatch  # Monitor GPU workloads
```

### Templates WITHOUT BuildWatch

These templates don't include BuildWatch (demonstrating it's optional):

- **embeddings-python** - Simple deployment, no monitoring overhead

## What You Need to Do

### For New Deployments

Simply use the updated templates or add `buildwatch` to your custom templates if desired.

### For Existing Deployments

If you're using a custom `deploy.yml` based on an older template:

1. Open your `deploy.yml` file
2. Add `buildwatch` to the `capabilities.features` list if you want monitoring:

```yaml
capabilities:
  runtime: docker
  features:
    - buildwatch  # Add this line
```

3. Redeploy:

```bash
linode-cli build deploy --wait
```

## Benefits of This Change

### 1. User Control
Users decide whether they want monitoring overhead.

### 2. Resource Efficiency
No BuildWatch service running on deployments that don't need it.

### 3. Consistent Pattern
BuildWatch follows the same pattern as other capabilities (`gpu-nvidia`, `redis`, etc.).

### 4. Configurable
Users can customize port, log retention, and metrics collection.

### 5. Explicit
Template clearly shows what's being installed and configured.

### 6. Discoverable
Feature is visible in template YAML, making it easier to understand what's deployed.

## BuildWatch Features

When enabled, BuildWatch provides:

- **Real-time Docker event streaming**
- **Automatic issue detection** (OOM kills, crash loops, restarts)
- **HTTP API** on port 9090
- **Container lifecycle tracking**
- **Resource metrics collection**

### API Endpoints

- `http://<instance-ip>:9090/health` - Service health check
- `http://<instance-ip>:9090/status` - Current deployment status
- `http://<instance-ip>:9090/events` - Recent Docker events
- `http://<instance-ip>:9090/issues` - Detected issues and alerts

## When to Use BuildWatch

✅ **Recommended for:**
- GPU workloads (detect OOM issues)
- Production deployments (issue alerting)
- Long-running services (uptime tracking)
- Development environments (debugging container issues)

❌ **Skip for:**
- Simple test deployments
- Minimal resource usage requirements
- Deployments without Docker containers
- When you don't need monitoring

## Example: Adding BuildWatch to Your Template

### Basic Template

```yaml
name: my-api
display_name: My API
version: 0.1.0

description: |
  My custom API deployment.

capabilities:
  runtime: docker
  features:
    - buildwatch  # Add BuildWatch monitoring

deploy:
  target: linode
  linode:
    image: linode/ubuntu24.04
    region_default: us-ord
    type_default: g6-standard-4
    
    container:
      image: myorg/myapi:latest
      internal_port: 8000
      external_port: 80
      
      health:
        type: http
        path: /health
        port: 8000
        success_codes: [200]
        initial_delay_seconds: 30
        timeout_seconds: 5
        max_retries: 12
```

### GPU Template with Custom BuildWatch Config

```yaml
name: gpu-inference
display_name: GPU Inference API
version: 0.1.0

description: |
  GPU-accelerated inference API with custom monitoring.

capabilities:
  runtime: docker
  features:
    - gpu-nvidia
    - docker-optimize
    - name: buildwatch
      config:
        port: 8080           # Custom port
        log_retention_days: 14  # 2-week retention
        enable_metrics: true

deploy:
  target: linode
  linode:
    image: linode/ubuntu22.04
    region_default: us-mia
    type_default: g6-standard-8
    
    container:
      image: pytorch/pytorch:2.0-cuda11.7
      internal_port: 8000
      external_port: 80
      
      health:
        type: http
        path: /health
        port: 8000
        success_codes: [200]
        initial_delay_seconds: 180
        timeout_seconds: 10
        max_retries: 60
```

## Validation

BuildWatch validates configuration parameters:

- **deployment_id**: Required (automatically provided by deploy command)
- **app_name**: Required (automatically provided by deploy command)
- **port**: Must be 1024-65535
- **log_retention_days**: Must be 1-365 days

Invalid configurations will fail during deployment with clear error messages.

## Troubleshooting

### Error: BuildWatch requires deployment_id

This error occurs if BuildWatch is used outside the standard deployment flow. BuildWatch needs deployment context which is automatically provided by `linode-cli build deploy`.

**Solution**: Ensure you're using the standard deploy command, not manually constructing cloud-init configs.

### Error: Invalid port

Port must be in the range 1024-65535.

**Solution**: Use a valid port in your config:
```yaml
- name: buildwatch
  config:
    port: 9090  # Valid port
```

### BuildWatch API not responding

Check that:
1. BuildWatch is in your features list
2. The service started successfully: `ssh root@<ip> 'systemctl status build-watcher'`
3. The correct port is used (default: 9090)
4. Firewall allows access to the port

## Documentation

For more information:

- [Template Development Guide](docs/template-development.md) - Complete template documentation
- [Template Quick Reference](docs/template-quick-reference.md) - Quick capability reference
- [BuildWatch Usage Guide](docs/buildwatch-usage.md) - Detailed BuildWatch documentation

## Questions?

If you have questions about this change or need help migrating:

- GitHub Issues: [linode-cli-ai/issues](https://github.com/linode/linode-cli-ai/issues)
- Community Forum: [Linode Community](https://www.linode.com/community/)

---

**Version**: Effective as of template system v2.0
**Date**: 2025-11-20
