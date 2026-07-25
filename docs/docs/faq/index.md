# Frequently Asked Questions

## General

**What is AMF?**
AMF (Automated Manuscript Formatter) is an enterprise-grade open-source tool that formats academic manuscripts into professionally styled DOCX documents.

**Who is it for?**
Researchers, academics, students, publishers — anyone who needs to format manuscripts according to style guidelines.

**Is it free?**
Yes, AMF is MIT-licensed open source. Free to use, modify, and distribute.

**What citation styles are supported?**
APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard, Vancouver, Turabian, ACS, AMA — 9 styles total.

## Technical

**Do I need an API server?**
The CLI can work standalone with `pip install amf-cli[local]`, or connect to a remote API server.

**Can I add custom styles?**
Yes, programmatically via the style registry API. A visual style editor is on the roadmap.

**Is there batch processing?**
Yes, use the CLI in a script loop or the SDK. Dedicated batch support is on the roadmap.

**Can I integrate with CI/CD?**
Yes. See the CI/CD tutorial and examples for GitHub Actions, GitLab CI, and pre-commit hooks.

## Troubleshooting

**Why is my DOCX not formatted correctly?**
Run `amf validate` to check for structural issues. Ensure required sections exist for your style.

**Why am I getting 422 errors?**
Check your request payload matches the API schema. Use `POST /api/v1/validate` for detailed errors.

**Can AMF handle large manuscripts?**
Yes, tested up to 300 pages. For larger documents, increase memory limits and timeout values.
