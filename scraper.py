import json
import re
import spacy
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime

# Load the local NLP model
nlp = spacy.load("en_core_web_sm")

# Define skills to hunt for
BIOINFO_SKILLS = [
    "python", " r ", " r,", "r/bioconductor", "seurat", "scanpy", 
    "nextflow", "snakemake", "crispr", "alphafold", "machine learning",
    "transcriptomics", "single-cell", "genomics", "bash", "linux"
]

def clean_html(raw_html):
    """Removes HTML tags from feed descriptions."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ")

def extract_job_data(text, default_link=None, default_title=None):
    text_lower = text.lower()
    
    # Extract Application Method
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    application_method = default_link
    if email_match:
        application_method = email_match.group(0)
        
    # Extract Skills
    skills = []
    for skill in BIOINFO_SKILLS:
        if skill.strip(", ") in text_lower:
            skills.append(skill.strip(", ").title())
            
    # Extract Entities via spaCy
    doc = nlp(text)
    employer_name = None
    location = None
    
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    locs = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
    
    if orgs:
        employer_name = orgs[0]
    if not employer_name:
         lab_match = re.search(r'([A-Z][a-z]+ Lab)', text)
         if lab_match:
             employer_name = lab_match.group(1)
    if locs:
        location = locs[0]
        
    # Infer Job Type
    job_type = "Unknown"
    if any(word in text_lower for word in ["phd", "postdoc", "university", "faculty", "lab"]):
        job_type = "Academia"
    elif any(word in text_lower for word in ["company", "startup", "industry", "inc", "ltd"]):
        job_type = "Industry"

    return {
        "employer_name": employer_name or "Unknown Employer",
        "job_title": default_title or "Bioinformatics Role",
        "job_type": job_type,
        "location": location or "Remote/Unknown",
        "application_method": application_method,
        "skills": list(set(skills)),
        "extracted_at": datetime.now().isoformat()
    }

def run_scraper():
    # Live RSS feeds for bioinformatics jobs [1]
    rss_feeds = [
        "https://jobrxiv.org/job-category/bioinformatics/feed/",
        "https://www.reddit.com/r/bioinformatics/.rss"
    ]
    
    jobs_db = []
    
    for feed_url in rss_feeds:
        print(f"Fetching jobs from {feed_url}...")
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries:
            # Combine the title and description for the NLP to read
            clean_text = clean_html(entry.get('description', '') + " " + entry.get('summary', ''))
            full_text = entry.title + " " + clean_text
            
            # Skip Reddit posts that aren't hiring
            if "reddit.com" in feed_url and not any(k in full_text.lower() for k in ["hiring", "job", "open position"]):
                continue

            job_data = extract_job_data(
                text=full_text, 
                default_link=entry.link, 
                default_title=entry.title
            )
            jobs_db.append(job_data)
            
    # Save the structured data to your static database file
    with open('data/jobs.json', 'w') as f:
        json.dump(jobs_db, f, indent=2)
        
    print(f"Successfully processed and saved {len(jobs_db)} real jobs.")

if __name__ == "__main__":
    run_scraper()
