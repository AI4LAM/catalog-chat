from paradag import SequentialProcessor, dag_run

from workflows import FOLIOWorkFlow, add_instance_sig

from chat import ChatGPT

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
                self.__update_record__(record)
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
