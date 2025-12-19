import random
import string
from flask import Flask, request, redirect, url_for, render_template, jsonify

app = Flask(__name__)

# partides[codi] = {
#   "jugador1": {"xut": (...), "aturada": (...)} o None,
#   "jugador2": {...} o None,
#   "sets": [ {"guanyador": "jugador1"/"jugador2"/"empat",
#              "punts_j1": int,
#              "punts_j2": int} ],
#   "total_sets": int
# }

partides = {}

ALÇADES = ["baixa", "mitjana", "alta"]
DIRECCIONS = ["esquerra", "centre", "dreta"]


def generar_codi(longitud=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=longitud))


def calcular_punts(xut, aturada):
    punts = 0
    if xut[0] == aturada[0]:
        punts += 1
    if xut[1] == aturada[1]:
        punts += 1
    return punts


@app.route("/", methods=["GET", "POST"])
def menu():
    error = None
    if request.method == "POST":
        accio = request.form.get("accio")

        if accio == "crear":
            codi = generar_codi()
            total_sets = int(request.form["sets"])
            partides[codi] = {
                "jugador1": None,
                "jugador2": None,
                "sets": [],
                "total_sets": total_sets
            }
            return redirect(url_for("seleccio", codi=codi))

        if accio == "unir":
            codi = request.form["codi"].upper()
            if codi not in partides:
                error = "Aquest codi de partida no existeix."
            else:
                return redirect(url_for("seleccio", codi=codi))

    return render_template("menu.html", error=error)


@app.route("/seleccio/<codi>")
def seleccio(codi):
    partida = partides.get(codi)
    if not partida:
        return redirect(url_for("menu"))
    sets_jugats = len(partida["sets"])
    total = partida["total_sets"]
    return render_template(
        "seleccio.html",
        codi=codi,
        sets_jugats=sets_jugats,
        total_sets=total
    )


@app.route("/jugador1/<codi>", methods=["GET", "POST"])
def jugador1(codi):
    return gestionar_jugada(codi, "jugador1")


@app.route("/jugador2/<codi>", methods=["GET", "POST"])
def jugador2(codi):
    return gestionar_jugada(codi, "jugador2")


def gestionar_jugada(codi, jugador):
    partida = partides.get(codi)
    if not partida:
        return redirect(url_for("menu"))

    error = None
    jugada = partida[jugador]
    sets_jugats = len(partida["sets"])
    total_sets = partida["total_sets"]

    # Si ja s'han jugat tots els sets, anem directament al resultat
    if sets_jugats >= total_sets:
        return redirect(url_for("resultat", codi=codi))

    if request.method == "POST":
        if jugada is not None:
            error = "Ja has enviat la teva jugada en aquest set."
        else:
            xut = (request.form["xut_alçada"], request.form["xut_direccio"])
            aturada = (request.form["aturada_alçada"], request.form["aturada_direccio"])
            partida[jugador] = {"xut": xut, "aturada": aturada}
            jugada = partida[jugador]

        # Si tots dos han jugat, tanquem el set
        if partida["jugador1"] and partida["jugador2"]:
            j1 = partida["jugador1"]
            j2 = partida["jugador2"]

            punts_j1 = calcular_punts(j2["xut"], j1["aturada"])
            punts_j2 = calcular_punts(j1["xut"], j2["aturada"])

            if punts_j1 > punts_j2:
                guanyador = "jugador1"
            elif punts_j2 > punts_j1:
                guanyador = "jugador2"
            else:
                guanyador = "empat"

            partida["sets"].append({
                "guanyador": guanyador,
                "punts_j1": punts_j1,
                "punts_j2": punts_j2
            })

            # Preparem següent set
            partida["jugador1"] = None
            partida["jugador2"] = None

            # Si hem arribat al límit de sets, anem a resultat
            if len(partida["sets"]) >= partida["total_sets"]:
                return redirect(url_for("resultat", codi=codi))

            # Sinó, el jugador pot seguir amb el següent set: redirigim
            return redirect(url_for(jugador, codi=codi))

    return render_template(
        "jugador.html",
        jugador=jugador,
        alçades=ALÇADES,
        direccions=DIRECCIONS,
        jugada=jugada,
        error=error,
        codi=codi,
        set_actual=sets_jugats + 1,
        total_sets=total_sets
    )


@app.route("/resultat/<codi>")
def resultat(codi):
    partida = partides.get(codi)
    if not partida:
        return redirect(url_for("menu"))

    # La UI principal del marcador ara s'actualitza via JS amb /api/estat
    return render_template("resultat.html", codi=codi)


@app.route("/reset/<codi>")
def reset(codi):
    partida = partides.get(codi)
    if partida:
        total_sets = partida["total_sets"]
        partides[codi] = {
            "jugador1": None,
            "jugador2": None,
            "sets": [],
            "total_sets": total_sets
        }
    return redirect(url_for("seleccio", codi=codi))


@app.route("/api/estat/<codi>")
def api_estat(codi):
    partida = partides.get(codi)
    if not partida:
        return jsonify({"error": "Partida no trobada"}), 404

    sets = partida["sets"]
    total_sets = partida["total_sets"]

    vict_j1 = sum(1 for s in sets if s["guanyador"] == "jugador1")
    vict_j2 = sum(1 for s in sets if s["guanyador"] == "jugador2")

    if len(sets) < total_sets:
        finalitzat = False
        guanyador_text = None
    else:
        finalitzat = True
        if vict_j1 > vict_j2:
            guanyador_text = "Guanya el Jugador 1!"
        elif vict_j2 > vict_j1:
            guanyador_text = "Guanya el Jugador 2!"
        else:
            guanyador_text = "Empat final!"

    return jsonify({
        "sets": sets,
        "total_sets": total_sets,
        "vict_j1": vict_j1,
        "vict_j2": vict_j2,
        "finalitzat": finalitzat,
        "guanyador_text": guanyador_text
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
