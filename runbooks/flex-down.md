# Flex Down Runbook
- Check ICMP probe in Prometheus (blackbox_icmp_flex)
- Check SMB TCP:445 (blackbox_tcp_smb)
- If both fail: host down or network; escalate.
- If ICMP up but TCP down: check SMB service on target.
