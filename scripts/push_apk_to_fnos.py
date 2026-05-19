from __future__ import annotations

import argparse
from pathlib import Path
import posixpath
import sys

import paramiko


HOST = "localhost"
USERNAME = "1099040334"
PASSWORD = "1099040334abc."
REMOTE_DIR = "/path/to/your/data"


def ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    current = ""
    for segment in remote_dir.strip("/").split("/"):
        current = f"{current}/{segment}"
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def delete_existing_apks(sftp: paramiko.SFTPClient, remote_dir: str) -> list[str]:
    deleted: list[str] = []
    for entry in sftp.listdir_attr(remote_dir):
        if entry.filename.lower().endswith(".apk"):
            remote_path = posixpath.join(remote_dir, entry.filename)
            sftp.remove(remote_path)
            deleted.append(entry.filename)
    return deleted


def push_apk(local_apk: Path, remote_name: str) -> None:
    if not local_apk.exists():
        raise FileNotFoundError(f"Local APK not found: {local_apk}")

    transport = paramiko.Transport((HOST, 22))
    transport.connect(username=USERNAME, password=PASSWORD)

    try:
        sftp = paramiko.SFTPClient.from_transport(transport)
        ensure_remote_dir(sftp, REMOTE_DIR)
        deleted = delete_existing_apks(sftp, REMOTE_DIR)
        remote_path = posixpath.join(REMOTE_DIR, remote_name)
        sftp.put(str(local_apk), remote_path)
        print(f"Remote directory: {REMOTE_DIR}")
        print(f"Deleted old APKs: {deleted if deleted else '[]'}")
        print(f"Uploaded APK: {remote_path}")
        print(f"Size: {local_apk.stat().st_size} bytes")
    finally:
        transport.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True, help="Local APK path")
    parser.add_argument("--remote-name", default="familycut-debug.apk", help="Remote APK filename")
    args = parser.parse_args()

    push_apk(Path(args.apk).resolve(), args.remote_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
