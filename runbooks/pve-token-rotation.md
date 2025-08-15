# Proxmox Exporter Token Rotation

1) In Proxmox UI, create a new API token for `root@pam` (or service user)
2) Update `docker/pve-exporter/pve.yml`:
```
default:
  verify_ssl: false
  user: root@pam
  token_name: <new_token_name>
  token_value: <new_token_secret>
```
3) Restart exporter: `docker restart pve-exporter`
4) Verify Prometheus target `pve` is UP
