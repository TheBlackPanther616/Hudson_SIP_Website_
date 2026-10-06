"""Application factory. Wires the presentation layer to the API layer only."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.dependencies import session_factory
from app.api.routes import history_router, plays_router, rules_router
from app.data.repositories import RuleRepository

__version__ = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Seed the rule library on startup so a fresh database is never empty."""
    session = session_factory()()
    try:
        RuleRepository(session).seed()
    finally:
        session.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="GridironIQ",
        version=__version__,
        description="Rule-grounded penalty determination for football officiating review.",
        lifespan=lifespan,
    )
    app.include_router(plays_router)
    app.include_router(rules_router)
    app.include_router(history_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

    return app


INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>GridironIQ</title>
<style>
 body{font-family:system-ui,Arial,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#16233a}
 h1{border-bottom:3px solid #1b3a6b;padding-bottom:.4rem}
 textarea{width:100%;height:8rem;font:inherit;padding:.6rem}
 button{background:#1b3a6b;color:#fff;border:0;padding:.6rem 1.2rem;font:inherit;cursor:pointer}
 .card{border:1px solid #d5dbe6;border-left:5px solid #1b3a6b;padding:1rem;margin-top:1rem}
 .muted{color:#5a6a85;font-size:.9rem}
</style></head><body>
<h1>GridironIQ</h1>
<p class="muted">Describe a play. The rule engine returns a determination with the rule it relied on.</p>
<textarea id="d" placeholder="The quarterback threw downfield; the cornerback grabbed the receiver's arm before the ball arrived on a catchable pass."></textarea>
<p><button onclick="go()">Analyze play</button></p>
<div id="out"></div>
<script>
async function go(){
  const d=document.getElementById('d').value;
  const out=document.getElementById('out');
  out.innerHTML='<p class="muted">Analyzing…</p>';
  try{
    const r=await fetch('/api/plays',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({description:d})});
    const j=await r.json();
    if(!r.ok){out.innerHTML='<div class="card">'+(j.detail?JSON.stringify(j.detail):'Request failed')+'</div>';return;}
    out.innerHTML='<div class="card"><strong>'+(j.is_penalty?'PENALTY':'NO CALL')+'</strong> &middot; confidence '+j.confidence+
      '<p>'+(j.matches.map(m=>'<b>'+m.name+'</b> ('+m.citation+')<br>'+m.rationale).join('<hr>')||'No rule condition was met.')+'</p>'+
      (j.advisor_note?'<p class="muted">'+j.advisor_note+'</p>':'')+'</div>';
  }catch(e){out.innerHTML='<div class="card">Error: '+e+'</div>';}
}
</script></body></html>"""

app = create_app()
