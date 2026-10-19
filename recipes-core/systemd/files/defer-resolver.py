#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the appliance's DNS startup ordering to the pinned systemd unit."""
from pathlib import Path
import sys


def defer_resolver(text):
    replacements = {
        "After=systemd-sysctl.service systemd-sysusers.service":
        "After=systemd-sysctl.service systemd-sysusers.service FMAccessibility.target",
        "Before=sysinit.target network.target nss-lookup.target shutdown.target initrd-switch-root.target":
        "Before=network.target nss-lookup.target shutdown.target initrd-switch-root.target",
    }
    lines = text.splitlines(keepends=True)
    for old in replacements:
        if sum(line.rstrip("\n") == old for line in lines) != 1:
            raise ValueError(f"Unexpected systemd-resolved ordering: {old}")
    return "".join(replacements.get(line.rstrip("\n"), line.rstrip("\n"))
                   + ("\n" if line.endswith("\n") else "") for line in lines)


if __name__ == "__main__":
    unit = Path(sys.argv[1])
    unit.write_text(defer_resolver(unit.read_text()))
