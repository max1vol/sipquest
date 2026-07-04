#!/usr/bin/env python3
from pathlib import Path
import html
import shutil
import subprocess
import tempfile
import textwrap


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SLIDES = ROOT / "slides"
SVGS = ROOT / "svg"
EXPORTS = ROOT / "exports"
W, H = 1920, 1080


def esc(value):
    return html.escape(str(value), quote=True)


def wrap_lines(text, width_px, size, max_lines=None):
    approx_chars = max(8, int(width_px / (size * 0.53)))
    lines = []
    for para in str(text).split("\n"):
        if not para.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(para, approx_chars, break_long_words=False))
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(". ") + "..."
    return lines


def text(x, y, body, size=42, width=700, fill="#12213f", weight=500,
         leading=1.18, anchor="start", opacity=1, max_lines=None):
    lines = wrap_lines(body, width, size, max_lines=max_lines)
    spans = []
    for i, line in enumerate(lines):
        dy = "0" if i == 0 else f"{size * leading:.1f}"
        spans.append(
            f"<tspan x='{x}' dy='{dy}'>{esc(line)}</tspan>"
        )
    return (
        f"<text x='{x}' y='{y}' fill='{fill}' font-family='Inter, Arial, sans-serif' "
        f"font-size='{size}' font-weight='{weight}' text-anchor='{anchor}' "
        f"opacity='{opacity}'>{''.join(spans)}</text>"
    )


def pill(x, y, label, fill="#ffffff", stroke="#d9e2f2", fg="#12213f", w=None):
    w = w or max(160, len(label) * 15 + 52)
    return (
        f"<rect x='{x}' y='{y}' width='{w}' height='54' rx='27' fill='{fill}' "
        f"stroke='{stroke}' stroke-width='2'/>"
        + text(x + w / 2, y + 35, label, size=22, width=w - 24, fill=fg,
               weight=700, anchor="middle")
    )


def card(x, y, w, h, fill="#ffffff", stroke="#d9e2f2", opacity=1):
    return (
        f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='26' fill='{fill}' "
        f"stroke='{stroke}' stroke-width='2' opacity='{opacity}'/>"
    )


def image(path, x, y, w, h, opacity=1, fit="slice"):
    mode = "xMidYMid slice" if fit == "slice" else "xMidYMid meet"
    rel = (ASSETS / path).resolve()
    return (
        f"<image href='{esc(rel.as_posix())}' x='{x}' y='{y}' width='{w}' "
        f"height='{h}' preserveAspectRatio='{mode}' opacity='{opacity}'/>"
    )


def circle_label(cx, cy, r, label, fill="#ffcf42", fg="#12213f"):
    return (
        f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='{fill}'/>"
        + text(cx, cy + r * 0.33, label, size=int(r * 0.9), width=r * 2,
               fill=fg, weight=800, anchor="middle")
    )


def qr_pattern(x, y, size=190):
    cell = size / 7
    blocks = {
        (0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2),
        (4, 0), (6, 0), (5, 1), (3, 2), (6, 2), (1, 4), (3, 4), (4, 4),
        (6, 4), (0, 5), (2, 5), (5, 5), (1, 6), (3, 6), (4, 6), (6, 6)
    }
    out = [
        f"<rect x='{x}' y='{y}' width='{size}' height='{size}' rx='18' fill='#fff' stroke='#d9e2f2' stroke-width='2'/>"
    ]
    for col, row in blocks:
        out.append(
            f"<rect x='{x + col * cell + 5}' y='{y + row * cell + 5}' "
            f"width='{cell - 9}' height='{cell - 9}' rx='4' fill='#12213f'/>"
        )
    return "".join(out)


