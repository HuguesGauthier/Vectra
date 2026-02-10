import os
import sys
import asyncio
import glob
import subprocess
from datetime import datetime
from typing import List

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # If FastMCP is not available, we might need a fallback or just fail until installed
    # For writing the file, I'll assume it will be installed.
    # If not, the user needs to install 'mcp'
    pass

# Initialize FastMCP Server
mcp = FastMCP("VectraRefactorAgent")

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.log")


def log_message(message: str):
    """Log a message with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


# --- TOOLS ---


@mcp.tool()
def list_files(directory: str, extensions: List[str] = [".py"]) -> List[str]:
    """Recursively list files in a directory filtered by extensions."""
    files = []
    cwd = os.getcwd()

    # Sanitize directory to prevent traversal above root
    if ".." in directory:
        return [
            f"Error: Access denied. You cannot traverse above the root directory ({cwd}). Use '.' for root."
        ]

    # If directory is just ".", use current dir
    search_dir = directory if directory and directory != "." else cwd

    # Handle relative paths properly
    if not os.path.isabs(search_dir):
        search_dir = os.path.join(cwd, search_dir)

    if not os.path.exists(search_dir):
        return [f"Error: Directory {search_dir} does not exist. CWD is {cwd}"]

    for root, _, filenames in os.walk(search_dir):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, filename)
                # Return relative path to CWD for easier reading by LLM
                rel_path = os.path.relpath(full_path, cwd)
                # Filter out garbage
                skip_dirs = [
                    "venv",
                    "node_modules",
                    "dist",
                    ".quasar",
                    "migrations",
                    "__pycache__",
                    ".git",
                ]
                if not any(d in rel_path for d in skip_dirs):
                    files.append(rel_path)
    return sorted(files)


@mcp.tool()
def read_file(path: str) -> str:
    """Read the content of a file."""
    if not os.path.exists(path):
        return f"Error: File {path} does not exist."
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file. Overwrites existing content."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@mcp.tool()
async def run_command(command: str) -> str:
    """Run a shell command and return output. Use for git, linters, pytest."""
    try:
        # Log command start
        log_message(f"Running command: {command}")

        # Prepare environment with venv Scripts in PATH
        env = os.environ.copy()
        python_exe = sys.executable
        if "Scripts" in python_exe:
            scripts_dir = os.path.dirname(python_exe)
            env["PATH"] = scripts_dir + os.pathsep + env.get("PATH", "")

        # Use asyncio subprocess for non-blocking execution
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            env=env,
            cwd=os.getcwd(),
        )
        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode(errors="replace").strip()
        stderr_text = stderr.decode(errors="replace").strip()

        # Truncate output if too long to prevent token limit errors
        max_len = 100000
        if len(stdout_text) > max_len:
            stdout_text = (
                stdout_text[:max_len]
                + f"\n... [Output truncated. Total length: {len(stdout_text)}]"
            )
        if len(stderr_text) > max_len:
            stderr_text = (
                stderr_text[:max_len]
                + f"\n... [Output truncated. Total length: {len(stderr_text)}]"
            )

        output = f"STDOUT:\n{stdout_text}\nSTDERR:\n{stderr_text}"

        # Log completion
        log_message(f"Command finished. Return code: {process.returncode}")

        return output
    except Exception as e:
        error_msg = f"Error running command: {str(e)}"
        log_message(error_msg)
        return error_msg


if __name__ == "__main__":
    # Start the server (stdio mode by default for FastMCP)
    mcp.run()
