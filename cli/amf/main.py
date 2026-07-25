import click
from pathlib import Path

from amf import __version__, __title__


@click.group(invoke_without_command=False)
@click.version_option(version=__version__, prog_name=__title__)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("-c", "--config", type=click.Path(exists=True), help="Path to config file")
@click.pass_context
def cli(ctx, verbose, config):
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    if config:
        ctx.obj["config_path"] = Path(config)


@cli.command()
@click.option("-i", "--input", required=True, type=click.Path(exists=True), help="Input manuscript file")
@click.option("-o", "--output", type=click.Path(), help="Output DOCX file path")
@click.option("-s", "--style", default="apa", help="Formatting style (apa, mla, chicago, ieee, etc.)")
@click.option("-O", "--options", type=str, help="JSON string of formatting options")
@click.option("-w", "--watch", is_flag=True, help="Watch mode - reformat on file changes")
@click.pass_context
def format(ctx, input, output, style, options, watch):
    from amf.commands.format import run_format
    run_format(input, output, style, options, watch, ctx.obj["verbose"])


@cli.command()
@click.option("-i", "--input", required=True, type=click.Path(exists=True), help="Input manuscript file")
@click.option("-s", "--style", default="apa", help="Style to validate against")
@click.option("-o", "--output", type=click.Path(), help="Output validation report as JSON")
@click.pass_context
def validate(ctx, input, style, output):
    from amf.commands.validate import run_validate
    run_validate(input, style, output, ctx.obj["verbose"])


@cli.command()
@click.option("-i", "--input", required=True, type=click.Path(exists=True), help="Input manuscript file")
@click.option("-s", "--style", default="apa", help="Formatting style")
@click.option("-o", "--output", type=click.Path(), help="Output HTML file path")
@click.option("--open", "open_browser", is_flag=True, help="Open preview in browser")
@click.pass_context
def preview(ctx, input, style, output, open_browser):
    from amf.commands.preview import run_preview
    run_preview(input, style, output, open_browser, ctx.obj["verbose"])


@cli.group()
def styles():
    """List and manage formatting styles"""


@styles.command("list")
def styles_list():
    from amf.commands.styles import list_styles
    list_styles()


@styles.command("show")
@click.argument("name")
def styles_show(name):
    from amf.commands.styles import show_style
    show_style(name)


@styles.command("export")
@click.argument("name")
@click.argument("file", type=click.Path())
def styles_export(name, file):
    from amf.commands.styles import export_style
    export_style(name, file)


@cli.command()
@click.option("-n", "--name", default="my-manuscript", help="Project name")
@click.option("-s", "--style", default="apa", help="Default formatting style")
@click.option("-o", "--output", default=".", type=click.Path(), help="Output directory")
@click.pass_context
def init(ctx, name, style, output):
    from amf.commands.init import run_init
    run_init(name, style, Path(output), ctx.obj["verbose"])


@cli.command()
@click.pass_context
def config(ctx):
    from amf.commands.config import show_config
    show_config()


if __name__ == "__main__":
    cli()
