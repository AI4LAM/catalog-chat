import asyncio
import datetime
import io
import json
import uuid

import pymarc

from typing import Optional
from pydantic import BaseModel
from pyodide.http import pyfetch

from js import console, document, JSON, Headers, localStorage, alert

from chat import add_history

class Okapi(BaseModel):
    folio: str = ""
    url: str = ""
    tenant: str = ""
    token: str = ""

    def headers(self):
        return {
            "Content-type": "application/json",
            "x-okapi-token": self.token,
            "x-okapi-tenant": self.tenant,
        }


def error_card(errors, okapi):
    prompt_history = document.getElementById("chat-history")
    created_at = datetime.datetime.utcnow()
    card_html = f"""<div id="{uuid.uuid4()}" class="card mb-3">
      <div class="card-header text-bg-danger">
        FOLIO Errors Response  at {created_at.isoformat()} 
      </div>
      <div class="card-body">"""
    for error in errors:
        card_html += f"\n<pre>{JSON.stringify(error, None, 4)}</pre>"
    card_html += """</div>
      <div class="card-footer">FOLIO server {okapi.folio} Okapi API {okapi.urll}</div>
    </div>"""
    if prompt_history.hasChildNodes():
        prompt_history.insertBefore(row_div, prompt_history.firstChild)
    else:
        prompt_history.appendChild(row_div)
    

   

def _get_okapi():
    existing_okapi = localStorage.getItem("okapi")
    if existing_okapi is None:
        alert("Missing Okapi")
        return None

    return Okapi.parse_obj(json.loads(existing_okapi))


def services():
    modal_body = document.getElementById("folioModalBody")
    modal_body.innerHTML = ""
    modal_label = document.getElementById("folioModalLabel")
    modal_label.innerHTML = "FOLIO Status"
    # folio_services_ol = document.createElement("ol")
    # auto_vendor_marc_li = document.createElement("li")
    # auto_vendor_marc_li.innerHTML = "Load Vendor MARC Records"
    # folio_services_ol.appendChild(auto_vendor_marc_li)
    h4 = document.createElement("h4")
    h4.innerHTML = "Logged into FOLIO"
    modal_body.appendChild(h4)
    div_logout = document.createElement("div")
    div_logout.innerHTML = """<button class="btn btn-primary" py-script="okapi=logout_folio()" data-bs-dismiss="modal">Log out</button>"""
    modal_body.appendChild(div_logout)


# Goal 1: Automate loading of vendor MARC records
# Goal 2: Generate Order records from brief MARC records
# Goal 3: Create Course reserves from a csv containing a faculty id, course name, course code, start date, end date, item barcode
# Goal 4: Assist staff by generating a quick add instance, holdings, and item from barcode not in FOLIO
# Goal 5: Given a title, find all items with it's circulation status, and reserve the nearest available item


async def login(okapi: Okapi):
    okapi_url = document.getElementById("okapiURI")
    tenant = document.getElementById("folioTenant")

    folio_url = document.getElementById("folioURI")
    user = document.getElementById("folioUser")
    password = document.getElementById("folioPassword")

    okapi.url = okapi_url.value
    okapi.tenant = tenant.value
    okapi.folio = folio_url.value

    headers = {"Content-type": "application/json", "x-okapi-tenant": okapi.tenant}

    payload = {"username": user.value, "password": password.value}

    kwargs = {
        "method": "POST",
        "headers": headers,
        "mode": "cors",
        "body": json.dumps(payload),
    }

    login_response = await pyfetch(f"{okapi.url}/authn/login", **kwargs)

    login_json = await login_response.json()

    okapi.token = login_json["okapiToken"]

    if login_response.ok:
        folio_button = document.getElementById("folioButton")
        folio_button.classList.remove("btn-outline-danger")
        folio_button.classList.add("btn-outline-success")
        default_folio = document.getElementById("folio-default")
        if not "d-none" in default_folio.classList:
            default_folio.classList.add("d-none")
        localStorage.setItem("okapi", okapi.json())
        services()
    else:
        console.log(f"Failed to log into Okapi {login_response}")


