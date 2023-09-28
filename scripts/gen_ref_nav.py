"""Generate the code reference pages and navigation."""

import textwrap
import yaml
from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

per_module_options = {
    "markdown": {"summary": {"attributes": True, "functions": True, "classes": True}}
}

modules = [
    Path("markdown", "__init__.py"),
    Path("markdown", "preprocessors.py"),
    Path("markdown", "blockparser.py"),
    Path("markdown", "blockprocessors.py"),
    Path("markdown", "treeprocessors.py"),
    Path("markdown", "inlinepatterns.py"),
    Path("markdown", "postprocessors.py"),
    Path("markdown", "serializers.py"),
    Path("markdown", "util.py"),
    Path("markdown", "htmlparser.py"),
    Path("markdown", "test_tools.py"),
    *sorted(Path("markdown", "extensions").rglob("*.py")),
]

for path in modules:
    module_path = path.with_suffix("")
    doc_path = path.with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1].startswith("_"):
        continue

    nav_parts = [f"<code>{part}</code>" for part in parts]
    nav[nav_parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}")
        if ident in per_module_options:
            yaml_options = yaml.dump({"options": per_module_options[ident]})
            fd.write(f"\n{textwrap.indent(yaml_options, prefix='    ')}")
        elif ident.startswith("markdown.extensions."):
            yaml_options = yaml.dump({"options": {"inherited_members": False}})
            fd.write(f"\n{textwrap.indent(yaml_options, prefix='    ')}")

    mkdocs_gen_files.set_edit_path(full_doc_path, ".." / path)

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
