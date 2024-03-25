from paradag import SequentialProcessor, dag_run

from chat import ChatGPT
from workflows import FOLIOWorkFlow, load_sinopia_sig, add_instance_sig


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

    functions = [
        load_sinopia_sig,
        add_instance_sig
    ]

    def __init__(self,  zero_shot=False):
        super().__init__()
        self.zero_shot = zero_shot



    async def __handle_func__(self, function_call) -> str:
        function_name = function_call.get("name")
        args = json.loads(function_call.get("arguments"))
        output = None
        match function_name:

            case "add_instance":
                record = json.loads(args.get("record"))
                self.__update_record__(record)
                console.log(f"SinopiaToFOLIO after update")
                instance_url = await add_instance(json.dumps(record))
                console.log(f"After SinopiaToFOLIO func call {instance_url}")
                output = instance_url

            case "load_sinopia":
                sinopia_rdf = await load_sinopia(args.get("resource_url"))
                prompt = "Add FOLIO Instance JSON record from" 
                add_history(f"{prompt}<pre>{sinopia_rdf}</pre>", "prompt")
                output = f"{prompt}\n{sinopia_rdf}"

            case _:
                output = f"Unknown function {function_name}"


        return output
    

    #async def system(self):
    #    system_prompt = SinopiaToFOLIO.system_prompt

    #    if self.zero_shot is False:
    #        system_prompt = f"{system_prompt}\n\nExamples"
    #        system_prompt += "\n".join(self.examples)

    #    return system_prompt

    async def run(self, chat_instance: ChatGPT, initial_prompt: str):
        add_history(initial_prompt, "prompt")
        chat_instance.functions = SinopiaToFOLIO.functions
        chat_result = await chat_instance(initial_prompt)
        add_history(chat_result, "response")
        function_call = chat_result["choices"][0]["message"].get("function_call")
        if function_call:
            first_result = await self.__handle_func__(function_call)
            console.log(f"First result")
            chat_result_rdf = await chat_instance(first_result)
            final_func_call = chat_result_rdf["choices"][0]["message"].get("function_call")
            console.log(f"Final func {final_func_call}")
            final_result = await self.__handle_func__(final_func_call)
            # console.log(f"The final result {final_result}")
            add_history(chat_result_rdf, "response")
            load_instance(final_result)

            return final_result
        return "Workflow finished without completing"
