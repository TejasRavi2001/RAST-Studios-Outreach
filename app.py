"""
app.py – RAST Studios Lead Dashboard (Flask + HTMX)
Run with: python app.py
Open:     http://localhost:5000
"""

import os
from datetime import date
from flask import Flask, render_template, request, jsonify, session, Response
from dotenv import load_dotenv
from database import (
    init_db, fetch_all_leads, fetch_lead, fetch_daily_queue,
    fetch_due_followups, update_field, delete_lead, get_stats, insert_lead
)
from outreach import fill_template, get_template_names, generate_dm

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
init_db()

STATUSES  = ["Not Contacted", "Contacted", "Converted", "Not Interested"]
CHANNELS  = ["", "Instagram", "WhatsApp", "Email", "LinkedIn"]
REPLIED   = ["", "Yes", "No", "Pending"]
CATEGORIES = ["Interior Designer", "Real Estate Agent", "Builder", "Architect"]

# ── Helper for undo ──
def get_old_value(lead_id: int, field: str):
    lead = fetch_lead(lead_id)
    return lead.get(field, '')

# ── Routes ──
@app.route("/")
def index():
    q        = request.args.get("q", "").lower()
    category = request.args.get("category", "")
    status   = request.args.get("status", "")
    tab      = request.args.get("tab", "leads")

    all_leads = fetch_all_leads()
    filtered = all_leads

    if tab == 'contacted':
        filtered = [l for l in filtered if l['status'] == 'Contacted']
        status = ''
    elif tab == 'leads' and status:
        filtered = [l for l in filtered if l['status'] == status]

    if q:
        filtered = [l for l in filtered if
            q in l["name"].lower() or
            q in (l["address"] or "").lower() or
            q in (l["instagram"] or "").lower()]
    if category:
        filtered = [l for l in filtered if l["category"] == category]

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

# ── Update (with undo) ──
@app.route("/lead/<int:lead_id>/update", methods=["POST"])
def update_lead(lead_id):
    field = request.form.get("field")
    value = request.form.get("value", "")
    try:
        old_value = get_old_value(lead_id, field)
        update_field(lead_id, field, value)
        if 'undo_stack' not in session:
            session['undo_stack'] = []
        session['undo_stack'].append({
            'lead_id': lead_id,
            'field': field,
            'old_value': old_value,
            'new_value': value
        })
        if len(session['undo_stack']) > 50:
            session['undo_stack'] = session['undo_stack'][-50:]
        session.modified = True
        return _cell_html(fetch_lead(lead_id), field)
    except Exception as e:
        return f'<span style="color:red">Error: {e}</span>', 400

@app.route("/undo", methods=["POST"])
def undo():
    stack = session.get('undo_stack', [])
    if not stack:
        return jsonify({'status': 'empty', 'message': 'Nothing to undo'})
    action = stack.pop()
    update_field(action['lead_id'], action['field'], action['old_value'])
    session['undo_stack'] = stack
    session.modified = True
    return jsonify({'status': 'ok'})

# ── Delete ──
@app.route("/lead/<int:lead_id>/delete", methods=["POST"])
def remove_lead(lead_id):
    delete_lead(lead_id)
    return ""

# ── Templates ──
@app.route("/lead/<int:lead_id>/message")
def get_message(lead_id):
    template_name = request.args.get("template", "Instagram DM")
    lead = fetch_lead(lead_id)
    msg = fill_template(template_name, lead)
    return jsonify({"message": msg, "name": lead.get("name", "")})

@app.route("/lead/<int:lead_id>/ai-message")
def ai_message(lead_id):
    lead = fetch_lead(lead_id)
    msg = generate_dm(lead)
    return jsonify({"message": msg})

# ── Export CSV ──
@app.route("/export")
def export_csv():
    import csv, io
    leads = fetch_all_leads()
    output = io.StringIO()
    fields = ["place_id","name","category","address","phone","website","rating",
              "status","channel","replied","last_contacted","follow_up_date",
              "instagram","notes"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(leads)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=rast_leads.csv"}
    )

# ── Import CSV (NOW RETURNS JSON) ──
@app.route("/import-csv", methods=["POST"])
def import_csv():
    import csv, io
    file = request.files.get("file")
    if not file:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    try:
        reader = csv.DictReader(io.StringIO(file.stream.read().decode("utf-8")))
        count = 0
        for row in reader:
            insert_lead({
                "place_id": row.get('place_id', f'import_{row.get("name", count)}'),
                "name": row['name'],
                "category": row.get('category', ''),
                "address": row.get('address', ''),
                "phone": row.get('phone', ''),
                "website": row.get('website', ''),
                "rating": float(row['rating']) if row.get('rating') else None,
                "instagram": row.get('instagram', ''),
                "status": row.get('status', 'Not Contacted'),
                "notes": row.get('notes', ''),
                "last_contacted": row.get('last_contacted', ''),
                "follow_up_date": row.get('follow_up_date', ''),
                "channel": row.get('channel', ''),
                "replied": row.get('replied', ''),
            })
            count += 1
        return jsonify({"success": True, "message": f"✅ Imported {count} leads!", "count": count})
    except Exception as e:
        return jsonify({"success": False, "message": f"❌ Import failed: {str(e)}"}), 500

# ── Helper ──
def _cell_html(lead: dict, field: str) -> str:
    from flask import render_template_string
    return render_template_string(
        "{{ lead[field] | e }}", lead=lead, field=field
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

# ── Jinja global ──
from datetime import date as _date
@app.template_global()
def today():
    return _date.today().isoformat()
