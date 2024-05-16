import asyncio

import json
import autogen
from autogen import UserProxyAgent, AssistantAgent, config_list_from_json

import panel as pn
pn.extension(design='material')

import dt_prompt as dt



template = pn.template.FastGridTemplate(
    title="Design Thinking Simulation",
   
    main_layout='card',
    prevent_collision=True,
)
with open('./design_thinking_team.json', 'r') as f:
    personas = json.load(f)

config_list = config_list_from_json(
    "OAI_CONFIG_LIST.json",
)

llm_config={"config_list": config_list}

input_future = None

class MyConversableAgent(autogen.ConversableAgent):

    async def a_get_human_input(self, prompt: str) -> str:
        global input_future
        chat_interface.send(prompt, user="System", respond=False)

        if input_future is None or input_future.done():
            input_future = asyncio.Future()

        await input_future

        input_value = input_future.result()
        input_future = None
        return input_value

personas_agents = []

for persona_name, persona_data in personas.items():
    persona_name = persona_data['Name']
    persona_prompt = dt.get_dt_prompt(persona_name, persona_data)
    persona_agent = AssistantAgent(
        name=persona_name,
        system_message=persona_prompt,
        llm_config=llm_config,
        human_input_mode="NEVER",
        description=f"{json.dumps(persona_data)}",
    )
    personas_agents.append(persona_agent)


user_proxy = UserProxyAgent(
    name="Admin",
    human_input_mode= "NEVER",
    system_message="Human Admin.",
    llm_config = llm_config,
    max_consecutive_auto_reply=5,
    default_auto_reply="Reply `TERMINATE` if the task is done.",
    is_termination_msg=lambda x: True if "TERMINATE" in x.get("content") else False,
 
)

groupchat = autogen.GroupChat(agents=[user_proxy] + personas_agents, messages=[], max_round=20)


manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

def print_messages(recipient, messages, sender, config):

    print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")

    content = messages[-1]['content']

    if all(key in messages[-1] for key in ['name']):
        chat_interface.send(content, user=messages[-1]['name'], respond=False)
    else:
        chat_interface.send(content, user=recipient.name, respond=False)
    
    return False, None  # required to ensure the agent communication flow continues

for persona in personas_agents:
    persona.register_reply(
        [autogen.Agent, None],
        reply_func=print_messages,
        config={"callback": None},
    )

user_proxy.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)

initiate_chat_task_created = False

async def delayed_initiate_chat(agent, recipient, message):

    global initiate_chat_task_created
    # Indicate that the task has been created
    initiate_chat_task_created = True

    # Wait for 2 seconds
    await asyncio.sleep(2)

    # Now initiate the chat
    await agent.a_initiate_chat(recipient, message=message)


async def callback(contents: str, user: str, instance: pn.chat.ChatInterface):
    
    global initiate_chat_task_created
    global input_future

    if not initiate_chat_task_created:
        asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))

    else:
        if input_future and not input_future.done():
            input_future.set_result(contents)
        else:
            print("There is currently no input being awaited.")


chat_interface = pn.chat.ChatInterface(callback=callback)
chat_interface.send(
    "Kickoff the meeting with your instructions..", user="System", respond=False
)

chat_interface.servable()



       