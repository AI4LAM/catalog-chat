import json

import rdflib

from js import document, console

from pyodide.http import pyfetch

BF = rdflib.Namespace("http://id.loc.gov/ontologies/bibframe/")
BFLC = rdflib.Namespace("http://id.loc.gov/ontologies/bflc/")
SHACL = rdflib.Namespace("http://www.w3.org/ns/shacl#")
SINOPIA = rdflib.Namespace("http://sinopia.io/vocabulary/")

def _bind_namespaces(graph: rdflib.Graph):
    graph.namespace_manager.bind("bf", BF)
    graph.namespace_manager.bind("bflc", BFLC)
    graph.namespace_manager.bind("sinopia",SINOPIA)
    graph.namespace_manager.bind("sh", SHACL)

async def add(*args):
    return "Add sinopia resource"


async def load(resource_url):
    sinopia_result = await pyfetch(resource_url)
    if sinopia_result.ok:
        sinopia_resource = await sinopia_result.json()
        rdf_graph = rdflib.Graph()
        _bind_namespaces(rdf_graph)
        rdf_graph.parse(data=json.dumps(sinopia_resource.get("data")), format="json-ld")
        turtle_rdf = rdf_graph.serialize(format='turtle')
        turtle_rdf = turtle_rdf.replace(">", "&gt;").replace("<", "&lt;")
        return turtle_rdf
