import json

from typing import Union

from js import console
from paradag import SequentialProcessor, dag_run

from chat import ChatGPT, add_history
from folio import add_instance, load_instance
from workflows import FOLIOWorkFlow, WorkFlowExecutor, add_instance_sig

from js import console


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

    def __init__(self, chat_instance: ChatGPT):
        super().__init__(chat_instance)
        self.chat.functions = NewResource.functions
        self.dag.add_vertex(
            self.initial_query, self.create_instance, self.load_into_folio
        )
        self.dag.add_edge(self.initial_query, self.create_instance)
        self.dag.add_edge(self.create_instance, self.load_into_folio)

    async def __handle_func__(self, function_call):
        function_name = function_call.get("name")
        args = json.loads(function_call.get("arguments"))
        output = None
        match function_name:
            case "add_instance":
                self.record = json.loads(args.get("record"))
                self.update_record()
                instance_url = await add_instance(json.dumps(self.record))
                output = instance_url

            case _:
                output = f"Unknown function {function_name}"
        return output

    async def initial_query(self):
        self.system()
        await self.chat.set_system(self.system_prompt)
        chat_result = await self.chat(self.initial_prompt)
        add_history(chat_result, "response")
        return chat_result["choices"][0]["message"].get("function_call")

    async def create_instance(self, *args) -> Union[str, None]:
        function_call = await args[0]
        msg = await self.__handle_func__(function_call)
        if not msg.startswith("Unknown") and msg.startswith("http"):
            return msg

    async def load_into_folio(self, *args):
        instance_url = await args[0]
        if instance_url is None:
            add_history(f"Failed to Load FOLIO Instance")
            return
        add_history(f"Load FOLIO Instance {instance_url}", "prompt")
        await load_instance(instance_url)

    async def run(self, initial_prompt: str):
        await super().run()
        add_history(initial_prompt, "prompt")
        self.initial_prompt = initial_prompt
        dag_run(self.dag, processor=SequentialProcessor(), executor=WorkFlowExecutor())
