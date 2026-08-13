# API Reference

Welcome to the **ScholarFormAI** API Reference. This document outlines the endpoints available for automating `.docx` formatting, uploading documents, and managing templates.

## Base URL

All API requests should be prefixed with the base URL:

```
https://api.scholarform.ai/v1
```

## Authentication

All endpoints require authentication via Bearer token. 

```http
Authorization: Bearer <YOUR_API_KEY>
```

## Endpoints

### 1. Format Document

**POST** `/format`

Formats an uploaded `.docx` file according to a specified scholarly template.

**Headers:**
- `Content-Type: multipart/form-data`

**Body Parameters:**
- `file` (File, required): The `.docx` file to be formatted.
- `template_id` (String, required): The ID of the template (e.g., `apa-7`, `mla-9`, `ieee`).
- `options` (JSON String, optional): Additional formatting options.

**Response:**
```json
{
  "status": "success",
  "data": {
    "job_id": "job_12345",
    "status_url": "https://api.scholarform.ai/v1/jobs/job_12345"
  }
}
```

### 2. Check Job Status

**GET** `/jobs/{job_id}`

Retrieves the status of a formatting job.

**Response (In Progress):**
```json
{
  "status": "processing",
  "progress": 45
}
```

**Response (Completed):**
```json
{
  "status": "completed",
  "download_url": "https://api.scholarform.ai/v1/downloads/file_12345.docx"
}
```

## See Also
- [Error Codes](ERROR_CODES.md)
- [SDK Guide](../sdk/SDK_GUIDE.md)
