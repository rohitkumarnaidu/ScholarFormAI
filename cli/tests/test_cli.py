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
