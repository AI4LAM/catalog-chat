import json

from typing import Optional
from pydantic import BaseModel
from pyodide.http import pyfetch

from js import document


class Airflow(BaseModel):
    is_active: bool = False
    url: str = ""
    user: str = ""
    password: str = ""


async def login(airflow_instance) -> Airflow:
    url = document.getElementById("airflowURI")
    user = document.getElementById("airflowUser")
    password = document.getElementById("airflowPassword")

    airflow_instance.url = url.value
    airflow_instance.user = user.value
    airflow_instance.password = password.value

    headers = {"Content-Type": "application/json"}

    kwargs = {
        "method": "POST",
        "headers": headers,
        "mode": "no-cors",
        "body": json.dumps({"user": {user.value: password.value}}),
    }

    login_result = await pyfetch(f"{url.value}/api/v1/pools", **kwargs)

    if login_result.ok:
        airflow_btn = document.getElementById("airflowButton")
        airflow_btn.classList.remove("btn-outline-danger")
        airflow_btn.classList.add("btn-outline-success")
