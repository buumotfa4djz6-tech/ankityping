#!/usr/bin/env python3
"""
Package management utility for ankityping plugin.

Provides easy installation, uninstallation, and maintenance functions
for the Anki typing practice plugin.
"""

from __future__ import annotations

import os
import sys
import shutil
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List


class PackageManager:
    """Package management utilities for ankityping."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.src_dir = self.project_root / "src" / "ankityping"
        self.package_name = "ankityping"
        self.version = self._get_version()

        # Common Anki addon directories
        self.anki_addon_dirs = self._find_anki_addon_dirs()

    def _get_version(self) -> str:
        """Get package version from pyproject.toml."""
        try:
            with open(self.project_root / "pyproject.toml", "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version = "):
                        return line.split("=")[1].strip().strip('"\'')
        except Exception:
            pass
        return "1.0.0"

    def _find_anki_addon_dirs(self) -> List[Path]:
        """Find Anki addon directories on the current system."""
        home = Path.home()
        addon_dirs = []

        # Common locations for Anki addons
        common_paths = [
            home / "Documents" / "Anki2" / "addons21",
            home / "Documents" / "Anki2" / "addons",
            home / ".local" / "share" / "anki2" / "addons21",
            home / "AppData" / "Roaming" / "Anki2" / "addons21",  # Windows
            Path("/Applications") / "Anki.app" / "Contents" / "Resources" / "addons21",  # macOS
        ]

        for path in common_paths:
            if path.exists() and path.is_dir():
                addon_dirs.append(path)

        return addon_dirs

    def install(self, target_dir: Optional[str] = None, force: bool = False) -> bool:
        """Install the plugin to Anki addon directory."""
        print(f"Installing {self.package_name} v{self.version}...")

        # Determine target directory
        if target_dir:
            install_path = Path(target_dir) / self.package_name
        else:
            if not self.anki_addon_dirs:
                print("[ERROR] Could not find Anki addon directory.")
                print("Please specify the target directory with --target-dir")
                return False

            # Use the first available addon directory
            install_path = self.anki_addon_dirs[0] / self.package_name

        # Check if already installed
        if install_path.exists() and not force:
            print(f"[ERROR] Plugin already installed at {install_path}")
            print("Use --force to overwrite existing installation")
            return False

        # Remove existing installation if force
        if install_path.exists() and force:
            print("Removing existing installation...")
            shutil.rmtree(install_path)

        try:
            # Create install directory
            install_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy plugin files
            print(f"Installing to: {install_path}")
            shutil.copytree(self.src_dir, install_path, dirs_exist_ok=True)

            # Copy meta.json (required for Anki addon configuration)
            meta_src = self.src_dir / "meta.json"
            meta_dst = install_path / "meta.json"
            if meta_src.exists():
                shutil.copy2(meta_src, meta_dst)

            # Copy config.json (default configuration)
            config_src = self.src_dir / "config.json"
            config_dst = install_path / "config.json"
            if config_src.exists():
                shutil.copy2(config_src, config_dst)

            print(f"[SUCCESS] Successfully installed {self.package_name} v{self.version}")
            print(f"Location: {install_path}")
            print("Please restart Anki to load the plugin")
            return True

        except Exception as e:
            print(f"[ERROR] Error installing plugin: {e}")
            return False

    def uninstall(self, target_dir: Optional[str] = None) -> bool:
        """Uninstall the plugin from Anki addon directory."""
        print(f"Uninstalling {self.package_name}...")

        # Find installed copies
        installed_paths = []

        if target_dir:
            install_path = Path(target_dir) / self.package_name
            if install_path.exists():
                installed_paths.append(install_path)
        else:
            for addon_dir in self.anki_addon_dirs:
                install_path = addon_dir / self.package_name
                if install_path.exists():
                    installed_paths.append(install_path)

        if not installed_paths:
            print("[ERROR] Plugin not found in any Anki addon directory")
            return False

        # Remove all installed copies
        try:
            for install_path in installed_paths:
                print(f"Removing: {install_path}")
                shutil.rmtree(install_path)

            print(f"[SUCCESS] Successfully uninstalled {self.package_name}")
            print("Please restart Anki to complete removal")
            return True

        except Exception as e:
            print(f"[ERROR] Error uninstalling plugin: {e}")
            return False

    def status(self) -> None:
        """Show installation status."""
        print(f"{self.package_name} v{self.version} Status")
        print("=" * 50)

        installed = False
        for addon_dir in self.anki_addon_dirs:
            install_path = addon_dir / self.package_name
            if install_path.exists():
                print(f"[OK] Installed at: {install_path}")
                installed = True

                # Show version if available
                try:
                    version_file = install_path / "VERSION"
                    if version_file.exists():
                        with open(version_file, 'r') as f:
                            installed_version = f.read().strip()
                        print(f"   Version: {installed_version}")
                except Exception:
                    pass

        if not installed:
            print("[NOT INSTALLED] Plugin not found in any Anki addon directory")

        print(f"\nScanned addon directories:")
        for addon_dir in self.anki_addon_dirs:
            status = "[OK]" if addon_dir.exists() else "[MISSING]"
            print(f"   {status} {addon_dir}")

    def build(self) -> bool:
        """Build distribution package."""
        print(f"Building {self.package_name} v{self.version} distribution package...")

        try:
            # Create build directory
            build_dir = self.project_root / "dist" / self.package_name
            if build_dir.exists():
                shutil.rmtree(build_dir)
            build_dir.mkdir(parents=True, exist_ok=True)

            # Copy source files
            print("Copying source files...")
            shutil.copytree(self.src_dir, build_dir / self.package_name)

            # Copy additional files
            additional_files = ["README.md", "LICENSE"]
            for file_name in additional_files:
                src_file = self.project_root / file_name
                if src_file.exists():
                    shutil.copy2(src_file, build_dir / file_name)

            # Copy plugin configuration files
            config_files = ["meta.json", "config.json"]
            for file_name in config_files:
                src_file = self.src_dir / file_name
                if src_file.exists():
                    shutil.copy2(src_file, build_dir / self.package_name / file_name)

            # Create package info
            package_info = {
                "name": self.package_name,
                "version": self.version,
                "build_time": str(Path.ctime(build_dir)),
                "files": self._get_package_files(build_dir)
            }

            with open(build_dir / "package_info.json", "w", encoding="utf-8") as f:
                json.dump(package_info, f, indent=2, ensure_ascii=False)

            # Create archive
            archive_name = f"{self.package_name}-v{self.version}"
            archive_path = self.project_root / "dist" / f"{archive_name}.zip"

            print("Creating archive...")
            shutil.make_archive(
                str(archive_path.with_suffix("")),  # Remove .zip extension
                "zip",
                build_dir.parent,
                build_dir.name
            )

            print(f"[SUCCESS] Build complete!")
            print(f"Package: {archive_path}")
            print(f"Size: {self._get_file_size(archive_path)}")

            return True

        except Exception as e:
            print(f"[ERROR] Build failed: {e}")
            return False

    def clean(self) -> bool:
        """Clean build artifacts."""
        print("Cleaning build artifacts...")

        try:
            # Remove build directories
            dirs_to_remove = [
                self.project_root / "build",
                self.project_root / "dist",
                self.project_root / "*.egg-info",
                self.project_root / "__pycache__",
                self.project_root / ".pytest_cache"
            ]

            for pattern in dirs_to_remove:
                for path in self.project_root.glob(pattern.name):
                    if path.is_dir():
                        shutil.rmtree(path)
                        print(f"Removed: {path}")
                    elif path.is_file():
                        path.unlink()
                        print(f"Removed: {path}")

            # Remove Python cache files
            for path in self.project_root.rglob("*.pyc"):
                path.unlink()
            for path in self.project_root.rglob("__pycache__"):
                if path.is_dir():
                    shutil.rmtree(path)

            print("[SUCCESS] Clean complete!")
            return True

        except Exception as e:
            print(f"[ERROR] Clean failed: {e}")
            return False

    def test(self) -> bool:
        """Run basic tests."""
        print("Running basic tests...")

        try:
            # Add source directory to Python path
            src_path = str(self.src_dir.parent)  # Add the parent directory so relative imports work
            if src_path not in sys.path:
                sys.path.insert(0, src_path)

            # Test configuration module independently
            print("Testing configuration...")
            try:
                sys.path.insert(0, str(self.src_dir))
                import config
                config_obj = config.get_config()
                print(f"   [OK] Configuration loaded (theme: {config_obj.ui.theme})")
            except Exception as e:
                print(f"   [FAIL] Configuration test: {e}")
                return False

            # Test core modules
            print("Testing core modules...")
            try:
                from ankityping.core.typing_engine import TypingEngine
                engine = TypingEngine("Hello World")
                result = engine.process_input("H")
                assert result.is_correct
                print("   [OK] typing_engine")
            except Exception as e:
                print(f"   [FAIL] typing_engine: {e}")
                return False

            try:
                from ankityping.core.stats import StatsCollector
                print("   [OK] stats module")
            except Exception as e:
                print(f"   [FAIL] stats module: {e}")
                return False

            try:
                from ankityping.core.hint import HintManager
                print("   [OK] hint module")
            except Exception as e:
                print(f"   [FAIL] hint module: {e}")
                return False

            # Test that we can at least import the main modules (without full functionality testing)
            print("Testing main modules...")
            try:
                import ankityping.anki_integration
                print("   [OK] anki_integration module")
            except Exception as e:
                print(f"   [FAIL] anki_integration module: {e}")
                return False

            try:
                import ankityping.ui.typing_dialog
                print("   [OK] typing_dialog module")
            except Exception as e:
                print(f"   [FAIL] typing_dialog module: {e}")
                return False

            try:
                import ankityping.ui.config_dialog
                print("   [OK] config_dialog module")
            except Exception as e:
                print(f"   [FAIL] config_dialog module: {e}")
                return False

            print("[SUCCESS] All tests passed!")
            return True

        except Exception as e:
            print(f"[FAIL] Test suite failed: {e}")
            return False

    def _get_package_files(self, directory: Path) -> List[str]:
        """Get list of files in package directory."""
        files = []
        for path in directory.rglob("*"):
            if path.is_file():
                relative_path = path.relative_to(directory)
                files.append(str(relative_path))
        return sorted(files)

    def _get_file_size(self, file_path: Path) -> str:
        """Get human-readable file size."""
        if not file_path.exists():
            return "0 B"

        size = file_path.stat().st_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def info(self) -> None:
        """Show package information."""
        print(f"{self.package_name} Package Information")
        print("=" * 50)
        print(f"Version: {self.version}")
        print(f"Project Root: {self.project_root}")
        print(f"Source Directory: {self.src_dir}")

        print("\nProject Files:")
        try:
            for path in sorted(self.src_dir.rglob("*")):
                if path.is_file():
                    relative_path = path.relative_to(self.src_dir)
                    print(f"   {relative_path}")
        except Exception as e:
            print(f"   [ERROR] Error listing files: {e}")

        print(f"\nAnki Addon Directories Found:")
        for addon_dir in self.anki_addon_dirs:
            print(f"   {addon_dir}")


def main():
    """Main entry point for package management CLI."""
    parser = argparse.ArgumentParser(
        description="Package management utility for ankityping plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python package.py install              # Install to default Anki directory
  python package.py install --force      # Force overwrite existing installation
  python package.py uninstall            # Uninstall from all locations
  python package.py build                # Build distribution package
  python package.py status               # Show installation status
  python package.py test                 # Run basic tests
  python package.py clean                # Clean build artifacts
  python package.py info                 # Show package information
        """
    )

    parser.add_argument(
        "command",
        choices=["install", "uninstall", "status", "build", "clean", "test", "info"],
        help="Command to execute"
    )

    parser.add_argument(
        "--target-dir",
        help="Target Anki addon directory (auto-detected if not specified)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing installation"
    )

    args = parser.parse_args()

    pm = PackageManager()

    if args.command == "install":
        success = pm.install(args.target_dir, args.force)
        sys.exit(0 if success else 1)

    elif args.command == "uninstall":
        success = pm.uninstall(args.target_dir)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        pm.status()

    elif args.command == "build":
        success = pm.build()
        sys.exit(0 if success else 1)

    elif args.command == "clean":
        success = pm.clean()
        sys.exit(0 if success else 1)

    elif args.command == "test":
        success = pm.test()
        sys.exit(0 if success else 1)

    elif args.command == "info":
        pm.info()


if __name__ == "__main__":
    main()