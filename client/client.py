import asyncio
import os
from dotenv import load_dotenv
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

async def create_agent():
    tools, exit_stack = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command='python3',
            args=['../mcp_server/main.py'],
        )
    )

    print(f"--- Connected to MCP. Discovered {len(tools)} tool(s). ---")
    for tool in tools:
        print(f"  - Discovered tool: {tool.name}")

    agent_instance = Agent(
        name="Agent",
        description="Convert JSON response into readable format",
        model="gemini-1.5-flash-latest",
        instruction="1. Retrieve the list of products or find certain product from the mcp server. 2. Convert the response into readable format.",
        tools=tools,
    )

    return agent_instance, exit_stack

async def async_input(prompt: str = "") -> str:
    return await asyncio.to_thread(input, prompt)

async def async_main():
    # queries = ["List Products", "List All products", "Do you have mango?", "How many products you have?"]
    session_service = InMemorySessionService()
    session = session_service.create_session(
       state={}, app_name='Product Lister/Finder Agent', user_id='user_fs'
    )
    root_agent, exit_stack = await create_agent()

    runner = Runner(
        app_name='Product Lister/Finder Agent',
        agent=root_agent,
        session_service=session_service,
    )

    print("Running agent...")
    while True:
        query = await async_input("User Query: ")
        if query.lower() in ["exit", "quit"]:
            print("Exiting...")
            break
        content = types.Content(role='user', parts=[types.Part(text=query)])
        events_async = runner.run_async(
            session_id=session.id, user_id=session.user_id, new_message=content
        )
        async for event in events_async:
            print(f"Event received: {event.content.parts[0].text}")
        print("\n")
    await exit_stack.aclose()


if __name__ == "__main__":
    asyncio.run(async_main())