import requests

def get_search_results(search_query):
    endpoint = f"https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&utf8=1&redirects=1&srprop=size&origin=*&srsearch={search_query}"
    response = requests.get(endpoint)
    data = response.json()
    results = data.get("query", {}).get("search", [])
    if len(results) > 0:
        title = results[0].get("title", "")
        if title:
            return get_summary(title)
    return None

def get_summary(title):
    endpoint = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&format=json&exsentences=5&explaintext=&origin=*&titles={title}"
    response = requests.get(endpoint)
    data = response.json()
    results = data.get("query", {}).get("pages", {})
    for result in results.values():
        return result.get("extract", "")
    return None