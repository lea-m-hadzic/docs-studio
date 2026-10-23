"""`check`: each diagnostic, and the markdown parsing underneath it."""

from __future__ import annotations

from pathlib import Path

import pytest

from docs_studio.validation import (
    anchors,
    check_project,
    headings,
    iter_fences,
    iter_links,
    slugify,
    strip_fences,
)


def codes(report) -> set[str]:
    return {d.code for d in report.diagnostics}


def errors(report) -> set[str]:
    return {d.code for d in report.errors}


# ------------------------------------------------------------------ markdown parsing


def test_fenced_code_is_not_scanned_as_prose():
    text = "before\n```python\n[link](nowhere.md)\n```\nafter\n"
    assert "nowhere.md" not in strip_fences(text)
    assert list(iter_links(text)) == []
    # Line numbering survives, so diagnostics point at the right line.
    assert len(strip_fences(text).splitlines()) == len(text.splitlines())


def test_tilde_fences_and_fences_longer_than_three_are_handled():
    text = "~~~~\n[a](b.md)\n~~~~\n[real](c.md)\n"
    assert [t for _, t in iter_links(text)] == ["c.md"]


def test_inline_code_is_not_scanned_as_a_link():
    assert list(iter_links("use `[a](b.md)` literally\n")) == []


def test_a_nested_image_label_resolves_to_the_outer_target():
    """The pattern both reference home pages use for a branded resource button."""
    line = '[![](assets/hf.svg){ .ds-resource-logo } Dataset](https://example.org/d){ .md-button }\n'
    assert [t for _, t in iter_links(line)] == ["assets/hf.svg", "https://example.org/d"]


def test_a_link_title_is_not_part_of_the_target():
    assert [t for _, t in iter_links('[a](page.md "Title")\n')] == ["page.md"]


def test_link_line_numbers_are_reported():
    text = "one\ntwo\n[a](b.md)\n"
    assert list(iter_links(text)) == [(3, "b.md")]


def test_headings_inside_code_are_not_headings():
    text = "# Real\n```bash\n# a shell comment\n```\n## Also real\n"
    assert [h for _, h in headings(text)] == ["Real", "Also real"]


@pytest.mark.parametrize(
    "heading, slug",
    [
        ("The robustness convention", "the-robustness-convention"),
        ("`is_estimate`", "is_estimate"),
        ("Welcome to ARIS.jl! { .ds-home-title }", "welcome-to-arisjl"),
        ("Choosing a judge", "choosing-a-judge"),
        ("Compliance (C1–C4)", "compliance-c1c4"),
        ("[A link](x.md) in a heading", "a-link-in-a-heading"),
    ],
)
def test_slugify_matches_the_toc_extension(heading, slug):
    assert slugify(heading) == slug


def test_explicit_anchor_ids_are_offered_too():
    assert "custom" in anchors("## A heading { #custom }\n")


def test_fences_are_enumerated_with_their_language_and_body():
    text = "```python\nx = 1\n```\n\n```bash\nls\n```\n"
    found = list(iter_fences(text))
    assert [(language, body.strip()) for _, language, body in found] == [
        ("python", "x = 1"),
        ("bash", "ls"),
    ]


# ------------------------------------------------------------------------ the checks


def test_a_freshly_generated_site_passes_everything_but_the_starter_notes(generated: Path):
    report = check_project(generated, build=False)
    assert report.ok, [d.render() for d in report.errors]
    assert errors(report) == set()
    # Two notes on a fresh site: the pages are still starters, and there is no root
    # NOTICE yet. Both are informational by design.
    assert codes(report) == {"starter-page", "attribution-file"}
    assert all(d.level == "info" for d in report.diagnostics)


def test_require_authored_turns_starter_pages_into_failures(generated: Path):
    report = check_project(generated, build=False, require_authored=True)
    assert not report.ok
    assert errors(report) == {"starter-page"}
    assert all(d.path and d.line == 1 for d in report.errors)


def test_a_missing_config_is_the_only_thing_reported(tmp_path: Path):
    report = check_project(tmp_path, build=False)
    assert errors(report) == {"config"}


def test_a_missing_docs_directory_is_reported(project_root: Path):
    report = check_project(project_root, build=False)
    assert "structure" in errors(report)


def test_a_broken_internal_link_names_the_file_and_line(generated: Path):
    page = generated / "docs" / "usage.md"
    page.write_text("# Usage\n\nSee [the guide](nowhere.md).\n", encoding="utf-8")
    report = check_project(generated, build=False)
    hit = next(d for d in report.errors if d.code == "link-missing-page")
    assert hit.path == "docs/usage.md" and hit.line == 3
    assert "nowhere.md" in hit.message


