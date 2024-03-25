import asyncio
import json

import sys
import time

from typing import Union

from js import console, document

from paradag import DAG

from chat import add_history, prompt_base, ChatGPT

from folio import (
    add_instance,
    get_contributor_types,
    get_contributor_name_types,
    get_identifier_types,
    get_instance_types,
    load_instance,
)

from sinopia import add as add_sinopia, load as load_sinopia


class WorkFlowExecutor(object):
    def __init__(self):
        self.__level = {}

    def param(self, vertex):
        return vertex

    def execute(self, param):
        if callable(param):
            args = self.__level.get(param)
            is_async = asyncio.iscoroutinefunction(param)
            console.log(f"In execute {param} is async {is_async}")
            if args:
                if is_async:
                    console.log(f"Before async call with {args}")
                    return asyncio.ensure_future(param(args))
                return param(args)
            else:
                if is_async:
                    return asyncio.ensure_future(param())
                return param()
        else:
            console.info(f"{param} is not callable")

    def deliver(self, vertex, result):
        console.log(
            f"In deliver {vertex} {asyncio.iscoroutinefunction(vertex)} {result}"
        )
        if asyncio.iscoroutinefunction(vertex):
            self.__level[vertex] = asyncio.ensure_future(result)
        else:
            self.__level[vertex] = result


def task(*args):
    """
    Task Decorator mimics Airflow task decorator for use in pyscript
    """
    func = args[0]

    def wrapper(*args, **kwargs):
        func(*args[1:], **kwargs)

    return wrapper


add_instance_sig = {
    "name": "add_instance",
    "description": "Adds an FOLIO Instance JSON record to FOLIO",
    "parameters": {
        "type": "object",
        "properties": {
            "record": {"type": "string", "description": "JSON FOLIO Instance"}
        },
    },
}

load_instance_sig = {
    "name": "load_instance",
    "description": "Loads an Instance to FOLIO iframe",
    "parameters": {
        "type": "object",
        "properties": {
            "instance_url": {"type": "string", "description": "URL To a FOLIO Instance"}
        },
    },
}

load_sinopia_sig = {
    "name": "load_sinopia",
    "description": "Loads a Sinopia URL and returns the RDF as JSON-LD",
    "parameters": {
        "type": "object",
        "properties": {
            "resource_url": {
                "type": "string",
                "description": "URL to a Sinopia Resource",
            }
        },
    },
}


class WorkFlow(object):
    dag: DAG = DAG()
    name: str = ""
    system: str = ""
    examples: list = []
    max_turns: int = 5


class FOLIOWorkFlow(WorkFlow):
    def __init__(self, chat_instance: Union[ChatGPT, None] = None):
        super().__init__()
        self.contributor_types = None
        self.contributor_name_types = None
        self.identifier_types = None
        self.instance_types = None
        self.record = None
        self.chat = chat_instance
        self.initial_prompt: str = ""

    async def get_types(self):
        if self.contributor_types is None:
            self.contributor_types = await get_contributor_types()

        if self.contributor_name_types is None:
            self.contributor_name_types = await get_contributor_name_types()

        if self.identifier_types is None:
            self.identifier_types = await get_identifier_types()

        if self.instance_types is None:
            self.instance_types = await get_instance_types()

    def update_record(self):
        self.record["instanceTypeId"] = self.instance_types.get("unspecified")
        for identifier in self.record.get("identifiers", []):
            if "identifierTypeName" in identifier:
                ident_name = identifier.pop("identifierTypeName")
                if ident_name.upper().startswith("OCLC"):
                    ident_name = "OCLC"
                identifier["identifierTypeId"] = self.identifier_types.get(ident_name)

        for contributor in self.record.get("contributors", []):
            contributor["contributorTypeId"] = self.contributor_types.get(
                contributor.get("contributorTypeText", "Contributor")
            )
            contributor["contributorNameTypeId"] = self.contributor_name_types.get(
                "Personal name"
            )

    async def run(self):
        await self.chat.set_system(self.system())
        if self.instance_types is None:
            await self.get_types()

    def system(self):
        system_prompt = self.system_prompt

        if len(self.examples) > 0:
            system_prompt = f"""{system_prompt}\nExamples:\n"""
            system_prompt += "\n".join(self.examples)
        self.system_prompt = system_prompt
