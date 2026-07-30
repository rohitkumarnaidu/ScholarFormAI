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


@cli.group()
def update():
    """Manage application updates"""


@update.command("check")
@click.option("--channel", help="Release channel to check (stable, beta, nightly, pre-release)")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_check(ctx, channel, json_output):
    from amf.commands.update import run_update_check
    run_update_check(channel, json_output, ctx.obj["verbose"])


@update.command("channel")
@click.argument("name", required=False)
@click.option("--set", "set_channel", help="Set active release channel")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_channel(ctx, name, set_channel, json_output):
    from amf.commands.update import run_update_channel
    channel_name = name or set_channel
    run_update_channel(channel_name, json_output, ctx.obj["verbose"])


@update.command("channels")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_channels(ctx, json_output):
    from amf.commands.update import run_update_channel
    run_update_channel(None, json_output, ctx.obj["verbose"])


@update.command("download")
@click.option("--version", help="Specific version to download")
@click.option("--retry", default=3, type=int, help="Maximum download retry attempts")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_download(ctx, version, retry, json_output):
    from amf.commands.update import run_update_download
    run_update_download(version, retry, json_output, ctx.obj["verbose"])


@update.command("verify")
@click.option("-f", "--file", "file_path", type=click.Path(exists=True), help="Path to asset file")
@click.option("-c", "--checksum", help="Expected SHA-256 checksum digest")
@click.option("-s", "--signature", help="ED25519/RSA digital signature string")
@click.option("-k", "--public-key", help="Public key for signature verification")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_verify(ctx, file_path, checksum, signature, public_key, json_output):
    from amf.commands.update import run_update_verify
    run_update_verify(file_path, checksum, signature, public_key, json_output, ctx.obj["verbose"])


@update.command("install")
@click.option("--version", help="Specific version tag to install")
@click.option("-f", "--file", "file_path", type=click.Path(exists=True), help="Downloaded update payload file")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_install(ctx, version, file_path, json_output):
    from amf.commands.update import run_update_install
    run_update_install(version, file_path, json_output, ctx.obj["verbose"])


@update.command("offline")
@click.argument("archive_path", type=click.Path(exists=True))
@click.option("-s", "--signature", help="ED25519/RSA digital signature string or file")
@click.option("-k", "--public-key", help="Public key for signature verification")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_offline(ctx, archive_path, signature, public_key, json_output):
    from amf.commands.update import run_update_offline
    run_update_offline(archive_path, signature, public_key, json_output, ctx.obj["verbose"])


@update.command("rollback")
@click.option("--version", help="Specific version tag to rollback to")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_rollback(ctx, version, json_output):
    from amf.commands.update import run_update_rollback
    run_update_rollback(version, json_output, ctx.obj["verbose"])


@update.command("history")
@click.option("--limit", default=20, type=int, help="Number of history entries to show")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_history(ctx, limit, json_output):
    from amf.commands.update import run_update_history
    run_update_history(limit, json_output, ctx.obj["verbose"])


@update.command("settings")
@click.option("--channel", help="Set release channel (stable, beta, nightly, pre-release)")
@click.option("--auto-check/--no-auto-check", default=None, help="Enable/disable auto-check")
@click.option("--auto-download/--no-auto-download", default=None, help="Enable/disable auto-download")
@click.option("--auto-install/--no-auto-install", default=None, help="Enable/disable auto-install")
@click.option("--verify-signature/--no-verify-signature", default=None, help="Enable/disable signature verification")
@click.option("--verify-checksum/--no-verify-checksum", default=None, help="Enable/disable checksum verification")
@click.option("--reset", is_flag=True, help="Reset update settings to defaults")
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_settings(
    ctx, channel, auto_check, auto_download, auto_install, verify_signature, verify_checksum, reset, json_output
):
    from amf.commands.update import run_update_settings
    run_update_settings(
        channel, auto_check, auto_download, auto_install, verify_signature, verify_checksum, reset, json_output, ctx.obj["verbose"]
    )


