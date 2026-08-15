# Error Codes

This document lists the error codes returned by the ScholarFormAI API and provides guidance on how to resolve them.

## HTTP Status Codes

The API uses standard HTTP status codes to indicate the success or failure of an API request.

| Code | Status | Description |
| --- | --- | --- |
| `200` | OK | The request was successful. |
| `201` | Created | A new resource was successfully created. |
| `202` | Accepted | The request was accepted and is being processed asynchronously. |
| `400` | Bad Request | The request was invalid or cannot be otherwise served. |
| `401` | Unauthorized | Authentication failed or user does not have permissions. |
| `403` | Forbidden | The authenticated user is not allowed to access the specified API endpoint. |
| `404` | Not Found | The requested resource could not be found. |
| `429` | Too Many Requests | The user has sent too many requests in a given amount of time. |
| `500` | Internal Server Error | An error occurred on the server. |

## ScholarFormAI Specific Error Codes

When an error occurs, the API returns a JSON response containing an `error_code` and a detailed `message`.

```json
{
  "error": {
    "code": "ERR_DOCX_CORRUPTED",
    "message": "The provided .docx file is corrupted and cannot be parsed."
  }
}
```

### Formatting Errors

| Code | Description | Resolution |
| --- | --- | --- |
| `ERR_DOCX_CORRUPTED` | The `.docx` file is corrupted. | Ensure the file opens in Microsoft Word without issues before uploading. |
| `ERR_UNSUPPORTED_TEMPLATE` | The requested `template_id` does not exist. | Check the available templates via the `/templates` endpoint. |
| `ERR_FILE_TOO_LARGE` | The uploaded document exceeds the maximum file size. | Reduce the file size. Maximum allowed is 50MB. |
| `ERR_PASSWORD_PROTECTED` | The uploaded `.docx` file is password protected. | Remove the password protection before processing. |

## Next Steps

- Return to [API Reference](API_REFERENCE.md).
- Review [Troubleshooting](../support/TROUBLESHOOTING.md).