def frame(content, bg="#f5f8ff"):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="sunrise" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fff8dd"/>
    <stop offset="0.52" stop-color="#eef8ff"/>
    <stop offset="1" stop-color="#f6f1ff"/>
  </linearGradient>
  <linearGradient id="darkGrad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#071226"/>
    <stop offset="1" stop-color="#12213f"/>
  </linearGradient>
  <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#ffe977"/>
    <stop offset="1" stop-color="#f69c2d"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="{bg}"/>
{content}
</svg>
"""


def footer(slide_no, dark=False):
    fill = "#ffffff" if dark else "#5c6a85"
    return (
        text(96, 1010, "SipQuest", size=24, width=300, fill=fill, weight=800)
        + text(1810, 1010, f"{slide_no:02d}/12", size=24, width=120, fill=fill,
               weight=700, anchor="end")
    )


def bullets(x, y, items, width=720, color="#243552", size=34, gap=30):
    out = []
    cur_y = y
    colors = ["#ffcf42", "#ff8d3a", "#55b6ff", "#a16eff", "#3ed6a2"]
    for i, item in enumerate(items):
        out.append(f"<circle cx='{x}' cy='{cur_y - 10}' r='9' fill='{colors[i % len(colors)]}'/>")
        lines = wrap_lines(item, width, size)
        out.append(text(x + 34, cur_y, "\n".join(lines), size=size, width=width,
                        fill=color, weight=520))
        cur_y += max(1, len(lines)) * size * 1.18 + gap
    return "".join(out)


def numbered_steps(items, x=145, y=260, w=500, h=132):
    out = []
    for i, (title, body, color) in enumerate(items, 1):
        sy = y + (i - 1) * (h + 26)
        out.append(card(x, sy, w, h, fill="#ffffff", stroke="#dce5f5"))
        out.append(circle_label(x + 58, sy + 66, 34, str(i), fill=color))
        out.append(text(x + 112, sy + 54, title, size=28, width=w - 150,
                        fill="#12213f", weight=800, max_lines=1))
        out.append(text(x + 112, sy + 91, body, size=22, width=w - 150,
                        fill="#5c6a85", weight=500, max_lines=2))
    return "".join(out)


def slide_01():
    c = image("product-hero.png", 820, 0, 1100, H)
    c += "<rect width='920' height='1080' fill='url(#darkGrad)'/>"
    c += pill(96, 88, "UK AI Agent Hackathon EP5 x Conduct", fill="#ffffff22",
              stroke="#ffffff44", fg="#ffffff", w=520)
    c += text(96, 295, "SipQuest", size=118, width=700, fill="#ffffff", weight=900)
    c += text(100, 385, "Collectible drinks where the drink disappears, but the collection remains.",
              size=46, width=690, fill="#f4f8ff", weight=650, leading=1.12)
    c += text(100, 562, "Teen-safe flavor discovery now. Optional 18+ collector proof later.",
              size=30, width=650, fill="#d9e9ff", weight=520)
    c += pill(96, 688, "FlavourDex", fill="#ffcf42", stroke="#ffcf42", fg="#12213f", w=220)
    c += pill(338, 688, "AI-generated art", fill="#55b6ff", stroke="#55b6ff", fg="#071226", w=282)
    c += pill(642, 688, "Quiet proof-of-claim", fill="#ffffff20", stroke="#ffffff45", fg="#ffffff", w=302)
    c += footer(1, dark=True)
    return frame(c, bg="#071226")


def slide_02():
    c = "<rect width='1920' height='1080' fill='url(#sunrise)'/>"
    c += text(96, 140, "The Problem", size=68, width=780, fill="#12213f", weight=900)
    c += text(96, 207, "Teen collecting has moved digital, but the products around it are stuck.",
              size=32, width=840, fill="#52627c", weight=520)
    items = [
        ("Physical clutter", "Cards and merch are fun to own, then hard to store."),
        ("Status is social", "Teen collectors want proof, progress, and comparison with friends."),
        ("Drinks are forgettable", "Most beverages vanish after one purchase and leave no memory."),
        ("Crypto feels unsafe", "NFT language sounds speculative, adult, and risky for minors."),
    ]
    xs = [96, 548, 1000, 1452]
    colors = ["#ffcf42", "#ff8d3a", "#55b6ff", "#a16eff"]
    for idx, (title, body) in enumerate(items):
        c += card(xs[idx], 350, 370, 430, fill="#ffffff", stroke="#dce5f5")
        c += circle_label(xs[idx] + 68, 430, 38, str(idx + 1), fill=colors[idx])
        c += text(xs[idx] + 46, 530, title, size=32, width=285, fill="#12213f", weight=850)
        c += text(xs[idx] + 46, 604, body, size=28, width=285, fill="#52627c", weight=520, leading=1.15)
    c += text(96, 890, "Pitch insight: build a collectible that does not create physical clutter or speculative pressure.",
              size=34, width=1100, fill="#12213f", weight=780)
    c += footer(2)
    return frame(c)


def slide_03():
    c = "<rect width='1920' height='1080' fill='#ffffff'/>"
    c += text(96, 136, "The Solution", size=66, width=760, fill="#12213f", weight=900)
    c += text(96, 210, "SipQuest turns every non-alcoholic flavor into a collectible unlock.",
              size=34, width=780, fill="#52627c", weight=540)
    c += bullets(118, 350, [
        "Every can belongs to a flavor universe.",
        "Hidden QR codes unlock owned flavors in FlavourDex.",
        "Sets, badges, voting, friend comparison, and AI flavor art create the loop.",
        "Blockchain is only used as quiet proof for limited claims, not as the headline."
    ], width=760, size=32)
    c += card(96, 820, 760, 115, fill="#fff8dd", stroke="#f2d780")
    c += text(130, 870, "Core line", size=24, width=220, fill="#8a6400", weight=800)
    c += text(130, 912, "Taste it once. Keep the proof forever.", size=34,
              width=650, fill="#12213f", weight=850)
    c += card(1045, 130, 760, 800, fill="#f8fbff", stroke="#dce5f5")
    c += image("flavor-cards.png", 1080, 170, 690, 388, fit="meet")
    c += text(1090, 650, "Example universe", size=28, width=500, fill="#52627c", weight=800)
    c += pill(1090, 700, "Lemon Bolt", fill="#ffcf42", stroke="#ffcf42", fg="#12213f", w=230)
    c += pill(1345, 700, "Mango Sun", fill="#ff8d3a", stroke="#ff8d3a", fg="#12213f", w=230)
    c += pill(1090, 780, "Winter Berry", fill="#55b6ff", stroke="#55b6ff", fg="#071226", w=260)
    c += pill(1380, 780, "Gold Lychee", fill="#f6a92d", stroke="#f6a92d", fg="#071226", w=260)
    c += footer(3)
    return frame(c)


def slide_04():
    c = "<rect width='1920' height='1080' fill='#f5f8ff'/>"
    c += image("product-hero.png", 0, 0, W, H)
    c += card(72, 56, 1170, 185, fill="#ffffff", stroke="#dce5f5")
    c += text(96, 130, "Why Drinks Work", size=66, width=900, fill="#12213f", weight=900)
    c += text(96, 198, "A drink is temporary, social, repeatable, and tied to taste.",
              size=32, width=870, fill="#52627c", weight=520)
    items = [
        ("Consumed, not stored", "No piles of cards, boxes, or merch."),
        ("Real-world ritual", "Buying, peeling, scanning, and sharing feels physical."),
        ("Repeat purchase loop", "New drops create new reasons to try again."),
        ("Taste creates memory", "A flavor is easier to remember than another generic badge."),
        ("Seasonal by nature", "Summer citrus, winter berry, launch batches, local drops.")
    ]
    x, y = 96, 320
    for i, (title, body) in enumerate(items):
        col = i % 3
        row = i // 3
        cx = x + col * 575
        cy = y + row * 280
        c += card(cx, cy, 500, 220, fill="#ffffff", stroke="#dce5f5")
        c += circle_label(cx + 58, cy + 70, 34, title[0], fill=["#ffcf42", "#ff8d3a", "#55b6ff", "#a16eff", "#3ed6a2"][i])
        c += text(cx + 112, cy + 70, title, size=31, width=340, fill="#12213f", weight=850)
        c += text(cx + 46, cy + 145, body, size=25, width=410, fill="#52627c", weight=520)
    c += footer(4)
    return frame(c)


def slide_05():
    c = image("qr-claim.png", 760, 0, 1160, H)
    c += "<rect width='920' height='1080' fill='#ffffff'/>"
    c += text(96, 126, "QR Claim System", size=62, width=760, fill="#12213f", weight=900)
    c += text(96, 194, "The physical can creates the moment. The code creates the memory.",
              size=32, width=720, fill="#52627c", weight=520)
    c += numbered_steps([
        ("Buy", "Choose a flavor or drop.", "#ffcf42"),
        ("Reveal", "Peel label, cap, or scratch panel.", "#ff8d3a"),
        ("Scan", "Claim the hidden one-time code.", "#55b6ff"),
        ("Unlock", "Add flavor, badge, and AI art.", "#3ed6a2"),
    ], x=96, y=302, w=650, h=126)
    c += qr_pattern(1490, 705, 220)
    c += footer(5)
    return frame(c)


def slide_06():
    c = "<rect width='1920' height='1080' fill='url(#sunrise)'/>"
    c += text(96, 130, "Rarity Without the Risk", size=62, width=950, fill="#12213f", weight=900)
    c += text(96, 198, "Rarity creates excitement. The product design keeps it away from gambling and child speculation.",
              size=31, width=1120, fill="#52627c", weight=520)
    tiers = [
        ("Common", "Always available flavors like Lemon Bolt and Mango Sun.", "#ffcf42"),
        ("Seasonal", "Timed releases like Winter Berry, with clear windows.", "#55b6ff"),
        ("Limited", "Numbered drops like Gold Lychee, with fixed supply.", "#f6a92d"),
    ]
    for i, (title, body, color) in enumerate(tiers):
        x = 110 + i * 575
        c += card(x, 330, 500, 270, fill="#ffffff", stroke="#dce5f5")
        c += circle_label(x + 70, 415, 44, str(i + 1), fill=color)
        c += text(x + 132, 404, title, size=36, width=310, fill="#12213f", weight=900)
        c += text(x + 48, 505, body, size=27, width=405, fill="#52627c", weight=520)
    c += card(150, 710, 740, 180, fill="#eef8ff", stroke="#b8dcff")
    c += text(194, 766, "Teen app rules", size=30, width=430, fill="#12213f", weight=900)
    c += text(194, 817, "No resale, no trading-for-money, no investment language, no loot-box mechanics.",
              size=27, width=625, fill="#34445f", weight=540)
    c += card(1010, 710, 760, 180, fill="#fff8dd", stroke="#f2d780")
    c += text(1054, 766, "18+ collector layer", size=30, width=460, fill="#12213f", weight=900)
    c += text(1054, 817, "Transparent numbered cans and optional sealed-claim status, separated from minors.",
              size=27, width=650, fill="#34445f", weight=540)
    c += footer(6)
    return frame(c)


def slide_07():
    c = image("app-mockup.png", 0, 0, W, H)
    c += "<rect x='80' y='80' width='760' height='820' rx='32' fill='#ffffff' opacity='0.94'/>"
    c += text(130, 157, "The FlavourDex App", size=54, width=650, fill="#12213f", weight=900)
    c += text(130, 224, "FlavourDex is a collection game about discovery, taste, and community.",
              size=29, width=620, fill="#52627c", weight=540)
    c += bullets(152, 354, [
        "Collection grid with locked and unlocked flavors.",
        "Set completion for launch, seasonal, city, and event drops.",
        "Badges for tasting, voting, and completing safe challenges.",
        "Friend comparison focused on status, not money.",
        "AI collectible art unlocked after each claim."
    ], width=590, size=28, gap=24)
    c += footer(7, dark=True)
    return frame(c)


def slide_08():
    c = "<rect width='1920' height='1080' fill='#ffffff'/>"
    c += image("ai-agent-lab.png", 1215, 105, 595, 335)
    c += text(96, 128, "AI Agent Layer", size=62, width=780, fill="#12213f", weight=900)
    c += text(96, 196, "For this hackathon, SipQuest can demo agents that create, check, and launch a flavor universe.",
              size=31, width=1040, fill="#52627c", weight=520)
    agents = [
        ("Flavor Agent", "Suggests flavor profiles from trend, season, and audience inputs."),
        ("Brand Agent", "Names flavors, writes lore, and proposes badge ideas."),
        ("Art Agent", "Generates collectible card art and can-label directions."),
        ("Safety Agent", "Flags health claims, caffeine risks, minor safety, and gambling language."),
        ("Drop Agent", "Creates rarity plans, QR batches, and demo inventory status.")
    ]
    for i, (title, body) in enumerate(agents):
        x = 96 + (i % 3) * 590
        y = 475 + (i // 3) * 220
        c += card(x, y, 520, 175, fill="#ffffff", stroke="#dce5f5")
        c += circle_label(x + 64, y + 62, 34, "AI", fill=["#ffcf42", "#ff8d3a", "#55b6ff", "#3ed6a2", "#a16eff"][i])
        c += text(x + 122, y + 58, title, size=29, width=330, fill="#12213f", weight=900)
        c += text(x + 46, y + 116, body, size=22, width=425, fill="#52627c", weight=520)
    c += card(1125, 850, 630, 112, fill="#071226", stroke="#071226")
    c += text(1162, 910, "Agent output becomes the live demo, not a food-safety shortcut.",
              size=24, width=555, fill="#ffffff", weight=760, leading=1.08)
    c += footer(8)
    return frame(c)


def slide_09():
    c = "<rect width='1920' height='1080' fill='#f8fbff'/>"
    c += text(96, 130, "How SipQuest Makes Money", size=62, width=950, fill="#12213f", weight=900)
    c += text(96, 198, "The core business is drinks and community, not token speculation.",
              size=32, width=840, fill="#52627c", weight=520)
    streams = [
        ("Drink sales", "Margin on everyday flavors, seasonal packs, and online bundles."),
        ("Limited drops", "Transparent numbered batches with clear supply and no teen resale market."),
        ("Brand collabs", "Movies, games, creators, local events, and school-safe campaigns."),
        ("Subscriptions", "Monthly discovery boxes for families and adult collectors."),
        ("18+ services", "Authentication, provenance, and marketplace integrations kept outside teen mode.")
    ]
    c += bullets(130, 330, [f"{title}: {body}" for title, body in streams[0:3]],
                 width=760, size=34, gap=36)
    c += bullets(1030, 330, [f"{title}: {body}" for title, body in streams[3:]],
                 width=690, size=34, gap=50)
    c += card(285, 815, 1350, 95, fill="#fff8dd", stroke="#f2d780")
    c += text(330, 874, "Business principle: earn because people like the drink, the art, and the community.",
              size=30, width=1240, fill="#12213f", weight=820)
    c += footer(9)
    return frame(c)


def slide_10():
    c = "<rect width='1920' height='1080' fill='url(#sunrise)'/>"
    c += text(96, 130, "Why This Is Different", size=62, width=900, fill="#12213f", weight=900)
    cols = [
        ("Ordinary drinks", "Taste-only. The moment ends when the can is gone.", "SipQuest adds proof, progress, and community."),
        ("Pokemon cards", "Collectible, but creates clutter and is not consumed.", "SipQuest lets the physical object disappear cleanly."),
        ("NFTs", "Often marketed as investment, trading, and speculation.", "SipQuest hides the chain and centers teen-safe ownership.")
    ]
    for i, (head, old, new) in enumerate(cols):
        x = 105 + i * 595
        c += card(x, 280, 510, 540, fill="#ffffff", stroke="#dce5f5")
        c += text(x + 44, 365, head, size=38, width=410, fill="#12213f", weight=900)
        c += text(x + 44, 485, old, size=29, width=410, fill="#6b7890", weight=520)
        c += f"<line x1='{x + 44}' y1='590' x2='{x + 465}' y2='590' stroke='#dce5f5' stroke-width='2'/>"
        c += text(x + 44, 675, new, size=30, width=410, fill="#12213f", weight=780)
    c += text(96, 920, "Positioning: collectible beverage platform, not a crypto product for kids.",
              size=34, width=1030, fill="#12213f", weight=850)
    c += footer(10)
    return frame(c)


def slide_11():
    c = "<rect width='1920' height='1080' fill='#071226'/>"
    c += text(96, 130, "Responsible Frame", size=62, width=800, fill="#ffffff", weight=900)
    c += text(96, 198, "The pitch is strongest when the guardrails are part of the product, not footnotes.",
              size=31, width=980, fill="#d9e9ff", weight=520)
    risks = [
        ("Children", "Parental controls, privacy-by-default profiles, no public location sharing."),
        ("Crypto", "Normal login first; wallet hidden; non-transferable collectibles for minors."),
        ("Gambling", "No paid random packs, odds language, jackpot framing, or teen resale."),
        ("Health", "Non-alcoholic, age-appropriate caffeine rules, sugar transparency, no medical claims.")
    ]
    for i, (title, body) in enumerate(risks):
        x = 115 + (i % 2) * 860
        y = 325 + (i // 2) * 260
        c += card(x, y, 760, 200, fill="#ffffff", stroke="#ffffff", opacity=0.96)
        c += circle_label(x + 70, y + 72, 40, "!", fill=["#ffcf42", "#55b6ff", "#ff8d3a", "#3ed6a2"][i])
        c += text(x + 132, y + 68, title, size=34, width=520, fill="#12213f", weight=900)
        c += text(x + 48, y + 135, body, size=26, width=650, fill="#52627c", weight=520)
    c += card(350, 860, 1220, 90, fill="#ffffff14", stroke="#ffffff35")
    c += text(400, 916, "Say: proof-of-claim, collection, taste, community. Do not say: investment, earning, jackpot, flipping.",
              size=27, width=1120, fill="#ffffff", weight=760)
    c += footer(11, dark=True)
    return frame(c, bg="#071226")


def slide_12():
    c = "<rect width='1920' height='1080' fill='#f8fbff'/>"
    c += image("qr-claim.png", 1040, 90, 760, 430, opacity=0.95)
    c += text(96, 130, "Hackathon MVP", size=62, width=720, fill="#12213f", weight=900)
    c += text(96, 198, "No manufacturing required. Build the claim loop and the agent demo.",
              size=32, width=810, fill="#52627c", weight=520)
    c += numbered_steps([
        ("Mock cans", "Printed labels on existing cans or blank packaging.", "#ffcf42"),
        ("Claim codes", "Unique QR stickers mapped to demo inventory.", "#55b6ff"),
        ("FlavourDex", "Mobile-friendly prototype with profiles, badges, and sets.", "#3ed6a2"),
        ("AI agents", "Generate flavors, names, art prompts, and safety reviews.", "#a16eff"),
        ("Proof layer", "Simple claim ledger now; optional chain proof for limited demo drops.", "#ff8d3a")
    ], x=96, y=310, w=800, h=112)
    c += card(1040, 610, 760, 250, fill="#071226", stroke="#071226")
    c += text(1090, 680, "Demo moment", size=36, width=600, fill="#ffffff", weight=900)
    c += text(1090, 750, "Judge scans a can, unlocks Gold Lychee in FlavourDex, sees AI art, and watches the safety agent explain why the drop is teen-safe.",
              size=29, width=640, fill="#d9e9ff", weight=540)
    c += text(1090, 915, "Buildable in a weekend.", size=34, width=600, fill="#ffcf42", weight=900)
    c += footer(12)
    return frame(c)


SLIDE_BUILDERS = [
    slide_01, slide_02, slide_03, slide_04, slide_05, slide_06,
    slide_07, slide_08, slide_09, slide_10, slide_11, slide_12
]


def run(cmd):
    print("+", " ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=ROOT, check=True)


def build_pdf_from_pngs(pngs, pdf_path):
    required = ["pngtopnm", "pnmtops", "gs"]
    missing = [tool for tool in required if not shutil.which(tool)]
    if missing:
        raise SystemExit(f"Cannot build PDF; missing: {', '.join(missing)}")

    with tempfile.TemporaryDirectory(prefix="sipquest-pdf-") as tmp:
        tmpdir = Path(tmp)
        ps_pages = []
        for idx, png in enumerate(pngs, 1):
            ppm = tmpdir / f"page-{idx:02d}.ppm"
            ps = tmpdir / f"page-{idx:02d}.ps"
            with ppm.open("wb") as out:
                subprocess.run(
                    ["pngtopnm", "-mix", "-background", "white", str(png)],
                    cwd=ROOT,
                    check=True,
                    stdout=out,
                )
            with ps.open("wb") as out:
                subprocess.run(
                    [
                        "pnmtops", "-noturn", "-center", "-setpage",
                        "-width", "13.333", "-height", "7.5",
                        "-imagewidth", "13.333", "-imageheight", "7.5",
                        str(ppm),
                    ],
                    cwd=ROOT,
                    check=True,
                    stdout=out,
                )
            ps_pages.append(ps)

        subprocess.run(
            [
                "gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-sOutputFile={pdf_path}",
                *map(str, ps_pages),
            ],
            cwd=ROOT,
            check=True,
        )


def main():
    for directory in (SLIDES, SVGS, EXPORTS):
        directory.mkdir(exist_ok=True)
    for path in SLIDES.glob("slide-*.png"):
        path.unlink()
    for path in SVGS.glob("slide-*.svg"):
        path.unlink()

    for idx, builder in enumerate(SLIDE_BUILDERS, 1):
        svg_path = SVGS / f"slide-{idx:02d}.svg"
        svg_path.write_text(builder(), encoding="utf-8")
        run([
            "convert", "-background", "white", "-density", "144",
            str(svg_path.relative_to(ROOT)),
            "-resize", f"{W}x{H}!",
            str((SLIDES / f"slide-{idx:02d}.png").relative_to(ROOT)),
        ])

    pdf_path = EXPORTS / "sipquest-pitch-deck.pdf"
    if pdf_path.exists():
        pdf_path.unlink()
    pngs = sorted(SLIDES.glob("slide-*.png"))
    try:
        run(["convert", *[str(p.relative_to(ROOT)) for p in pngs],
             str(pdf_path.relative_to(ROOT))])
    except subprocess.CalledProcessError:
        print("ImageMagick PDF output is blocked; using Netpbm + Ghostscript fallback.")
        build_pdf_from_pngs(pngs, pdf_path)
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    if not shutil.which("convert"):
        raise SystemExit("ImageMagick 'convert' is required.")
    main()
