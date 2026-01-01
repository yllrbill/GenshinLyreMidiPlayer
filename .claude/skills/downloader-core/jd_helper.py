#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JDownloader 2 Helper for downloader-core

Provides Python interface to JDownloader 2 via MyJDownloader API.

Requirements:
    pip install myjdapi

Environment Variables:
    MYJD_EMAIL    - MyJDownloader account email
    MYJD_PASSWORD - MyJDownloader account password
    MYJD_DEVICE   - (optional) Specific device name

Usage:
    # Add links
    python jd_helper.py add "https://mega.nz/file/xxx" "https://mediafire.com/xxx"

    # Check status
    python jd_helper.py status

    # List devices
    python jd_helper.py devices
"""

import os
import sys
import json

try:
    import myjdapi
except ImportError:
    print("[ERROR] myjdapi not installed. Run: pip install myjdapi")
    sys.exit(1)


def get_credentials():
    """Get MyJDownloader credentials from environment variables."""
    email = os.environ.get("MYJD_EMAIL")
    password = os.environ.get("MYJD_PASSWORD")
    device = os.environ.get("MYJD_DEVICE")

    if not email or not password:
        print("[ERROR] Missing environment variables:")
        if not email:
            print("  - MYJD_EMAIL")
        if not password:
            print("  - MYJD_PASSWORD")
        print("\nSet them with:")
        print('  setx MYJD_EMAIL "your@email.com"')
        print('  setx MYJD_PASSWORD "your_password"')
        sys.exit(1)

    return email, password, device


def connect():
    """Connect to MyJDownloader and return device object."""
    email, password, device_name = get_credentials()

    jd = myjdapi.Myjdapi()
    jd.set_app_key("downloader-core")

    try:
        jd.connect(email, password)
        jd.update_devices()
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)

    devices = jd.list_devices()
    if not devices:
        print("[ERROR] No JDownloader devices found.")
        print("Make sure JDownloader 2 is running and connected to MyJDownloader.")
        sys.exit(1)

    if device_name:
        try:
            return jd.get_device(device_name)
        except Exception:
            print(f"[ERROR] Device '{device_name}' not found.")
            print("Available devices:")
            for d in devices:
                print(f"  - {d['name']}")
            sys.exit(1)
    else:
        # Use first available device
        return jd.get_device(devices[0]["name"])


def add_links(urls, output_dir=None, autostart=True, package_name="downloader-core"):
    """Add links to JDownloader queue."""
    device = connect()

    links = ",".join(urls) if isinstance(urls, list) else urls

    params = {
        "autostart": autostart,
        "links": links,
        "packageName": package_name
    }

    if output_dir:
        params["destinationFolder"] = output_dir

    try:
        device.linkgrabber.add_links([params])
        result = {
            "status": "OK",
            "links_added": len(urls) if isinstance(urls, list) else 1,
            "autostart": autostart
        }
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        result = {"status": "ERROR", "error": str(e)}
        print(json.dumps(result, indent=2))
        return result


def get_status():
    """Get current download status."""
    device = connect()

    try:
        state = device.downloadcontroller.get_current_state()
        packages = device.downloads.query_packages()
        links = device.linkgrabber.query_links()

        result = {
            "status": "OK",
            "state": state,
            "downloads": {
                "packages": len(packages) if packages else 0
            },
            "linkgrabber": {
                "links": len(links) if links else 0
            }
        }
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        result = {"status": "ERROR", "error": str(e)}
        print(json.dumps(result, indent=2))
        return result


def list_devices():
    """List available JDownloader devices."""
    email, password, _ = get_credentials()

    jd = myjdapi.Myjdapi()
    jd.set_app_key("downloader-core")

    try:
        jd.connect(email, password)
        jd.update_devices()
        devices = jd.list_devices()

        result = {
            "status": "OK",
            "devices": [d["name"] for d in devices]
        }
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        result = {"status": "ERROR", "error": str(e)}
        print(json.dumps(result, indent=2))
        return result


def start_downloads():
    """Start all downloads."""
    device = connect()

    try:
        device.downloadcontroller.start_downloads()
        result = {"status": "OK", "action": "start_downloads"}
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        result = {"status": "ERROR", "error": str(e)}
        print(json.dumps(result, indent=2))
        return result


def print_usage():
    """Print usage information."""
    print(__doc__)
    print("\nCommands:")
    print("  add <url> [url2] ...  - Add links to JDownloader")
    print("  status                - Get download status")
    print("  devices               - List available devices")
    print("  start                 - Start all downloads")
    print("\nOptions for 'add':")
    print("  -o, --output <dir>    - Output directory")
    print("  --no-autostart        - Don't start download automatically")
    print("  -p, --package <name>  - Package name")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: jd_helper.py add <url> [url2] ...")
            sys.exit(1)

        # Parse options
        urls = []
        output_dir = None
        autostart = True
        package_name = "downloader-core"

        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg in ("-o", "--output") and i + 1 < len(sys.argv):
                output_dir = sys.argv[i + 1]
                i += 2
            elif arg == "--no-autostart":
                autostart = False
                i += 1
            elif arg in ("-p", "--package") and i + 1 < len(sys.argv):
                package_name = sys.argv[i + 1]
                i += 2
            else:
                urls.append(arg)
                i += 1

        if not urls:
            print("[ERROR] No URLs provided")
            sys.exit(1)

        add_links(urls, output_dir, autostart, package_name)

    elif command == "status":
        get_status()

    elif command == "devices":
        list_devices()

    elif command == "start":
        start_downloads()

    elif command in ("-h", "--help", "help"):
        print_usage()

    else:
        print(f"[ERROR] Unknown command: {command}")
        print_usage()
        sys.exit(1)
