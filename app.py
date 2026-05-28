import json
import os
import random
import secrets
import string
import time
from flask import (Flask, request, redirect, url_for, render_template,
                   jsonify, session, stream_with_context, Response)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# partides[codi] = {
#   "jugador1": {"xut": (h,d), "aturada": (h,d)} o None,
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


@app.route("/seleccio/<codi>", methods=["GET", "POST"])
def seleccio(codi):
    partida = partides.get(codi)
    if not partida:
        return redirect(url_for("menu"))

    if request.method == "POST":
        rol = request.form.get("rol")
        if rol in ("jugador1", "jugador2"):
            session["rol"] = rol
            session["codi"] = codi
            return redirect(url_for(rol, codi=codi))

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
    if session.get("rol") != "jugador1" or session.get("codi") != codi:
        return redirect(url_for("seleccio", codi=codi))
    return gestionar_jugada(codi, "jugador1")


@app.route("/jugador2/<codi>", methods=["GET", "POST"])
def jugador2(codi):
    if session.get("rol") != "jugador2" or session.get("codi") != codi:
        return redirect(url_for("seleccio", codi=codi))
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
        # Validar nonce per evitar resubmissió
        nonce_esperat = partida.pop(f"{jugador}_nonce", None)
        nonce_rebut = request.form.get("nonce")
        if nonce_rebut != nonce_esperat:
            error = "Aquest formulari ha caducat. Torna a obrir la pàgina."
        elif jugada is not None:
            error = "Ja has enviat la teva jugada en aquest set."
        else:
            # Validar que el set encara és l'actual
            try:
                set_esperat = int(request.form.get("set_esperat", 0))
            except (ValueError, TypeError):
                set_esperat = 0
            if set_esperat != sets_jugats + 1:
                error = "El set ha canviat. Torna a carregar la pàgina."
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
            partida.pop("jugador1_nonce", None)
            partida.pop("jugador2_nonce", None)

            # Anem a resultat per mostrar el resultat del set
            return redirect(url_for("resultat", codi=codi))

    # Generar nonce fresc per al formulari (només si es mostrarà el formulari)
    if jugada is None:
        nonce = secrets.token_hex(8)
        partida[f"{jugador}_nonce"] = nonce
    else:
        nonce = None

    return render_template(
        "jugador.html",
        jugador=jugador,
        alçades=ALÇADES,
        direccions=DIRECCIONS,
        jugada=jugada,
        error=error,
        codi=codi,
        set_actual=sets_jugats + 1,
        total_sets=total_sets,
        nonce=nonce
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
    session.pop("rol", None)
    session.pop("codi", None)
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


def build_estat(codi, partida):
    """Calcula l'estat actual de la partida."""
    sets = partida["sets"]
    total_sets = partida["total_sets"]
    j1_te_jugada = partida["jugador1"] is not None
    j2_te_jugada = partida["jugador2"] is not None

    vict_j1 = sum(1 for s in sets if s["guanyador"] == "jugador1")
    vict_j2 = sum(1 for s in sets if s["guanyador"] == "jugador2")

    finalitzat = len(sets) >= total_sets

    if finalitzat:
        guanyador_text = None
        if vict_j1 > vict_j2:
            guanyador_text = "Guanya el Jugador 1!"
        elif vict_j2 > vict_j1:
            guanyador_text = "Guanya el Jugador 2!"
        else:
            guanyador_text = "Empat final!"
    else:
        guanyador_text = None

    if finalitzat:
        esperant_jugador = False
        set_acabat = False
        estat_text = "Partida finalitzada!"
    elif j1_te_jugada and j2_te_jugada:
        esperant_jugador = False
        set_acabat = True
        estat_text = "Set completat!"
    elif j1_te_jugada or j2_te_jugada:
        esperant_jugador = True
        set_acabat = False
        qui = "Jugador 1" if j1_te_jugada else "Jugador 2"
        estat_text = f"{qui} ha enviat la seva jugada. Esperant l'altre..."
    elif len(sets) > 0:
        esperant_jugador = False
        set_acabat = True
        estat_text = f"Set {len(sets)} completat!"
    else:
        esperant_jugador = False
        set_acabat = False
        estat_text = "Esperant jugadors..."

    te_toca = False
    rol = session.get("rol")
    if not finalitzat and rol in ("jugador1", "jugador2") and session.get("codi") == codi:
        if partida[rol] is None:
            te_toca = True

    return {
        "sets": sets,
        "total_sets": total_sets,
        "vict_j1": vict_j1,
        "vict_j2": vict_j2,
        "finalitzat": finalitzat,
        "guanyador_text": guanyador_text,
        "esperant_jugador": esperant_jugador,
        "set_acabat": set_acabat,
        "estat_text": estat_text,
        "te_toca": te_toca
    }


@app.route("/api/estat/<codi>")
def api_estat(codi):
    partida = partides.get(codi)
    if not partida:
        return jsonify({"error": "Partida no trobada"}), 404
    return jsonify(build_estat(codi, partida))


@app.route("/api/stream/<codi>")
def api_stream(codi):
    def generate():
        last = None
        while True:
            partida = partides.get(codi)
            if not partida:
                yield "event: reload\ndata: {}\n\n"
                return
            state = build_estat(codi, partida)
            payload = json.dumps(state)
            if payload != last:
                yield f"event: update\ndata: {payload}\n\n"
                last = payload
            time.sleep(0.5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


if __name__ == "__main__":
    dev = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=5000, debug=dev, threaded=True)
