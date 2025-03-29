from aiohttp import web
import asyncio
import json
from typing import Set, List
import threading

class SongServer:
    def __init__(self):
        self.app = web.Application()
        self.sse_connections: Set[web.StreamResponse] = set()
        self.songs: List[str] = []
        self.setup_routes()
        self.runner = None
        self.site = None

    def setup_routes(self):
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/stream', self.handle_stream)
        self.app.router.add_post('/update', self.handle_update)

    async def handle_index(self, request: web.Request) -> web.Response:
        return web.FileResponse(r"data/index.html")

    async def handle_stream(self, request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
        await response.prepare(request)
        self.sse_connections.add(response)
        
        try:
            await response.write(f"data: {json.dumps({'songs': self.songs})}\n\n".encode('utf-8'))
            
            while True:
                await asyncio.sleep(5)
                try:
                    await response.write(b': heartbeat\n\n')
                except:
                    break
        except:
            pass
        finally:
            self.sse_connections.discard(response)
            try:
                await response.write_eof()
            except:
                pass
        return response

    async def handle_update(self, request: web.Request) -> web.Response:
        data = await request.json()
        self.songs = data.get('songs', [])
        
        message = f"data: {json.dumps({'songs': self.songs})}\n\n".encode('utf-8')
        for conn in list(self.sse_connections):
            try:
                await conn.write(message)
            except:
                self.sse_connections.discard(conn)
        
        return web.json_response({"status": "success", "count": len(self.songs)})

    async def start_server(self, port: int = 8080):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()
        print(f"网页版点歌列表： http://localhost:{port}")

    def run_in_thread(self, port: int = 8080):
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_server(port))
            loop.run_forever()

        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()

    def stop(self):
        if self.site:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.site.stop())
            loop.run_until_complete(self.runner.cleanup())

def songlistserverrun():
    server = SongServer()
    server.run_in_thread()