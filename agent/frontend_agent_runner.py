import asyncio
import os
import sys
import json
import argparse
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
    os.path.dirname(os.path.abspath(__file__)), "frontend_agent_state.json"
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


async def run_frontend_agent(goal: str, target_file: str = None):
    print(f"🚀 Starting Frontend Agent with goal: {goal}")
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

            # Define Tool Wrappers for Manual Execution
            async def execute_tool(name, args):
                print(f"  🔧 Executing Tool: {name}({args})")
                try:
                    result = await session.call_tool(name, arguments=args)
                    return result.content[0].text
                except Exception as e:
                    return f"Error executing tool {name}: {e}"

            # Tools definition for Gemini
            def list_files(directory: str, extensions: list[str]):
                pass

            def read_file(path: str):
                pass

            def write_file(path: str, content: str):
                pass

            def run_command(command: str):
                pass

            gemini_tools = [list_files, read_file, write_file, run_command]

            # Initialize Model
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                tools=gemini_tools,
            )

            chat = model.start_chat()

            context = ""
            if target_file:
                context = f"The user wants you to focus ONLY on this file: {target_file}. Read it first."

            # Load Frontend Prompt if available
            frontend_prompt = ""
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # 1. Specialized Frontend Architect Prompt
            frontend_prompt_path = os.path.join(
                root_dir, "prompts", "prompt_architect_P0_frontend.md"
            )
            if os.path.exists(frontend_prompt_path):
                try:
                    with open(frontend_prompt_path, "r", encoding="utf-8") as f:
                        frontend_prompt += f"\n\n--- FRONTEND ARCHITECTURAL STANDARDS (MANDATORY) ---\n{f.read()}\n--------------------------------------------\n"
                except Exception as e:
                    print(f"⚠️ Could not read specialized frontend prompt: {e}")

            # 2. General Architect Prompt (Optional extra context)
            general_prompt_path = os.path.join(
                root_dir, "prompts", "prompt_architect_P0.md"
            )
            if os.path.exists(general_prompt_path):
                try:
                    with open(general_prompt_path, "r", encoding="utf-8") as f:
                        frontend_prompt += f"\n\n--- GENERAL ARCHITECTURAL STANDARDS ---\n{f.read()}\n--------------------------------------------\n"
                except Exception as e:
                    print(f"⚠️ Could not read general architect prompt: {e}")

            system_instruction = f"""
            You are an autonomous AI Frontend Developer Agent specialized in Vue 3, Quasar, and TypeScript.
            Your goal is: {goal}
            {context}
            
            {frontend_prompt}
            
            EXECUTION PLAN:
            1. Analyze the goal.
            2. Explore the codebase using `list_files(extensions=['.vue', '.ts', '.js'])` if needed.
            3. Read the target file.
            4. Make a plan for refactoring:
               - Use Vue 3 Composition API (`<script setup lang="ts">`).
               - Follow TypeScript best practices.
               - Leverage Quasar components and utility classes.
            5. Implementation:
               - **CRITICAL**: Maintain all existing logic and functionality.
               - **CRITICAL**: Do not use placeholders or "TO-DO" comments.
               - Rewrite the file with improvements.
            6. Verification:
               - Run `npm run lint` or `eslint <file>` via `run_command` if possible.
               - Run `npx prettier --write <file>` to ensure formatting.
            7. Finalize and output "TASK_FINISHED".
            """

            # Initial Prompt
            print("🤖 Agent Thinking...")
            response = await chat.send_message_async(system_instruction)

            # Loop for Tool Calls
            max_turns = 50
            for i in range(max_turns):
                function_calls = [
                    part.function_call for part in response.parts if part.function_call
                ]

                if function_calls:
                    responses = []
                    for fn in function_calls:
                        tool_result = await execute_tool(fn.name, dict(fn.args))
                        if len(tool_result) > 20000:
                            tool_result = tool_result[:20000] + "... [Truncated]"
                        responses.append(
                            content.Part(
                                function_response=content.FunctionResponse(
                                    name=fn.name, response={"result": tool_result}
                                )
                            )
                        )

                    print("  📤 Sending Tool Results...", end="", flush=True)
                    response = await chat.send_message_async(responses)
                    print(" Done.")
                else:
                    agent_text = response.text
                    print(f"🤖 Agent: {agent_text}")
                    if "TASK_FINISHED" in agent_text.upper():
                        return True
                    break
            return False


async def main():
    parser = argparse.ArgumentParser(description="Frontend AI Developer Agent")
    parser.add_argument("target", help="File or directory to process")
    parser.add_argument(
        "--goal",
        default="Refactor this component to use Composition API, standard TypeScript interfaces, and optimize performance.",
        help="Goal for the agent",
    )

    args = parser.parse_args()
    target_path = os.path.abspath(args.target)
    processed_files = load_state()

    files_to_process = []
    if os.path.isfile(target_path):
        files_to_process.append(target_path)
    elif os.path.isdir(target_path):
        # We'd need to adapt the scan logic here if batching
        pass

    for file_path in files_to_process:
        success = await run_frontend_agent(args.goal, target_file=file_path)
        if success:
            processed_files.add(file_path)
            save_state(processed_files)
            print(f"✅ Finished: {os.path.basename(file_path)}")


if __name__ == "__main__":
    asyncio.run(main())
