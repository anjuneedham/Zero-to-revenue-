"""Challenge outreach copy for BuildFlow and Agriloop (annual plan, two months free, one-on-one onboarding).
Deterministic templates: never invent a result, testimonial, user count or relationship about the prospect.
Anything only the owner knows is an explicit [OWNER TO FILL] placeholder, same rule everywhere in the app."""

FILL = "[OWNER TO FILL]"

PRODUCT = {
    "buildflow": {
        "name": "BuildFlow",
        "what": "an app that keeps your customers, jobs and photos in one place and gives you a public profile "
                "where new customers can find and contact you. Your leads stay yours, and it is one flat price.",
        "audience": "contractors and tradespeople",
    },
    "agriloop": {
        "name": "AgriLoop",
        "what": "a marketplace app that connects Caribbean farmers, buyers and agricultural communities, so you "
                "can list what you grow and reach buyers directly.",
        "audience": "farmers and agri-buyers",
    },
}


def _price(offer: dict) -> str:
    ps = offer.get("plans") or []
    if not ps:
        return f"{FILL} (annual price)"
    if len(ps) == 1:
        lab = "" if ps[0]["key"] == "standard" else ps[0]["label"] + " "
        return f"{lab}${ps[0]['annual_usd']:,.0f}" + ("/year" if lab else " for the year")
    return " or ".join(f"{p['label']} ${p['annual_usd']:,.0f}/year" for p in ps)


def _offer_line(venture: str, offer: dict) -> str:
    n = PRODUCT[venture]["name"]
    fm = int(offer.get("free_months") or 0)
    deal = f"That is 12 months for the price of {12 - fm} ({fm} months free). " if fm else ""
    return (f"I'm offering a founding {n} annual plan: {_price(offer)}. {deal}"
            "I set it up with you personally, one-on-one: a full onboarding, not a link and good luck.")


def channels() -> tuple:
    return ("email", "whatsapp", "instagram", "facebook", "call", "in_person", "other")


def draft(lead: dict, offer: dict, channel: str = "email") -> str:
    venture = lead.get("venture") if lead.get("venture") in PRODUCT else "buildflow"
    p = PRODUCT[venture]
    name = (lead.get("name") or "").strip() or "there"
    biz = (lead.get("business") or "").strip() or "your business"
    hook = f"{FILL} (one honest, specific sentence on why you're contacting {biz}: something true you noticed, not a template compliment)"
    offer_line = _offer_line(venture, offer)
    close = "Worth a 15-minute chat? Reply 'not now' and I'll leave it there."
    sign = f"{FILL} (your name and number)"
    if channel == "email":
        return "\n".join([
            f"Subject: {biz} + {p['name']}: set up together, first {int(offer.get('free_months') or 0)} months free"
            if offer.get("free_months") else f"Subject: {biz} + {p['name']}: set up together",
            "", f"Hi {name},", "", hook + ".", "",
            f"{p['name']} is {p['what']}", "", offer_line, "",
            f"{FILL} (if you have a live profile, screenshot or example to link, put it here; otherwise delete this line).", "",
            close, "", sign])
    short = [f"Hi {name}, {hook}.", f"{p['name']} is {p['what']}", offer_line, close, sign]
    return "\n\n".join(short)


def follow_up(lead: dict, offer: dict, channel: str = "email") -> str:
    venture = lead.get("venture") if lead.get("venture") in PRODUCT else "buildflow"
    p = PRODUCT[venture]
    name = (lead.get("name") or "").strip() or "there"
    body = (f"Hi {name}, following up once on {p['name']}. The founding annual offer ({_price(offer)}, "
            f"{int(offer.get('free_months') or 0)} months free, one-on-one onboarding) is still open for {lead.get('business') or 'you'}. "
            f"{FILL} (one new, true reason to reply: a question, an example, a slot you can offer). "
            "If it's not for you, just say 'not now' and I won't message again.")
    if channel == "email":
        return f"Subject: Re: {p['name']} for {lead.get('business') or 'your business'}\n\n{body}\n\n{FILL} (your name and number)"
    return body
