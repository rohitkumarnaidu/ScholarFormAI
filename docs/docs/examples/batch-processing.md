# Batch Processing Example

This example demonstrates how to perform batch formatting of multiple academic manuscripts concurrently using ScholarForm AI.

## Overview

In editorial offices, conference proceedings management, or university departments, processing dozens or hundreds of manuscripts manually is impractical. ScholarForm AI provides batch CLI commands and asynchronous Python SDK routines to format entire directories of documents efficiently.

---

## 1. Batch Formatting via CLI

To format an entire directory of Markdown/LaTeX files into a specified target style:

```bash
amf batch --input-dir ./submissions/ --output-dir ./formatted_docx/ --style ieee --concurrency 4
```

### Batch CLI Options

- `--input-dir, -d`: Directory containing input `.md` or `.tex` manuscript files.
- `--output-dir, -o`: Target directory where formatted `.docx` files will be saved.
- `--style, -s`: Default style to apply (`ieee`, `apa7`, `mla9`, etc.).
- `--concurrency, -c`: Maximum parallel formatting workers (default: 4).
- `--recursive, -r`: Search subdirectories recursively for manuscripts.
- `--config`: Path to a custom batch configuration file (`amf-batch.yaml`).

---

## 2. Using Batch Configuration (`amf-batch.yaml`)

For complex projects with heterogeneous requirements, create an `amf-batch.yaml` file in your root folder:

```yaml
version: "1.0"
default_style: "ieee"
output_dir: "./formatted_output"
concurrency: 8

targets:
  - input: "./submissions/journal_papers/*.md"
    style: "ieee"
    include_toc: false

  - input: "./submissions/theses/*.tex"
    style: "apa7"
    template: "./templates/university_thesis_template.docx"
    include_toc: true

  - input: "./submissions/reports/*.md"
    style: "chicago"
```

Execute the batch run using the configuration file:

```bash
amf batch --config amf-batch.yaml
```

---

## 3. Asynchronous Batch Processing via Python SDK

Using `AsyncAMFClient`, you can execute high-throughput parallel document formatting directly within Python:

```python
import asyncio
from pathlib import Path
from amf_sdk import AsyncAMFClient

async def process_manuscripts_batch():
    async with AsyncAMFClient(base_url="http://localhost:8000") as client:
        input_dir = Path("./submissions")
        output_dir = Path("./formatted_output")
        output_dir.mkdir(exist_ok=True)

        files = list(input_dir.glob("*.md"))
        print(f"Found {len(files)} manuscripts to format...")

        tasks = []
        for file_path in files:
            out_path = output_dir / f"{file_path.stem}.docx"
            task = client.format_document(
                file_path=str(file_path),
                output_path=str(out_path),
                style="ieee"
            )
            tasks.append(task)

        # Process all manuscripts concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if not isinstance(r, Exception))
        print(f"Batch completed: {successful}/{len(files)} successful.")

if __name__ == "__main__":
    asyncio.run(process_manuscripts_batch())
```

---

## 4. Batch Audit Log & Summary

When a batch job completes, ScholarForm AI generates a detailed JSON report (`batch_report.json`):

```json
{
  "total_files": 25,
  "successful": 25,
  "failed": 0,
  "elapsed_time_seconds": 14.82,
  "average_time_per_doc": 0.59,
  "details": [
    {
      "input_file": "submissions/paper01.md",
      "output_file": "formatted_output/paper01.docx",
      "status": "success",
      "quality_score": 98.5
    }
  ]
}
```
