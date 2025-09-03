# main.py
from flask import Flask, request, session, redirect, url_for, render_template_string
import os
import random
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "adventurerio_secret_key")

# ----- Config -----
MAX_PLAYERS = 4
STARTING_LIFE = 100

# ----- Characters (names only for selection) -----
CHARACTERS = ["Ana", "Bruno", "Iara", "Lucas", "Mariana", "Thiago"]

# ----- 20+ Perguntas (simplificadas A/B) -----
# Cada opção contém: vida (delta) e atributos que mudam (pontos)
QUESTIONS = [
    {"fase":1,"pergunta":"Você encontra uma ponte desgastada. A) atravessar correndo  B) procurar alternativa",
     "A":{"vida":-8,"coragem":6},"B":{"vida":-3,"sabedoria":6}},
    {"fase":1,"pergunta":"Ouves barulho atrás de uma porta. A) abrir  B) esperar e observar",
     "A":{"vida":-10,"coragem":8},"B":{"vida":-4,"sabedoria":6}},
    {"fase":1,"pergunta":"Um morador pede ajuda com carga. A) ajudar B) seguir caminho",
     "A":{"vida":-5,"empatia":7},"B":{"vida":-7,"racionalidade":5}},
    {"fase":2,"pergunta":"A chuva aumenta e a rua alaga. A) atravessar com pressa B) buscar abrigo",
     "A":{"vida":-12,"coragem":8},"B":{"vida":-4,"sabedoria":7}},
    {"fase":2,"pergunta":"Você encontra um mapa misterioso. A) seguir mapa B) ignorar",
     "A":{"vida":-6,"curiosidade":6},"B":{"vida":-3,"racionalidade":6}},
    {"fase":2,"pergunta":"Um comerciante oferece atalho duvidoso. A) aceitar B) recusar",
     "A":{"vida":-14,"ganancia":7},"B":{"vida":-2,"sabedoria":8}},
    {"fase":3,"pergunta":"Alguém te desafia a correr por um telhado. A) aceitar B) recusar",
     "A":{"vida":-20,"coragem":12},"B":{"vida":-5,"racionalidade":8}},
    {"fase":3,"pergunta":"Você vê um ferido no caminho. A) parar para ajudar B) seguir missão",
     "A":{"vida":-6,"empatia":10},"B":{"vida":-18,"ganancia":6}},
    {"fase":3,"pergunta":"O grupo quer dividir as provisões. A) dividir justo B) guardar para si",
     "A":{"vida":-3,"empatia":6},"B":{"vida":-7,"ganancia":8}},
    {"fase":4,"pergunta":"Chefe bloqueia passagem; negociar ou lutar? A) negociar B) lutar",
     "A":{"vida":-8,"sabedoria":10},"B":{"vida":-22,"coragem":15}},
    {"fase":4,"pergunta":"Tesouro protegido por armadilha. A) tentar pegar B) deixar",
     "A":{"vida":-26,"ganancia":14},"B":{"vida":-6,"sabedoria":12}},
    {"fase":4,"pergunta":"Uma criança pede para ir junto. A) aceitar B) recusar",
     "A":{"vida":-7,"empatia":12},"B":{"vida":-5,"racionalidade":10}},
    {"fase":5,"pergunta":"Última encruzilhada: guiar pela intuição ou lógica? A) intuição B) lógica",
     "A":{"vida":-5,"criatividade":10},"B":{"vida":-5,"racionalidade":12}},
    {"fase":5,"pergunta":"Um aliado trai você. A) perdoar B) retaliar",
     "A":{"vida":-10,"empatia":14},"B":{"vida":-18,"coragem":10}},
    {"fase":5,"pergunta":"Final: salvar a cidade ou recuperar algo pessoal? A) salvar B) recuperar",
     "A":{"vida":-20,"empatia":18},"B":{"vida":-15,"ganancia":18}},
    # Replicar até atingir 20+ perguntas (para garantir, vamos adicionar variações simples)
]

