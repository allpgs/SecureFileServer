from aiohttp import web

__VERSION__ = "1.2"

app = web.Application()
routes = web.RouteTableDef()

with open("./index.html", "r", encoding="utf-8") as f:
    html = f.read()

@routes.get("/")
@routes.get("/*")
async def maintenance(request):
    return web.Response(text=html, content_type="text/html")

app.add_routes(routes)
print(f"Server Version: {__VERSION__}")
web.run_app(app, host="0.0.0.0", port=1234)