import pandas as pd
import re
import PyPDF2

# ==============================
# LOAD FILES
# ==============================

# Load existing group assignments
assignments_df = pd.read_excel("group_assignments.xlsx")

# Load class list from PDF
def extract_students_from_pdf(pdf_path):
    """Extract student names from classlist PDF"""
    students = []
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text = page.extract_text()
            lines = text.split('\n')
            
            # Look for lines that contain student names in "Last, First" format
            for line in lines:
                # Skip header lines and empty lines
                if 'Last First Name' in line or not line.strip():
                    continue
                # Basic pattern to detect name format (has comma, letters)
                if ',' in line and any(c.isalpha() for c in line):
                    # Extract the name part (first field typically)
                    parts = line.split()
                    if parts:
                        # Try to extract "Last, First" pattern
                        name_candidate = ' '.join(parts[:2]) if len(parts) >= 2 else parts[0]
                        if ',' in name_candidate:
                            students.append(name_candidate)
    return students

# Try to read from PDF first, fallback to Excel if needed
try:
    all_students = extract_students_from_pdf("classlist.pdf")
    print(f"Loaded {len(all_students)} students from classlist.pdf")
except Exception as e:
    print(f"Error reading PDF: {e}")
    print("Falling back to Excel file...")
    # Fallback to Excel
    full_students_df = pd.read_excel("seng321_ClassList.xlsx")
    # Look for "Last First Name" column
    if "Last First Name" in full_students_df.columns:
        all_students = full_students_df["Last First Name"].tolist()
    else:
        all_students = full_students_df.iloc[:, 0].tolist()
    print(f"Loaded {len(all_students)} students from Excel")

# ==============================
# HELPER FUNCTIONS
# ==============================

def normalize_name(name):
    """Normalize names for comparison"""
    if pd.isna(name):
        return ""
    return re.sub(r"[^a-z]", "", str(name).lower())

# ==============================
# IDENTIFY UNASSIGNED STUDENTS
# ==============================

# Normalize names for comparison
assigned_students = set(assignments_df["Student Name"].apply(normalize_name))

# Find unassigned students
unassigned_students = []
for student in all_students:
    if normalize_name(student) not in assigned_students:
        unassigned_students.append(student)

print(f"\nFound {len(unassigned_students)} unassigned students")
print(f"Total assigned: {len(assigned_students)}")
print(f"Total students: {len(all_students)}")

# ==============================
# GET CURRENT GROUP SIZES
# ==============================

team_counts = assignments_df["Team Name"].value_counts().sort_index()
print("\nCurrent group sizes:")
for team, count in team_counts.items():
    print(f"  {team}: {count} students")

# ==============================
# DISTRIBUTE UNASSIGNED STUDENTS
# ==============================

# Get list of teams and their current sizes
teams = sorted(assignments_df["Team Name"].unique())
team_sizes = {team: len(assignments_df[assignments_df["Team Name"] == team]) for team in teams}

# Get domain for each team
team_domains = {}
for team in teams:
    domain = assignments_df[assignments_df["Team Name"] == team]["Domain"].iloc[0]
    team_domains[team] = domain

# Add unassigned students to groups, balancing sizes
new_assignments = []

for student in unassigned_students:
    # Find the team with smallest size
    smallest_team = min(team_sizes, key=team_sizes.get)
    
    new_assignments.append({
        "Team Name": smallest_team,
        "Student Name": student,
        "Domain": team_domains[smallest_team],
        "Score": 0  # No score available for students who didn't complete survey
    })
    
    team_sizes[smallest_team] += 1

# ==============================
# COMBINE AND SAVE
# ==============================

# Add new assignments to existing ones
new_assignments_df = pd.DataFrame(new_assignments)
final_df = pd.concat([assignments_df, new_assignments_df], ignore_index=True)

# Sort by Team Name and Student Name
final_df = final_df.sort_values(["Team Name", "Student Name"])

# Save to Excel
final_df.to_excel("group_assignments_complete.xlsx", index=False)

# ==============================
# PRINT SUMMARY
# ==============================

print("\n" + "="*50)
print("FINAL GROUP ASSIGNMENTS")
print("="*50)

for team in sorted(final_df["Team Name"].unique()):
    team_df = final_df[final_df["Team Name"] == team]
    domain = team_df["Domain"].iloc[0]
    count = len(team_df)
    total_score = team_df["Score"].sum()
    print(f"\n{team} ({domain}): {count} students, Total Score: {total_score}")
    for _, row in team_df.iterrows():
        score_str = f"(Score: {row['Score']})" if row['Score'] > 0 else "(No survey)"
        print(f"  - {row['Student Name']} {score_str}")

print("\n" + "="*50)
print(f"Complete assignments saved to: group_assignments_complete.xlsx")
print("="*50)