# add filler to reach 20+ if needed
while len(QUESTIONS) < 22:
    i = len(QUESTIONS) + 1
    QUESTIONS.append({
        "fase": min(5, 1 + (i//4)),
        "pergunta": f"Decisão extra #{i}: escolha com cuidado. A) arriscar B) manter-se",
        "A": {"vida": -6 - (i%3)*2, "coragem": 5 + (i%4)},
        "B": {"vida": -3 - (i%2)*2, "sabedoria": 5 + ((i+1)%4)}
    })


# ---------- Helpers ----------
def ensure_session():
    if 'players' not in session:
        session['players'] = []
    if 'vidas' not in session:
        session['vidas'] = {}
    if 'attributes' not in session:
        session['attributes'] = {}
    if 'progress' not in session:
        session['progress'] = {}

def clamp(v, lo=0, hi=999):
    return max(lo, min(hi, v))

# ---------- Routes (templates embedded) ----------
@app.route('/', methods=['GET','POST'])
def index():
    ensure_session()
    if request.method == 'POST':
        players = request.form.getlist('players')
        # limit players
        players = players[:MAX_PLAYERS]
        if not players:
            return render_template_string(INDEX_HTML, characters=CHARACTERS, error="Escolha pelo menos 1 personagem.")
        session['players'] = players
        session['vidas'] = {p: STARTING_LIFE for p in players}
        session['attributes'] = {p: {} for p in players}
        session['progress'] = {p: 0 for p in players}
        # store order for hotseat
        session['order'] = players
        return redirect(url_for('play', player=players[0]))
    return render_template_string(INDEX_HTML, characters=CHARACTERS, error=None)

@app.route('/play/<player>', methods=['GET','POST'])
def play(player):
    ensure_session()
    if player not in session['players']:
        return redirect(url_for('index'))

    if request.method == 'POST':
        choice = request.form.get('choice')
        idx = session['progress'].get(player, 0)
        if idx >= len(QUESTIONS):
            return redirect(url_for('final'))
        q = QUESTIONS[idx]
        # apply effects
        option = q.get(choice)
        if not option:
            # invalid, ignore
            return redirect(url_for('play', player=player))
        # update life
        session['vidas'][player] = clamp(session['vidas'][player] + option.get('vida',0), 0, 9999)
        # update attributes
        for k,v in option.items():
            if k == 'vida': continue
            session['attributes'][player][k] = session['attributes'][player].get(k,0) + v
        session['progress'][player] = idx + 1
        # check life critical
        if session['vidas'][player] <= 20:
            return redirect(url_for('minigame', player=player))
        # next player or same player (hotseat rotates)
        # rotate to next player who still has remaining questions, or final
        order = session.get('order', session['players'])
        # find next index that still has progress < len(QUESTIONS)
        for _ in range(len(order)):
            # rotate the list: pop first and append
            order = order[1:] + order[:1]
            next_player = order[0]
            if session['progress'].get(next_player,0) < len(QUESTIONS):
                session['order'] = order
                return redirect(url_for('play', player=next_player))
        # all done -> final
        return redirect(url_for('final'))

    # GET: show current question for this player
    idx = session['progress'].get(player, 0)
    if idx >= len(QUESTIONS):
        return redirect(url_for('final'))
    q = QUESTIONS[idx]
    vida = session['vidas'].get(player, STARTING_LIFE)
    return render_template_string(PLAY_HTML, player=player, q=q, vida=vida, idx=idx+1, total=len(QUESTIONS))

@app.route('/minigame/<player>', methods=['GET','POST'])
def minigame(player):
    ensure_session()
    if player not in session['players']:
        return redirect(url_for('index'))
    if request.method == 'POST':
        try:
            clicks = int(request.form.get('clicks', '0'))
        except:
            clicks = 0
        # reward: each click restores 1 life (can tune)
        session['vidas'][player] = clamp(session['vidas'][player] + clicks, 0, 9999)
        # after minigame return to play for same player
        return redirect(url_for('play', player=player))
    vida = session['vidas'].get(player, STARTING_LIFE)
    # difficulty hint: if player already used minigames many times we could tune, for simplicity keep fixed
    return render_template_string(MINIGAME_HTML, player=player, vida=vida)

@app.route('/final')
def final():
    ensure_session()
    # build simple profiles (convert attributes to normalized percentages)
    profiles = {}
    for p in session.get('players', []):
        attrs = session['attributes'].get(p, {})
        # select core keys and ensure consistent order
        keys = ["coragem","sabedoria","empatia","racionalidade","ganancia","criatividade","curiosidade"]
        values = [attrs.get(k,0) for k in keys]
        # normalize to percent of max found among keys (avoid all zeros)
        maxv = max(max(values),1)
        percents = [int((v/maxv)*100) for v in values]
        profiles[p] = {"labels": keys, "values": percents, "raw": attrs}
    return render_template_string(FINAL_HTML, profiles=profiles)

# ---------- Templates ----------
INDEX_HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AdventureRio — Início</title>
<style>
  :root{--bg:#0b1220;--card:#0f1726;--accent:#0ea5a4;--muted:#94a3b8;}
  body{font-family:Inter, system-ui, Arial; margin:0; background:linear-gradient(180deg,#061021 0%, #071426 100%); color:#e6eef6; display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px;}
  .card{background:var(--card); padding:20px;border-radius:14px; width:100%;max-width:760px; box-shadow:0 8px 30px rgba(2,6,23,0.6);}
  h1{margin:0 0 8px 0; font-size:28px; color:#f1f8fb;}
  p.small{color:var(--muted); margin:8px 0 18px 0;}
  .chars{display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:10px;}
  label.char{background:#071a2a;padding:10px;border-radius:10px; display:flex;align-items:center;justify-content:center; cursor:pointer; border:1px solid rgba(255,255,255,0.03);}
  input[type=checkbox]{display:none;}
  label.char:hover{transform:translateY(-4px); transition:all .18s;}
  button.primary{background:var(--accent); color:#042026; border:none; padding:12px 18px; border-radius:10px; font-weight:700; cursor:pointer; width:100%; margin-top:14px;}
  .foot{font-size:13px;color:var(--muted); margin-top:12px;}
  .error{color:#ffb4b4; margin-bottom:10px;}
</style>
</head>
<body>
  <div class="card">
    <h1>AdventureRio</h1>
    <p class="small">Jogo narrativo criado com comandos de prompt + IA durante curso na <strong>DIO.me</strong>. Escolha 1–4 personagens e comece a aventura!</p>
    {% if error %}<div class="error">{{error}}</div>{% endif %}
    <form method="POST">
      <div class="chars">
        {% for c in characters %}
          <label class="char"><input type="checkbox" name="players" value="{{c}}"> {{c}}</label>
        {% endfor %}
      </div>
      <button class="primary" type="submit">Começar Aventura</button>
      <div class="foot">Funciona em celular e desktop — compartilhe o link com seus amigos.</div>
    </form>
  </div>
</body>
</html>
"""

PLAY_HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AdventureRio — Jogo</title>
<style>
  :root{--bg:#071426;--card:#0f1726;--accent:#f59e0b;--muted:#93a4b6;}
  body{font-family:Inter, Arial; background:linear-gradient(180deg,#041021 0%, #071426 100%); color:#eaf5ff; margin:0; padding:18px; display:flex; align-items:center; justify-content:center; min-height:100vh;}
  .card{width:100%;max-width:820px;background:var(--card);padding:20px;border-radius:14px; box-shadow:0 10px 30px rgba(0,0,0,0.6);}
  h2{margin:0;color:#fff;}
  .meta{color:var(--muted); margin-bottom:14px;}
  .question{font-size:18px;margin:10px 0 16px 0;}
  .choices{display:flex; gap:12px; flex-wrap:wrap;}
  button.choice{flex:1; min-width:140px; padding:14px; border-radius:10px; border:none; font-weight:700; cursor:pointer;}
  button.a{background:#10b981;color:#032016;}
  button.b{background:#3b82f6;color:#06203a;}
  .life{margin-top:12px;color:#fff;}
  .small{color:var(--muted); font-size:13px; margin-top:10px;}
</style>
</head>
<body>
  <div class="card">
    <h2>Jogador: {{player}}</h2>
    <div class="meta">Pergunta {{idx}} / {{total}} — Vida: <strong>{{vida}}</strong></div>
    <div class="question">{{q['pergunta']}}</div>
    <form method="POST" class="choices">
      <button class="choice a" name="choice" value="A">A</button>
      <button class="choice b" name="choice" value="B">B</button>
    </form>
    <div class="small">Escolhas influenciam atributos e podem ativar um mini-jogo se a vida estiver crítica.</div>
  </div>
</body>
</html>
"""

MINIGAME_HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mini-jogo — Cliques</title>
<style>
  :root{--card:#0f1726;--accent:#ef4444;}
  body{font-family:Inter, Arial; background:linear-gradient(180deg,#041021,#071426); color:#fff; margin:0; padding:18px; display:flex;align-items:center;justify-content:center;min-height:100vh;}
  .card{background:var(--card);padding:18px;border-radius:12px;width:100%;max-width:600px;text-align:center;}
  h2{margin:0 0 8px 0;}
  .timer{font-size:22px;margin:6px 0;}
  .counter{font-size:40px;margin:8px 0;color:var(--accent);}
  button.click{padding:16px 22px;border-radius:12px;border:none;background:#10b981;color:#052014;font-weight:800;font-size:18px;cursor:pointer;width:70%;max-width:280px;}
  .small{color:#94a3b8;margin-top:8px;}
</style>
</head>
<body>
  <div class="card">
    <h2>Última Chance — Mini-jogo</h2>
    <div class="timer">Tempo restante: <span id="time">5.0</span>s</div>
    <div class="counter" id="count">0</div>
    <button class="click" onclick="doClick()">CLIQUE!</button>
    <div class="small">Cada clique recupera 1 ponto de vida. Boa sorte, {{player}}! Vida atual: {{vida}}</div>
    <form id="frm" method="POST">
      <input type="hidden" name="clicks" id="clicks">
    </form>
  </div>
<script>
let clicks = 0;
let t = 5.0;
let running = true;
function doClick(){ if(!running) return; clicks++; document.getElementById('count').innerText = clicks; }
let timer = setInterval(()=> {
  t = Math.max(0, (Math.round((t-0.1)*10)/10));
  document.getElementById('time').innerText = t.toFixed(1);
  if (t <= 0) {
    running = false;
    clearInterval(timer);
    document.getElementById('clicks').value = clicks;
    document.getElementById('frm').submit();
  }
}, 100);
</script>
</body>
</html>
"""

FINAL_HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AdventureRio — Perfil Final</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body{font-family:Inter, Arial;background:linear-gradient(180deg,#061021,#071426);color:#fff;padding:18px;min-height:100vh;}
  .card{background:#0b1220;padding:18px;border-radius:12px;max-width:900px;margin:10px auto;}
  h1{margin:0 0 12px 0;}
  .player{margin:18px 0;padding:12px;border-radius:10px;background:#071426;}
  canvas{width:100% !important; height:260px !important;}
  .desc{color:#a9c0d6;margin-top:8px;font-size:14px;}
</style>
</head>
<body>
  <div class="card">
    <h1>Perfis Finais</h1>
    {% for name, p in profiles.items() %}
      <div class="player">
        <h2>{{name}}</h2>
        <canvas id="chart{{loop.index}}"></canvas>
        <div class="desc">
          {% if p.raw %}
            {% for k,v in p.raw.items() %}
              <strong>{{k}}:</strong> {{v}} &nbsp;
            {% endfor %}
          {% else %}
            Sem atributos registrados.
          {% endif %}
        </div>
      </div>
    {% endfor %}
  </div>

<script>
{% for name, p in profiles.items() %}
new Chart(document.getElementById('chart{{loop.index}}').getContext('2d'), {
  type:'bar',
  data:{
    labels: {{ p.labels|tojson }},
    datasets:[{
      label: '{{ name }}',
      data: {{ p.values|tojson }},
      backgroundColor: ['rgba(255,99,132,0.7)','rgba(54,162,235,0.7)','rgba(75,192,192,0.7)','rgba(255,206,86,0.7)','rgba(153,102,255,0.7)','rgba(99,255,160,0.7)','rgba(200,150,255,0.7)']
    }]
  },
  options:{responsive:true, scales:{y:{beginAtZero:true, max:100}}}
});
{% endfor %}
</script>
</body>
</html>
"""

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