async def load_marc_record(marc_file):
    if marc_file.element.files.length > 0:
        marc_file_item = marc_file.element.files.item(0)
        marc_binary = await marc_file_item.text()
        marc_reader = pymarc.MARCReader(
            io.BytesIO(bytes(marc_binary, encoding="utf-8"))
        )
        marc_record = next(marc_reader)
        return str(marc_record)



async def get_instance(okapi, uuid):
    kwargs = {"headers": okapi.headers()}

    instance_response = await pyfetch(
        f"{okapi.url}/instance-storage/instances/{uuid}", **kwargs
    )

    if instance_response.ok:
        instance = await instance_response.json()
        return instance
    else:
        print(f"ERROR retrieving {uuid} {instance_response}")


async def add_instance(record):
    okapi = _get_okapi()
    kwargs = {
        "method": "POST",
        "headers": okapi.headers(),
        "mode": "cors",
        "body": record,
    }
    #console.log(f"Add Instance kwargs {kwargs}")
    instance_response = await pyfetch(
        f"{okapi.url}/instance-storage/instances", **kwargs
    )
    if instance_response.ok:
        instance = await instance_response.json()
        console.log(f"Added record with uuid of {instance['id']}")
        return f"""{okapi.folio}/inventory/view/{instance["id"]}"""
    else:
        console.log(f"Error adding {instance_response}")
        error_card(instance_response, okapi)
        return instance_response


async def get_types(endpoint, selected_types, type_key, name_key="name"):
    okapi = _get_okapi()
    kwargs = {"headers": okapi.headers()}
    output = {}
    type_response = await pyfetch(f"{okapi.url}{endpoint}", **kwargs)
    if type_response.ok:
        types = await type_response.json()
        for row in types.get(type_key, []):
            if row[name_key] in selected_types:
                output[row[name_key]] = row["id"]
    return output


async def get_contributor_types() -> dict:
    selected_types = ["Actor", "Author", "Contributor", "Editor", "Narrator", "Publisher"]
    output = await get_types(
        "/contributor-types?limit=500", selected_types, "contributorTypes"
    )
    return output


async def get_contributor_name_types() -> dict:
    selected_types = ["Personal name", "Corporate name"]
    output = await get_types(
        "/contributor-name-types", selected_types, "contributorNameTypes"
    )
    return output


async def get_identifier_types() -> dict:
    selected_types = ["DOI", "ISBN", "LCCN", "ISSN", "OCLC", "Local identifier"]
    output = await get_types(
        "/identifier-types?limit=500", selected_types, "identifierTypes"
    )
    return output


async def get_instance_types() -> dict:
    selected_types = [
        "text",
        "still image",
        "computer program",
        "computer dataset",
        "two-dimensional moving image",
        "notated music",
        "unspecified",
    ]
    output = await get_types(
        "/instance-types?limit=500", selected_types, "instanceTypes"
    )
    return output

def load_instance(url):
    default_folio = document.getElementById("folio-default")
    if not "d-none" in default_folio.classList:
        default_folio.classList.add("d-none")
    folio_iframe = document.getElementById("folio-system-frame")
    folio_iframe.src = url 

def logout_folio():
    modal_body = document.getElementById("folioModalBody")
    modal_label = document.getElementById("folioModalLabel")
    modal_label.innerHTML = "Login to FOLIO"
    modal_body ="""<form>
    <div class="mb-3">
      <label for="folioURI" class="form-label">FOLIO URI</label>
        <input class="form-control" id="folioURI">
    </div>
    <div class="mb-3">
      <label for="okapiURI" class="form-label">Okapi URI</label>
      <input class="form-control" id="okapiURI">
    </div>
    <div class="mb-3">
      <label for="folioTenant" class="form-label">Tenant</label>
      <input class="form-control" id="folioTenant">
    </div>
    <div class="mb-3">
      <label for="folioUser" class="form-label">Username</label>
      <input class="form-control" id="folioUser">
    </div>
    <div class="mb-3">
      <label for="folioPassword" class="form-label">Password</label>
      <input type="password" class="form-control" id="folioPassword">
    </div>
    <button type="button"
      data-bs-dismiss="modal"
      class="btn btn-primary"
      py-click="asyncio.ensure_future(login_okapi())">Login</button>
   </form>"""
    return None
  
