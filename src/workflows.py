import asyncio
import json
import sys
import time

from js import console, document

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
          "instance_url": {"type": "string", "description": "URL To a FOLIO Instance" }
      }
    }
}

class WorkFlow(object):
    name: str = ""
    system: str = ""
    examples: list = []
    max_turns: int = 5


class FOLIOWorkFlow(WorkFlow):
    def __init__(self):
        self.contributor_types = None
        self.contributor_name_types = None
        self.identifier_types = None
        self.instance_types = None

    async def get_types(self):
        if self.contributor_types is None:
            self.contributor_types = await get_contributor_types()

        if self.contributor_name_types is None:
            self.contributor_name_types = await get_contributor_name_types()

        if self.identifier_types is None:
            self.identifier_types = await get_identifier_types()

        if self.instance_types is None:
            self.instance_types = await get_instance_types()


class AssignLCSH(WorkFlow):
    name = "Assign Library of Congress Subject Heading to record"
    system_prompt = "As an expert cataloger, you will use the context to assign Library of Congress Subject Headings to terms"

    examples = []

    def __init__(self, zero_shot=False):
        self.system = system
        self.react = react

    async def system(self):
        system_prompt = AssignLCSH.system_prompt

        if self.zero_shot is False:
            system_prompt = f"""{system_prompt}\nExamples:\n"""
            system_prompt += "\n".join(MARC21toFOLIO.examples)


        return system_prompt

    async def run(self, chat_instance: ChatGPT, initial_prompt: str):
        add_history(initial_prompt, "prompt")
        if not self.react:
            chat_result = await chat_instance(initial_prompt)
            add_history(chat_result, "response")
            return
        count = 0
        while count < AssignLCSH.max_turns:
            count += 1


class MARC21toFOLIO(FOLIOWorkFlow):
    name = "MARC21 to FOLIO Inventory Record"
    system_prompt = """In the role as an expert cataloger, you will be given a MARC21 record and then convert
to a FOLIO Instance JSON record
"""

    examples = [
        """Q: =LDR  01071cam a2200349 i 4500
=001  a757722
=003  SIRSI
=005  19910715000000.0
=008  791017s1977\\\\onca\\\\\b\\\\001\0\eng\\
=015  \\$aC77-001233-7
=020  \\$a0070824525
=020  \\$a9780070824522
=050  0\$aHA29$b.E72
=082  \\$a519.5
=100  1\$aErickson, Bonnie H.$0(SIRSI)415236
=245  10$aUnderstanding data /$cBonnie H. Erickson, T. A. Nosanchuk.
=260  \\$aToronto ;$aNew York :$bMcGraw-Hill Ryerson,$cc1977.
=300  \\$axi, 388 p. :$bill. ;$c23 cm.
=490  1\$aMcGraw-Hill Ryerson series in Canadian sociology
=500  \\$aIncludes index.
=504  \\$aBibliography: p. 383-384.
=596  \\$a1
=650  \0$aStatistics.$0(SIRSI)1064412
=700  1\$aNosanchuk, T. A.,$d1935-$0(SIRSI)54329
=830  \0$aMcGraw-Hill Ryerson series in Canadian sociology.$0(SIRSI)1108560

           A: {
"source": "MARC",
"title": "Understanding data / Bonnie H. Erickson, T. A. Nosanchuk.",
"indexTitle": "Understanding data", 
"series": ["McGraw-Hill Ryerson series in Canadian sociology"], 
"identifiers": [
  {"identifierTypeName": "ISBN", "value": "0070824525"}, 
  {"identifierTypeName": "ISBN", "value": "9780070824522"}], 
"contributors": [
 {"name": "Erickson, Bonnie H", "contributorTypeText": "Contributor", "primary": true}, 
 {"name": "Nosanchuk, T. A., 1935-", "contributorTypeText": "Contributor", "primary": false}], 
"subjects": ["Statistics"], 
"classifications": [
  {"classificationNumber": "HA29 .E72", "classificationTypeName": "LC"}, 
  {"classificationNumber": "519.5", "classificationTypeName": "Dewey"}], 
"publication": [{"publisher": "McGraw-Hill Ryerson", "place": "Toronto New York", "dateOfPublication": "c1977"}], 
"physicalDescriptions": ["xi, 388 p. : ill. ; 23 cm."], 
"languages": ["eng"], 
"notes": [
  {"note": "Includes index", "staffOnly": false}, 
  {"note": "Bibliography: p. 383-384", "staffOnly": false}] 
}
 """
    ]

    functions = [
        add_instance_sig,
    ]


    def __init__(self, zero_shot=False):
        super().__init__()
        self.zero_shot = zero_shot

    def __update_record__(self, record):
        record["instanceTypeId"] = self.instance_types.get("text")
        for identifier in record.get("identifiers", []):
            if "identifierTypeName" in identifier:
                ident_name = identifier.pop("identifierTypeName")
                if ident_name.startswith("OCLC"):
                    ident_name = "OCLC"
                identifier["identifierTypeId"] = self.identifier_types.get(ident_name)



    async def system(self):
        system_prompt = MARC21toFOLIO.system_prompt

        if self.instance_types is None:
            await self.get_types()

        
        if self.zero_shot is False:
            system_prompt = f"""{system_prompt}\nExamples\n"""
            system_prompt += "\n".join(MARC21toFOLIO.examples)
       

        return system_prompt


    async def run(self, chat_instance, initial_prompt: str):
        add_history(f"<pre>{initial_prompt}</pre>", "prompt")
        chat_instance.functions = MARC21toFOLIO.functions
        chat_result = await chat_instance(initial_prompt)
        function_call = chat_result["choices"][0]["message"].get("function_call")
        if not function_call:
            return
        add_history(chat_result, "response")
        function_name = function_call.get("name")
        args = json.loads(function_call.get("arguments"))
        console.log(f"Function name {function_name} args: {args}")
        if function_name.startswith("add_instance"):
            record = json.loads(args.get("record"))
            console.log("Before updating record")
            self.__update_record__(record)
            instance_url = await add_instance(json.dumps(record))
            msg = f"Load FOLIO Instance {instance_url}"
            add_history(msg, "prompt")
        load_chat_result = await chat_instance(msg)
        function_call = load_chat_result["choices"][0]["message"].get("function_call")
            
                    
        


