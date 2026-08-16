# ScholarFormAI React Integration Example

This sample project demonstrates how to integrate the ScholarFormAI document formatting API into a React application.

## Overview

This example uses:

- React 18
- Tailwind CSS
- Axios for API requests

## Quick Start

1. Install dependencies:

   ```bash
   npm install
   ```

2. Set your ScholarFormAI API Key:

   ```bash
   cp .env.example .env
   # Edit .env and set VITE_SCHOLARFORM_API_KEY
   ```

3. Run the development server:

   ```bash
   npm run dev
   ```

## Key Code References

- `src/api/client.ts` - Axios instance configured with the API key.
- `src/components/Uploader.tsx` - File upload component that handles the multipart/form-data request to the `/v1/format` endpoint.
- `src/components/LivePreview.tsx` - Component that connects to the Server-Sent Events (SSE) endpoint to stream formatting progress in real-time.
