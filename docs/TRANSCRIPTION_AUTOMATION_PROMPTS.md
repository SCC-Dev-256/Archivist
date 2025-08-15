# Transcription Automation Verification Prompts

These prompts help confirm that the scheduled transcription pipeline is active and configured correctly.

## Quick Checklist
1. Activate the environment and start the system
2. Run the built-in test suite
3. Inspect Celery workers and scheduled tasks
4. Confirm the processing schedule
5. Monitor the logs for task activity
6. Manually trigger processing if needed

## Example Prompt Sequence

1. **Start the system**
```bash
source venv_py311/bin/activate
python3 start_complete_system.py
```

2. **Verify tests**
```bash
python3 test_vod_system.py
```

3. **Inspect Celery**
```bash
celery -A core.tasks inspect active
celery -A core.tasks inspect scheduled
```

4. **Validate schedule**
```bash
echo $VOD_PROCESSING_TIME  # Default 19:00
```

5. **Watch logs**
```bash
tail -f logs/archivist.log | grep -E "(VOD|caption|process)"
```

6. **Trigger processing manually**
```bash
python3 -c "from core.tasks.vod_processing import process_recent_vods; result = process_recent_vods.delay(); print(f'Processing triggered: {result.id}')"
```

### Prompt Example

> "Please run `python3 test_vod_system.py` and confirm `process_recent_vods` appears in the Celery beat schedule. Check `logs/archivist.log` for recent `process_recent_vods` executions to verify the automation is running."