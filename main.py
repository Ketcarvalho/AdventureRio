from flask import Flask, render_template_string, request, redirect, url_for, session
import random

app = Flask(__name__)
app.secret_key = "adventurerio_secret"

# ----------------- Dados principais -----------------
questions = [
    {"q": "Você encontra uma trilha escura na floresta. Segue por ela?",
     "choices": {"Sim": {"courage": 2}, "Não": {"wisdom": 2}}},
    {"q": "Um viajante pede ajuda com bagagens pesadas. O que faz?",
     "choices": {"Ajuda": {"empathy": 2}, "Ignora": {"curiosity": 2}}},
    {"q": "Você vê uma placa misteriosa. Investiga?",
     "choices": {"Sim": {"curiosity": 2}, "Não": {"wisdom": 2}}},
    {"q": "Um rio está bloqueando seu caminho. O que faz?",
     "choices": {"Tenta atravessar": {"courage": 2}, "Procura ponte": {"wisdom": 2}}},
    {"q": "Uma criança perdida chora. Você a ajuda?",
     "choices": {"Sim": {"empathy": 2}, "Ignora": {"curiosity": 2}}},
]

# ----------------- Templates -----------------
layout = """
<!doctype html>
<html>
<head>
  <title>AdventureRio</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: Arial, sans-serif; text-align:center; background:#f4f4f9; margin:0; padding:0;}
    .container { padding:20px; }
    button { padding:10px 20px; margin:10px; border:none; border-radius:8px; background:#4CAF50; color:white; font-size:16px;}
    button:hover { background:#45a049; cursor:pointer;}
    .life { font-weight:bold; color:#e74c3c;}
  </style>
</head>
<body>
<div class="container">
  {% block content %}{% endblock %}
</div>
</body>
</html>
"""

intro_template = """
{% extends "layout" %}
{% block content %}
<h1>🌟 AdventureRio 🌟</h1>
<p>Bem-vindo(a)! Suas escolhas vão definir seu destino.<br>
Responda perguntas, preserve sua vida e descubra sua personalidade no final.</p>
<p><b>Objetivo:</b> tomar boas decisões e sobreviver!</p>
<a href="{{ url_for('start_game') }}"><button>Iniciar Jogo</button></a>
{% endblock %}
"""

question_template = """
{% extends "layout" %}
{% block content %}
<h2>{{ question['q'] }}</h2>
<p>❤️ Vida: <span class="life">{{ session['life'] }}</span></p>
{% for choice, effect in question['choices'].items() %}
  <form method="post">
    <button name="answer" value="{{ choice }}">{{ choice }}</button>
  </form>
{% endfor %}
{% endblock %}
"""

minigame_template = """
{% extends "layout" %}
{% block content %}
<h2>⚡ Mini-jogo!</h2>
<p>Clique 10 vezes para recuperar energia!</p>
<p>Cliques: <span id="count">0</span>/10</p>
<button onclick="clickCount()">Clique!</button>
<form id="form" method="post" style="display:none;">
  <input type="hidden" name="win" value="1">
</form>
<script>
let count=0;
function clickCount(){
  count++;
  document.getElementById("count").innerText = count;
  if(count>=10){ document.getElementById("form").submit(); }
}
</script>
{% endblock %}
"""

result_template = """
{% extends "layout" %}
{% block content %}
<h1>🎉 Fim da Jornada!</h1>
<p>Veja o resumo da sua personalidade:</p>
<canvas id="chart" width="300" height="300"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
var ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['Coragem','Sabedoria','Empatia','Curiosidade'],
    datasets: [{
      label: 'Seus pontos',
      data: [{{p['courage']}}, {{p['wisdom']}}, {{p['empathy']}}, {{p['curiosity']}}],
      backgroundColor:['#e74c3c','#3498db','#2ecc71','#9b59b6']
    }]
  }
});
</script>
<a href="{{ url_for('intro') }}"><button>Jogar Novamente</button></a>
{% endblock %}
"""

# ----------------- Rotas -----------------
@app.route("/")
def intro():
    return render_template_string(intro_template, layout=layout)

@app.route("/start")
def start_game():
    session['life'] = 3
    session['points'] = {"courage":0,"wisdom":0,"empathy":0,"curiosity":0}
    session['q_index'] = 0
    return redirect(url_for("question"))

@app.route("/question", methods=["GET","POST"])
def question():
    if session['q_index'] >= len(questions):
        return redirect(url_for("result"))

    q = questions[session['q_index']]

    if request.method == "POST":
        ans = request.form["answer"]
        effects = q["choices"][ans]
        for k,v in effects.items():
            session['points'][k]+=v

        # chance de perder vida
        if random.random() < 0.5:
            session['life'] -= 1

        if session['life'] <= 0:
            return redirect(url_for("minigame"))

        session['q_index'] += 1
        return redirect(url_for("question"))

    return render_template_string(question_template, layout=layout, question=q, session=session)

@app.route("/minigame", methods=["GET","POST"])
def minigame():
    if request.method=="POST":
        session['life'] += 2
        return redirect(url_for("question"))
    return render_template_string(minigame_template, layout=layout)

@app.route("/result")
def result():
    return render_template_string(result_template, layout=layout, p=session['points'])

# ----------------- Run -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
