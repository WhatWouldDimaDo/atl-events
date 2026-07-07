import re

with open('data.js', 'r') as f:
    content = f.read()

entries = [
    ("Sol Dance", "scheduled", "2nd Sunday monthly"),
    ("Morningside Farmers Market", "scheduled", "Saturdays 8 AM-noon"),
    ("Chefs.*Farmers Market at Pullman", "scheduled", "Saturdays year-round"),
    ("Peachtree Road Farmers Market", "scheduled", "Saturdays year-round"),
    ("Grant Park Farmers Market", "scheduled", "Sundays 9 AM-1 PM, Apr-Dec"),
    ("Piedmont Park Green Market", "seasonal", "Saturdays Mar-Dec"),
    ("Five Rhythms", "scheduled", "Sundays 4 PM + Fridays"),
    ("Castleberry Hill Art Stroll", "scheduled", "2nd Friday monthly"),
    ("Free Yoga in Piedmont Park", "seasonal", "Saturdays, summer"),
    ("Strawberry Picking at Jaemor", "seasonal", "Late Apr-May"),
    ("Apple Picking in Blue Ridge", "seasonal", "Sep-Oct"),
    ("Pumpkin Patch", "seasonal", "October"),
    ("Outdoor Movie Night.*Atlantic", "seasonal", "Summer months"),
    ("ABG Summer Nights", "seasonal", "Summer Thursdays"),
    ("Fernbank After Dark", "scheduled", "Monthly Fridays"),
    ("High Museum.*Second Sunday", "scheduled", "2nd Sunday monthly"),
    ("Lake Claire.*Drum Circle", "scheduled", "Monthly, full moon"),
    ("Atlanta Streets Alive", "scheduled", "Selected dates Apr-Nov"),
    ("Glow Nights", "seasonal", "Summer 2026"),
    ("Red Light.*Jazz Jam", "scheduled", "Wednesdays 8 PM"),
    ("ATLPTN Group Rides", "scheduled", "Check Instagram for dates"),
    ("Critical Mass ATL", "scheduled", "Last Friday monthly"),
]

patched = 0
for name_pat, avail, avail_note in entries:
    # Match the entry block: find name line then url/imageUrl/notes line and append before closing brace
    pattern = r"(id: 'e\d+', name: '" + name_pat + r".*?notes: '[^']*')\s*\n(\s*[}])"
    note_field = ", availabilityNote: '" + avail_note + "'" if avail_note else ""
    replacement = r"\1,\n    availability: '" + avail + "'" + note_field + r"\n\2"
    new_content, n = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if n == 1:
        content = new_content
        patched += 1
        print("OK " + name_pat[:40] + " -> " + avail)
    else:
        print("MISS " + name_pat[:40])

with open('data.js', 'w') as f:
    f.write(content)
print("\nPatched " + str(patched) + " entries")
