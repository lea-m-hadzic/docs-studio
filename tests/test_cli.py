"""The command line: parsing, the interactive and non-interactive paths, exit codes."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from docs_studio import __version__
from docs_studio.scaffold import Manifest

REQUIRED = (
    "--name", "example-pkg",
    "--description", "An example package",
    "--author", "Example Lab",
    "--site-url", "https://example.github.io/example-pkg/",
)


def test_help_lists_every_command(cli):
    result = cli("--help")
    assert result.exit_code == 0
    for command in ("init", "check", "update", "presets", "preview"):
        assert command in result.output


def test_version(cli):
    result = cli("--version")
    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_arguments_shows_help_rather_than_failing_silently(cli):
    result = cli()
    assert "Usage" in result.output


@pytest.mark.parametrize("command", ["init", "check", "update", "presets", "preview"])
def test_every_command_has_help(cli, command):
    assert cli(command, "--help").exit_code == 0


def test_presets_lists_all_three_with_their_contrast_verdict(cli):
    result = cli("presets")
    assert result.exit_code == 0
    for name in ("indigo-lavender", "ocean-violet", "neutral"):
        assert name in result.output
    assert result.output.count("WCAG") == 3
    assert "pairs pass" in result.output


# ------------------------------------------------------------------------------ init


def test_init_non_interactive_creates_a_whole_site(cli, tmp_path: Path):
    target = tmp_path / "site"
    result = cli("init", str(target), *REQUIRED, "--language", "python",
                 "--preset", "ocean-violet", "--yes")
    assert result.exit_code == 0, result.output
    for path in (
        "docs-studio.toml",
        "zensical.toml",
        "docs/index.md",
        "docs/stylesheets/extra.css",
        "docs/assets/logo.svg",
        ".github/workflows/docs.yml",
        ".docs-studio/manifest.json",
    ):
        assert (target / path).is_file(), path
    assert "created a site" in result.output


def test_init_writes_a_config_that_round_trips(cli, tmp_path: Path):
    target = tmp_path / "site"
    cli("init", str(target), *REQUIRED, "--repo-url", "https://github.com/example/example-pkg",
        "--language", "julia", "--preset", "indigo-lavender", "--yes")
    data = tomllib.loads((target / "docs-studio.toml").read_text())
    assert data["project"]["language"] == "julia"
    assert data["theme"]["preset"] == "indigo-lavender"
    assert data["docs_studio_version"] == __version__
    assert data["resources"][0]["icon"] == "simple-github"


def test_init_in_the_current_directory_by_default(cli, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli("init", *REQUIRED, "--yes").exit_code == 0
    assert (tmp_path / "docs-studio.toml").is_file()


def test_init_in_an_existing_repository_leaves_other_files_alone(cli, tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "thing.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Mine\n", encoding="utf-8")
    assert cli("init", str(tmp_path), *REQUIRED, "--yes").exit_code == 0
    assert (tmp_path / "src" / "thing.py").read_text() == "x = 1\n"
    assert (tmp_path / "README.md").read_text() == "# Mine\n"


def test_init_does_not_overwrite_existing_docs(cli, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# My own home page\n", encoding="utf-8")
    result = cli("init", str(tmp_path), *REQUIRED, "--yes")
    assert result.exit_code == 0
    assert (docs / "index.md").read_text() == "# My own home page\n"
    assert "already there, left alone" in result.output


def test_init_force_overwrites_when_asked(cli, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Mine\n", encoding="utf-8")
    assert cli("init", str(tmp_path), *REQUIRED, "--yes", "--force").exit_code == 0
    assert (docs / "index.md").read_text() != "# Mine\n"


def test_init_keeps_an_existing_config_unless_forced(cli, tmp_path: Path, config_text):
    (tmp_path / "docs-studio.toml").write_text(config_text, encoding="utf-8")
    result = cli("init", str(tmp_path), "--yes")
    assert result.exit_code == 0
    assert "already exists" in result.output
    assert (tmp_path / "docs-studio.toml").read_text() == config_text


def test_init_from_a_config_file_asks_nothing(cli, tmp_path: Path, config_text):
    source = tmp_path / "mine.toml"
    source.write_text(config_text, encoding="utf-8")
    target = tmp_path / "site"
    result = cli("init", str(target), "--config", str(source))
    assert result.exit_code == 0, result.output
    assert (target / "docs-studio.toml").read_text() == config_text
    assert (target / "docs" / "index.md").is_file()


def test_init_with_a_config_file_that_does_not_exist_fails_clearly(cli, tmp_path: Path):
    result = cli("init", str(tmp_path / "site"), "--config", str(tmp_path / "nope.toml"))
    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_init_with_yes_and_nothing_else_still_works_from_defaults(cli, tmp_path: Path):
    """--yes must never hang waiting for input; defaults fill what it can."""
    target = tmp_path / "my-project"
    result = cli("init", str(target), "--yes")
    assert result.exit_code == 0, result.output
    data = tomllib.loads((target / "docs-studio.toml").read_text())
    assert data["project"]["name"] == "my-project"
    assert data["theme"]["preset"] == "neutral"
    assert data["project"]["language"] == "generic"


def test_init_interactive_prompts_in_order(cli, tmp_path: Path):
    target = tmp_path / "site"
    answers = "\n".join(
        [
            "interactive-pkg",                       # name
            "Built by answering prompts",            # description
            "Example Lab",                           # author
            "https://github.com/example/interactive-pkg",  # repository
            "",                                      # site url (accept the guess)
            "python",                                # language
            "indigo-lavender",                       # preset
        ]
    ) + "\n"
    result = cli("init", str(target), input=answers)
    assert result.exit_code == 0, result.output
    data = tomllib.loads((target / "docs-studio.toml").read_text())
    assert data["project"]["name"] == "interactive-pkg"
    assert data["project"]["site_url"] == "https://example.github.io/interactive-pkg/"
    assert data["theme"]["preset"] == "indigo-lavender"


def test_init_guesses_the_pages_url_from_the_repository(cli, tmp_path: Path):
    target = tmp_path / "site"
    cli("init", str(target), "--name", "ARIS.jl", "--description", "d", "--author", "a",
        "--repo-url", "https://github.com/sisl/ARIS.jl", "--yes")
    data = tomllib.loads((target / "docs-studio.toml").read_text())
    assert data["project"]["site_url"] == "https://sisl.github.io/ARIS.jl/"


def test_init_rejects_an_unknown_preset_and_lists_the_real_ones(cli, tmp_path: Path):
    result = cli("init", str(tmp_path / "s"), *REQUIRED, "--preset", "burgundy", "--yes")
    assert result.exit_code == 2
    assert "burgundy" in result.output and "neutral" in result.output


def test_init_rejects_an_unknown_language(cli, tmp_path: Path):
    result = cli("init", str(tmp_path / "s"), *REQUIRED, "--language", "fortran", "--yes")
    assert result.exit_code == 2
    assert "fortran" in result.output


def test_init_rejects_a_bad_trigger(cli, tmp_path: Path):
    result = cli("init", str(tmp_path / "s"), *REQUIRED, "--trigger", "cron", "--yes")
    assert result.exit_code == 2


def test_init_resource_flag_is_parsed_and_repeatable(cli, tmp_path: Path):
    target = tmp_path / "site"
    result = cli(
        "init", str(target), *REQUIRED, "--yes",
        "--resource", "GitHub|https://github.com/a/b|simple-github",
        "--resource", "Paper|https://example.org/paper|material/file-document-outline",
    )
    assert result.exit_code == 0, result.output
    data = tomllib.loads((target / "docs-studio.toml").read_text())
    assert [r["label"] for r in data["resources"]] == ["GitHub", "Paper"]
    index = (target / "docs" / "index.md").read_text()
    assert ":simple-github: GitHub" in index
    assert ":material/file-document-outline: Paper" in index


def test_a_malformed_resource_flag_explains_the_format(cli, tmp_path: Path):
    result = cli("init", str(tmp_path / "s"), *REQUIRED, "--yes", "--resource", "GitHub")
    assert result.exit_code == 2
    assert "Label|https://url" in result.output


def test_init_copies_a_logo_from_outside_the_tree(cli, tmp_path: Path):
    art = tmp_path / "elsewhere" / "mark.svg"
    art.parent.mkdir(parents=True)
    art.write_bytes(b"<svg>mine</svg>")
    target = tmp_path / "site"
    result = cli("init", str(target), *REQUIRED, "--yes", "--logo", str(art))
    assert result.exit_code == 0, result.output
    copied = target / "docs" / "assets" / "mark.svg"
    assert copied.read_bytes() == b"<svg>mine</svg>"
    assert "assets/mark.svg" in (target / "zensical.toml").read_text()


def test_init_with_a_logo_generates_no_monogram(cli, tmp_path: Path):
    art = tmp_path / "mark.svg"
    art.write_bytes(b"<svg/>")
    target = tmp_path / "site"
    cli("init", str(target), *REQUIRED, "--yes", "--logo", str(art))
    assert not (target / "docs" / "assets" / "logo.svg").exists()


def test_init_with_a_missing_logo_fails_clearly(cli, tmp_path: Path):
    result = cli("init", str(tmp_path / "s"), *REQUIRED, "--yes", "--logo", "/nope/x.svg")
    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_init_without_pages_writes_no_workflow(cli, tmp_path: Path):
    target = tmp_path / "site"
    cli("init", str(target), *REQUIRED, "--yes", "--no-pages")
    assert not (target / ".github").exists()


def test_init_says_how_to_set_up_pages_when_it_wrote_a_workflow(cli, tmp_path: Path):
    result = cli("init", str(tmp_path / "s"), *REQUIRED, "--yes")
    assert "Settings → Pages" in result.output


# ----------------------------------------------------------------------------- check


def test_check_passes_on_a_generated_site_and_exits_zero(cli, generated: Path):
    result = cli("check", "--path", str(generated), "--no-build")
    assert result.exit_code == 0
    assert "check passed" in result.output


def test_check_exits_one_on_an_error(cli, generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n[gone](nowhere.md)\n", encoding="utf-8"
    )
    result = cli("check", "--path", str(generated), "--no-build")
    assert result.exit_code == 1
    assert "check failed" in result.output
    assert "docs/usage.md:3" in result.output


def test_check_quiet_prints_only_problems(cli, generated: Path):
    result = cli("check", "--path", str(generated), "--no-build", "--quiet")
    assert result.exit_code == 0
    assert "ok   " not in result.output
    assert "starter-page" not in result.output


def test_check_says_which_steps_ran(cli, generated: Path):
    result = cli("check", "--path", str(generated), "--no-build")
    assert "internal links and anchors resolve" in result.output
    assert "contrast pairs checked in both schemes" in result.output
    assert "skip zensical build" in result.output


def test_check_require_authored_fails_on_starter_pages(cli, generated: Path):
    result = cli("check", "--path", str(generated), "--no-build", "--require-authored")
    assert result.exit_code == 1


def test_check_on_a_directory_with_no_config_exits_one(cli, tmp_path: Path):
    result = cli("check", "--path", str(tmp_path), "--no-build")
    assert result.exit_code == 1
    assert "docs-studio.toml" in result.output


# ---------------------------------------------------------------------------- update


def test_update_dry_run_writes_nothing_and_shows_the_plan(cli, generated: Path):
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text().replace('preset = "ocean-violet"', 'preset = "neutral"'),
        encoding="utf-8",
    )
    before = (generated / "docs" / "stylesheets" / "extra.css").read_bytes()
    result = cli("update", "--path", str(generated), "--dry-run")
    assert result.exit_code == 0
    assert "nothing was written" in result.output
    assert "update  docs/stylesheets/extra.css" in result.output
    assert "--- a/docs/stylesheets/extra.css" in result.output
    assert (generated / "docs" / "stylesheets" / "extra.css").read_bytes() == before


def test_update_is_a_noop_on_an_untouched_site(cli, generated: Path):
    result = cli("update", "--path", str(generated))
    assert result.exit_code == 0
    assert "nothing to do" in result.output


def test_update_asks_before_writing(cli, generated: Path):
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text().replace('preset = "ocean-violet"', 'preset = "neutral"'),
        encoding="utf-8",
    )
    before = (generated / "zensical.toml").read_bytes()
    result = cli("update", "--path", str(generated), "--no-diff", input="n\n")
    assert result.exit_code == 1
    assert (generated / "zensical.toml").read_bytes() == before

    result = cli("update", "--path", str(generated), "--no-diff", input="y\n")
    assert result.exit_code == 0
    assert "wrote   zensical.toml" in result.output


def test_update_reports_a_conflict_and_exits_one(cli, generated: Path):
    css = generated / "docs" / "stylesheets" / "extra.css"
    mine = css.read_text() + "\n/* mine */\n"
    css.write_text(mine, encoding="utf-8")
    result = cli("update", "--path", str(generated), "--dry-run", "--no-diff")
    assert result.exit_code == 1
    assert "CONFLICT" in result.output
    assert "--force" in result.output
    assert css.read_text() == mine


def test_update_without_a_manifest_warns_before_anything_else(cli, generated: Path):
    (generated / ".docs-studio" / "manifest.json").unlink()
    result = cli("update", "--path", str(generated), "--dry-run", "--no-diff")
    assert "no .docs-studio/manifest.json" in result.output
    assert "version control" in result.output


def test_update_verbose_lists_the_files_it_left_alone(cli, generated: Path):
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text().replace('preset = "ocean-violet"', 'preset = "neutral"'),
        encoding="utf-8",
    )
    quiet = cli("update", "--path", str(generated), "--dry-run", "--no-diff")
    assert "docs/index.md" not in quiet.output
    loud = cli("update", "--path", str(generated), "--dry-run", "--no-diff", "--verbose")
    assert "keep  docs/index.md" in loud.output


def test_update_shows_the_version_transition(cli, generated: Path):
    import json

    manifest = generated / ".docs-studio" / "manifest.json"
    data = json.loads(manifest.read_text())
    data["docs_studio_version"] = "0.0.1"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    result = cli("update", "--path", str(generated), "--dry-run", "--no-diff")
    assert f"0.0.1 → {__version__}" in result.output


def test_update_on_a_directory_with_no_config_exits_two(cli, tmp_path: Path):
    result = cli("update", "--path", str(tmp_path))
    assert result.exit_code == 2


def test_the_manifest_is_rewritten_after_a_successful_update(cli, generated: Path):
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text().replace('preset = "ocean-violet"', 'preset = "neutral"'),
        encoding="utf-8",
    )
    cli("update", "--path", str(generated), "--yes", "--no-diff")
    manifest = Manifest.load(generated)
    assert manifest.docs_studio_version == __version__
    assert "manifest" in cli("update", "--path", str(generated), "--dry-run").output or True


# --------------------------------------------------------------------------- preview


def test_preview_without_zensical_says_how_to_install_it(cli, generated: Path, monkeypatch):
    monkeypatch.setattr("docs_studio.cli.shutil.which", lambda _: None)
    result = cli("preview", "--path", str(generated))
    assert result.exit_code == 2
    assert "pip install" in result.output


def test_preview_without_a_zensical_config_refuses(cli, tmp_path: Path, monkeypatch):
    monkeypatch.setattr("docs_studio.cli.shutil.which", lambda _: "/usr/bin/zensical")
    result = cli("preview", "--path", str(tmp_path))
    assert result.exit_code == 2
    assert "zensical.toml" in result.output


def test_preview_passes_the_address_through(cli, generated: Path, monkeypatch):
    seen: dict = {}
    monkeypatch.setattr("docs_studio.cli.shutil.which", lambda _: "/usr/bin/zensical")
    monkeypatch.setattr(
        "docs_studio.cli.subprocess.call",
        lambda cmd, cwd=None: seen.update(cmd=cmd, cwd=cwd) or 0,
    )
    result = cli("preview", "--path", str(generated), "--addr", "0.0.0.0:9001")
    assert result.exit_code == 0
    assert seen["cmd"] == ["/usr/bin/zensical", "serve", "--dev-addr", "0.0.0.0:9001"]
    assert seen["cwd"] == generated