def test_a_broken_anchor_is_reported_for_both_same_page_and_cross_page(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n[here](#no-such-heading)\n\n[there](install.md#also-missing)\n",
        encoding="utf-8",
    )
    report = check_project(generated, build=False)
    anchors_reported = [d for d in report.errors if d.code == "anchor-missing"]
    assert len(anchors_reported) == 2


def test_a_resolving_anchor_is_not_reported(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n## A section\n\n[jump](#a-section)\n", encoding="utf-8"
    )
    assert "anchor-missing" not in codes(check_project(generated, build=False))


def test_a_page_missing_from_the_nav_is_an_error(generated: Path):
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text().replace('pages = ["api.md"]', 'pages = ["api.md", "gone.md"]'),
        encoding="utf-8",
    )
    assert "nav-missing-page" in errors(check_project(generated, build=False))


def test_an_orphaned_page_is_a_warning_not_an_error(generated: Path):
    (generated / "docs" / "orphan.md").write_text("# Orphan\n", encoding="utf-8")
    report = check_project(generated, build=False)
    assert report.ok
    hit = next(d for d in report.diagnostics if d.code == "page-not-in-nav")
    assert hit.level == "warning" and hit.path == "docs/orphan.md"


def test_a_duplicated_nav_entry_is_caught_by_the_config_layer(generated: Path):
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text().replace(
            'pages = ["quickstart.md", "install.md"]',
            'pages = ["quickstart.md", "install.md", "install.md"]',
        ),
        encoding="utf-8",
    )
    report = check_project(generated, build=False)
    assert errors(report) == {"config"}
    assert "install.md" in report.errors[0].message


def test_a_missing_asset_is_reported(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        '# Usage\n\n<img src="assets/absent.png" alt="">\n', encoding="utf-8"
    )
    assert "asset-missing" in errors(check_project(generated, build=False))


def test_a_logo_the_config_points_at_but_that_is_gone_is_reported(generated: Path):
    (generated / "docs" / "assets" / "logo.svg").unlink()
    assert "theme-asset-missing" in errors(check_project(generated, build=False))


def test_a_dark_logo_referenced_only_from_css_is_still_checked(generated: Path):
    """The swap lives in the stylesheet, so nothing else would notice it was broken."""
    (generated / "docs" / "assets" / "logo-dark.svg").unlink()
    assert "css-asset-missing" in errors(check_project(generated, build=False))


def test_a_missing_stylesheet_is_reported(generated: Path):
    (generated / "docs" / "stylesheets" / "extra.css").unlink()
    assert "stylesheet-missing" in errors(check_project(generated, build=False))


def test_an_absolute_link_that_would_break_under_a_pages_sub_path_is_an_error(
    generated: Path,
):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n[home](/index.html)\n", encoding="utf-8"
    )
    report = check_project(generated, build=False)
    hit = next(d for d in report.errors if d.code == "absolute-path-link")
    assert "/example-pkg/" in hit.message


def test_an_absolute_asset_path_is_an_error_too(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        '# Usage\n\n<img src="/assets/logo.svg" alt="">\n', encoding="utf-8"
    )
    assert "absolute-path-asset" in errors(check_project(generated, build=False))


