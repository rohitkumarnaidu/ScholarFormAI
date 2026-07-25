# Troubleshooting Guide

## Common Issues

### "Style not found" error

**Cause**: The specified style ID doesn't match any registered style.

**Solution**: Run `amf styles list` or `GET /api/v1/styles` to see available styles. Style IDs are lowercase (e.g., `apa`, `mla`, `ieee`).

### "Manuscript title is required" validation error

**Cause**: The manuscript object doesn't have a title or title is empty.

**Solution**: Ensure your manuscript has a non-empty title field. In Markdown, the first `# Heading` is used as the title.

### DOCX file won't open

**Cause**: Corrupted file or incompatible Word version.

**Solution**: 
1. Ensure you're using Word 2010 or later
2. Try opening with LibreOffice or Google Docs
3. Regenerate the file with default options

### Preview shows raw HTML

**Cause**: The preview endpoint returned HTML but the browser isn't rendering it.

**Solution**: Make sure you're viewing the preview in the web UI or a browser. The CLI `preview --open` command opens the HTML file in your default browser.

### Docker: port already in use

**Cause**: Another service is using port 3000, 8000, or 8080.

**Solution**: 
```bash
# Change ports in docker-compose.yml or stop conflicting services
docker compose down
netstat -ano | findstr :3000
```

### Docker: permission denied

**Cause**: The non-root user in the container doesn't have permission to write.

**Solution**: Ensure the uploads directory has correct permissions:
```bash
chmod 777 ./backend/uploads
```

### CLI: "requests not installed"

**Cause**: Running CLI without API connectivity and without the `local` extra.

**Solution**:
```bash
pip install amf-cli[local]
# Or ensure the AMF API server is running
```

## Debugging

### Enable verbose logging

```bash
# CLI
amf -v format -i manuscript.md

# Backend
AMF_LOG_LEVEL=debug uvicorn app.main:app --reload

# Check Docker logs
docker compose logs -f backend
```

### Check API health

```bash
curl http://localhost:8000/health
```

### Test API directly

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"manuscript": {"title": "Test"}, "style_id": "apa"}'
```

## Getting Help

If you can't resolve your issue:

1. Search [GitHub Issues](https://github.com/amf/automated-manuscript-formatter/issues)
2. Ask on [GitHub Discussions](https://github.com/amf/automated-manuscript-formatter/discussions)
3. Check the [FAQ](FAQ.md)
