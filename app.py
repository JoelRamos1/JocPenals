from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

jugades = {"jugador1": None, "jugador2": None}

ALÇADES = ["baixa", "mitjana", "alta"]
DIRECCIONS = ["esquerra", "centre", "dreta"]

def calcular_punts(xut, aturada):
    punts = 0
    if xut[0] == aturada[0]:
        punts += 1
    if xut[1] == aturada[1]:
        punts += 1
    return punts

@app.route("/")
def menu():
    return render_template("menu.html")

@app.route("/jugador1", methods=["GET", "POST"])
def jugador1():
    return gestionar_jugada("jugador1")

@app.route("/jugador2", methods=["GET", "POST"])
def jugador2():
    return gestionar_jugada("jugador2")

def gestionar_jugada(jugador):
    error = None
    jugada = jugades[jugador]
    if request.method == "POST":
        if jugada is not None:
            error = "Ja has enviat la teva jugada."
        else:
            xut = (request.form["xut_alçada"], request.form["xut_direccio"])
            aturada = (request.form["aturada_alçada"], request.form["aturada_direccio"])
            jugades[jugador] = {"xut": xut, "aturada": aturada}
            jugada = jugades[jugador]

    return render_template("jugador.html",
                           jugador=jugador,
                           alçades=ALÇADES,
                           direccions=DIRECCIONS,
                           jugada=jugada,
                           error=error)

@app.route("/resultat")
def resultat():
    if not jugades["jugador1"] or not jugades["jugador2"]:
        return render_template("resultat.html", jugades=jugades, punts_j1=None, punts_j2=None, guanyador=None)

    j1, j2 = jugades["jugador1"], jugades["jugador2"]
    punts_j1 = calcular_punts(j2["xut"], j1["aturada"])
    punts_j2 = calcular_punts(j1["xut"], j2["aturada"])

    if punts_j1 > punts_j2:
        guanyador = "Guanya el Jugador 1!"
    elif punts_j2 > punts_j1:
        guanyador = "Guanya el Jugador 2!"
    else:
        guanyador = "Empat!"

    return render_template("resultat.html",
                           jugades=jugades,
                           punts_j1=punts_j1,
                           punts_j2=punts_j2,
                           guanyador=guanyador)

@app.route("/reset")
def reset():
    jugades["jugador1"] = None
    jugades["jugador2"] = None
    return redirect(url_for("menu"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
