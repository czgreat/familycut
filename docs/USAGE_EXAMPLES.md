# Usage and API Examples

**Language:** English | [中文](USAGE_EXAMPLES.zh-CN.md)

These examples use public-safe placeholder data. Replace URLs, tokens, paths, and settings before running them in your own environment, and make sure you are allowed to process the target data.

## Example 1: Backend health

Start the compose stack and verify the backend before opening web apps.

## Example 2: Local web development

Run admin and mobile web apps separately against a local backend while iterating UI changes.

## curl Examples

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/docs
```

Request bodies can change between versions; use local `/docs` or the source model definitions as the final reference.


## Local Validation Tips

- Start from `README.md` and bring the service up first.
- Call the health endpoint before running operations that write state or send notifications.
- Use synthetic or public demo data; do not paste private data into issues, screenshots, or commits.
- When using an AI assistant, provide this file, the deployment guide, and sanitized logs.