class NewResource(FOLIOWorkFlow):
    name = "Create a New Resource"
    system_prompt = """You are an expert cataloger, return any records as FOLIO JSON"""
    examples = [
        """Q: Parable of the Sower by Octiva Butler, published in 1993 by Four Walls Eight Windows in New York

           A: {"title": "Parable of the Sower", "source": "ChatGPT", 
                 "contributors": [{"name": "Octiva Butler", "contributorTypeText": "Author"}], 
                "publication": [{"publisher": "Four Walls Eight Windows", "dateOfPublication": "1993", "place": "New York"}] }}
        """
    ]
    functions = [
        add_instance_sig,
    ]

    def __init__(self, zero_shot=False):
        super().__init__()
        self.zero_shot = zero_shot


    async def __handle_func__(self, function_call):
        function_name = function_call.get("name")
        args = json.loads(function_call.get("arguments"))
        output = None
        match function_name:
            case "add_instance":
                record = json.loads(args.get("record"))
                record["instanceTypeId"] = self.instance_types.get("unspecified")
                for contributor in record.get("contributors", []):
                    contributor["contributorTypeId"] = self.contributor_types.get(
                        contributor.get("contributorTypeText"),
                        "Contributor"
                    )
                    contributor[
                        "contributorNameTypeId"
                    ] = self.contributor_name_types.get("Personal name")
                    instance_url = await add_instance(json.dumps(record))
                    output = instance_url

            case "load_instance":
                instance_url = json.loads(args.get("instance_url"))
                load_instance(instance_url)
                output = f"Loaded {instance_url} into iframe" 
                
            case _:
                output = f"Unknown function {function_name}"
        return output


    async def system(self):
        system_prompt = NewResource.system_prompt
        if self.instance_types is None:
            await self.get_types()

        if self.zero_shot is False:
            system_prompt = f"""{system_prompt}\nExamples:\n"""
            system_prompt += "\n".join(NewResource.examples)

        return system_prompt

    async def run(self, chat_instance: ChatGPT, initial_prompt: str):
        add_history(initial_prompt, "prompt")
        chat_instance.functions = NewResource.functions
        chat_result = await chat_instance(initial_prompt)
        function_call = chat_result["choices"][0]["message"].get("function_call")
        if function_call:
            add_history(chat_result, "response")
            msg = await self.__handle_func__(function_call)
            if not msg.startswith("Unknown"):
                instance_url = msg
                msg = f"Load FOLIO Instance {instance_url}"
                add_history(msg, "prompt")
                load_instance(instance_url)
        return f"Finished {instance_url}"


class SinopiaToFOLIO(FOLIOWorkFlow):
    name = "Sinopia BIBFRAME to FOLIO Inventory Instance"
    system_prompt = """You are an expert cataloger, given a Sinopia URL you will retrieve the JSON Linked Data
and convert it to a FOLIO Instance JSON record"""

    examples = []

    functions = [
        add_instance
    ]

    def __init__(self,  zero_shot=False):
        super().__init__()
        self.zero_shot = zero_shot

    async def system(self):
        system_prompt = SinopiaToFOLIO.system_prompt

        if self.zero_shot is False:
            system_prompt = f"{system_prompt}\n\nExamples"
            system_prompt += "\n".join(self.examples)

        return system_prompt

    async def run(self, chat_instance: ChatGPT, initial_prompt: str):
        add_history(initial_prompt, "prompt")
        chat_result.functions = SinopiaToFOLIO.functions
        chat_result = await chat_instance(initial_prompt)
        add_history(chat_result, "response")

 