def test_a_protocol_relative_url_is_not_mistaken_for_a_site_path(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n[x](//example.org/a)\n", encoding="utf-8"
    )
    report = check_project(generated, build=False)
    assert "absolute-path-link" not in codes(report)


def test_an_unclosed_fence_is_reported(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n```python\nx = 1\n", encoding="utf-8"
    )
    assert "fence-unbalanced" in errors(check_project(generated, build=False))


def test_markdown_shape_warnings(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\nSome prose\n- a list with no blank line before it\n\n"
        "- top\n  - nested by two spaces\n",
        encoding="utf-8",
    )
    found = codes(check_project(generated, build=False))
    assert "list-needs-blank-line" in found
    assert "list-indent" in found


def test_python_fences_are_parsed_with_a_real_parser(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n```python\ndef f(:\n```\n", encoding="utf-8"
    )
    report = check_project(generated, build=False)
    hit = next(d for d in report.errors if d.code == "fence-syntax")
    assert hit.path == "docs/usage.md" and "does not parse" in hit.message


@pytest.mark.parametrize(
    "language, body",
    [("json", '{"a": }'), ("toml", "a = = 1")],
)
def test_json_and_toml_fences_are_parsed_too(generated: Path, language, body):
    (generated / "docs" / "usage.md").write_text(
        f"# Usage\n\n```{language}\n{body}\n```\n", encoding="utf-8"
    )
    assert "fence-syntax" in errors(check_project(generated, build=False))


def test_a_language_with_no_parser_here_is_left_alone_rather_than_guessed_at(
    generated: Path,
):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n```julia\nthis is not valid julia ]]]\n```\n", encoding="utf-8"
    )
    report = check_project(generated, build=False)
    assert "fence-syntax" not in codes(report)


def test_an_unlabelled_fence_is_a_warning(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n```\nplain\n```\n", encoding="utf-8"
    )
    assert "fence-unlabelled" in codes(check_project(generated, build=False))


def test_a_fence_language_outside_the_profile_is_only_a_note(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n```julia\nx = 1\n```\n", encoding="utf-8"
    )
    report = check_project(generated, build=False)
    hit = next(d for d in report.diagnostics if d.code == "fence-unexpected-language")
    assert hit.level == "info"
    assert report.ok


def test_a_language_any_docs_site_uses_draws_no_comment(generated: Path):
    """CSS, YAML and the rest are legitimate on any site, whatever it documents."""
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n```css\n.a { color: red; }\n```\n\n```yaml\nkey: value\n```\n"
        "\n```diff\n-old\n+new\n```\n",
        encoding="utf-8",
    )
    report = check_project(generated, build=False)
    assert "fence-unexpected-language" not in codes(report)
    assert report.ok


def test_a_mistyped_fence_language_is_still_reported(generated: Path):
    """The point of the check: it must not have been widened into uselessness."""
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n```pyton\nx = 1\n```\n", encoding="utf-8"
    )
    report = check_project(generated, build=False)
    hit = next(d for d in report.diagnostics if d.code == "fence-unexpected-language")
    assert "pyton" in hit.message and hit.level == "info"


def test_another_profiles_language_is_still_reported(generated: Path):
    """`julia` on a Python site is a note, because it usually means a mistake."""
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n```julia\nx = 1\n```\n", encoding="utf-8"
    )
    assert "fence-unexpected-language" in codes(check_project(generated, build=False))


def test_unrendered_template_syntax_in_a_generated_file_is_an_error(generated: Path):
    css = generated / "docs" / "stylesheets" / "extra.css"
    css.write_text(css.read_text() + "\n/* {{ oops }} */\n", encoding="utf-8")
    assert "template-leftover" in errors(check_project(generated, build=False))


def test_github_actions_expressions_are_not_mistaken_for_template_syntax(
    generated: Path,
):
    workflow = (generated / ".github" / "workflows" / "docs.yml").read_text()
    assert "${{" in workflow
    assert "template-leftover" not in codes(check_project(generated, build=False))


def test_a_palette_that_fails_contrast_is_an_error_in_check(generated: Path):
    config = generated / "docs-studio.toml"
    config.write_text(
        config.read_text().replace(
            '[theme]\npreset = "ocean-violet"',
            '[theme]\npreset = "ocean-violet"\n[theme.light]\nfg_body = "#f4f4f4"',
        ),
        encoding="utf-8",
    )
    report = check_project(generated, build=False)
    assert "contrast" in errors(report)
    assert any("light" in d.message for d in report.errors if d.code == "contrast")


def test_a_missing_manifest_is_a_warning_with_advice(generated: Path):
    (generated / ".docs-studio" / "manifest.json").unlink()
    report = check_project(generated, build=False)
    hit = next(d for d in report.diagnostics if d.code == "manifest-missing")
    assert hit.level == "warning"
    assert "version control" in hit.message


def test_an_edited_managed_file_is_flagged_before_update_is_ever_run(generated: Path):
    css = generated / "docs" / "stylesheets" / "extra.css"
    css.write_text(css.read_text() + "\n/* mine */\n", encoding="utf-8")
    report = check_project(generated, build=False)
    hit = next(d for d in report.diagnostics if d.code == "managed-file-edited")
    assert hit.level == "warning" and hit.path == "docs/stylesheets/extra.css"


def test_check_reports_what_it_skipped(generated: Path):
    report = check_project(generated, build=False)
    assert any("not requested" in step for step in report.skipped)


def test_diagnostics_render_with_file_and_line(generated: Path):
    (generated / "docs" / "usage.md").write_text(
        "# Usage\n\n[a](nope.md)\n", encoding="utf-8"
    )
    report = check_project(generated, build=False)
    rendered = next(d.render() for d in report.errors)
    assert "docs/usage.md:3" in rendered and "link-missing-page" in rendered
