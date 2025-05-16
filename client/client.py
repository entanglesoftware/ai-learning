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
    # tools, exit_stack = await MCPToolset.from_server(
    #     connection_params=StdioServerParameters(
    #     command='npx',
    #     args=["-y",
    #           "@openbnb/mcp-server-airbnb",
    #           "--ignore-robots-txt",
    #         ],
    #       )
    #     )

    print(f"--- Connected to MCP. Discovered {len(tools)} tool(s). ---")
    for tool in tools:
        print(f"  - Discovered tool: {tool.name}")
    # agent_instance = Agent(
    #     model='gemini-2.0-flash',
    #     name='airbnb_assistant',
    #     instruction='Help user interact with the AirBNB website and listings.',
    #     tools=tools,
    # )

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

# async def async_main():
#     agent, exit_stack = await create_agent()
#     session_service = InMemorySessionService()
#     session = session_service.create_session(
#         state={}, app_name='json_reader', user_id='user_123'
#     )
#     runner = Runner(
#         app_name='helper agent',
#         agent=agent,
#         session_service=session_service,
#     )
#
#     try:
#         while True:
#             # user_input = await async_input("User Query: ")
#             user_input = "User Query: List Products"
#
#             if user_input.lower() in ["exit", "quit"]:
#                 print("Exiting...")
#                 break
#             if len(user_input) == 0:
#                 user_input = "List Products"
#             content = types.Content(role='user', parts=[types.Part(text=user_input)])
#             events_async = runner.run_async(
#                 session_id=session.id,
#                 user_id=session.user_id,
#                 new_message=content
#             )
#
#             async for event in events_async:
#                 print(f"Response: {event.content}")
#             break
#     finally:
#         await exit_stack.aclose()
#         print("MCP connection closed. Cleanup complete.")

async def async_main():
    queries = ["List Products", "List All products", "Do you have mango?", "How many products you have?"]
    session_service = InMemorySessionService()
    session = session_service.create_session(
       state={}, app_name='Product Lister/Finder Agent', user_id='user_fs'
    )
    # content = types.Content(role='user', parts=[types.Part(text=query)])
    root_agent, exit_stack = await create_agent()

    runner = Runner(
        app_name='Product Lister/Finder Agent',
        agent=root_agent,
        session_service=session_service,
    )

    print("Running agent...")
    for query in queries:
        print(f"User Query: {query}")
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