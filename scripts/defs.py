"""Shared helpers for the check scripts. Only needs pyyaml."""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def files(pattern):
    return sorted(ROOT.glob(pattern))


def rel(p):
    return Path(p).relative_to(ROOT).as_posix()


class Report:
    """Collects errors (fail the build) and warnings (shown, do not fail)."""

    def __init__(self, title):
        self.title, self.errors, self.warnings, self.checks = title, [], [], 0

    def check(self, ok, msg):
        self.checks += 1
        if not ok:
            self.errors.append(msg)
        return ok

    def warn(self, ok, msg):
        if not ok:
            self.warnings.append(msg)
        return ok

    def finish(self, summary="", max_warnings=15):
        print(f"{self.title}: ran {self.checks} checks. {summary}".strip())
        if self.warnings:
            print(f"  {len(self.warnings)} warning(s) - things referenced but not written yet (do not fail):")
            for w in self.warnings[:max_warnings]:
                print("   !", w)
            if len(self.warnings) > max_warnings:
                print(f"   ... and {len(self.warnings) - max_warnings} more")
        if self.errors:
            print(f"FAILED ({len(self.errors)}):")
            for e in self.errors:
                print("   x", e)
            sys.exit(1)
        print("OK")
