"""
ChatGPT React-Action

Inspired by this blog post https://til.simonwillison.net/llms/python-react-pattern
"""
import asyncio
import datetime
import json
import re
import uuid

from typing import Optional
from js import console, document, localStorage

from pyodide.http import pyfetch


def _add_prompt_to_history(text):
    ident = uuid.uuid4()
    time_stamp = datetime.datetime.utcnow()
    card = document.createElement("div")
    card.setAttribute("id", ident)
    for css_class in ["card", "border-dark", "mb-3"]:
        card.classList.add(css_class)
    card_header = document.createElement("div")
    card_header.classList.add("card-header")
    card_header.innerHTML = f"Prompt at {time_stamp}"
    card.appendChild(card_header)
    card_body = document.createElement("div")
    card_body.classList.add("card-body")
    card_body.innerHTML = text
    card.appendChild(card_body)
    card_footer = document.createElement("div")
    card_footer.classList.add("card-footer")
    footer_text = document.createElement("small")
    footer_text.innerHTML = f"ID {ident}"
    card_footer.appendChild(footer_text)
    card.appendChild(card_footer)
    row_div = document.createElement("div")
    row_div.classList.add("row")
    div_wrapper = document.createElement("div")
    div_wrapper.classList.add("col-md-10")
    div_wrapper.appendChild(card)
    row_div.appendChild(div_wrapper)
    prompt_history = document.getElementById("chat-history")
    if prompt_history.hasChildNodes():
        prompt_history.insertBefore(row_div, prompt_history.firstChild)
    else:
        prompt_history.appendChild(row_div)
    return False


def _add_response_to_history(response):
    created_at = datetime.datetime.fromtimestamp(response["created"])
    html_string = f"""<div id="{response['id']}" class="card border-danger mb-3">
      <div class="card-header">
        Response at {created_at.isoformat()} 
      </div>
      <div class="card-body">"""
    for choice in response["choices"]:
        message = choice.get("message")
        html_string += f"<p>Role {message['role']}</p>"
        if message.get("function_call"):
            html_string += (
                f"<pre>{json.dumps(message['function_call'], indent=2)}</pre>"
            )
        else:
            html_string += f"<p>{message['content']}</p>"

    html_string += f"""</div>
      <div class="card-footer">
        <small>ID {response['id']} Tokens: prompt: {response['usage']['prompt_tokens']} completion: {response['usage']['completion_tokens']}</small>
      </div>
    </div>
    """
    row_div = document.createElement("div")
    row_div.classList.add("row")
    div_wrapper = document.createElement("div")
    for class_ in ["col-md-10", "offset-md-1"]:
        div_wrapper.classList.add(class_)
    div_wrapper.innerHTML = html_string
    row_div.appendChild(div_wrapper)
    prompt_history = document.getElementById("chat-history")
    if prompt_history.hasChildNodes():
        prompt_history.insertBefore(row_div, prompt_history.firstChild)
    else:
        prompt_history.appendChild(row_div)
    return False


def add_history(value, type_of):
    match type_of:
        case "prompt":
            result = _add_prompt_to_history(value)
        case "response":
            result = _add_response_to_history(value)

    return result


async def login():
    bearer_key_element = document.getElementById("chatApiKey")
    chat_gpt = ChatGPT(key=bearer_key_element.value)
    chatgpt_button = document.getElementById("chatGPTButton")
    chatgpt_button.classList.remove("btn-outline-danger")
    chatgpt_button.classList.add("btn-outline-success")
    chat_prompts_div = document.getElementById("chat-gpt-prompts")
    chat_prompts_div.classList.remove("d-none")
    update_chat_modal(chat_gpt)
    return chat_gpt


