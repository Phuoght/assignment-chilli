import os
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import random

# ==============================
# DYNAMIC CONTENT GENERATOR
# ==============================
def get_unique_procedures(policy_name):
    actions = ["Submit", "Review", "Verify", "Validate", "Approve", "Audit", "Archive", "Log", "Monitor", "Execute"]
    targets = ["request", "documentation", "compliance report", "log entry", "security clearance", "system update"]
    steps = [
        f"{random.choice(actions)} the {policy_name} {random.choice(targets)} via the enterprise portal.",
        f"The {random.choice(['Manager', 'Lead', 'Supervisor', 'Director'])} must perform a initial check on {policy_name} requirements.",
        f"Internal validation for {policy_name} should be completed using the standard {random.choice(['digital', 'physical', 'automated'])} workflow.",
        f"Final decision on the {policy_name} instance will be recorded in the database within {random.randint(2, 7)} business days.",
        f"Maintenance of this {policy_name} record is required every {random.randint(1, 12)} months."
    ]
    return steps

def get_unique_risks(policy_name):
    categories = ["Operational", "Legal", "Security", "Financial", "Reputational", "Technical"]
    risk_descriptions = [
        f"Non-compliance with {policy_name} internal standards.",
        f"Inconsistent modification of {policy_name} master records.",
        f"Exposure of data related to {policy_name} operations.",
        f"Strategic bottleneck in the {policy_name} lifecycle.",
        f"Discrepancy in the reporting of {policy_name} benchmarks."
    ]
    severities = ["Low", "Medium", "High", "Critical"]
    mitigations = [
        f"Strict {policy_name} governance", 
        f"Real-time {policy_name} notifications", 
        f"Biannual {policy_name} workshops", 
        f"End-to-end encryption of {policy_name} logs"
    ]
    
    rows = []
    # Pick 3 unique risk descriptions for this file
    selected_risks = random.sample(risk_descriptions, 3)
    for desc in selected_risks:
        rows.append([
            random.choice(categories),
            desc,
            random.choice(severities),
            random.choice(mitigations)
        ])
    return rows

def get_unique_roles(policy_name):
    all_roles = ["HR", "IT", "Finance", "Legal", "Engineering", "Operations", "Marketing", "Executive Board", "Risk Management", "Public Relations"]
    selected = random.sample(all_roles, random.randint(3, 4))
    return selected

# ==============================
# DOC WRITER
# ==============================
def write_enterprise_doc(filepath, title, sections):
    doc = Document()
    header = doc.sections[0].header
    p = header.paragraphs[0]
    p.text = f"CHILLI CORP | {title} | REF-{random.randint(100000, 999999)}"
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    doc.add_heading(title, 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(
        f"Document Control ID: POL-{random.randint(100, 999)}-{random.randint(10, 99)}\n"
        f"Authorized Owner: {random.choice(['Corporate Admin', 'Legal Dept', 'HR Strategy', 'Risk Management'])}\n"
        "Data Classification: CONFIDENTIAL / INTERNAL\n"
        f"Effective Date: {random.randint(1, 28)}/04/2026\n"
        "Revision Status: V2.5 (Fully Dynamic)"
    )
    doc.add_page_break()

    for i, sec in enumerate(sections, 1):
        doc.add_heading(f"{i}. {sec['title']}", level=1)
        for block in sec["content"]:
            if isinstance(block, str):
                doc.add_paragraph(block)
            elif isinstance(block, dict) and block["type"] == "table":
                table = doc.add_table(rows=1, cols=len(block["headers"]))
                table.style = 'Table Grid'
                hdr = table.rows[0].cells
                for j, h in enumerate(block["headers"]): hdr[j].text = h
                for row in block["rows"]:
                    r = table.add_row().cells
                    for j, v in enumerate(row): r[j].text = str(v)
    doc.save(filepath)

# ==============================
# MAIN ENGINE
# ==============================
def generate_all():
    policies = [
        "Leave", "Working_Hours", "Remote_Work", "Code_of_Conduct", "IT_Usage",
        "Confidentiality", "Onboarding", "Performance", "Expense", "Travel",
        "Dress_Code", "Attendance", "Data_Security", "Training", "Promotion",
        "Termination", "Health", "Work_From_Home", "Email", "Meeting"
    ]
    
    base_dir = os.path.join(os.getcwd(), "docs", "internal_policies")
    if not os.path.exists(base_dir): os.makedirs(base_dir)

    print(f"🚀 Generating 20 TOTALLY UNIQUE Policies in: {base_dir}")
    for i, name in enumerate(policies, 1):
        filepath = os.path.join(base_dir, f"{i:02d}_{name}_Policy.docx")
        
        # Generate UNIQUE sections for this specific policy
        sections = [
            {
                "title": f"Framework for {name.replace('_', ' ')} Management",
                "content": [
                    f"This document provides the mandatory framework for managing {name} within the corporate structure of Chilli Corp.",
                    f"All personnel must adhere to these {name} standards to ensure operational integrity."
                ]
            },
            {
                "title": "Specific Execution Steps",
                "content": [f"Step {idx+1}: {step}" for idx, step in enumerate(get_unique_procedures(name))]
            },
            {
                "title": f"Risk Identification Matrix for {name}",
                "content": [
                    {
                        "type": "table",
                        "headers": ["Risk Category", "Specific Scenario", "Severity", "Mandatory Control"],
                        "rows": get_unique_risks(name)
                    }
                ]
            },
            {
                "title": "Stakeholders & Responsibilities",
                "content": [f"- {role} Team: Primary responsibility for enforcing {name} protocols." for role in get_unique_roles(name)]
            }
        ]

        write_enterprise_doc(filepath, f"{name.upper()} MANAGEMENT POLICY", sections)
        print(f"   ✔ [{i}/20] {name}_Policy.docx generated with 100% unique content.")

if __name__ == "__main__":
    generate_all()