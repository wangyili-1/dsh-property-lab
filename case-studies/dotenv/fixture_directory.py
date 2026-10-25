"""Temporary storage for public, synthetic case data in the authorized workspace.

Windows Python 3.13's TemporaryDirectory uses mkdir(0o700), which installs a
protected DACL and drops the workspace's sandbox SID. A normal unique directory
inherits the existing workspace ACL instead. Cleanup remains mandatory.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from uuid import uuid4


@contextmanager
def fixture_directory(prefix=".dotenv-case-"):
    if prefix not in (".dotenv-case-", ".dotenv-control-"):
        raise ValueError("Use a fixed synthetic-fixture prefix")
    root = Path(__file__).resolve().parent
    if os.name != "nt":
        with TemporaryDirectory(prefix=prefix, dir=root) as directory:
            yield Path(directory)
        return

    directory = root / (prefix + uuid4().hex)
    # Atomically create only our unique child. Default mode retains inherited
    # workspace permissions; no ACL, token, or sandbox policy is edited.
    directory.mkdir()
    try:
        yield directory
    finally:
        # Never clean unrelated paths, follow a replaced directory, or suppress
        # cleanup failures. A failure must still make this test unsuccessful.
        if directory.is_symlink() or directory.resolve().parent != root:
            raise RuntimeError("Fixture directory no longer resolves inside its root")
        shutil.rmtree(directory)
