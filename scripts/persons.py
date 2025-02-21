import os
import requests
from rdflib import Graph, URIRef, RDF, Namespace
from tqdm import tqdm
from acdh_cidoc_pyutils import (
    make_e42_identifiers,
    make_appellations,
    make_birth_death_entities,
    make_affiliations,
    make_entity_label,
    make_occupations,
    tei_relation_to_SRPC3_in_social_relation,
)
from acdh_xml_pyutils.xml import NSMAP
from acdh_cidoc_pyutils.namespaces import CIDOC
from acdh_tei_pyutils.tei import TeiReader
from acdh_tei_pyutils.utils import get_xmlid, check_for_hash

TYPE_DOMAIN = "https://pfp-custom-types"
g = Graph()
domain = "https://wmp1.acdh.oeaw.ac.at/"
PU = Namespace(domain)

rdf_dir = "./datasets"
os.makedirs(rdf_dir, exist_ok=True)

index_file = "listperson.xml"
entity_type = "person"

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
    item_label = make_entity_label(x.xpath(".//tei:persName[1]", namespaces=NSMAP)[0])[
        0
    ]
    item_id = f"{PU}{xml_id}"
    subj = URIRef(item_id)
    g.add((subj, RDF.type, CIDOC["E21_Person"]))
    affilliations = make_affiliations(
        subj,
        x,
        f"{PU}",
        item_label,
        org_id_xpath="./tei:orgName/@key",
        org_label_xpath="./tei:orgName/text()",
        add_org_object=True
    )
    g += affilliations

    # ids
    g += make_e42_identifiers(
        subj,
        x,
        type_domain="https://pfp-custom-types",
        default_lang="de",
    )

    # names
    g += make_appellations(
        subj, x, type_domain="https://pfp-custom-types", default_lang="de"
    )

    # birth
    try:
        x.xpath(".//tei:birth/tei:date", namespaces=NSMAP)[0]
        event_graph, birth_uri, birth_timestamp = make_birth_death_entities(
            subj,
            x,
            f"{PU}place__",
            event_type="birth",
            default_prefix="Geburt von",
            date_node_xpath="/tei:date[1]",
        )
        g += event_graph
    except IndexError:
        pass

    # death
    try:
        x.xpath(".//tei:death/tei:date", namespaces=NSMAP)[0]
        event_graph, birth_uri, birth_timestamp = make_birth_death_entities(
            subj,
            x,
            f"{PU}place__",
            event_type="death",
            default_prefix="Tod von",
            date_node_xpath="/tei:date[1]",
        )
        g += event_graph
    except IndexError:
        pass

    # occupations
    g += make_occupations(subj, x)[0]

    # birth/death places
    for y in x.xpath(
        ".//tei:residence[@type='Geburtsort']/tei:placeName", namespaces=NSMAP
    ):
        place_id = check_for_hash(y.attrib["key"])
        place_uri = URIRef(f"{domain}{place_id}")
        g.add((URIRef(f"{subj}/birth"), CIDOC["P7_took_place_at"], place_uri))

    for y in x.xpath(
        ".//tei:residence[@type='Sterbeort']/tei:placeName", namespaces=NSMAP
    ):
        place_id = check_for_hash(y.attrib["key"])
        place_uri = URIRef(f"{domain}{place_id}")
        g.add((URIRef(f"{subj}/death"), CIDOC["P7_took_place_at"], place_uri))

    # residences

    for y in x.xpath(".//tei:residence/tei:placeName[@key]", namespaces=NSMAP):
        place_id = check_for_hash(y.attrib["key"])
        place_uri = URIRef(f"{domain}{place_id}")
        g.add((subj, CIDOC["P74_has_current_or_former_residence"], place_uri))


lookup_dict = requests.get("https://pfp-schema.acdh.oeaw.ac.at/mappings/person-person.json").json()

for x in doc.any_xpath(".//tei:relation"):
    g += tei_relation_to_SRPC3_in_social_relation(
        x, domain=domain, lookup_dict=lookup_dict
    )

g.parse("https://pfp-schema.acdh.oeaw.ac.at/types/person-person/person-person.ttl")


save_path = os.path.join(rdf_dir, f"wmp1_{entity_type}.nt")
print(f"saving graph as {save_path}")
g.serialize(save_path, format="nt", encoding="utf-8")
