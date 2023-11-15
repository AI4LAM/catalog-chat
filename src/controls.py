import asyncio
import datetime
import io
import json

import pymarc

from js import Blob, console, document, alert, JSON, URL

from chat import add_history
from workflows import AssignLCSH, NewResource, MARC21toFOLIO, SinopiaToFOLIO


def clear_chat_prompt(chat_gpt_instance):
    main_chat_textarea = document.getElementById("mainChatPrompt")
    system_card = document.getElementById("system-card")
    system_card.classList.add("d-none")
    workflow_title = document.getElementById("workflow-title")
    workflow_title.innerHTML = ""
    main_chat_textarea.value = ""
    mrc_upload_btn = document.getElementById("marc-upload-btn")
    mrc_upload_btn.classList.add("d-none")
    prompt_history = document.getElementById("chat-history")
    prompt_history.innerHTML = ""
    if chat_gpt_instance != None:
        chat_gpt_instance.messages = []
    loading_spinner = document.getElementById("chat-loading")
    loading_spinner.classList.add("d-none")
    _clear_vector_db()
    return None


def download(chat_instance, workflow):
    export_obj = {
        "chat_instance": {
           "endpoint": chat_instance.openai_url,
           "model": chat_instance.model,
           "temperature": chat_instance.temperature,
           "messages": chat_instance.messages,
           "functions": chat_instance.functions
        },
        "workflow": {
           "name": workflow.name
        }
    }
    anchor = document.createElement("a")
    blob = Blob.new([json.dumps(export_obj, indent=2)], { "type": 'application/json' })
    anchor.href = URL.createObjectURL(blob)
    current = datetime.datetime.utcnow()
    anchor.download =  f"export-{current.isoformat()}.json"
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    # download_btn.removeChild(anchor)

def load_chat_session(page_name):
    iframe_chat = document.getElementById('chat-gpt-session')
    iframe_chat.src = f"history/{page_name}.html"


def load_folio_default():
    folio_modal = document.getElementById("folioModal")
    folio_url = document.getElementById("folioURI")
    okapi_url = document.getElementById("okapiURI")
    tenant = document.getElementById("folioTenant")
    user = document.getElementById("folioUser")
    password = document.getElementById("folioPassword")
    folio_default = document.getElementById("folio-default")

    folio_url.value = "https://folio-nolana.dev.folio.org"
    okapi_url.value = "https://folio-nolana-okapi.dev.folio.org"
    tenant.value = "diku"
    user.value = "diku_admin"
    password.value = "admin"

    folio_default.classList.add("d-none")


async def init_workflow(workflow_slug):
    workflow_title_h2 = document.getElementById("workflow-title")
    chat_prompt_textarea = document.getElementById("mainChatPrompt")
    folio_vector_chkbx = document.getElementById("folio-vector-db")
    sinopia_vector_chkbox = document.getElementById("sinopia-vector-db")
    lcsh_vector_chkbox = document.getElementById("lcsh-vector-db")
    examples_div = document.getElementById("prompt-examples")
    system_card = document.getElementById("system-card")
    loading_spinner = document.getElementById("chat-loading")
    loading_spinner.classList.add("d-none")

    system_div = document.getElementById("system-message")

    system_div.innerHTML = ""
    examples_div.innerHTML = ""
    system_card.classList.remove("d-none")
    # chat_prompt_textarea.value = prompt_base
    _clear_vector_db()
    mrc_upload_btn = document.getElementById("marc-upload-btn")
    mrc_upload_btn.classList.add("d-none")


    match workflow_slug:
        case "add-lcsh":
            lcsh_vector_chkbox.checked = True
            workflow = AssignLCSH(zero_shot=True)
            msg = workflow.name

        case "bf-to-marc":
            msg = "Generate a MARC Record from Sinopia BIBFRAME RDF"
            lcsh_vector_chkbox.checked = True
            # sinopia_vector_chkbox.checked = True
            workflow = "bf_to_marc"

        case "marc-to-folio":
            mrc_upload_btn.classList.remove("d-none")
            workflow = MARC21toFOLIO(zero_shot=True)
            msg = workflow.name

        case "new-resource":
            # folio_vector_chkbx.checked = True
            lcsh_vector_chkbox.checked = True
            # sinopia_vector_chkbox.checked = True
            workflow = NewResource(zero_shot=True)
            msg = workflow.name

        case "transform-bf-folio":
            # folio_vector_chkbx.checked = True
            # sinopia_vector_chkbox.checked = True
            workflow = SinopiaToFOLIO(zero_shot=True)
            msg = workflow.name

        case _:
            msg = "None selected"
            workflow = None

    # console.log(f"Workflow {workflow_slug} {workflow}")
    workflow_title_h2.innerHTML = f"<strong>Workflow:</strong> {msg}"
    if hasattr(workflow, "system"):
        system_result = await workflow.system()
        system_div.innerHTML = f"""<textarea id="system-text" class="form-control" rows=5>{system_result}</textarea>"""
    if hasattr(workflow, "examples"):
        for i, example in enumerate(workflow.examples):
            example_div = document.createElement("div")
            example_div.classList.add("form-check")
            example_div.innerHTML = f"""<input class="form-check-input" type="checkbox" value="" id="workflow-example-chkbox-{i}" checked></input>
                             
                               <textarea id="workflow-example-{i}" class="form-control" rows=3>{example}</textarea>"""
            examples_div.append(example_div)
    return workflow


async def load_marc_record(marc_file):
    if marc_file.element.files.length > 0:
        marc_file_item = marc_file.element.files.item(0)
        marc_binary = await marc_file_item.text()
        marc_reader = pymarc.MARCReader(
            io.BytesIO(bytes(marc_binary, encoding="utf-8"))
        )
        marc_record = next(marc_reader)
        return str(marc_record)


def new_example():
    examples_div = document.getElementById("prompt-examples")
    count = examples_div.children.length + 1
    new_example_div = document.createElement("div")
    new_example_div.classList.add("form-check")
    new_example_div.innerHTML = f"""<input class="form-check-input" type="checkbox" value="" id="workflow-example-chkbox-{count}" checked></input>
                             
                               <textarea id="workflow-example-{count}" class="form-control" rows=3></textarea>"""
    examples_div.appendChild(new_example_div)



async def run_prompt(workflow, chat_gpt_instance):
    main_chat_textarea = document.getElementById("mainChatPrompt")
    loading_spinner = document.getElementById("chat-loading")
    loading_spinner.classList.remove("d-none")

    #console.log(f"Workflow is {workflow}")
    if workflow is None:
        alert("Workflow is None")
        
        return
    prompt_examples_div = document.getElementById("prompt-examples")
    examples = []
    for check_box in prompt_examples_div.getElementsByTagName("input"):
        if check_box.checked:
            examples.append(check_box.nextElementSibling.value)
    if len(examples) > 0:
        workflow.zero_shot = False
        workflow.examples = examples
  
    system = await workflow.system()
    await chat_gpt_instance.set_system(system)
    current = main_chat_textarea.value
    if len(current) > 0:
        run_result = await workflow.run(chat_gpt_instance, current)
        loading_spinner.classList.add("d-none")

        # console.log(f"Run result {run_result}")
        main_chat_textarea.value = ""


def _clear_vector_db():
    folio_vector_chkbx = document.getElementById("folio-vector-db")
    sinopia_vector_chkbox = document.getElementById("sinopia-vector-db")
    lcsh_vector_chkbox = document.getElementById("lcsh-vector-db")
    for checkbox in [folio_vector_chkbx, sinopia_vector_chkbox, lcsh_vector_chkbox]:
        checkbox.checked = False
