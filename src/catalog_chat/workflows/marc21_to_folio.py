from paradag import SequentialProcessor, dag_run

from workflows import FOLIOWorkFlow, add_instance_sig

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
        args = json.loads(function_call.get("arguments"), strict=False)
        #console.log(f"Function name {function_name} args: {args}")
        if function_name.startswith("add_instance"):
            record = args.get("record")
            if isinstance(record, str):
                record = json.loads(record, strict=False)
            self.__update_record__(record)
            instance_url = await add_instance(json.dumps(record))
            msg = f"Load FOLIO Instance {instance_url}"
            add_history(msg, "prompt")
        load_chat_result = await chat_instance(msg)
        function_call = load_chat_result["choices"][0]["message"].get("function_call")
