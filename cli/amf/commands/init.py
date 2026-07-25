import json
from pathlib import Path

from rich.panel import Panel

from amf._console import get_console

console = get_console()

MANUSCRIPT_TEMPLATE = """# {title}

## Author Information

**Author 1 Name**
Affiliation: University/Institution
Email: author1@institution.edu

**Corresponding Author:**
Name: Author 1
Email: author1@institution.edu

## Abstract

Write your abstract here. A concise summary of your research, including background, methods, results, and conclusions.

**Keywords:** keyword1, keyword2, keyword3

## Introduction

Start your introduction here. Provide background context, identify the research gap, and state your research question or hypothesis.

## Methods

Describe your research methodology, including:
- Study design
- Participants/sample
- Materials and apparatus
- Procedure
- Data analysis

## Results

Present your findings. Use clear and concise language.

## Discussion

Interpret your results and discuss their implications. Compare with previous research.

## Conclusion

Summarize your key findings and suggest future research directions.

## References

1. Author, A. A. (Year). Title of the article. *Journal Name*, Volume(Issue), Page range. https://doi.org/xxxx
2. Author, B. B. (Year). *Title of the book*. Publisher.
"""

CONFIG_TEMPLATE = {
    "style": "{style}",
    "output_dir": "output",
    "page_size": "A4",
    "font_family": "Times New Roman",
    "font_size": 12,
    "line_spacing": 2.0,
    "include_toc": False,
    "include_page_numbers": True,
    "include_running_header": True,
}


def run_init(name: str, style: str, output_dir: Path, verbose: bool):
    project_dir = output_dir / name
    if project_dir.exists():
        console.print(f"[yellow]Warning:[/yellow] Directory '{project_dir}' already exists")
    else:
        project_dir.mkdir(parents=True)

    manuscript_file = project_dir / "manuscript.md"
    if not manuscript_file.exists():
        manuscript_file.write_text(MANUSCRIPT_TEMPLATE.format(title=name.replace("-", " ").title(), style=style))
        console.print(f"[green]✓[/green] Created {manuscript_file}")
    else:
        console.print(f"[yellow]•[/yellow] {manuscript_file} already exists")

    config_file = project_dir / "amf.config.json"
    if not config_file.exists():
        config = CONFIG_TEMPLATE.copy()
        config["style"] = style
        config_file.write_text(json.dumps(config, indent=2))
        console.print(f"[green]✓[/green] Created {config_file}")
    else:
        console.print(f"[yellow]•[/yellow] {config_file} already exists")

    references_file = project_dir / "references.bib"
    if not references_file.exists():
        references_file.write_text("% Add your references here in BibTeX format\n")
        console.print(f"[green]✓[/green] Created {references_file}")
    else:
        console.print(f"[yellow]•[/yellow] {references_file} already exists")

    console.print()
    console.print(Panel(
        f"[bold]Project initialized:[/bold] {project_dir}\n\n"
        f"  • {manuscript_file.name} - Your manuscript content\n"
        f"  • {config_file.name} - Project configuration\n"
        f"  • {references_file.name} - Bibliography references\n\n"
        f"Run: [cyan]amf format -i {manuscript_file} -s {style}[/cyan]",
        title="Project Created",
    ))
