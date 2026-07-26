# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R
from setuptools import setup
from setuptools.command.build_py import build_py

# Diagnostics-server-only modules: excluded from the package because the
# diagnostics server is a separate, admin/technical-only runtime that must
# never run alongside the main controller (see HandOver.md "Runtime
# separation"). These files stay in the source repo untouched.
EXCLUDED_MODULES = {"main_mjpeg_server", "maindiagnostics", "qrtest"}


class ExcludeDiagnosticsBuildPy(build_py):
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        return [m for m in modules if m[1] not in EXCLUDED_MODULES]


setup(cmdclass={"build_py": ExcludeDiagnosticsBuildPy})
