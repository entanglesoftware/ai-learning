import asyncio
from dotenv import load_dotenv
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

load_dotenv()

CartItems = []
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
        name="Wine_Commerce_Helper",
        description="You are a wine e-commerce helper. You are able to retrieve the list of products or find certain product from the mcp server. ",
        model="gemini-1.5-flash-latest",
        instruction='''
            1. You can search for wine products from the mcp server.
            2. If user asks for details about specific wine product, search for it first,if there are multiple results select the most relevant one,  then find details using product url and lwin fetched during search.
            3. To add to cart a wine product,
                3.1 First search using search tool if not already
                3.2 Then get wine details using WineDetails tool
                3.3 You will get product_id from WineDetails Tool, This is what we use in AddToCart function.
                3.4 Use AddToCart tool to finally add to cart. Always confirm the exact product and quantity(Packs) before adding to cart. Also, add product to CartItems array after successful response from mcp server.
            4. List all items in CartItems array.
            Make sure to use the tools as specified in the tool list. If you don't get the appropriate tools , just say that you don't know.
            ''',
        tools=tools,
    )

    return agent_instance, exit_stack

async def async_input(prompt: str = "") -> str:
    return await asyncio.to_thread(input, prompt)

async def async_main():
    root_agent, exit_stack = await create_agent()

    session_service = InMemorySessionService()

    runner = Runner(
        app_name='Product_Lister/Finder_Agent',
        agent=root_agent,
        session_service=session_service,
    )

    session = session_service.create_session(
       state={}, app_name='Product_Lister/Finder_Agent', user_id='user_fs'
    )
    print(f"Session created: {session.id}")

    session_id = ["None"] * 5
    session_id[0] = session.id
    num = 0
    print("Running agent...")
    while True:
        query = await async_input(f"User Query {num}: ")
        if query.lower() in ["exit", "quit"]:
            print("Exiting...")
            break
        if "switch up" in query.lower():
            num = num + 1
            if session_id[num] != "None":
                print(f"Session already exists. Switching to existing session {session_id[num]}")
                id = session_id[num]
                session = session_service.get_session(app_name='Product_Lister/Finder_Agent', user_id='user_fs', session_id=id)

            else :
                print("No existing session found. Creating new session.")
                session = session_service.create_session(
                    state={}, app_name='Product_Lister/Finder_Agent', user_id='user_fs'
                )
                session_id[num] = session.id
                print(f"New session created: {session.id}")
            continue
        if "switch down" in query.lower():
            num = num - 1
            if session_id[num] != "None":
                print(f"Session already exists. Switching to existing session {session_id[num]}")
                id = session_id[num]
                session = session_service.get_session(app_name='Product_Lister/Finder_Agent', user_id='user_fs',
                                                      session_id=id)

            else:
                print("No existing session found. Creating new session.")
                session = session_service.create_session(
                    state={}, app_name='Product_Lister/Finder_Agent', user_id='user_fs'
                )
                session_id[num] = session.id
                print(f"New session created: {session.id}")
            continue
        content = types.Content(role='user', parts=[types.Part(text=query)])
        events_async = runner.run_async(
            session_id=session.id, user_id=session.user_id, new_message=content
        )

        async for event in events_async:
            print(f"Event received: {event.content.parts[0].text}")
        print("\n")
        print(f"session events{session.events}")
        print(f"State: {session.state}")

    await exit_stack.aclose()


if __name__ == "__main__":
    asyncio.run(async_main())