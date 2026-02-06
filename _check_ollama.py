import aiohttp, asyncio

async def check():
    async with aiohttp.ClientSession() as s:
        async with s.get("http://localhost:11434/api/tags") as r:
            data = await r.json()
            for m in data.get("models", []):
                print(f"{m['name']:40s}  {m.get('size',0)//1024//1024:>6d} MB")
        # Test chat with glm-4.7-flash (local, should be fast)
        for model in ["glm-4.7-flash:latest", "kimi-k2.5:cloud"]:
            print(f"\nTesting chat with '{model}'...")
            try:
                async with s.post("http://localhost:11434/api/chat", json={
                    "model": model, "messages": [{"role":"user","content":"say hi in 5 words"}], "stream": False
                }, timeout=aiohttp.ClientTimeout(total=120)) as r:
                    d = await r.json()
                    if r.status == 200:
                        print(f"  OK: {d.get('message',{}).get('content','')[:100]}")
                    else:
                        print(f"  FAIL {r.status}: {str(d)[:100]}")
            except Exception as e:
                print(f"  ERROR: {e}")

asyncio.run(check())
