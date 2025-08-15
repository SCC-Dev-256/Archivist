# Contributing to Archivist Monitoring

## Prerequisites
- Docker and Docker Compose
- Access to the VM or local environment with required ports

## Run the monitoring stack locally
1) Copy `.env.example` to `.env` and set placeholders as needed.
2) From the repo root:
```
sudo docker compose up -d prometheus grafana blackbox-exporter node-exporter process-exporter pve-exporter redis-exporter postgres-exporter alertmanager celery-exporter
```
3) Verify:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (login: admin / GF_ADMIN_PASSWORD)
- Alertmanager: http://localhost:9093

## Making changes to dashboards
- Place JSON panels in `docker/grafana/dashboards/`.
- Provisioning is in `docker/grafana/provisioning/dashboards/dashboards.yaml`.
- After editing JSON, restart Grafana:
```
docker restart archivist-grafana
```
- Add screenshots and a short note in PR description.

## Making changes to alerts
- Edit/add files in `docker/prometheus/alerting/*.yml`.
- Validate with `promtool` if available.
- Reload Prometheus:
```
curl -X POST http://localhost:9090/-/reload
```
- Include example firing conditions in the PR.

## File_sd targets
- Update `docker/prometheus/file_sd/*.yml` for Flex hosts and labels.
- Reload Prometheus as above.

## Coding style for configs
- Keep YAML formatted and alphabetize labels.
- Use host networking for local dev (as in compose) to simplify connections.

## Secrets
- Never commit `.env`. Use `.env.example` to demonstrate structure.

## PR checklist
- [ ] Dashboards render without 500s (Grafana datasource points to running Prometheus)
- [ ] Prometheus reloads cleanly; no errors in logs
- [ ] New alerts include severity and meaningful annotations
- [ ] Docs updated (monitoring.md / runbooks) when behavior changes
