import os
import requests
from tqdm import tqdm
from acdh_cidoc_pyutils import (
    make_e42_identifiers,
    make_appellations,
)
from acdh_cidoc_pyutils.namespaces import CIDOC
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import get_xmlid
from acdh_xml_pyutils.xml import NSMAP
from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDF

TYPE_DOMAIN = "https://pfp-custom-types"

g = Graph()
domain = "https://wmp1.acdh.oeaw.ac.at/"
PU = Namespace(domain)

rdf_dir = "./datasets"
os.makedirs(rdf_dir, exist_ok=True)

index_file = "listorg.xml"
entity_type = "org"

print("check if source file exists")
BASE_URL = "https://wmp1.acdh.oeaw.ac.at/"
if os.path.exists(index_file):
    pass
else:
    url = f"{BASE_URL}{index_file}"
    print(f"fetching {index_file} from {url}")
    response = requests.get(url)
    with open(index_file, "wb") as file:
        file.write(response.content)

doc = TeiReader(index_file)
items = doc.any_xpath(f".//tei:{entity_type}[@xml:id]")

for x in tqdm(items, total=len(items)):
    xml_id = get_xmlid(x)
    item_id = f"{PU}{xml_id}"
    subj = URIRef(item_id)
    g.add((subj, RDF.type, CIDOC["E74_Group"]))

    # ids
    g += make_e42_identifiers(
        subj,
        x,
        type_domain="http://hansi/4/ever",
        default_lang="de",
    )

    # names
    g += make_appellations(
        subj, x, type_domain="http://hansi/4/ever", default_lang="de"
    )

    # located
    for y in x.xpath(
        ".//tei:location[@type='located_in_place']/tei:placeName/@key", namespaces=NSMAP
    ):
        g.add((subj, CIDOC["P74_has_current_or_former_residence"], URIRef(f"{PU}{y}")))


save_path = os.path.join(rdf_dir, f"wkfm_{entity_type}.nt")
print(f"saving graph as {save_path}")
g.serialize(save_path, format="nt", encoding="utf-8")
