#!/usr/bin/env python3
"""List root-level empty objects on macOS/Linux; never judge or delete them."""
import argparse
import json
import os
import stat

DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def scan_root(root):
    root = os.path.abspath(root)
    result = {"root": root, "entries_examined": 0, "candidates": [], "errors": []}
    try:
        root_fd = os.open(root, DIRECTORY_FLAGS)
    except OSError as error:
        result["errors"].append({"path": root, "error": str(error)})
        return result
    try:
        with os.scandir(root_fd) as entries:
            for entry in entries:
                result["entries_examined"] += 1
                path = os.path.join(root, entry.name)
                try:
                    info = os.stat(entry.name, dir_fd=root_fd, follow_symlinks=False)
                    kind = None
                    if stat.S_ISDIR(info.st_mode):
                        # Descriptor-relative O_NOFOLLOW also rejects a concurrent link swap.
                        child_fd = os.open(entry.name, DIRECTORY_FLAGS, dir_fd=root_fd)
                        try:
                            opened = os.fstat(child_fd)
                            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                                raise OSError("Directory identity changed during scan")
                            with os.scandir(child_fd) as children:
                                if next(children, None) is None:
                                    kind = "empty_directory"
                        finally:
                            os.close(child_fd)
                    elif stat.S_ISREG(info.st_mode) and info.st_size == 0:
                        kind = "zero_byte_file"
                    if kind:
                        result["candidates"].append({"path": path, "kind": kind,
                                                     "device": info.st_dev, "inode": info.st_ino})
                except OSError as error:
                    result["errors"].append({"path": path, "error": str(error)})
    except OSError as error:
        result["errors"].append({"path": root, "error": str(error)})
    finally:
        os.close(root_fd)
    result["candidates"].sort(key=lambda item: item["path"])
    result["errors"].sort(key=lambda item: item["path"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Project root to inspect, one level only")
    result = scan_root(parser.parse_args().root)
    print(json.dumps(result, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
