import os
import sys
import json
import openai
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional
from contextlib import AsyncExitStack

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to get OpenAI response (with optional tools)
async def get_openai_response(messages, functions=None):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        functions=functions,
        function_call="auto" if functions else None,
        temperature=0.7,
        max_tokens=1000
    )
    return response["choices"][0]["message"]

class MCPClient:
    def __init__(self):
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\n✅ Connected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI API and call tools if requested"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Use tools if needed."},
            {"role": "user", "content": query}
        ]

        # Get tool definitions from MCP server
        tools_response = await self.session.list_tools()
        tools = tools_response.tools

        # Define functions for tools
        functions = [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters if hasattr(tool, 'parameters') else {}
            }
            for tool in tools
        ]

        # Ask OpenAI for a response
        first_reply = await get_openai_response(messages, functions)
        if "function_call" in first_reply:
            func_call = first_reply["function_call"]
            tool_name = func_call["name"]
            tool_args = json.loads(func_call.get("arguments", "{}"))

            # Call the tool requested by OpenAI
            tool_result = await self.session.call_tool(tool_name, tool_args)

            # Handle the result in case it doesn't have 'output'
            if hasattr(tool_result, 'output'):
                tool_output = tool_result.output
            else:
                tool_output = str(tool_result)

            # Add the function call and its result to the message list
            messages.append(first_reply)
            messages.append({
                "role": "function",
                "name": tool_name,
                "content": tool_output
            })

            # Ask OpenAI again with tool output
            final_reply = await get_openai_response(messages)
            return final_reply["content"]

        # If no tool was needed
        return first_reply["content"]

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\n🚀 MCP Client Started! Type your queries or 'quit' to exit.")
        while True:
            query = input("\n🗨️ Query: ").strip()
            if query.lower() == 'quit':
                break

            response = await self.process_query(query)
            print("\n🤖", response)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())

# import os
# import sys
# import json
# import asyncio
# import httpx
# from dotenv import load_dotenv
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
# from typing import Optional
# from contextlib import AsyncExitStack

# load_dotenv()
# API_BASE = os.getenv("PROPRIETARY_API_BASE")  # e.g., https://winegpt-api.cruworldwine.com/

# async def get_model_response(messages, functions=None):
#     headers = {
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "model": "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
#         "messages": messages,
#         "temperature": 0.7,
#         "max_tokens": 1000,
#     }

#     if functions:
#         payload["tools"] = functions
#         payload["tool_choice"] = "auto"

#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             f"{API_BASE.rstrip('/')}/v1/models", 
#             headers=headers,
#             json=payload,
#             timeout=30
#         )
#         response.raise_for_status()
#         data = response.json()

#         print("✅ Connected to the proprietary model successfully.")
#         return data["choices"][0]["message"]



# class MCPClient:
#     def __init__(self):
#         self.exit_stack = AsyncExitStack()

#     async def connect_to_server(self, server_script_path: str):
#         is_python = server_script_path.endswith('.py')
#         is_js = server_script_path.endswith('.js')
#         if not (is_python or is_js):
#             raise ValueError("Server script must be a .py or .js file")

#         command = "python" if is_python else "node"
#         server_params = StdioServerParameters(
#             command=command,
#             args=[server_script_path],
#             env=None
#         )

#         stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
#         self.stdio, self.write = stdio_transport
#         self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
#         await self.session.initialize()

#         response = await self.session.list_tools()
#         tools = response.tools
#         print("\n✅ Connected to server with tools:", [tool.name for tool in tools])

#     async def process_query(self, query: str) -> str:
#         messages = [
#             {"role": "system", "content": "You are a helpful assistant. Use tools if needed."},
#             {"role": "user", "content": query}
#         ]

#         tools_response = await self.session.list_tools()
#         tools = tools_response.tools

#         functions = [
#             {
#                 "name": tool.name,
#                 "description": tool.description,
#                 "parameters": tool.parameters if hasattr(tool, 'parameters') else {}
#             }
#             for tool in tools
#         ]

#         first_reply = await get_model_response(messages, functions)
#         if "tool_call" in first_reply:
#             func_call = first_reply["tool_call"]
#             tool_name = func_call["name"]
#             tool_args = json.loads(func_call.get("arguments", "{}"))

#             tool_result = await self.session.call_tool(tool_name, tool_args)
#             tool_output = getattr(tool_result, 'output', str(tool_result))

#             messages.append(first_reply)
#             messages.append({
#                 "role": "tool",
#                 "name": tool_name,
#                 "content": tool_output
#             })

#             final_reply = await get_model_response(messages)
#             return final_reply["content"]

#         return first_reply["content"]

#     async def chat_loop(self):
#         print("\n🚀 MCP Client Started! Type your queries or 'quit' to exit.")
#         while True:
#             query = input("\n🗨️ Query: ").strip()
#             if query.lower() == 'quit':
#                 break
#             response = await self.process_query(query)
#             print("\n🤖", response)

#     async def cleanup(self):
#         await self.exit_stack.aclose()

# async def main():
#     if len(sys.argv) < 2:
#         print("Usage: python client.py <path_to_server_script>")
#         sys.exit(1)

#     client = MCPClient()
#     try:
#         await client.connect_to_server(sys.argv[1])
#         await client.chat_loop()
#     finally:
#         await client.cleanup()

# if __name__ == "__main__":
#     asyncio.run(main())

