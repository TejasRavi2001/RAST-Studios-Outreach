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
    Returns a complete sentence starting with "Came across [business]..."
    """
    name     = lead.get("name", "")
    area     = _extract_area(lead)
    category = (lead.get("category") or "").lower()
    rating   = lead.get("rating")

    # Build the base: "Came across {name} while looking at {category}s in {area}."
    if category:
        cat_plural = category + "s"  # quick and dirty plural
        base = f"Came across {name} while looking at {cat_plural} in {area}"
    else:
        base = f"Came across {name} while looking at design businesses in {area}"

    # Add rating-based hook
    if rating and float(rating) >= 4.5:
        return base + f", you are clearly doing solid work."
    elif rating and float(rating) >= 4.0:
        return base + f", well rated in the area."
    else:
        return base + "."

# ── Templates ─────────────────────────────────────────────────────────────────
# Each template follows: [personalisation line] + [what we do] + [value prop] + [CTA]
# No buzzwords, no flattery.

def _build_instagram(lead: dict) -> str:
    hook = _personalization_line(lead)
    cat  = (lead.get("category") or "design business").lower()
    return (
        f"{hook}\n\n"
        f"We run RAST Studios — we make 3D renders and walkthroughs for {cat}s in Bangalore. "
        f"Helps clients visualise the space before anything is built, which makes approvals a lot smoother.\n\n"
        f"Happy to share a couple of samples if it's relevant to what you're working on?"
    )

def _build_whatsapp(lead: dict) -> str:
    hook = _personalization_line(lead)
    cat  = (lead.get("category") or "design business").lower()
    return (
        f"Hi, {hook}\n\n"
        f"We run RAST Studios — we make 3D renders and walkthroughs for {cat}s in Bangalore. "
        f"Helps clients visualise the space before anything is built, which makes approvals a lot smoother.\n\n"
        f"Happy to share a couple of samples if it's relevant to what you're working on?"
    )

def _build_email(lead: dict) -> str:
    hook = _personalization_line(lead)
    name = lead.get("name", "")
    cat  = (lead.get("category") or "design business").lower()
    return (
        f"Subject: Quick question — 3D renders for {name}\n\n"
        f"Hi,\n\n"
        f"{hook}\n\n"
        f"We run RAST Studios, a Bangalore-based 3D visualisation studio. "
        f"We help {cat}s present projects to clients with photorealistic renders and walkthroughs "
        f"before construction starts — the kind of visuals that make it easier for clients to commit.\n\n"
        f"I have a couple of samples that might be relevant to the type of projects {name} works on. "
        f"Worth a quick look?\n\n"
        f"Best,\n"
        f"Tejas\n"
        f"RAST Studios, Bangalore"
    )

def _build_linkedin(lead: dict) -> str:
    hook = _personalization_line(lead)
    cat  = (lead.get("category") or "design").lower()
    return (
        f"{hook}\n\n"
        f"We run RAST Studios, a 3D architectural visualisation studio in Bangalore. "
        f"We create renders and walkthroughs that help {cat}s present projects more clearly to clients — "
        f"particularly useful at the proposal and approval stage.\n\n"
        f"Happy to share some samples if useful."
    )

def _build_overflow(lead: dict) -> str:
    """
    Premium template for high‑end leads – pitches Unreal Engine, VR walkthroughs,
    and overflow capacity for busy studios.
    """
    hook = _personalization_line(lead)
    name = lead.get("name", "")
    cat  = (lead.get("category") or "design business").lower()
    return (
        f"{hook}\n\n"
        f"We run RAST Studios — we specialise in high‑end 3D visualisation using Unreal Engine "
        f"for real‑time renders, VR walkthroughs, and cinematics. We also take on overflow work "
        f"when your team is at capacity.\n\n"
        f"If you ever need extra render support or want to explore VR presentations for your clients, "
        f"I'd love to show you what we can do.\n\n"
        f"Let me know if a quick call makes sense?"
    )

# ── Public interface ──────────────────────────────────────────────────────────

TEMPLATE_BUILDERS = {
    "Instagram DM": _build_instagram,
    "WhatsApp":     _build_whatsapp,
    "Email":        _build_email,
    "LinkedIn":     _build_linkedin,
    "Overflow / VR": _build_overflow,
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
2. Personalisation line: start with "Came across [business] while looking at [category]s in [area]" 
   and optionally add ", you are clearly doing solid work" if rating >= 4.5.
3. Generic core: "We run RAST Studios — we make 3D renders and walkthroughs for [category]s in Bangalore. 
   Helps clients visualise the space before anything is built, which makes approvals a lot smoother."
4. CTA: "Happy to share a couple of samples if it's relevant to what you're working on?"
5. Under 90 words total.
6. No em-dashes. No buzzwords. No "hope this finds you well".
7. Sound like a real person, not a sales email.
8. Do not use the word "stunning", "amazing", "incredible", "excited", "passionate".
9. End with a question.

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
        "name":     "New Door Venture",
        "category": "Real Estate Agent",
        "address":  "Indiranagar, Bangalore",
        "website":  "https://newdoor.in",
        "rating":   4.7,
    }
    print("=== Instagram DM ===")
    print(fill_template("Instagram DM", sample))
    print("\n=== WhatsApp ===")
    print(fill_template("WhatsApp", sample))
    print("\n=== Email ===")
    print(fill_template("Email", sample))
    print("\n=== LinkedIn ===")
    print(fill_template("LinkedIn", sample))
    print("\n=== Overflow / VR ===")
    print(fill_template("Overflow / VR", sample))
