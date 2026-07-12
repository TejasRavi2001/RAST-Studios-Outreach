"""
outreach.py — Message templates + AI DM generator for RAST Studios.

80/20 rule:
  80% = proven generic core (value prop, who we are, soft CTA)
  20% = one personalised line based on lead data (name, area, category, rating)

Goal: sound like a human who noticed them, not a bot blasting everyone.
"""

import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_area(lead: dict) -> str:
    """Pull the first part of the address as the local area."""
    addr = lead.get("address", "")
    if not addr:
        return "Bangalore"
    parts = [p.strip() for p in addr.split(",")]
    return parts[0] if parts else "Bangalore"

def _personalization_line(lead: dict) -> str:
    """
    Generate the 20% personalisation hook.
    Uses whatever data we have — area, rating, category nuance.
    Keeps it one short sentence, observation not flattery.
    """
    name     = lead.get("name", "")
    area     = _extract_area(lead)
    category = (lead.get("category") or "").lower()
    rating   = lead.get("rating")
    website  = lead.get("website", "")

    # Priority: rating > area-specific > category-specific > generic
    if rating and float(rating) >= 4.5:
        return f"Came across {name} while looking at top-rated {category}s in {area} — clearly doing solid work."
    elif area and area.lower() not in ("bangalore", "bengaluru", ""):
        return f"Noticed {name} while looking at {category}s in {area}."
    elif "real estate" in category:
        return f"Saw {name} while researching agencies helping clients visualise properties before buying."
    elif "architect" in category:
        return f"Came across {name} while looking at architecture firms in Bangalore."
    elif "interior" in category:
        return f"Came across {name} while looking at interior studios in {area}."
    elif "builder" in category or "contractor" in category:
        return f"Saw {name} while researching builders working on residential projects in {area}."
    else:
        return f"Came across {name} while looking at design businesses in {area}."

# ── Templates ─────────────────────────────────────────────────────────────────
# Structure: [personalisation line] + [what we do] + [one value prop] + [soft CTA]
# Keep each under 100 words. No buzzwords. No "I hope this finds you well."

def _build_instagram(lead: dict) -> str:
    hook = _personalization_line(lead)
    return (
        f"{hook}\n\n"
        f"I run RAST Studios — we make 3D renders and walkthroughs for {(lead.get('category') or 'design').lower()}s in Bangalore. "
        f"Helps clients visualise the space before anything is built, which makes approvals a lot smoother.\n\n"
        f"Happy to share a couple of samples if it's relevant to what you're working on?"
    )

def _build_whatsapp(lead: dict) -> str:
    hook = _personalization_line(lead)
    name = lead.get("name", "")
    return (
        f"Hi, {hook}\n\n"
        f"I'm Tejas from RAST Studios, a 3D visualisation studio in Bangalore. "
        f"We work with {(lead.get('category') or 'design').lower()}s to create renders and walkthroughs "
        f"that help clients say yes faster.\n\n"
        f"Would it be ok if I sent over a few samples relevant to {name}'s work?"
    )

def _build_email(lead: dict) -> str:
    hook     = _personalization_line(lead)
    name     = lead.get("name", "")
    category = (lead.get("category") or "design business").lower()
    return (
        f"Subject: Quick question — 3D renders for {name}\n\n"
        f"Hi,\n\n"
        f"{hook}\n\n"
        f"I run RAST Studios, a Bangalore-based 3D visualisation studio. "
        f"We help {category}s present projects to clients with photorealistic renders and walkthroughs "
        f"before construction starts — the kind of visuals that make it easier for clients to commit.\n\n"
        f"I have a couple of samples that might be relevant to the type of projects {name} works on. "
        f"Worth a quick look?\n\n"
        f"Best,\n"
        f"Tejas\n"
        f"RAST Studios, Bangalore"
    )

def _build_linkedin(lead: dict) -> str:
    hook     = _personalization_line(lead)
    category = (lead.get("category") or "design").lower()
    return (
        f"{hook}\n\n"
        f"I run RAST Studios, a 3D architectural visualisation studio in Bangalore. "
        f"We create renders and walkthroughs that help {category}s present projects more clearly to clients — "
        f"particularly useful at the proposal and approval stage.\n\n"
        f"Happy to share some samples if useful."
    )

# ── Public interface ──────────────────────────────────────────────────────────

TEMPLATE_BUILDERS = {
    "Instagram DM": _build_instagram,
    "WhatsApp":     _build_whatsapp,
    "Email":        _build_email,
    "LinkedIn":     _build_linkedin,
}

def fill_template(template_name: str, lead: dict) -> str:
    builder = TEMPLATE_BUILDERS.get(template_name)
    if not builder:
        return ""
    return builder(lead)

def get_template_names() -> list[str]:
    return list(TEMPLATE_BUILDERS.keys())

def generate_dm(lead: dict) -> str:
    """
    AI-generated message via Anthropic API.
    Uses the 80/20 rule in the prompt — generic core + one personalisation hook.
    Falls back gracefully if no API key.
    """
    if not ANTHROPIC_API_KEY:
        return "ANTHROPIC_API_KEY not set. Using templates instead."

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        area     = _extract_area(lead)
        category = (lead.get("category") or "business").lower()
        rating   = lead.get("rating")
        name     = lead.get("name", "")

        prompt = f"""
You are writing a cold outreach DM for RAST Studios, a 3D architectural visualisation
studio in Bangalore run by Tejas (25yo founder).

Lead details:
- Business: {name}
- Category: {category}
- Area: {area}
- Rating: {rating or 'not available'}
- Website: {lead.get('website') or 'not available'}

STRICT RULES — follow all of them:
1. Structure: one personalisation line (20%) + generic core (80%)
2. Personalisation line: one specific observation about this business.
   Use area, category, or rating. Do NOT say "love your work" or "impressive portfolio".
   Say something factual: "Noticed [name] while looking at [category]s in [area]."
3. Generic core: who RAST Studios is, what we do (3D renders + walkthroughs),
   one value prop (helps clients visualise before construction, smoother approvals),
   soft CTA (share samples, no pressure).
4. Under 90 words total.
5. No em-dashes. No buzzwords. No "hope this finds you well".
6. Sound like a real person, not a sales email.
7. Do not use the word "stunning", "amazing", "incredible", "excited", "passionate".
8. End with a question, not a statement.

Write only the message. No subject line unless it is an email format.
"""
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    except Exception as e:
        return f"Error: {e}"


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample = {
        "name":     "Studio 7 Interiors",
        "category": "Interior Designer",
        "address":  "Indiranagar, Bangalore",
        "website":  "https://studio7.in",
        "rating":   4.7,
    }
    print("=== Instagram ===")
    print(fill_template("Instagram DM", sample))
    print("\n=== WhatsApp ===")
    print(fill_template("WhatsApp", sample))
    print("\n=== Email ===")
    print(fill_template("Email", sample))
    print("\n=== LinkedIn ===")
    print(fill_template("LinkedIn", sample))