@update.command("release-notes")
@click.argument("version", required=False)
@click.option("--json", "json_output", is_flag=True, help="Output response in JSON format")
@click.pass_context
def update_release_notes(ctx, version, json_output):
    from amf.commands.update import run_update_release_notes
    run_update_release_notes(version, json_output, ctx.obj["verbose"])



@cli.group()
def issue():
    """Report and manage issues"""


@issue.command("report")
@click.option("-t", "--title", required=True, help="Issue title")
@click.option("-d", "--description", required=True, help="Issue description")
@click.option("-c", "--category", default="bug", type=click.Choice(["bug", "feature-request", "general-feedback", "performance", "security", "crash", "ai-feedback", "documentation", "question", "other"]), help="Issue category")
@click.option("-s", "--severity", default="medium", type=click.Choice(["critical", "high", "medium", "low", "suggestion"]), help="Issue severity")
@click.option("-n", "--name", help="Reporter name")
@click.option("-e", "--email", help="Reporter email")
@click.option("--anonymous/--no-anonymous", default=False, help="Submit anonymously")
@click.option("--attach-logs", is_flag=True, help="Attach application logs")
@click.pass_context
def issue_report(ctx, title, description, category, severity, name, email, anonymous, attach_logs):
    from amf.commands.issues import run_issue_report
    run_issue_report(title, description, category, severity, name, email, anonymous, attach_logs, ctx.obj["verbose"])


@issue.command("list")
@click.option("--status", type=click.Choice(["new", "triaged", "in-progress", "resolved", "closed", "duplicate", "wont-fix", "needs-info"]), help="Filter by status")
@click.option("--category", type=click.Choice(["bug", "feature-request", "general-feedback", "performance", "security", "crash", "ai-feedback", "documentation", "question", "other"]), help="Filter by category")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low", "suggestion"]), help="Filter by severity")
@click.option("--label", help="Filter by label")
@click.option("--search", help="Search query")
@click.option("-l", "--limit", default=20, type=int, help="Number of results")
@click.pass_context
def issue_list(ctx, status, category, severity, label, search, limit):
    from amf.commands.issues import run_issue_list
    run_issue_list(status, category, severity, label, search, limit, ctx.obj["verbose"])


@issue.command("show")
@click.argument("issue_id")
@click.pass_context
def issue_show(ctx, issue_id):
    from amf.commands.issues import run_issue_show
    run_issue_show(issue_id, ctx.obj["verbose"])


@issue.command("comment")
@click.argument("issue_id")
@click.option("-b", "--body", required=True, help="Comment body")
@click.pass_context
def issue_comment(ctx, issue_id, body):
    from amf.commands.issues import run_issue_comment
    run_issue_comment(issue_id, body, ctx.obj["verbose"])


@issue.command("update")
@click.argument("issue_id")
@click.option("--status", type=click.Choice(["new", "triaged", "in-progress", "resolved", "closed", "duplicate", "wont-fix", "needs-info"]), help="New status")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low", "suggestion"]), help="New severity")
@click.option("--assign", help="Assign to user")
@click.option("--milestone", help="Set milestone")
@click.pass_context
def issue_update(ctx, issue_id, status, severity, assign, milestone):
    from amf.commands.issues import run_issue_update
    run_issue_update(issue_id, status, severity, assign, milestone, ctx.obj["verbose"])


@issue.command("search")
@click.argument("query")
@click.option("-l", "--limit", default=20, type=int, help="Number of results")
@click.pass_context
def issue_search(ctx, query, limit):
    from amf.commands.issues import run_issue_search
    run_issue_search(query, limit, ctx.obj["verbose"])


@issue.command("stats")
@click.pass_context
def issue_stats(ctx):
    from amf.commands.issues import run_issue_stats
    run_issue_stats(ctx.obj["verbose"])


@issue.command("labels")
@click.pass_context
def issue_labels(ctx):
    from amf.commands.issues import run_issue_labels
    run_issue_labels(ctx.obj["verbose"])


@issue.command("backup")
@click.pass_context
def issue_backup(ctx):
    from amf.commands.issues import run_issue_backup
    run_issue_backup(ctx.obj["verbose"])


if __name__ == "__main__":
    cli()
