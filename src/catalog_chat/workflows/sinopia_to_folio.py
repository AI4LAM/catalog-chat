from typing import Union

from js import console
from paradag import SequentialProcessor, dag_run

from chat import ChatGPT, add_history
from workflows import (
    FOLIOWorkFlow,
    WorkFlowExecutor,
    load_sinopia_sig,
    add_instance_sig,
)


class SinopiaToFOLIO(FOLIOWorkFlow):
    name = "Sinopia BIBFRAME to FOLIO Inventory Instance"
    system_prompt = """You are an expert cataloger, given a Sinopia URL you will retrieve the JSON Linked Data
and convert it to a FOLIO Instance JSON record"""

    examples = [
        """Q: @prefix bf: <http://id.loc.gov/ontologies/bibframe/> .
@prefix bflc: <http://id.loc.gov/ontologies/bflc/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sinopia: <http://sinopia.io/vocabulary/> .

<https://api.stage.sinopia.io/resource/bd072fe6-f189-4a39-9f0c-0dac4d1ef0bd> a bf:Work ;
    bf:title [ a bf:Title ;
    bf:mainTitle "Parable of the Sower"@en ] ;
    bf:contribution [ a bflc:PrimaryContribution ;
            bf:agent <http://id.loc.gov/authorities/names/n2020014067> ;
            bf:role <http://id.loc.gov/vocabulary/relators/aut> ] ;
    bf:note [ a bf:Note ;
            rdfs:label "Includes bibliographical references (pages [235]-301) and index"@en ] ;
    

<http://id.loc.gov/rwo/agents/n79056654> a bf:Agent,
        bf:Person ;
    rdfs:label "Butler, Octavia E."@en .

<http://id.loc.gov/vocabulary/relators/aut> a bf:Role ;
    rdfs:label "Author" .

    A:  {"title": "Parable of the Sower", "source": "Sinopia", 
         "contributors": [{"name": "Octiva Butler", "contributorTypeText": "Author", "primary": true}], 
         "notes": [{ value: "Includes bibliographical references (pages [235]-301) and index"}],
         'languages': ['eng']}

"""
    ]

    functions = [load_sinopia_sig, add_instance_sig]

    def __init__(self, chat_instance: ChatGPT):
        super().__init__(chat_instance)
        self.chat.functions = SinopiaToFOLIO.functions
        self.dag.add_vertex(
            self.initial_query, self.load_sinopia_resource, self.create_instance
        )
        self.dag.add_edge(self.initial_query, self.load_sinopia_resource)
        self.dag.add_edge(self.load_sinopia_resource, self.create_instance)

    async def create_instance(self, *args) -> Union[str, None]:
        function_call = await args[0]
        record = json.loads(args.get("record"))
        console.log(f"Create instance Function call {function_call}")
        instance_url = ""
        if function_call.startswith("adds_instance"):
            self.update_record(record)
            instance_url = await add_instance(json.dumps(record))
        else:
            console.log(f"Unknown function {function_call}")
        if not instance_url.startswith("Unknown") and instance_url.startswith("http"):
            return instance_url

    async def initial_query(self):
        self.system()
        await self.chat.set_system(self.system_prompt)
        chat_result = await self.chat(self.initial_prompt)
        add_history(chat_result, "response")
        return chat_result["choices"][0]["message"].get("function_call")

    async def load_sinopia_resource(self, *args):
        resource_url = await args[0]
        console.log(f"In load_sinopia_resource {resource_url}")
        sinopia_rdf = await load_sinopia(resource_url)
        prompt = "Add FOLIO Instance JSON record from"
        add_history(f"{prompt}<pre>{sinopia_rdf}</pre>", "prompt")
        return f"{prompt}\n{sinopia_rdf}"

    async def run(self, initial_prompt: str):
        await super().run()
        self.initial_prompt = initial_prompt
        add_history(initial_prompt, "prompt")
        console.log(f"Before dag_run, {self.dag}")
        dag_run(self.dag, processor=SequentialProcessor(), executor=WorkFlowExecutor())
