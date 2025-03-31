import requests
import networkx as nx
import matplotlib.pyplot as plt
from SPARQLWrapper import SPARQLWrapper, JSON

def get_wikidata_id(drug_name):
    """Retrieve the Wikidata ID for a given drug name."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "search": drug_name,
        "language": "en",
        "type": "item"
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data["search"]:
        return data["search"][0]["id"]
    else:
        raise ValueError(f"No Wikidata ID found for drug: {drug_name}")

def get_drug_interactions(drug_wikidata_id, drug_name, limit=20):
    """Query Wikidata for drug-drug interactions of a specific drug."""
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    query = f"""
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX wd: <http://www.wikidata.org/entity/>

    SELECT ?drug2Label ?interactionTypeLabel
    WHERE {{
      wd:{drug_wikidata_id} wdt:P129 ?drug2 .
      OPTIONAL {{ wd:{drug_wikidata_id} wdt:P2175 ?interactionType }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT {limit}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    interactions = []
    for result in results["results"]["bindings"]:
        drug2 = result["drug2Label"]["value"]
        interaction = result.get("interactionTypeLabel", {}).get("value", "Unknown")
        interactions.append((drug_name, drug2, interaction))
    return interactions

def visualize_graph(interactions, drug_name):
    """Visualize drug interactions using NetworkX and Matplotlib."""
    G = nx.DiGraph()
    for drug1, drug2, interaction in interactions:
        G.add_node(drug1, color='red')
        G.add_node(drug2, color='blue')
        G.add_edge(drug1, drug2, label=interaction)
    pos = nx.spring_layout(G, seed=42)
    node_colors = [G.nodes[n]['color'] for n in G.nodes]
    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, node_color=node_colors, edge_color="gray", font_size=10, node_size=2000, font_weight="bold")
    edge_labels = {(drug1, drug2): interaction for drug1, drug2, interaction in interactions}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9, label_pos=0.5)
    plt.title(f"Drug Interactions for {drug_name}")
    plt.show()

drug_name = "Aspirin"
try:
    drug_wikidata_id = get_wikidata_id(drug_name)
    interactions = get_drug_interactions(drug_wikidata_id, drug_name)
    print(interactions)
    visualize_graph(interactions, drug_name)
except ValueError as e:
    print(e)
