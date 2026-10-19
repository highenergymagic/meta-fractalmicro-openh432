#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare writable /etc from immutable defaults; never modify the active tree.

This is a file-level three-way reconciliation, not a text merge. Conflicts
abort preparation. The caller must quiesce configuration writers before the
final prepare and must only activate a completed deployment.
"""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile


class Conflict(ValueError):
    pass


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("configuration root must be a real directory")
    result = {}

    def visit(directory, prefix=""):
        for item in sorted(directory.iterdir()):
            name = prefix + item.name
            info = item.lstat()
            mode = info.st_mode
            record = dict(mode=stat.S_IMODE(mode), uid=info.st_uid, gid=info.st_gid)
            record["xattrs"] = {
                key: base64.b64encode(os.getxattr(item, key, follow_symlinks=False)).decode()
                for key in sorted(os.listxattr(item, follow_symlinks=False))
            }
            if stat.S_ISLNK(mode):
                record.update(kind="link", value=os.readlink(item))
            elif stat.S_ISDIR(mode):
                record.update(kind="dir")
            elif stat.S_ISREG(mode):
                with item.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                record.update(kind="file", value=digest)
            else:
                raise ValueError(f"unsupported configuration object: {name}")
            result[name] = record
            if record["kind"] == "dir":
                visit(item, name + "/")

    visit(root)
    return result


def configuration_record(record):
    """SELinux labels belong to the OS policy, not the user's configuration."""
    if record is None:
        return None
    return {**record, "xattrs": {key: value for key, value in record["xattrs"].items()
                                 if key != "security.selinux"}}


def plan(old, current, new):
    """Return path -> source, rejecting content, metadata and tree conflicts."""
    selected = {}
    conflicts = []
    for name in sorted(old.keys() | current.keys() | new.keys()):
        before, local, vendor = old.get(name), current.get(name), new.get(name)
        baseline = configuration_record(before)
        local_config = configuration_record(local)
        vendor_config = configuration_record(vendor)
        if local_config == baseline:
            chosen, source = vendor, "new"
        elif vendor_config == baseline or vendor_config == local_config:
            chosen, source = local, "current"
        else:
            conflicts.append(name)
            continue
        if chosen is not None:
            if vendor is not None:
                chosen = configuration_record(chosen)
                if "security.selinux" in vendor["xattrs"]:
                    chosen["xattrs"]["security.selinux"] = vendor["xattrs"]["security.selinux"]
            selected[name] = (source, chosen)
    # Deleting/replacing a directory must not silently swallow new children.
    for name in selected:
        for ancestor in Path(name).parents:
            if str(ancestor) == ".":
                break
            parent = selected.get(ancestor.as_posix())
            if parent is None or parent[1]["kind"] != "dir":
                conflicts.append(name)
                break
    if conflicts:
        raise Conflict("configuration conflicts: " + ", ".join(sorted(set(conflicts))))
    return selected


def materialize(destination, selection, roots):
    destination.mkdir(mode=0o700)
    # Directories are initially writable by the owner; restore metadata last.
    for name, (source, record) in sorted(selection.items()):
        target = destination / name
        origin = roots[source] / name
        if record["kind"] == "dir":
            target.mkdir(mode=0o700)
        elif record["kind"] == "link":
            target.symlink_to(record["value"])
        else:
            with origin.open("rb") as incoming, target.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
                outgoing.flush()
                os.fsync(outgoing.fileno())
    for name, (_, record) in sorted(selection.items(), reverse=True):
        target = destination / name
        info = target.lstat()
        if (info.st_uid, info.st_gid) != (record["uid"], record["gid"]):
            os.chown(target, record["uid"], record["gid"], follow_symlinks=False)
        if record["kind"] != "link":
            os.chmod(target, record["mode"])
        for key, value in record["xattrs"].items():
            os.setxattr(target, key, base64.b64decode(value), follow_symlinks=False)
    os.chmod(destination, 0o755)


def sync_tree(root):
    for directory, _, files in os.walk(root, followlinks=False):
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def prepare(defaults, destination, previous=None):
    defaults, destination = Path(defaults), Path(destination)
    parent = destination.parent
    if not parent.is_dir() or parent.is_symlink() or parent.resolve() != parent.absolute():
        raise ValueError("deployment parent must be an existing canonical directory")
    if destination.name in ("", ".", ".."):
        raise ValueError("invalid deployment name")
    with (parent / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if destination.exists() or destination.is_symlink():
            raise ValueError("deployment already exists; refuse to overwrite")
        new = inventory(defaults)
        roots = {"new": defaults}
        if previous is None:
            selected = {key: ("new", value) for key, value in new.items()}
        else:
            previous = Path(previous)
            if previous.is_symlink():
                raise ValueError("previous deployment must not be a symlink")
            metadata = json.loads((previous / "deployment.json").read_text())
            if metadata.get("version") != 1 or metadata.get("complete") is not True:
                raise ValueError("previous deployment is incomplete")
            old = inventory(previous / "defaults")
            if old != metadata["defaults"]:
                raise ValueError("previous factory baseline changed")
            current = inventory(previous / "etc")
            roots["current"] = previous / "etc"
            selected = plan(old, current, new)
        temporary = Path(tempfile.mkdtemp(prefix=".prepare-", dir=parent))
        try:
            materialize(temporary / "etc", selected, roots)
            materialize(temporary / "defaults", {k: ("new", v) for k, v in new.items()}, roots)
            # Detect writers racing the capture; callers must still quiesce
            # writers through activation. Never publish a mixed snapshot.
            if inventory(defaults) != new:
                raise ValueError("factory defaults changed during preparation")
            if previous is not None and inventory(previous / "etc") != current:
                raise ValueError("live configuration changed during preparation")
            if inventory(temporary / "etc") != {k: v for k, (_, v) in selected.items()}:
                raise ValueError("configuration copy verification failed")
            if inventory(temporary / "defaults") != new:
                raise ValueError("factory copy verification failed")
            (temporary / "deployment.json").write_text(json.dumps(
                {"version": 1, "complete": True, "defaults": new},
                sort_keys=True, separators=(",", ":")) + "\n")
            sync_tree(temporary)
            os.rename(temporary, destination)
            fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            # Only this invocation's private staging tree is removed.
            if temporary.exists():
                shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("defaults", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    try:
        prepare(args.defaults, args.destination, args.previous)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Configuration preparation failed: {error}\n")


if __name__ == "__main__":
    main()
