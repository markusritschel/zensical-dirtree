from zensical_dirtree import asset_path
from zensical_dirtree.cli import main


def test_install_copies_assets(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    assert main(["install", "--docs-dir", str(docs)]) == 0
    css = docs / "stylesheets" / "dirtree.css"
    js = docs / "javascripts" / "dirtree.js"
    assert css.read_bytes() == asset_path("dirtree.css").read_bytes()
    assert js.read_bytes() == asset_path("dirtree.js").read_bytes()


def test_install_overwrites_stale_assets(tmp_path):
    docs = tmp_path / "docs"
    (docs / "javascripts").mkdir(parents=True)
    (docs / "javascripts" / "dirtree.js").write_text("old")
    assert main(["install", "--docs-dir", str(docs)]) == 0
    assert (docs / "javascripts" / "dirtree.js").read_text() != "old"


def test_install_missing_docs_dir(tmp_path, capsys):
    assert main(["install", "--docs-dir", str(tmp_path / "nope")]) == 1
    assert "No such directory" in capsys.readouterr().err
