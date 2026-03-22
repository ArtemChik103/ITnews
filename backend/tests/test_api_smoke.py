import urllib.request, json, sys

def test_get(name, url):
    try:
        r = urllib.request.urlopen(url, timeout=15)
        d = json.loads(r.read())
        return name, True, r.status, d
    except Exception as e:
        return name, False, 0, str(e)

def test_post(name, url, body):
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        r = urllib.request.urlopen(req, timeout=30)
        d = json.loads(r.read())
        return name, True, r.status, d
    except Exception as e:
        return name, False, 0, str(e)

results = []

# GET endpoints
gets = [
    ("health", "http://127.0.0.1:8000/health"),
    ("articles_page", "http://127.0.0.1:8000/api/articles?page=1&page_size=5"),
    ("articles_filter", "http://127.0.0.1:8000/api/articles?source=TechCrunch&page_size=3"),
    ("articles_sort", "http://127.0.0.1:8000/api/articles?sort=ingested_at&page_size=2"),
    ("clusters", "http://127.0.0.1:8000/api/clusters"),
    ("graph_empty", "http://127.0.0.1:8000/api/graph"),
    ("graph_article1", "http://127.0.0.1:8000/api/graph?article_id=1"),
]

for name, url in gets:
    results.append(test_get(name, url))

# Test article detail with first article id
_, ok, _, adata = results[1]  # articles_page
if ok and adata.get("items"):
    aid = adata["items"][0]["id"]
    results.append(test_get("article_detail", f"http://127.0.0.1:8000/api/articles/{aid}"))

# POST /api/search
results.append(test_post("rag_search", "http://127.0.0.1:8000/api/search", {"question": "What companies are in AI?", "top_k": 3}))

# Print results
passed = 0
failed = 0
for name, ok, code, data in results:
    if ok:
        passed += 1
        info = ""
        if isinstance(data, dict):
            if "items" in data:
                info = f"items={len(data['items'])} total={data.get('total', '?')}"
            elif "clusters" in data:
                info = f"clusters={len(data['clusters'])}"
            elif "nodes" in data:
                info = f"nodes={len(data['nodes'])} edges={len(data['edges'])}"
            elif "answer" in data:
                info = f"status={data.get('status')} answer_len={len(data.get('answer',''))}"
            elif "content_clean" in data:
                info = f"title_len={len(data.get('title',''))} entities={len(data.get('entities',[]))} related={len(data.get('related_articles',[]))}"
            elif "status" in data:
                info = f"status={data['status']}"
        print(f"  PASS {name} ({code}) {info}")
    else:
        failed += 1
        print(f"  FAIL {name}: {data}")

print(f"\n  {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
