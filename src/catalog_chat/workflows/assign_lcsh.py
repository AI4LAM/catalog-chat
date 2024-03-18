from typing import Union

from chat import add_history, ChatGPT
from workflows import WorkFlow

class AssignLCSH(WorkFlow):
    name = "Assign Library of Congress Subject Heading to record"
    system_prompt = "As an expert cataloger, you will use the context to assign Library of Congress Subject Headings to terms"

    examples = []

    def __init__(self, zero_shot:bool=False, chat_instance: Union[ChatGPT, None]=None):
        self.system = system
        self.react = react
        self.chat = chat_instance
        

    async def system(self):
        system_prompt = AssignLCSH.system_prompt

        if self.zero_shot is False:
            system_prompt = f"""{system_prompt}\nExamples:\n"""
            system_prompt += "\n".join(AssignLCSH.examples)

        return system_prompt

    async def run(self, initial_prompt: str):
        add_history(initial_prompt, "prompt")
        if not self.react:
            chat_result = await self.chat(initial_prompt)
            add_history(chat_result, "response")
            return
        count = 0
        while count < AssignLCSH.max_turns:
            count += 1
