import asyncio
import os
import sys
import json
import argparse
import glob
import google.generativeai as genai
from dotenv import load_dotenv
from google.ai.generativelanguage_v1beta.types import content

# Try importing MCP SDK
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP library not found. Please run 'pip install mcp'.")
    sys.exit(1)

# Configuration
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Try finding .env in parent dir
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(parent_dir, ".env")
    load_dotenv(env_path)
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY not found.")
    sys.exit(1)

genai.configure(api_key=api_key)

STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "backend_agent_state.json"
)


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()


def save_state(processed_files):
    with open(STATE_FILE, "w") as f:
        json.dump(list(processed_files), f, indent=2)


def get_python_files(directory):
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".py"):
                # Exclude venv, migrations, etc.
                if "venv" in root or "migrations" in root or "__pycache__" in root:
                    continue
                files.append(os.path.join(root, filename))
    return files


async def run_agent(goal: str, target_file: str = None):
    print(f"🚀 Starting Agent with goal: {goal}")
    if target_file:
        print(f"📄 Target File: {target_file}")

    server_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "server.py"
    )
    server_params = StdioServerParameters(
        command=sys.executable, args=[server_script], env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List Tools to confirm connection
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"🛠️ Connected Tools: {tool_names}")

            # Define Tool Wrappers for Manual Execution
            async def execute_tool(name, args):
                print(f"  🔧 Executing Tool: {name}({args})")
                try:
                    result = await session.call_tool(name, arguments=args)
                    return result.content[0].text
                except Exception as e:
                    return f"Error executing tool {name}: {e}"

            # Define Tools for Gemini (Schema)
            def list_files(directory: str):
                """Recursively list all Python files in a directory."""
                pass

            def read_file(path: str):
                """Read the content of a file."""
                pass

            def write_file(path: str, content: str):
                """Write content to a file. Overwrites existing content."""
                import shutil

                if os.path.exists(path):
                    backup_path = path + ".bak"
                    shutil.copy2(path, backup_path)
                    print(f"  💾 Backup created: {backup_path}")

                # Create parent directories if they don't exist
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"File written to {path}. Backup saved to {path}.bak"

            def run_command(command: str):
                """Run a shell command (git, linters, pytest)."""
                pass

            gemini_tools = [list_files, read_file, write_file, run_command]

            # Initialize Model
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",  # Upgrade to Gemini 3 Flash for latest capabilities
                tools=gemini_tools,
            )

            # Start Chat (Manual Execution Mode)
            chat = model.start_chat()

            context = ""
            if target_file:
                context = f"The user wants you to focus ONLY on this file: {target_file}. Read it first. All tools (black, isort, flake8, pytest) are available via 'python -m <tool>'."

            system_instruction = f"""
            You are an autonomous AI Developer Agent.
            Your goal is: {goal}
            {context}

            FOLLOW THIS STRUCTURED WORKFLOW (STRICT PHASED EXECUTION):

            PHASE 1: RESEARCH & PLANNING
            1. **Analyze**: Read the target file and any relevant project structure.
            2. **Inventory**: Check if a test file exists (e.g., `tests/api/v1/endpoints/test_audio.py`).
            3. **Output Plan**: Output a `[PLAN]` section describing your approach.
            4. **Output Task List**: Output a `[TASK LIST]` with granular steps (e.g., "Add type hints to func X", "Create test skeleton").

            PHASE 2: SEQUENTIAL EXECUTION
            1. **Execute**: Follow your task list step-by-step.
            2. **Batching**: Only perform ONE `write_file` call per turn, but include all necessary logic/docstring changes for that file in that single call. 
            3. **Test Skeleton**: If the test file is missing, you MUST CREATE it before attempting to run tests.

            PHASE 3: CLEANUP & VALIDATION
            1. **Consolidated Tooling**: Chain your cleanup commands in one turn if possible: `python -m black <path> && python -m isort <path> && python -m flake8 <path>`.
            2. **Fix & Verify**: If `flake8` fails, fix the code and RE-RUN the cleanup.

            PHASE 4: TESTING & COVERAGE
            1. **Verify**: Run `pytest` with coverage. Goal: 95% coverage on the source file.
            2. **Report**: Your final response MUST include the final coverage percentage.
            3. **Finalize**: Output "TASK_FINISHED" only when coverage is met and linting passes.

            CRITICAL SAFETY & COST CONTROL:
            - **STABILITY**: Once docstrings and logic are verified by tests, DO NOT modify them for cosmetic reasons.
            - **ANTI-LOOP**: If you are stuck on a linting error for more than 2 turns, STOP and report the deadlock.
            - **NO PIP**: Do NOT run `pip install`.
            - **ROUTING**: NEVER modify FastAPI router prefixes or mounting logic (e.g., `APIRouter(prefix=...)`).
            - **MANDATORY**: Use `python -m <tool>` for black, isort, and flake8.
            """

            # Initial Prompt
            print("🤖 Agent Thinking...")
            response = await chat.send_message_async(system_instruction)

            # Loop for Tool Calls
            max_turns = (
                200  # Increased to allow for thorough refactoring/testing cycles
            )
            for i in range(max_turns):
                # Check for Function Calls
                function_calls = []
                for part in response.parts:
                    if fn := part.function_call:
                        function_calls.append(fn)

                if function_calls:
                    # Execute all function calls
                    responses = []
                    for fn in function_calls:
                        tool_name = fn.name
                        tool_args = dict(fn.args)

                        tool_result = await execute_tool(tool_name, tool_args)

                        # TRUNCATE to avoid payload issues
                        if len(tool_result) > 20000:
                            tool_result = tool_result[:20000] + "... [Output Truncated]"

                        responses.append(
                            content.Part(
                                function_response=content.FunctionResponse(
                                    name=tool_name, response={"result": tool_result}
                                )
                            )
                        )

                    # Send results back to Gemini
                    print("  📤 Sending Tool Results to Gemini...", end="", flush=True)
                    try:
                        response = await chat.send_message_async(responses)
                        print(" Done.")
                    except Exception as e:
                        print(f"\n❌ Error sending results to Gemini: {e}")
                        # Fallback: Send a simple error message to keep the conversation going
                        try:
                            fallback_responses = []
                            for fn in function_calls:
                                fallback_responses.append(
                                    content.Part(
                                        function_response=content.FunctionResponse(
                                            name=fn.name,
                                            response={
                                                "result": "Error: Output too large or malformed. Please try a different approach."
                                            },
                                        )
                                    )
                                )
                            response = await chat.send_message_async(fallback_responses)
                            print("  ✅ Recovered with fallback message.")
                        except Exception as fallback_e:
                            print(f"  ❌ CRITICAL: Fallback failed too: {fallback_e}")
                            break

                else:
                    # No tool calls, just text response
                    agent_text = response.text
                    print(f"🤖 Agent: {agent_text}")

                    # Robust completion check (case-insensitive)
                    completion_signals = [
                        "TASK_FINISHED",
                        "TASK_FINISHED_WITH_ERRORS",
                        "TASK_COMPLETED",
                        "TERMINÉ",
                        "FINISHED",
                    ]

                    if any(sig in agent_text.upper() for sig in completion_signals):
                        print(
                            f"✅ Agent signalled completion ({'Success' if 'TASK_FINISHED' in agent_text.upper() else 'Finished with errors'})."
                        )
                        return True

                    # Stop if no tool calls and no explicit finish signal
                    print(
                        "⚠️ No tool calls detected and no completion signal found. Stopping."
                    )
                    return False

            print(f"⚠️ Reached max turns ({max_turns}). Stopping.")
            return False


