import os
import requests
import networkx as nx
import matplotlib.pyplot as plt
from SPARQLWrapper import SPARQLWrapper, JSON
import xml.etree.ElementTree as ET

# --------------------------
# Helper Functions
# --------------------------
def fetch_sparql_results(endpoint, query):
    """Helper function to execute a SPARQL query and return results."""
    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        print(f"SPARQL query failed: {e}")
        return []

# --------------------------
# Wikipedia Context
# --------------------------
def get_dbpedia_interactions(drug):
    """Fetch drug interactions from DBpedia."""
    query = f"""
    SELECT ?interaction WHERE {{
        dbr:{drug} dbo:drugInteraction ?interaction .
    }}
    """
    results = fetch_sparql_results("http://dbpedia.org/sparql", query)
    return [result['interaction']['value'].split("/")[-1] for result in results]

def get_wikidata_interactions(drug):
    """Fetch drug interactions from Wikidata."""
    query = f"""
    SELECT ?interaction WHERE {{
        wd:{drug} wdt:P769 ?interaction .
    }}
    """
    results = fetch_sparql_results("https://query.wikidata.org/sparql", query)
    return [result['interaction']['value'].split("/")[-1] for result in results]

# --------------------------
# Arxiv Context
# --------------------------
def get_arxiv_context(query):
    """Fetch research papers from Arxiv based on a query."""
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": 5
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        papers = []
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            summary = entry.find("{http://www.w3.org/2005/Atom}summary").text
            papers.append({"title": title, "summary": summary})
        return papers
    except requests.exceptions.RequestException as e:
        print(f"Arxiv API request failed: {e}")
        return []

# --------------------------
# Combined Context
# --------------------------
def fetch_combined_context(drug):
    """Fetch combined context from DBpedia, Wikidata, Google Knowledge Graph, and Arxiv."""
    dbpedia_context = get_dbpedia_interactions(drug)
    wikidata_context = get_wikidata_interactions(drug)
    arxiv_context = get_arxiv_context(drug)

    combined_context = {
        "DBpedia": dbpedia_context,
        "Wikidata": wikidata_context,
        "Arxiv": arxiv_context,
    }

    return combined_context

def get_google_kg_interactions(drug):
    """Fetch drug-related data from Google Knowledge Graph API."""
    api_key = os.getenv("GOOGLE_KG_API_KEY")
    if not api_key:
        print("Google KG API key not found.")
        return []

    url = "https://kgsearch.googleapis.com/v1/entities:search"
    params = {
        "query": drug,
        "key": api_key,
        "limit": 10,
        "indent": True
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return [
            item["result"]["name"]
            for item in data.get("itemListElement", [])
            if "result" in item and "name" in item["result"]
        ]
    except requests.exceptions.RequestException as e:
        print(f"Google KG API request failed: {e}")
        return []

def fetch_food_context(drug):
    """
    Fetch combined drug interaction data from DBpedia, Wikidata, and Google Knowledge Graph.
    """
    dbpedia_interactions = get_dbpedia_interactions(drug)
    wikidata_interactions = get_wikidata_interactions(drug)
    google_kg_interactions = get_google_kg_interactions(drug)

    combined_interactions = {
        "DBpedia": dbpedia_interactions,
        "Wikidata": wikidata_interactions,
        "GoogleKG": google_kg_interactions
    }

    return combined_interactions

def check_combined_interaction(drug1, drug2):
    """Check for common interactions between two drugs and visualize."""
    interactions1 = set(get_dbpedia_interactions(drug1) +
                        get_wikidata_interactions(drug1) +
                        get_google_kg_interactions(drug1))

    interactions2 = set(get_dbpedia_interactions(drug2) +
                        get_wikidata_interactions(drug2) +
                        get_google_kg_interactions(drug2))

    common_interactions = interactions1 & interactions2
    visualize_interactions(drug1, drug2, interactions1, interactions2, common_interactions)

    return common_interactions if common_interactions else "No known combined interactions found."

# --------------------------
# Visualization (from onto.py)
# --------------------------
def visualize_interactions(drug1, drug2, interactions1, interactions2, common_interactions):
    """Visualize drug interactions as a network graph."""
    import networkx as nx
    import matplotlib.pyplot as plt

    G = nx.Graph()
    G.add_node(drug1, color="blue")
    G.add_node(drug2, color="green")

    for interaction in interactions1:
        G.add_edge(drug1, interaction, color="blue")
    for interaction in interactions2:
        G.add_edge(drug2, interaction, color="green")
    for interaction in common_interactions:
        G.add_edge(drug1, interaction, color="red")
        G.add_edge(drug2, interaction, color="red")

    pos = nx.spring_layout(G)
    colors = [G[u][v]["color"] for u, v in G.edges()]
    nx.draw(G, pos, with_labels=True, edge_color=colors, node_color="lightblue", node_size=2000, font_size=10)
    plt.show()

if __name__ == "__main__":
    drug1 = input("Enter first drug name: ").strip().replace(" ", "_")
    drug2 = input("Enter second drug name: ").strip().replace(" ", "_")
    print(check_combined_interaction(drug1, drug2))
