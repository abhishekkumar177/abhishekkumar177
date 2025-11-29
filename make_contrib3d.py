# make_contrib3d.py
# Generates an isometric 3D-looking contribution graph SVG for a GitHub user.
# Usage: python make_contrib3d.py <github-username>

import sys, math, requests
from bs4 import BeautifulSoup
from datetime import datetime

PALETTE = [
    "#ebedf0",  # 0
    "#c6e48b",  # 1
    "#7bc96f",  # 2
    "#239a3b",  # 3
    "#196127",  # 4+
]

def fetch_calendar(username):
    url = f"https://github.com/{username}"
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch {url} (status {r.status_code})")
    soup = BeautifulSoup(r.text, "html.parser")
    cal = soup.find("svg", {"class": "js-calendar-graph-svg"})
    if not cal:
        raise RuntimeError("Could not find contribution graph on profile page.")
    rects = cal.find_all("rect", {"class": "ContributionCalendar-day"})
    if not rects:
        # fallback older class names
        rects = cal.find_all("rect", {"class": "day"})
    days = []
    for r in rects:
        date = r.get("data-date")
        count = r.get("data-count")
        if date is None or count is None:
            continue
        days.append((date, int(count)))
    # sort by date ascending
    days.sort(key=lambda x: x[0])
    return days

def map_to_weeks(days):
    # Build weeks array: each week is list of 7 entries (Mon-Sun or Sun-Sat depending on GitHub)
    # GitHub weeks start on Sunday in the SVG layout. We will keep that.
    weeks = []
    week = []
    for date_str, count in days:
        dt = datetime.fromisoformat(date_str)
        # weekday: Monday=0..Sunday=6; GitHub's svg aligns by row, but the rects are already in weekly columns.
        # Simpler approach: group by consecutive blocks of 7 as they appear.
        week.append((date_str, count))
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        # pad the last week on top if shorter
        while len(week) < 7:
            week.append((None, 0))
        weeks.append(week)
    return weeks

def count_to_tier(c):
    if c == 0:
        return 0
    if c < 3:
        return 1
    if c < 8:
        return 2
    if c < 20:
        return 3
    return 4

def make_isometric_svg(weeks, username, outname="contrib3d.svg"):
    # geometry
    cell_w = 72     # width of top parallelogram
    cell_h = 24     # vertical size of top parallelogram
    gap_x = 12
    gap_y = 8
    base_x = 40
    base_y = 40
    max_height_px = 140  # maximum extrude height for highest tier

    cols = len(weeks)
    rows = 7

    svg_w = base_x*2 + cols * (cell_w + gap_x)
    svg_h = base_y*2 + rows * (cell_h + gap_y) + max_height_px

    def top_polygon(x, y):
        # x,y are top-left anchor for the cube top
        # top parallelogram points relative to (x,y)
        return [
            (x, y),
            (x + cell_w/2, y - cell_h/2),
            (x + cell_w, y),
            (x + cell_w/2, y + cell_h/2),
        ]

    def face_polygons(x, y, height):
        # returns front and right face polygons given top anchor and height
        top = top_polygon(x,y)
        # front face: connects top[0]->top[3] down by height
        front = [
            top[0],
            top[3],
            (top[3][0], top[3][1] + height),
            (top[0][0], top[0][1] + height),
        ]
        # right face: connects top[2]->top[3] down by height
        right = [
            top[2],
            top[3],
            (top[3][0], top[3][1] + height),
            (top[2][0], top[2][1] + height),
        ]
        return front, right

    def poly_to_str(poly):
        return " ".join(f"{int(px)},{int(py)}" for px,py in poly)

    # build svg content
    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">')
    parts.append('<defs>')
    parts.append('<linearGradient id="gTop" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#e6f7ea"/><stop offset="1" stop-color="#9be9a8"/></linearGradient>')
    parts.append('</defs>')
    parts.append(f'<rect width="100%" height="100%" fill="#fff"/>')
    parts.append(f'<g transform="translate(0,0)">')

    # iterate columns (weeks) left-to-right
    for col, week in enumerate(weeks):
        for row in range(rows):
            date_str, count = week[row]
            tier = count_to_tier(count)
            color = PALETTE[tier]
            # compute x,y anchor for top based on column and row
            x = base_x + col * (cell_w + gap_x)
            y = base_y + row * (cell_h + gap_y)
            # height scaled by tier (for visual)
            hpx = int((tier / 4.0) * max_height_px)
            # draw top
            top = top_polygon(x,y)
            parts.append(f'<polygon points="{poly_to_str(top)}" fill="{color}" stroke="#ccc" stroke-width="1"/>')
            if hpx > 2:
                front, right = face_polygons(x,y,hpx)
                # darker shades for faces
                parts.append(f'<polygon points="{poly_to_str(front)}" fill="#cce9d0" opacity="0.95" stroke="#b8d3b4" stroke-width="0.6"/>')
                parts.append(f'<polygon points="{poly_to_str(right)}" fill="#b5dca8" opacity="0.95" stroke="#9fc589" stroke-width="0.6"/>')
            # small tooltip (title)
            if date_str:
                parts.append(f'<title>{date_str}: {count} contributions</title>')
    parts.append('</g>')
    parts.append('</svg>')

    with open(outname, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"Wrote {outname} (weeks={len(weeks)}, cols*rows={len(weeks)*7})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_contrib3d.py <github-username>")
        sys.exit(1)
    username = sys.argv[1].strip()
    days = fetch_calendar(username)
    weeks = map_to_weeks(days)
    make_isometric_svg(weeks, username, outname="contrib3d.svg")
