import random
import string
from flask import Flask, request, redirect, url_for, render_template, jsonify

app = Flask(__name__)

# partides[codi] = {
#   "jugador1": [{"xut": (h,d), "aturada": (h,d)}, ...],  # sets jugats
#   "jugador2": [{"xut": (h,d), "aturada": (h,d)}, ...],
#   "total_sets": int,
#   "resultats": None | [{"guanyador": ..., "punts_j1": int, "punts_j2": int}, ...]
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


def resoldre_resultats(j1_sets, j2_sets):
    resultats = []
    for i in range(min(len(j1_sets), len(j2_sets))):
        j1 = j1_sets[i]
        j2 = j2_sets[i]
        punts_j1 = calcular_punts(j2["xut"], j1["aturada"])
        punts_j2 = calcular_punts(j1["xut"], j2["aturada"])
        if punts_j1 > punts_j2:
            guanyador = "jugador1"
        elif punts_j2 > punts_j1:
            guanyador = "jugador2"
        else:
            guanyador = "empat"
        resultats.append({
            "guanyador": guanyador,
            "punts_j1": punts_j1,
            "punts_j2": punts_j2
        })
    return resultats


@app.route("/", methods=["GET", "POST"])
def menu():
    error = None
    if request.method == "POST":
        accio = request.form.get("accio")

        if accio == "crear":
            codi = generar_codi()
            total_sets = int(request.form["sets"])
            partides[codi] = {
                "jugador1": [],
                "jugador2": [],
                "total_sets": total_sets,
                "resultats": None
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
    total = partida["total_sets"]
    return render_template(
        "seleccio.html",
        codi=codi,
        sets_j1=len(partida["jugador1"]),
        sets_j2=len(partida["jugador2"]),
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

    total_sets = partida["total_sets"]
    sets_actual = len(partida[jugador])

    # Si ja ha jugat tots els sets, va al resultat
    if sets_actual >= total_sets:
        return redirect(url_for("resultat", codi=codi))

    if request.method == "POST":
        xut = (request.form["xut_alçada"], request.form["xut_direccio"])
        aturada = (request.form["aturada_alçada"], request.form["aturada_direccio"])
        partida[jugador].append({"xut": xut, "aturada": aturada})
        sets_actual += 1

        # Si ja ha acabat tots els sets, va al resultat
        if sets_actual >= total_sets:
            return redirect(url_for("resultat", codi=codi))

        return redirect(url_for(jugador, codi=codi))

    return render_template(
        "jugador.html",
        jugador=jugador,
        alçades=ALÇADES,
        direccions=DIRECCIONS,
        set_actual=sets_actual + 1,
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
            "jugador1": [],
            "jugador2": [],
            "total_sets": total_sets,
            "resultats": None
        }
    return redirect(url_for("seleccio", codi=codi))


@app.route("/api/estat/<codi>")
def api_estat(codi):
    partida = partides.get(codi)
    if not partida:
        return jsonify({"error": "Partida no trobada"}), 404

    total_sets = partida["total_sets"]
    j1_fet = len(partida["jugador1"]) >= total_sets
    j2_fet = len(partida["jugador2"]) >= total_sets

    if j1_fet and j2_fet and partida["resultats"] is None:
        partida["resultats"] = resoldre_resultats(partida["jugador1"], partida["jugador2"])

    sets = partida["resultats"] if partida["resultats"] is not None else []
    finalitzat = partida["resultats"] is not None

    vict_j1 = sum(1 for s in sets if s["guanyador"] == "jugador1") if sets else 0
    vict_j2 = sum(1 for s in sets if s["guanyador"] == "jugador2") if sets else 0

    if finalitzat:
        if vict_j1 > vict_j2:
            guanyador_text = "Guanya el Jugador 1!"
        elif vict_j2 > vict_j1:
            guanyador_text = "Guanya el Jugador 2!"
        else:
            guanyador_text = "Empat final!"
    else:
        guanyador_text = None

    if j1_fet and j2_fet:
        estat_text = "Partida finalitzada!"
    elif j1_fet:
        estat_text = "Jugador 1 ha acabat. Esperant Jugador 2..."
    elif j2_fet:
        estat_text = "Jugador 2 ha acabat. Esperant Jugador 1..."
    else:
        estat_text = "Tots dos jugadors estan jugant..."

    return jsonify({
        "sets": sets,
        "total_sets": total_sets,
        "vict_j1": vict_j1,
        "vict_j2": vict_j2,
        "finalitzat": finalitzat,
        "guanyador_text": guanyador_text,
        "estat_text": estat_text,
        "j1_fet": j1_fet,
        "j2_fet": j2_fet
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
