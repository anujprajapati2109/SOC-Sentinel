# Contributing to SOC Sentinel

SOC Sentinel is a cybersecurity platform, so changes must be deliberate, reviewable, and easy to test.

## Coding Style

- Use Python 3.12+.
- Follow PEP 8.
- Use type hints for new Python code.
- Keep route handlers thin.
- Put business logic in services.
- Keep detection and correlation rules independent.
- Avoid hardcoded environment values such as local IP addresses, secrets, or absolute user paths.
- Add comments only where the code is not obvious.

## Branch Naming

Use short, descriptive branch names:

```text
feature/endpoint-response-history
fix/heartbeat-timeout
docs/cloud-deployment-guide
chore/repository-cleanup
```

## Commit Messages

Use clear imperative commit messages:

```text
Add endpoint response command history
Fix telemetry severity badge rendering
Document Oracle Cloud deployment
Remove generated build artifacts
```

## Pull Request Process

1. Keep pull requests focused on one feature, fix, or documentation update.
2. Explain the reason for the change.
3. List the files and modules affected.
4. Include manual test steps.
5. Confirm that no runtime secrets, logs, databases, or binaries are included.
6. Request review before merging.

## Security Contributions

Do not open public pull requests containing real credentials, production logs, API keys, endpoint identifiers, private IP inventories, or incident evidence from a real environment.

For sensitive security issues, report privately to the maintainer instead of publishing exploit details in an issue.
