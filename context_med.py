import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import tiktoken
import arxiv  # Import the arXiv library

MAX_TOKENS = 20000  

def get_context(drug_name, pubmed_limit=5, arxiv_limit=5):
    """
    Retrieve comprehensive information about a drug, including its PubChem data,
    Wikipedia summary, related PubMed articles, and arXiv articles, ensuring the total token count
    does not exceed the model's context window.

    Parameters:
    - drug_name (str): The common name of the drug.
    - pubmed_limit (int): Maximum number of PubMed articles to retrieve.
    - arxiv_limit (int): Maximum number of arXiv articles to retrieve.

    Returns:
    - dict: A dictionary containing the drug's context information.
    """
    context = {"Drug Name": drug_name}

    pubchem_data = get_pubchem_data(drug_name)
    context["PubChem Data"] = pubchem_data

    wikipedia_summary = get_wikipedia_summary(drug_name)
    context["Wikipedia Summary"] = wikipedia_summary

    pubmed_articles = get_pubmed_articles(drug_name, pubmed_limit)
    context["PubMed Articles"] = pubmed_articles

    arxiv_articles = get_arxiv_articles(drug_name, arxiv_limit)
    context["arXiv Articles"] = arxiv_articles

    truncated_context = truncate_context(context, MAX_TOKENS)

    return truncated_context

def get_pubchem_data(drug_name):
    """Fetch chemical properties from PubChem."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/property/MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES/JSON"
    response = requests.get(url)
    if response.ok:
        data = response.json()
        properties = data.get("PropertyTable", {}).get("Properties", [{}])[0]
        return {
            "Molecular Formula": properties.get("MolecularFormula", "N/A"),
            "Molecular Weight": properties.get("MolecularWeight", "N/A"),
            "IUPAC Name": properties.get("IUPACName", "N/A"),
            "Canonical SMILES": properties.get("CanonicalSMILES", "N/A")
        }
    return {}

def get_wikipedia_summary(drug_name):
    """Fetch the summary section from Wikipedia for the given drug."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{drug_name}"
    response = requests.get(url)
    if response.ok:
        data = response.json()
        return data.get("extract", "No summary available.")
    return "No summary available."

def get_pubmed_articles(drug_name, limit):
    """Fetch related articles from PubMed."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": drug_name,
        "retmax": limit,
        "retmode": "xml"
    }
    response = requests.get(url, params=params)
    articles = []
    if response.ok:
        root = ET.fromstring(response.content)
        ids = [id_elem.text for id_elem in root.findall(".//Id")]
        for pubmed_id in ids:
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": pubmed_id,
                "retmode": "json"
            }
            fetch_response = requests.get(fetch_url, params=fetch_params)
            if fetch_response.ok:
                summary = fetch_response.json().get("result", {}).get(pubmed_id, {})
                articles.append({
                    "Title": summary.get("title", "No title available"),
                    "Source": summary.get("source", "No source available"),
                    "Publication Date": summary.get("pubdate", "No date available"),
                    "PubMed ID": pubmed_id,
                    "URL": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"
                })
    return articles

def get_arxiv_articles(query, limit=5):
    """
    Fetch related articles from arXiv.

    Parameters:
    - query (str): The search query for arXiv.
    - limit (int): Maximum number of articles to retrieve.

    Returns:
    - list: A list of dictionaries containing arXiv article details.
    """
    articles = []
    search = arxiv.Search(
        query=query,
        max_results=limit,
        sort_by=arxiv.SortCriterion.Relevance
    )
    for result in search.results():
        articles.append({
            "Title": result.title,
            "Authors": ", ".join(author.name for author in result.authors),
            "Published Date": result.published.strftime("%Y-%m-%d"),
            "Summary": result.summary,
            "URL": result.entry_id
        })
    return articles

def truncate_context(context, max_tokens):
    """
    Truncate the context dictionary to ensure the total token count does not exceed max_tokens.

    Parameters:
    - context (dict): The context dictionary containing various sections of information.
    - max_tokens (int): The maximum number of tokens allowed.

    Returns:
    - dict: The truncated context dictionary.
    """
    tokenizer = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text):
        return len(tokenizer.encode(text))

    sections = {}
    total_tokens = 0
    for key, value in context.items():
        if isinstance(value, list):
            serialized_value = "\n".join(str(item) for item in value)
        else:
            serialized_value = str(value)
        token_count = count_tokens(serialized_value)
        sections[key] = {
            "content": serialized_value,
            "tokens": token_count
        }
        total_tokens += token_count

    if total_tokens <= max_tokens:
        return context

    section_order = ["PubChem Data", "Wikipedia Summary", "PubMed Articles", "arXiv Articles"]
    truncated_context = {}
    remaining_tokens = max_tokens

    for section in section_order:
        if section in sections:
            if sections[section]["tokens"] <= remaining_tokens:
                truncated_context[section] = context[section]
                remaining_tokens -= sections[section]["tokens"]
            else:
                # Truncate the content to fit the remaining tokens
                truncated_content = truncate_text(sections[section]["content"], remaining_tokens, tokenizer)
                truncated_context[section] = truncated_content
                break

    return truncated_context

def truncate_text(text, max_tokens, tokenizer):
    """
    Truncate a text string to fit within the specified number of tokens.

    Parameters:
    - text (str): The text to be truncated.
    - max_tokens (int): The maximum number of tokens allowed.
    - tokenizer: The tokenizer instance used to encode the text.

    Returns:
    - str: The truncated text.
    """
    tokens = tokenizer.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
    return tokenizer.decode(tokens)
