import pandas as pd
import re
from difflib import get_close_matches
from collections import defaultdict

# ==============================
# LOAD CSV
# ==============================

df = pd.read_csv("survey_results.csv")

# ==============================
# COLUMN DEFINITIONS
# ==============================

NAME_COL = "name"
TEAMMATE_COL = "needed_colleagues names"

COURSE_COLS = [
    "SENG 275 (Testing)",
    "SENG 310 (Human Computer Interaction)",
    "CSC 370 (Databases)",
    "CSC 375 (Systems Analysis)"
]

EXPERIENCE_COLS = [
    "UML experience",
    "UI experience",
    "co-op experience",
    "data science  experience",
    "development experience",
    "IT experience",
    "quality assurance experience",
    "research experience",
    "system administration experience",
    "Other experience"
]

DOMAIN_COLS = {
    "Transportation": "Transportation preference",
    "Health": "Health preference",
    "Environment": "Environment preference"
}

# ==============================
# HELPER FUNCTIONS
# ==============================

def normalize_name(name):
    if pd.isna(name):
        return ""
    return re.sub(r"[^a-z]", "", name.lower())

def parse_teammates(text):
    if pd.isna(text):
        return []
    return [t.strip() for t in re.split(r",|and|\n", text.lower()) if t.strip()]

def fuzzy_match(name, candidates):
    matches = get_close_matches(name, candidates, n=1, cutoff=0.7)
    return matches[0] if matches else None

def score_row(row):
    """
    Score = number of courses taken + number of experience areas
    """
    course_score = sum(1 for c in COURSE_COLS if not pd.isna(row[c]))
    experience_score = sum(1 for e in EXPERIENCE_COLS if not pd.isna(row[e]))
    return course_score + experience_score

# ==============================
# PREPROCESS DATA
# ==============================

df["normalized_name"] = df[NAME_COL].apply(normalize_name)
df["balance_score"] = df.apply(score_row, axis=1)

normalized_names = list(df["normalized_name"])

NUM_GROUPS = 8

# ==============================
# INITIAL GROUP STRUCTURE
# ==============================

# Create 8 groups with domains distributed evenly
# 3 domains -> aim for roughly 3, 3, 2 groups or 3, 2, 3 distribution
groups = []
group_domains = []

# Distribute domains: Transportation gets 3, Health gets 3, Environment gets 2
domain_distribution = ["Transportation", "Transportation", "Transportation", 
                       "Health", "Health", "Health",
                       "Environment", "Environment"]

for i, domain in enumerate(domain_distribution):
    groups.append([])
    group_domains.append(domain)

group_scores = [0] * NUM_GROUPS
group_sizes = [0] * NUM_GROUPS

# ==============================
# STEP 1: ASSIGN BY DOMAIN PREFERENCE
# ==============================

# First, categorize students by their preferred domain
domain_preferences = {
    "Transportation": [],
    "Health": [],
    "Environment": [],
    "No Preference": []
}

for _, row in df.iterrows():
    preferences = {
        domain: row[col]
        for domain, col in DOMAIN_COLS.items()
        if not pd.isna(row[col])
    }

    if preferences:
        chosen_domain = max(preferences, key=preferences.get)
        domain_preferences[chosen_domain].append(row)
    else:
        domain_preferences["No Preference"].append(row)

# Assign students to groups within their preferred domain
for domain in ["Transportation", "Health", "Environment"]:
    # Find groups for this domain
    domain_group_indices = [i for i, d in enumerate(group_domains) if d == domain]
    students = domain_preferences[domain]
    
    # Distribute students evenly across domain groups
    for i, student in enumerate(students):
        # Round-robin assignment to balance group sizes
        target_group = domain_group_indices[i % len(domain_group_indices)]
        groups[target_group].append(student)
        group_scores[target_group] += student["balance_score"]
        group_sizes[target_group] += 1

# ==============================
# STEP 2: HANDLE PREFERRED TEAMMATES
# ==============================

# Build a mapping of student name to group index
name_to_group = {}
for group_idx, group_members in enumerate(groups):
    for m in group_members:
        name_to_group[m["normalized_name"]] = group_idx

# Try to move students to be with their preferred teammates
for group_idx, group_members in enumerate(list(groups)):
    for m in list(group_members):
        if m["normalized_name"] not in name_to_group:
            continue
            
        current_group = name_to_group[m["normalized_name"]]
        requested = parse_teammates(m[TEAMMATE_COL])

        for r in requested:
            r_norm = normalize_name(r)
            match = fuzzy_match(r_norm, normalized_names)

            if match and match in name_to_group:
                other_group = name_to_group[match]

                # Only move if they're in different groups AND same domain
                if (other_group != current_group and 
                    group_domains[other_group] == group_domains[current_group]):
                    
                    student_row = df[df["normalized_name"] == match].iloc[0]
                    
                    # Move student to current group
                    groups[other_group] = [
                        x for x in groups[other_group]
                        if x["normalized_name"] != match
                    ]
                    groups[current_group].append(student_row)
                    
                    group_scores[current_group] += student_row["balance_score"]
                    group_scores[other_group] -= student_row["balance_score"]
                    group_sizes[current_group] += 1
                    group_sizes[other_group] -= 1
                    
                    name_to_group[match] = current_group

# ==============================
# STEP 3: ASSIGN UNASSIGNED STUDENTS
# ==============================

unassigned = domain_preferences["No Preference"]

for row in unassigned:
    # Find the group with smallest size
    target_group = min(range(NUM_GROUPS), key=lambda i: group_sizes[i])
    groups[target_group].append(row)
    group_scores[target_group] += row["balance_score"]
    group_sizes[target_group] += 1

# ==============================
# OUTPUT RESULTS
# ==============================

output = []

for group_idx, members in enumerate(groups):
    group_name = f"Team {group_idx + 1}"
    domain = group_domains[group_idx]
    
    for m in members:
        output.append({
            "Team Name": group_name,
            "Student Name": m[NAME_COL],
            "Domain": domain,
            "Score": m["balance_score"]
        })

output_df = pd.DataFrame(output)
output_df.to_excel("group_assignments.xlsx", index=False)

# Print summary
print("Group assignments saved to group_assignments.xlsx")
print("\nGroup Summary:")
for i in range(NUM_GROUPS):
    print(f"Team {i+1} ({group_domains[i]}): {group_sizes[i]} students, Total Score: {group_scores[i]}")