class ChatGPT(object):
    def __init__(
        self,
        key,
        endpoint_url="https://api.openai.com/v1/chat/completions",
        model="gpt-3.5-turbo",
        temperature=0.9,
        max_tokens=1050,
    ):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }
        self.openai_url = endpoint_url
        self.system = None
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.messages = []
        self.functions = None
        localStorage.setItem("chat_gpt_token", key)

    async def __call__(self, message):
        message = {"role": "user", "content": message}
        self.messages.append(message)
        result = await self.execute()
        #console.log(f"Adding {result} to messages")
        self.messages.append(result["choices"][0]["message"])
        return result

    async def set_system(self, system):
        self.system = system
        system_message = {"role": "system", "content": self.system}
        # Remove any existing system messages
        for i, message in enumerate(self.messages):
            if message["role"] == "system":
                self.messages.pop(i)
        self.messages.insert(0, system_message)

    async def execute(self):
        body = {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.functions:
            body["functions"] = self.functions
        kwargs = {
            "method": "POST",
            "headers": self.headers,
            "body": json.dumps(body),
        }
        completion = await pyfetch(self.openai_url, **kwargs)
        if completion.ok:
            result = await completion.json()
        else:
            result = {"error": completion.status, "message": completion.status_text}
        return result


def update_chat_modal(chat_gpt_instance):
    modal_body = document.getElementById("chatApiKeyModalBody")
    modal_body.innerHTML = ""
    instance_dl = document.createElement("dl")
    endpoint_dt = document.createElement("dt")
    endpoint_dt.innerHTML = "OpenAI Endpoint"
    instance_dl.appendChild(endpoint_dt)
    endpoint_dd = document.createElement("dd")
    endpoint_dd.innerHTML = chat_gpt_instance.openai_url
    instance_dl.appendChild(endpoint_dd)
    model_dt = document.createElement("dt")
    model_dt.innerHTML = "Model"
    instance_dl.appendChild(model_dt)
    model_dd = document.createElement("dd")
    model_dd.innerHTML = chat_gpt_instance.model
    instance_dl.appendChild(model_dd)
    temp_dt = document.createElement("dt")
    temp_dt.innerHTML = "Temperature"
    instance_dl.appendChild(temp_dt)
    temp_dd = document.createElement("dd")
    temp_dd.innerHTML = chat_gpt_instance.temperature
    instance_dl.appendChild(temp_dd)
    modal_body.appendChild(instance_dl)
    max_tokens_dt = document.createElement("dt")
    max_tokens_dt.innerHTML = "Max Tokens"
    instance_dl.appendChild(max_tokens_dt)
    max_tokens_dd = document.createElement("dd")
    max_tokens_dd.innerHTML = chat_gpt_instance.max_tokens
    instance_dl.appendChild(max_tokens_dd)


action_re = re.compile(r"^Action: (\w+): (.*)$")


prompt_base = """
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

"""

actions = """
retrieve_instance:
e.g. folio_instance: 529056f1-d1a2-5dd6-b074-311847ab362a


assign_lchs:
e.g. lcsh: 
"""

marc2folio_prompt = """
In the role as an expert cataloger, you will be given a MARC21 record and then convert
to a FOLIO Instance JSON record

MARC21 record:
"""

marc2folio_prompt2 = """
In the role as an expert cataloger, you will be given a MARC21 record and then convert
to a FOLIO Instance JSON record

Example session:

Question: Convert this MARC21 record to a FOLIO Instance
=LDR  00704cam a22002051  4500
=001  a3044621
=003  SIRSI
=008  850513q19401949enkab\\\\\\\\\000\0\eng\d
=035  \\$a(OCoLC-M)12030243
=035  \\$a(OCoLC-I)275077884
=040  \\$aCSJ$cCSJ$dCSt-H$dOrLoB
=049  \\$aHINA
=100  1\$aKearsey, A.$q(Alexander Horace Cyril),$d1877-
=245  14$aThe operations in Egypt and Palestine: August, 1914, to June, 1917;$billustrating the field service regulations /$cby A. Kearsey.
=250  \\$a3d ed.
=260  \\$aAldershot,$bGale & Polden$c[194-?]
=300  \\$axvii, 154 p.$bmaps, fold. diagr.$c22 cm.
=596  \\$a25
=650  \0$aWorld War, 1914-1918$xCampaigns$zTurkey and the Near East.
=918  \\$a3044621

Observation:
{'id': 'e52f84b1-027a-5905-a00d-0bdeff370caa',
 '_version': 1,
 'hrid': 'a3044621',
 'source': 'MARC',
 'title': 'The operations in Egypt and Palestine: August, 1914, to June, 1917; illustrating the field service regulations / by A. Kearsey.',
 'indexTitle': 'Operations in egypt and palestine: august, 1914, to june, 1917; illustrating the field service regulations',
 'alternativeTitles': [],
 'editions': ['3d ed'],
 'series': [],
 'identifiers': [{'value': '(OCoLC-M)12030243',
   'identifierTypeId': '7e591197-f335-4afb-bc6d-a6d76ca3bace'},
  {'value': '(OCoLC-I)275077884',
   'identifierTypeId': '7e591197-f335-4afb-bc6d-a6d76ca3bace'}],
 'contributors': [{'name': 'Kearsey, A. (Alexander Horace Cyril), 1877-',
   'contributorTypeId': '9f0a2cf0-7a9b-45a2-a403-f68d2850d07c',
   'contributorTypeText': 'Contributor',
   'contributorNameTypeId': '2b94c631-fca9-4892-a730-03ee529ffe2a',
   'primary': True}],
 'subjects': ['World War, 1914-1918 Campaigns Turkey and the Near East'],
 'classifications': [],
 'publication': [{'publisher': 'Gale & Polden',
   'place': 'Aldershot',
   'dateOfPublication': '[194-?]'}],
 'publicationFrequency': [],
 'publicationRange': [],
 'electronicAccess': [],
 'instanceTypeId': '30fffe0e-e985-4144-b2e2-1e8179bdb41f',
 'instanceFormatIds': [],
 'instanceFormats': [],
 'physicalDescriptions': ['xvii, 154 p. maps, fold. diagr. 22 cm.'],
 'languages': ['eng'],
 'notes': [],
 'administrativeNotes': ['Identifier(s) from previous system: a3044621'],
 'modeOfIssuanceId': '9d18a02f-5897-4c31-9106-c9abb5c7ae8b',
 'catalogedDate': '1995-08-21',
 'previouslyHeld': False,
 'staffSuppress': False,
 'discoverySuppress': False,
 'statisticalCodeIds': [],
 'statusUpdatedDate': '2023-02-11T16:45:56.888+0000',
 'holdingsRecords2': [],
 'natureOfContentTermIds': []}
"""

lcsh_prompt = f"""
Create Library of Congress Subject Headings (LCSH) for the following subjects:

"""

prompt_action = """
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

marc2folio:
e.g. marc2folio:   

Example session:

Question: Generate a FOLIO Instance record from this MARC record
=LDR \n=001 

"""
