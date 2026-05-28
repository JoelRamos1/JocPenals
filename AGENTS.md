# JocPenals — Agent guide

## Project

- **Flask** (Python 3.14) penalty shootout duel game.
- All game state is **in-memory** (`partides` dict in `app.py`); restarting the server loses all games.
- UI language: Catalan.
- Only dependency: `Flask`. No `requirements.txt` — install with `pip install flask`.

## Commands

```bash
venv\Scripts\python app.py          # run dev server at http://localhost:5000
venv\Scripts\python -m flask run    # alternative if FLASK_APP=app.py is set
```

- Dev server runs on `0.0.0.0:5000` with `debug=True`.

## Entry points

| Route | Purpose |
|---|---|
| `GET /` | Menu: create or join a game |
| `GET /seleccio/<codi>` | Choose player slot (Jugador 1 / Jugador 2) |
| `GET,POST /jugador1/<codi>` | Player 1: submit shot + save |
| `GET,POST /jugador2/<codi>` | Player 2: submit shot + save |
| `GET /resultat/<codi>` | Live scoreboard (polls `/api/estat/<codi>` every 1.5s) |
| `GET /reset/<codi>` | Reset game, keep same code |
| `GET /api/estat/<codi>` | JSON game state |

## Repository structure

```
app.py              # single-file Flask app
templates/          # 4 Jinja2 templates
static/style.css    # stylesheet
venv/               # committed virtual env (gitignored internally)
AGENTS.md
README.md
```

## Notable

- No tests, no CI, no linters, no formatters, no typechecking.
- Game codes are 6-char alphanumeric (uppercase + digits), generated randomly.
- Scoring: both height and direction must match the opponent's shot to earn points.
- No database — all data lost on server restart.
- The `resultat.html` page uses `setInterval(refrescarMarcador, 1500)` for live updates.
- **Game flow**: each player plays all their sets sequentially (no alternating). Results are calculated only after both players finish all sets.
