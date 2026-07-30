# Runbooks

## Incident Response

### Service Unreachable

**Symptoms**: `curl http://localhost:8000/health` fails or returns non-200.

**Steps**:
1. Check Docker status: `docker compose ps`
2. Check container logs: `docker compose logs backend`
3. Restart service: `docker compose restart backend`
4. If persistent, check disk space and memory
5. Escalate if hardware issue

### High Error Rate

**Symptoms**: API returning 5xx errors, users reporting failures.

**Steps**:
1. Check recent changes/deployments
2. Review backend logs for error patterns
3. Check `AMF_MAX_UPLOAD_SIZE` configuration
4. Verify database connection (if configured)
5. Roll back recent changes if necessary

### Slow Formatting

**Symptoms**: Format requests taking > 30 seconds.

**Steps**:
1. Check concurrent request count
2. Monitor CPU and memory usage
3. Check for large manuscript processing
4. Scale horizontally if needed
5. Consider increasing resource limits

## Maintenance

### Daily

- Verify health endpoint
- Check Docker container status
- Review error logs

### Weekly

- Review performance metrics
- Check disk usage
- Update dependencies if needed

### Monthly

- Review and rotate API keys
- Audit configuration
- Backup configurations
- Review and update documentation

## Disaster Recovery

### Full Service Outage

1. **Assess**: Check all services, hardware, network
2. **Contain**: Stop all services, preserve logs
3. **Restore**: 
   ```bash
   docker compose down
   docker compose up -d
   ```
4. **Verify**: Run health checks, test formatting
5. **Post-mortem**: Document root cause and prevention

### Data Loss

1. Restore from backup: `cp backup/config.json config/`
2. Verify service health
3. Test with known manuscripts
