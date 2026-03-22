import urllib.request, json, sys

passed = 0
failed = 0

def check(name, ok, info=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS {name} {info}")
    else:
        failed += 1
        print(f"  FAIL {name} {info}")

# 1. Article detail with entities (article 2 has Jack Dorsey)
r = urllib.request.urlopen("http://127.0.0.1:8000/api/articles/2", timeout=15)
d = json.loads(r.read())
check("article_2_detail", True, f"entities={len(d['entities'])} related={len(d['related_articles'])}")
check("article_2_has_entities", len(d["entities"]) > 0, f"found {len(d['entities'])}")

# 2. Graph for article with entities
r = urllib.request.urlopen("http://127.0.0.1:8000/api/graph?article_id=2", timeout=15)
d = json.loads(r.read())
check("graph_article_2", True, f"nodes={len(d['nodes'])} edges={len(d['edges'])}")
check("graph_has_nodes", len(d["nodes"]) > 0, f"found {len(d['nodes'])}")

# 3. Entity detail - use first entity from article 2
r = urllib.request.urlopen("http://127.0.0.1:8000/api/articles/2", timeout=15)
art = json.loads(r.read())
if art["entities"]:
    ename = art["entities"][0]["name"]
    url = f"http://127.0.0.1:8000/api/entities/{urllib.request.quote(ename)}"
    r = urllib.request.urlopen(url, timeout=15)
    ed = json.loads(r.read())
    check("entity_detail", True, f"name={ed['name']} type={ed['type']} articles={len(ed['articles'])}")
    check("entity_has_articles", len(ed["articles"]) > 0)

    # 4. Graph by entity
    url2 = f"http://127.0.0.1:8000/api/graph?entity_name={urllib.request.quote(ename)}"
    r2 = urllib.request.urlopen(url2, timeout=15)
    gd = json.loads(r2.read())
    check("graph_by_entity", True, f"nodes={len(gd['nodes'])} edges={len(gd['edges'])}")
    check("entity_graph_has_nodes", len(gd["nodes"]) > 0)

# 5. Filters
r = urllib.request.urlopen("http://127.0.0.1:8000/api/articles?language=en&page_size=5", timeout=15)
d = json.loads(r.read())
check("filter_language_en", True, f"items={len(d['items'])} total={d['total']}")
all_en = all(a["language"] == "en" for a in d["items"])
check("filter_language_correct", all_en, "all items are en" if all_en else "MISMATCH")

# 6. Pagination
r = urllib.request.urlopen("http://127.0.0.1:8000/api/articles?page=2&page_size=10", timeout=15)
d = json.loads(r.read())
check("pagination_page2", d["page"] == 2, f"page={d['page']} items={len(d['items'])}")

# 7. Clusters
r = urllib.request.urlopen("http://127.0.0.1:8000/api/clusters", timeout=15)
d = json.loads(r.read())
check("clusters_list", len(d["clusters"]) > 0, f"clusters={len(d['clusters'])}")
if d["clusters"]:
    c = d["clusters"][0]
    check("cluster_has_fields", "cluster_id" in c and "size" in c and "sample_articles" in c)

# 8. Semantic search
r = urllib.request.urlopen("http://127.0.0.1:8000/api/search/semantic?q=AI%20technology&top_k=3", timeout=15)
d = json.loads(r.read())
check("semantic_search", True, f"items={len(d['items'])} query={d['query']}")
check("semantic_has_results", len(d["items"]) > 0)

# 9. RAG full flow
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/search",
    data=json.dumps({"question": "What companies are mentioned in recent news?", "top_k": 5, "use_graph": True}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
r = urllib.request.urlopen(req, timeout=30)
d = json.loads(r.read())
check("rag_search", True, f"status={d['status']} answer_len={len(d['answer'])} sources={len(d['sources'])}")
check("rag_has_answer", len(d["answer"]) > 0)
check("rag_has_sources", len(d["sources"]) > 0)
check("rag_has_debug", d["retrieval_debug"]["vector_hits"] > 0)

# 10. API contract validation
r = urllib.request.urlopen("http://127.0.0.1:8000/api/articles/2", timeout=15)
d = json.loads(r.read())
required_fields = ["id", "title", "content_clean", "source", "url", "published_at", "language", "cluster_id", "entities", "related_articles"]
missing = [f for f in required_fields if f not in d]
check("article_detail_schema", len(missing) == 0, f"missing: {missing}" if missing else "all fields present")

print(f"\n  TOTAL: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
