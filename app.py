"""
app.py — RAST Studios Lead Dashboard (Flask + HTMX)
Run with: python app.py
Open:     http://localhost:5000
"""

import os
from datetime import date
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from database import (
    init_db, fetch_all_leads, fetch_lead, fetch_daily_queue,
    fetch_due_followups, update_field, delete_lead, get_stats
)
from outreach import fill_template, get_template_names, generate_dm

load_dotenv()
app = Flask(__name__)
init_db()

STATUSES  = ["Not Contacted", "Contacted", "Converted", "Not Interested"]
CHANNELS  = ["", "Instagram", "WhatsApp", "Email", "LinkedIn"]
REPLIED   = ["", "Yes", "No", "Pending"]
CATEGORIES = ["Interior Designer", "Real Estate Agent", "Builder", "Architect"]

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    q        = request.args.get("q", "").lower()
    category = request.args.get("category", "")
    status   = request.args.get("status", "")
    tab      = request.args.get("tab", "leads")

    all_leads = fetch_all_leads()
    filtered  = all_leads

    if q:
        filtered = [l for l in filtered if
            q in l["name"].lower() or
            q in (l["address"] or "").lower() or
            q in (l["instagram"] or "").lower()]
    if category:
        filtered = [l for l in filtered if l["category"] == category]
    if status:
        filtered = [l for l in filtered if l["status"] == status]

    stats     = get_stats()
    due       = fetch_due_followups()
    queue     = fetch_daily_queue()
    templates = get_template_names()

    return render_template("index.html",
        leads=filtered,
        all_leads=all_leads,
        stats=stats,
        due=due,
        queue=queue,
        templates=templates,
        statuses=STATUSES,
        channels=CHANNELS,
        replied_opts=REPLIED,
        categories=CATEGORIES,
        q=request.args.get("q", ""),
        sel_category=category,
        sel_status=status,
        tab=tab,
        today=date.today().isoformat(),
    )

# ── Inline field update (HTMX) ────────────────────────────────────────────────

@app.route("/lead/<int:lead_id>/update", methods=["POST"])
def update_lead(lead_id):
    field = request.form.get("field")
    value = request.form.get("value", "")
    try:
        update_field(lead_id, field, value)
        lead = fetch_lead(lead_id)
        # Return just the updated cell HTML
        return _cell_html(lead, field)
    except Exception as e:
        return f'<span style="color:red">Error: {e}</span>', 400

# ── Delete ────────────────────────────────────────────────────────────────────

@app.route("/lead/<int:lead_id>/delete", methods=["POST"])
def remove_lead(lead_id):
    delete_lead(lead_id)
    return ""   # HTMX removes the row

# ── Template message API ──────────────────────────────────────────────────────

@app.route("/lead/<int:lead_id>/message")
def get_message(lead_id):
    template_name = request.args.get("template", "Instagram DM")
    lead = fetch_lead(lead_id)
    msg  = fill_template(template_name, lead)
    return jsonify({"message": msg, "name": lead.get("name", "")})

# ── AI DM API ─────────────────────────────────────────────────────────────────

@app.route("/lead/<int:lead_id>/ai-message")
def ai_message(lead_id):
    lead = fetch_lead(lead_id)
    msg  = generate_dm(lead)
    return jsonify({"message": msg})

# ── Export CSV ────────────────────────────────────────────────────────────────

@app.route("/export")
def export_csv():
    import csv, io
    leads = fetch_all_leads()
    output = io.StringIO()
    fields = ["name","category","address","phone","website","rating",
              "status","channel","replied","last_contacted","follow_up_date",
              "instagram","notes"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(leads)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=rast_leads.csv"}
    )

# ── Cell HTML helper ──────────────────────────────────────────────────────────

def _cell_html(lead: dict, field: str) -> str:
    """Return rendered HTML for a single updated cell."""
    from flask import render_template_string
    return render_template_string(
        "{{ lead[field] | e }}", lead=lead, field=field
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

# ── Jinja filter: today's date for overdue highlighting ───────────────────────
from datetime import date as _date

@app.template_global()
def today():
    return _date.today().isoformat()
