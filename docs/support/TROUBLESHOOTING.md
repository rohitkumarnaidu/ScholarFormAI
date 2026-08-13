# Troubleshooting Guide

This guide provides steps to resolve common issues encountered while using ScholarFormAI.

## API Connectivity Issues

**Symptom:** You receive `401 Unauthorized` or `403 Forbidden` errors.
**Solution:**
1. Ensure your API key is included in the `Authorization: Bearer <TOKEN>` header.
2. Verify that your API key has not expired or been revoked in the Developer Dashboard.
3. Check if your IP address is whitelisted (if you have IP restrictions enabled).

**Symptom:** You receive `429 Too Many Requests`.
**Solution:**
1. Implement exponential backoff in your application.
2. If you consistently hit rate limits, consider upgrading your API plan.

## Document Processing Issues

**Symptom:** API returns `ERR_DOCX_CORRUPTED`.
**Solution:**
1. Open the file in Microsoft Word.
2. Go to `File > Save As` and save a fresh copy of the `.docx` file.
3. Upload the fresh copy. This usually fixes underlying XML inconsistencies.

**Symptom:** Citations are not formatted correctly.
**Solution:**
1. Ensure you have enabled the `--citations` flag if using the CLI, or set `format_citations: true` in the API payload.
2. Verify that your citations follow standard placeholder formats (e.g., EndNote, Mendeley fields) that the engine can recognize.

## SDK Errors

**Symptom:** `ModuleNotFoundError` or similar dependency issues in Python.
**Solution:**
Ensure you are using a virtual environment and have installed the correct version:
```bash
python -m pip install --upgrade scholarform-sdk
```

## Still Need Help?
- Review our [FAQ](FAQ.md).
- Check the [API Error Codes](../api/ERROR_CODES.md).
- Open an issue on our GitHub repository or contact support.
