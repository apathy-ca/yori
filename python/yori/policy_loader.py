"""
YORI Policy Loader

Utilities for loading, validating, and compiling Rego policy files.
"""

import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class PolicyLoader:
    """
    Utility for managing Rego policy files.

    Handles compilation of .rego files to .wasm for use with OPA.
    """

    def __init__(self, policy_dir: Path):
        """
        Initialize policy loader.

        Args:
            policy_dir: Directory containing .rego source files
        """
        self.policy_dir = Path(policy_dir)
        self.opa_cli = shutil.which("opa")

        if not self.opa_cli:
            logger.warning("OPA CLI not found - policy compilation not available")

    def list_rego_files(self) -> List[Path]:
        """
        Find all .rego files in the policy directory.

        Returns:
            List of .rego file paths
        """
        if not self.policy_dir.exists():
            logger.warning(f"Policy directory does not exist: {self.policy_dir}")
            return []

        rego_files = list(self.policy_dir.glob("*.rego"))
        logger.info(f"Found {len(rego_files)} .rego files in {self.policy_dir}")
        return rego_files

    def validate_rego(self, rego_file: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate a .rego file using OPA CLI.

        Args:
            rego_file: Path to .rego file

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.opa_cli:
            return False, "OPA CLI not available"

        try:
            result = subprocess.run(
                [self.opa_cli, "check", str(rego_file)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Validation timeout"
        except Exception as e:
            return False, f"Validation error: {e}"

    def compile_to_wasm(
        self,
        rego_file: Path,
        output_dir: Optional[Path] = None,
        entrypoint: Optional[str] = None,
    ) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Compile a .rego file to WebAssembly.

        Args:
            rego_file: Path to .rego file
            output_dir: Output directory (defaults to same dir as rego_file)
            entrypoint: OPA entrypoint (e.g., "yori/bedtime/allow")

        Returns:
            Tuple of (success, wasm_path, error_message)
        """
        if not self.opa_cli:
            return False, None, "OPA CLI not available"

        # Default output directory
        if output_dir is None:
            output_dir = rego_file.parent

        # Default entrypoint based on package name
        if entrypoint is None:
            # Extract package name from .rego file
            package_name = self._extract_package_name(rego_file)
            if package_name:
                entrypoint = f"{package_name}/allow"
            else:
                return False, None, "Could not determine entrypoint from package"

        # Output .wasm file
        wasm_file = output_dir / f"{rego_file.stem}.wasm"

        try:
            # Build command: opa build -t wasm -e <entrypoint> policy.rego
            result = subprocess.run(
                [
                    self.opa_cli,
                    "build",
                    "-t", "wasm",
                    "-e", entrypoint,
                    "-o", str(wasm_file.with_suffix(".tar.gz")),
                    str(rego_file),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # OPA outputs a tarball, extract the .wasm file
                import tarfile
                with tarfile.open(wasm_file.with_suffix(".tar.gz"), "r:gz") as tar:
                    # Extract policy.wasm from bundle
                    tar.extract("policy.wasm", path=output_dir)

                # Rename to match source file
                extracted = output_dir / "policy.wasm"
                extracted.rename(wasm_file)

                # Clean up tarball
                wasm_file.with_suffix(".tar.gz").unlink()

                logger.info(f"Compiled {rego_file.name} to {wasm_file.name}")
                return True, wasm_file, None
            else:
                return False, None, result.stderr

        except subprocess.TimeoutExpired:
            return False, None, "Compilation timeout"
        except Exception as e:
            return False, None, f"Compilation error: {e}"

    def _extract_package_name(self, rego_file: Path) -> Optional[str]:
        """
        Extract package name from a .rego file.

        Args:
            rego_file: Path to .rego file

        Returns:
            Package name (e.g., "yori.bedtime") or None
        """
        try:
            with open(rego_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("package "):
                        # Extract package name
                        package = line[8:].strip()
                        return package
            return None
        except Exception as e:
            logger.error(f"Failed to extract package from {rego_file}: {e}")
            return None

    def compile_all(self, output_dir: Optional[Path] = None) -> Tuple[int, int]:
        """
        Compile all .rego files to .wasm.

        Args:
            output_dir: Output directory for .wasm files

        Returns:
            Tuple of (success_count, failure_count)
        """
        rego_files = self.list_rego_files()
        success_count = 0
        failure_count = 0

        for rego_file in rego_files:
            # First validate
            is_valid, error = self.validate_rego(rego_file)
            if not is_valid:
                logger.error(f"Validation failed for {rego_file.name}: {error}")
                failure_count += 1
                continue

            # Then compile
            success, wasm_path, error = self.compile_to_wasm(rego_file, output_dir)
            if success:
                success_count += 1
            else:
                logger.error(f"Compilation failed for {rego_file.name}: {error}")
                failure_count += 1

        logger.info(
            f"Compiled {success_count} policies, {failure_count} failures"
        )
        return success_count, failure_count


def compile_policies(
    policy_dir: str = "/usr/local/etc/yori/policies",
    output_dir: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Compile all Rego policies in a directory to WebAssembly.

    Args:
        policy_dir: Directory containing .rego files
        output_dir: Output directory for .wasm files (defaults to policy_dir)

    Returns:
        Tuple of (success_count, failure_count)
    """
    loader = PolicyLoader(Path(policy_dir))
    out_path = Path(output_dir) if output_dir else None
    return loader.compile_all(out_path)
