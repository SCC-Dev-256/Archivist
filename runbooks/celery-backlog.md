# Celery Backlog Response & Scaling

## Symptoms
- `CeleryQueueBacklogHigh/Critical` alerts
- Growing `celery_queue_length`

## Actions
1) Inspect queues
```
curl -s http://127.0.0.1:9808/metrics | grep celery_queue_length
```
2) Scale workers
- Increase concurrency: adjust `--concurrency` and restart workers
- Add worker instances for hot queues
3) Shed load / throttle
- Temporarily pause low-priority producers
4) Investigate slow tasks
- Check p95 runtime panels
- Profile slow tasks; optimize I/O and external calls
5) Clear poison pills
- Identify repeatedly failing tasks; fix root cause

## Recovery
- Confirm backlog decreasing and alert resolves
