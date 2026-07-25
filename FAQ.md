# Frequently Asked Questions

## General

### What is AMF?
AMF (Automated Manuscript Formatter) is an enterprise-grade tool that formats academic manuscripts into professionally styled DOCX documents. It supports major citation styles including APA, MLA, Chicago, IEEE, and more.

### Who is AMF for?
Researchers, academics, students, publishers, and anyone who needs to format academic manuscripts according to specific style guidelines.

### Is AMF free?
Yes! AMF is open source under the MIT License. It's free to use, modify, and distribute.

## Usage

### What input formats are supported?
Markdown, LaTeX, and plain text.

### What citation styles are supported?
APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard, Vancouver, Turabian, ACS, and AMA. More styles can be added.

### Can I create custom styles?
Not yet via the UI, but custom styles can be added programmatically through the style registry API. A visual style creator is on the roadmap.

### Can I format multiple manuscripts at once?
Batch processing is planned for a future release. For now, you can use the CLI in a scripted loop.

## Technical

### Do I need an API server?
The CLI can work with or without an API server. With the `local` extra, it uses the same formatting engine directly. Without it, it connects to an AMF API server.

### How do I deploy AMF in production?
See the [Deployment Guide](DEPLOYMENT.md) for detailed instructions on Docker, Kubernetes, and cloud deployments.

### Is there a Python SDK?
Yes! See the [SDK Guide](SDK_GUIDE.md) for documentation and examples.

### Can I integrate AMF into my CI/CD pipeline?
Yes. The CLI and API are designed for CI/CD integration. See the CI/CD example in the examples directory.

## Troubleshooting

### The generated DOCX doesn't look right
Run `amf validate` first to check for issues. Make sure your manuscript has the required sections for your selected style.

### The API is returning 422 errors
Check that your request body matches the expected schema. Use `/api/v1/validate` to get detailed error messages.

### Docker containers won't start
Ensure ports 3000, 8000, and 8080 are available. Check Docker logs with `docker compose logs`.
