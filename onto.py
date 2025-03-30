from SPARQLWrapper import SPARQLWrapper, JSON
import networkx as nx
import matplotlib.pyplot as plt
import requests
import os
from dotenv import load_dotenv

# --------------------------
# Configuration
# --------------------------
load_dotenv()
GKG_API_KEY = os.getenv("gkg_api")
DBPEDIA_SPARQL = "https://dbpedia.org/sparql"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# --------------------------
# Core Functions
# --------------------------
def get_user_input():
    return (
        input("Enter first drug: ").strip(),
        input("Enter second drug: ").strip()
    )

def get_interaction_report(drug_a, drug_b):
    def query_source(source_func, drug):
        try:
            return source_func(drug)
        except:
            return set()
    
    sources = [query_dbpedia, query_wikidata, query_google_kg]
    
    neighbors_a = set().union(*[query_source(f, drug_a) for f in sources])
    neighbors_b = set().union(*[query_source(f, drug_b) for f in sources])
    
    return {
        "drug_a": drug_a,
        "drug_b": drug_b,
        "direct": drug_b in neighbors_a or drug_a in neighbors_b,
        "common": neighbors_a & neighbors_b,
        "neighbors_a": neighbors_a,
        "neighbors_b": neighbors_b
    }

def display_report(report):
    print(f"\nInteraction Report ({report['drug_a']} vs {report['drug_b']}):")
    print(f"Direct interaction: {'Yes' if report['direct'] else 'No'}")
    print(f"Shared interactions: {report['common'] or 'None'}")

def visualize_interaction(report):
    G = nx.Graph()
    G.add_edges_from((report['drug_a'], n) for n in report['neighbors_a'])
    G.add_edges_from((report['drug_b'], n) for n in report['neighbors_b'])
    
    edge_colors = [
        'red' if n in report['common'] else 'black'
        for n in G.nodes() if n != report['drug_a'] and n != report['drug_b']
    ]
    
    plt.figure(figsize=(12, 8))
    nx.draw(G, nx.spring_layout(G, seed=42), 
            with_labels=True, node_color='lightblue',
            edge_color=edge_colors, node_size=2500)
    plt.title(f"Interaction Map: {report['drug_a']} vs {report['drug_b']}")
    plt.show()

# --------------------------
# Data Source Functions
# --------------------------
def query_dbpedia(drug):
    sparql = SPARQLWrapper(DBPEDIA_SPARQL)
    sparql.setQuery(f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        SELECT ?relatedDrug WHERE {{
            dbr:{drug} dbo:relatedDrug ?relatedDrug .
        }} LIMIT 10
    """)
    return {result["relatedDrug"]["value"].split("/")[-1] 
            for result in sparql.query().convert()["results"]["bindings"]}

def query_wikidata(drug):
    sparql = SPARQLWrapper(WIKIDATA_SPARQL)
    sparql.setQuery(f"""
        SELECT ?interactionLabel WHERE {{
            wd:{drug} wdt:P769 ?interaction .
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
    """)
    return {result["interactionLabel"]["value"] 
            for result in sparql.query().convert()["results"]["bindings"]}

def query_google_kg(drug):
    response = requests.get(
        "https://kgsearch.googleapis.com/v1/entities:search",
        params={"query": drug, "key": GKG_API_KEY, "limit": 10, "languages": "en"}
    )
    return {item.get("result", {}).get("name", "Unknown") 
            for item in response.json().get("itemListElement", [])}

# --------------------------
# Main Execution
# --------------------------
def main():
    drug_a, drug_b = get_user_input()
    report = get_interaction_report(drug_a, drug_b)
    display_report(report)
    
    if input("\nVisualize interaction? (y/n): ").lower() == 'y':
        visualize_interaction(report)

if __name__ == "__main__":
    main()