async def main():
    parser = argparse.ArgumentParser(description="AI Developer Agent Runner")
    parser.add_argument(
        "target", nargs="?", default="app", help="File or directory to process"
    )
    parser.add_argument("--reset", action="store_true", help="Reset validation state")
    parser.add_argument(
        "--goal",
        default="Refactor this file to add type hints and improve code quality.",
        help="Goal for the agent",
    )

    args = parser.parse_args()

    target_path = os.path.abspath(args.target)
    processed_files = load_state()

    if args.reset:
        processed_files = set()
        print("🔄 State reset.")

    files_to_process = []

    if os.path.isfile(target_path):
        files_to_process.append(target_path)
    elif os.path.isdir(target_path):
        print(f"📂 Scanning directory: {target_path}")
        all_files = get_python_files(target_path)
        # Filter processed
        for f in all_files:
            if f not in processed_files:
                files_to_process.append(f)
            else:
                print(f"⏭️ Skipping already processed: {os.path.basename(f)}")
    else:
        print(f"❌ Invalid target: {target_path}")
        sys.exit(1)

    print(f"📋 Found {len(files_to_process)} files to process.")

    for file_path in files_to_process:
        print(f"\n==========================================")
        print(f"👉 Processing: {file_path}")
        print(f"==========================================")

        # Customize goal for the specific file
        current_goal = args.goal.replace("{file}", file_path)
        if "{file}" not in args.goal and "this file" in args.goal:
            # If strictly generic, append the filename for clarity
            current_goal += f" (Target: {file_path})"

        success = await run_agent(current_goal, target_file=file_path)

        # Consider any "True" return as a completion of the session for that file
        # to avoid infinite retries if the agent reached a terminal state.
        if success:
            processed_files.add(file_path)
            save_state(processed_files)
            print(f"✅ Marked {os.path.basename(file_path)} as complete/processed.")
        else:
            print(
                f"❌ Failed or reached max turns without finishing: {os.path.basename(file_path)}"
            )


if __name__ == "__main__":
    asyncio.run(main())
