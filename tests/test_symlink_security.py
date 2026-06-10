import os
from koraku.tools.registry import _resolve_host_path
from koraku.core.config import settings


def test_resolve_host_path_symlink_vulnerability(tmp_path, monkeypatch):
    # Set up a workspace and a file outside of it
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside_secret = tmp_path / "secret.txt"
    outside_secret.write_text("secret")

    # Mock the workspace root
    monkeypatch.setattr(
        "koraku.tools.registry._effective_workspace_root", lambda: str(workspace)
    )

    # Ensure restrict_to_workspace is True
    monkeypatch.setattr(settings, "host_file_tools_restrict_to_workspace", True)

    # Create a symlink inside the workspace pointing to the outside file
    symlink_path = workspace / "symlink_to_secret"
    os.symlink(str(outside_secret), str(symlink_path))

    # Test resolving the path for reading (parent_for_new_file=False)
    # The old code correctly blocked this.
    fpath, err = _resolve_host_path("symlink_to_secret", parent_for_new_file=False)
    assert err is not None
    assert "Path must stay under workspace" in err

    # Test resolving the path for writing (parent_for_new_file=True)
    # The old code failed here!
    fpath, err = _resolve_host_path("symlink_to_secret", parent_for_new_file=True)
    assert err is not None
    assert "Path must stay under workspace" in err
