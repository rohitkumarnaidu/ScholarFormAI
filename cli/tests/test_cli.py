from pathlib import Path

from click.testing import CliRunner

from amf.main import cli


def test_version(runner: CliRunner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "AMF CLI" in result.output


def test_init(runner: CliRunner, temp_dir: Path):
    project_name = "test-project"
    result = runner.invoke(cli, ["init", "-n", project_name, "-o", str(temp_dir)])
    assert result.exit_code == 0
    assert (temp_dir / project_name).exists()
    assert (temp_dir / project_name / "manuscript.md").exists()
    assert (temp_dir / project_name / "amf.config.json").exists()
    assert (temp_dir / project_name / "references.bib").exists()


def test_init_with_style(runner: CliRunner, temp_dir: Path):
    result = runner.invoke(cli, ["init", "-n", "my-paper", "-s", "mla", "-o", str(temp_dir)])
    assert result.exit_code == 0
    config_path = temp_dir / "my-paper" / "amf.config.json"
    assert config_path.exists()
    import json
    config = json.loads(config_path.read_text())
    assert config["style"] == "mla"


def test_format_missing_file(runner: CliRunner):
    result = runner.invoke(cli, ["format", "-i", "nonexistent.md"])
    assert result.exit_code != 0
    assert "does not exist" in result.output or "not found" in result.output


def test_format_with_markdown(runner: CliRunner, sample_manuscript: Path):
    result = runner.invoke(cli, ["format", "-i", str(sample_manuscript), "-s", "apa"])
    assert result.exit_code == 0


def test_preview(runner: CliRunner, sample_manuscript: Path):
    result = runner.invoke(cli, ["preview", "-i", str(sample_manuscript), "-s", "apa"])
    assert result.exit_code == 0


def test_validate(runner: CliRunner, sample_manuscript: Path):
    result = runner.invoke(cli, ["validate", "-i", str(sample_manuscript), "-s", "apa"])
    assert result.exit_code in (0, 1)
    assert "valid" in result.output.lower() or "error" in result.output.lower() or "Validation" in result.output


def test_styles_list(runner: CliRunner):
    result = runner.invoke(cli, ["styles", "list"])
    assert result.exit_code == 0
    assert "APA" in result.output
    assert "MLA" in result.output


def test_manuscript_change_handler(sample_manuscript: Path, temp_dir: Path, unittest_mock=None):
    from unittest.mock import MagicMock, patch

    from watchdog.events import FileModifiedEvent

    from amf.commands.format import ManuscriptChangeHandler

    mock_client = MagicMock()
    output_file = temp_dir / "out.docx"
    handler = ManuscriptChangeHandler(mock_client, sample_manuscript, output_file, "apa", {})

    with patch("amf.commands.format._format_single") as mock_format_single:
        # Event for a different file should be ignored
        other_event = FileModifiedEvent(str(temp_dir / "other.txt"))
        handler.on_modified(other_event)
        mock_format_single.assert_not_called()

        # Event for directory should be ignored
        dir_event = FileModifiedEvent(str(sample_manuscript.parent))
        dir_event.is_directory = True
        handler.on_modified(dir_event)
        mock_format_single.assert_not_called()

        # Event for the manuscript file should trigger reformatting
        target_event = FileModifiedEvent(str(sample_manuscript))
        handler.on_modified(target_event)
        mock_format_single.assert_called_once_with(mock_client, sample_manuscript.resolve(), output_file, "apa", {})


def test_format_watch_mode_invocation(runner: CliRunner, sample_manuscript: Path):
    from unittest.mock import patch

    with patch("amf.commands.format._format_and_watch") as mock_watch:
        result = runner.invoke(cli, ["format", "-i", str(sample_manuscript), "-s", "apa", "-w"])
        assert result.exit_code == 0
        mock_watch.assert_called_once()

