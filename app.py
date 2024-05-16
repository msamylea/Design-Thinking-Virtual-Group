import dt_team as dt
import panel as pn
import dt_prompt as dtp
import asyncio
import random
import config as cfg 

import json
import autogen
from autogen import UserProxyAgent, AssistantAgent, config_list_from_json

pn.extension(design='material', notifications=True)

output_area = pn.widgets.TextAreaInput(auto_grow=True, sizing_mode='stretch_width', height=800)


chat_interface = pn.chat.ChatInterface(callback=None, height=800, show_rerun=False, show_undo=False)
chat_interface_placeholder = pn.Row(chat_interface)
pn.state.notifications.position = 'center-center'

def summarize_chat(event):
    print("summarize_chat called")  # Debug print statement
    try:
        with open('./chat_summary.json', 'r') as f:
            chat_summary = json.load(f)
        print(f"chat_summary: {chat_summary}")  # Debug print statement

    except FileNotFoundError:
        pn.state.notifications.error('No chat summary found. Conduct a session first.')
        return
    llm = cfg.completions_model

    response = llm.chat.completions.create(
        messages = [
            {"role": "system",
            "content": f"Analyze the meeting notes and provide a detailed summary and analysis of the discussion in markdown format. Meeting: {chat_summary}"},
        ],
        model="l3custom"
    )
    print(f"response: {response}")  # Debug print statement

    analysis = response.choices[0].message.content
    output_area.value = analysis
    return analysis
    
def create_team(event):

    if not len(multi_choice.value) > 1:
        pn.state.notifications.error('Please select at least two team members to begin')
    else:
        selected_team = [dt.design_thinking_team[v] for v in multi_choice.value]
        persona_name = [dt.design_thinking_team[v]['name'] for v in multi_choice.value]
        persona_data = [dt.design_thinking_team[v]['description'] for v in multi_choice.value]

        with open ('selected_team.json', 'w') as file:
            json.dump(selected_team, file, indent=4)

        return selected_team, persona_name, persona_data
    

    
def start_sim(event):

    global initiate_chat_task_created
    global input_future
    initiate_chat_task_created = False
    input_future = None

    try:
        with open('./selected_team.json', 'r') as f:
            personas = json.load(f)

    except FileNotFoundError:
        pn.state.notifications.error('Please create a team before starting the simulation.')
        return
    
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

    for persona in personas:
        persona_name = persona['name']
        persona_data = persona['description']
        persona_prompt = dtp.get_dt_prompt(persona_name, persona_data)
        persona_agent = AssistantAgent(
            name=persona_name,
            system_message=persona_prompt,
            llm_config=llm_config,
            human_input_mode="NEVER",
            description=json.dumps(persona_data),
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

    facilitator = AssistantAgent(
        name="Facilitator",
        system_message="You facilitate the design thinking workshop. You are responsible for guiding the team through the workshop and ensuring that the team stays on track. You are not a participant in the workshop, but you are there to help the team when needed. You are the facilitator.",
        llm_config=llm_config,
        human_input_mode="NEVER",
        description="Facilitator of the design thinking workshop.",
    )

    def custom_speaker_selection_func(last_speaker: autogen.Agent, groupchat: autogen.GroupChat):
        messages = groupchat.messages
        if len(messages) <= 1:
            return facilitator
        elif last_speaker == facilitator:
            return random.choice(personas_agents)
        else:
            # Encourage personas to respond to each other
            last_message = messages[-1]['content']
            for persona in personas_agents:
                if persona.name in last_message:
                    return persona
            return random.choice(personas_agents)

    groupchat = autogen.GroupChat(agents=[user_proxy, facilitator] + personas_agents, messages=[], max_round=60, allow_repeat_speaker=False, speaker_selection_method=custom_speaker_selection_func)


    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    
    def print_messages(recipient, messages, sender, config):
        print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")
        
        content = messages[-1]['content']
        
        try:
            with open('./chat_summary.json', 'r') as f:
                chat_summary = json.load(f)
        except FileNotFoundError:
            chat_summary = []
        
        if content.strip():
            if all(key in messages[-1] for key in ['name']):
                message = f"{messages[-1]['name']}: {content}"
                chat_interface.send(message, user=messages[-1]['name'], respond=False)
            else:
                message = f"{recipient.name}: {content}"
                chat_interface.send(message, user=recipient.name, respond=False)
            
            chat_summary.append(message)  # Append the message to the loaded list
        
        # Save the updated chat summary to the JSON file
        with open('./chat_summary.json', 'w') as f:
            json.dump(chat_summary, f, indent=4)
        
        return False, None

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


    chat_interface.clear()
    chat_interface.callback = callback

    chat_interface.send(
        "Kickoff the meeting with your instructions..", user="System", respond=False
    )


    # chat_interface_placeholder.objects = [chat_interface, pn.Row(summarize_button)]


        
multi_choice = pn.widgets.MultiChoice(name='MultiSelect', value=[],
    options=list(dt.design_thinking_team.keys()), width=450, height=350)

submit_button = pn.widgets.Button(name='Create My Team', button_type='primary', clicks=0)
submit_button.on_click(create_team)


start_button = pn.widgets.Button(name='Start Simulation', button_type='success')
start_button.on_click(start_sim)

buttons = pn.Row(submit_button, start_button)
box = pn.WidgetBox('# Select Your Team Members', multi_choice, buttons, width=600)

@pn.depends(multi_choice.param.value)
def get_description(value):
    if value:
        descriptions = [f"**{v}**: {dt.design_thinking_team[v]['description']}" for v in value]
        return "\n\n".join(descriptions)
    return ''

description = pn.pane.Markdown(get_description, width=600, styles={'font-size': '12px'})
# Create a column for the team setup
team_setup = pn.Column(
    pn.WidgetBox('# Select Your Team Members', multi_choice, buttons, sizing_mode='stretch_width'),
    pn.WidgetBox('# Team Members', description, height=500, sizing_mode='stretch_width'),
)

summary_row = pn.Row(
    pn.WidgetBox(output_area, sizing_mode='stretch_width'),
)
summarize_button = pn.widgets.Button(name='Summarize Chat', button_type='primary')
summarize_button.on_click(summarize_chat)
layout = pn.Column(
    pn.Row(
        pn.WidgetBox(team_setup, width=800, sizing_mode='stretch_width'),
        pn.WidgetBox(chat_interface_placeholder, summarize_button, sizing_mode='stretch_width'),
    ),
    summary_row,
)

template = pn.template.FastGridTemplate(
    title="Design Thinking Simulation",
    main_layout='card',
    prevent_collision=True,
)

template.main[0:12, 0:12] = layout

template.servable()