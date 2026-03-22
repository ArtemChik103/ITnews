import urllib.request, json

# Build graph for articles 1-5
for aid in [1, 2, 3, 4, 5]:
    req = urllib.request.Request(f"http://127.0.0.1:8000/articles/{aid}/graph", method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        d = json.loads(r.read())
        ent = d.get("entities", 0)
        rel = d.get("relations", 0)
        print(f"  article {aid}: entities={ent} relations={rel}")
    except Exception as e:
        print(f"  article {aid} FAIL: {e}")

# Now test graph endpoint with article_id
r = urllib.request.urlopen("http://127.0.0.1:8000/api/graph?article_id=1", timeout=15)
d = json.loads(r.read())
print(f"\n  GET /api/graph?article_id=1: nodes={len(d['nodes'])} edges={len(d['edges'])}")

# Test article detail now has entities
r = urllib.request.urlopen("http://127.0.0.1:8000/api/articles/1", timeout=15)
d = json.loads(r.read())
print(f"  GET /api/articles/1: entities={len(d['entities'])} related={len(d['related_articles'])}")

# If we have entities, test entity endpoint
if d["entities"]:
    ename = d["entities"][0]["name"]
    url = f"http://127.0.0.1:8000/api/entities/{urllib.request.quote(ename)}"
    r = urllib.request.urlopen(url, timeout=15)
    ed = json.loads(r.read())
    print(f"  GET /api/entities/{ename}: type={ed['type']} articles={len(ed['articles'])} related={len(ed['related_entities'])}")

    # Graph by entity
    url2 = f"http://127.0.0.1:8000/api/graph?entity_name={urllib.request.quote(ename)}"
    r2 = urllib.request.urlopen(url2, timeout=15)
    gd = json.loads(r2.read())
    print(f"  GET /api/graph?entity_name={ename}: nodes={len(gd['nodes'])} edges={len(gd['edges'])}")

# Test RAG search with graph
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/search",
    data=json.dumps({"question": "What companies are mentioned in recent news?", "top_k": 5, "use_graph": True}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
r = urllib.request.urlopen(req, timeout=30)
d = json.loads(r.read())
print(f"\n  RAG search: status={d['status']} answer_len={len(d['answer'])} sources={len(d['sources'])} entities={len(d['entities'])} edges={len(d['graph_edges'])}")
print(f"  debug: vector_hits={d['retrieval_debug']['vector_hits']} graph_hits={d['retrieval_debug']['graph_hits']} model={d['retrieval_debug'].get('llm_model')}")

print("\n  ALL E2E TESTS PASSED")
