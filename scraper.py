import json
import re
import spacy
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import os

# Load the local, free NLP model (Zero API keys required)
nlp = spacy.load("en_core_web_sm")

# Define skills to hunt for
BIOINFO_SKILLS = [
    "python", " r ", " r,", "r/bioconductor", "seurat", "scanpy", 
    "nextflow", "snakemake", "crispr", "alphafold", "machine learning",
    "transcriptomics", "single-cell", "genomics", "bash", "linux", "pytorch"
]

def clean_html(raw_html):
    """Removes HTML tags from feed descriptions."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ")

def extract_job_data(text, default_link=None, default_title=None):
    text_lower = text.lower()
    
    # 1. Extract Application Method
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    application_method = default_link
    if email_match:
        application_method = email_match.group(0)
        
    # 2. Extract Skills
    skills = []
    for skill in BIOINFO_SKILLS:
        if skill.strip(", ") in text_lower:
            skills.append(skill.strip(", ").title())
            
    # 3. Extract Entities via local NLP
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
        
    # 4. Infer Job Type
    job_type = "Unknown"
    if any(word in text_lower for word in ["phd", "postdoc", "university", "faculty", "lab"]):
        job_type = "Academia"
    elif any(word in text_lower for word in ["company", "startup", "industry", "inc", "ltd", "pharma"]):
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
    # The Ultimate Token-Free Global Feed List
    rss_feeds = [
        # --- MAJOR SCIENCE & PUBLISHING PORTALS ---
        # Nature Careers - Filtered for Computational Biology & Bioinformatics
        "https://www.nature.com/naturecareers/jobs/rss?keywords=bioinformatics",
        # Science Careers - AAAS Official Job Board
        "https://jobs.sciencecareers.org/jobs/bioinformatics/?format=rss",
        
        # --- GLOBAL RESEARCH & ACADEMIC NETWORKS ---
        # EURAXESS - The European Commission's massive research database
        "https://euraxess.ec.europa.eu/jobs/search/feed/rss?keywords=bioinformatics",
        # FindAPostDoc - UK/EU heavy, but globally used for postdocs
        "https://www.findapostdoc.com/rss/jobs.aspx?Keywords=bioinformatics",
        "https://www.findapostdoc.com/rss/jobs.aspx?Keywords=computational%20biology",
        # FindAPhD - For PhD candidates
        "https://www.findaphd.com/rss/phds.aspx?Keywords=bioinformatics",
        
        # --- BIOINFORMATICS SPECIFIC COMMUNITIES ---
        # JobRxiv - The leading preprint server job board (highly used globally)
        "https://jobrxiv.org/job-category/bioinformatics/feed/",
        # Bioinformatics.org - One of the oldest dedicated boards
        "https://www.bioinformatics.org/jobs/?format=rss",
        
        # --- THE COMPANY OF BIOLOGISTS (The Node) ---
        # EvoDevo and genomics-heavy roles
        "https://thenode.biologists.com/jobs/feed/",
        
        # --- INFORMAL/SOCIAL HIRING ---
        # Reddit - Where PIs and startups often post directly
        "https://www.reddit.com/r/bioinformatics/.rss"
    ]
    
    # ... rest of the run_scraper() code remains exactly the same ...
    
    jobs_db = []
    
    for feed_url in rss_feeds:
        print(f"Fetching token-free jobs from {feed_url}...")
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                clean_text = clean_html(entry.get('description', '') + " " + entry.get('summary', ''))
                full_text = entry.title + " " + clean_text
                
                if "reddit.com" in feed_url and not any(k in full_text.lower() for k in ["hiring", "job", "open position"]):
                    continue
    
                job_data = extract_job_data(
                    text=full_text, 
                    default_link=entry.link, 
                    default_title=entry.title
                )
                
                # Fallback to the RSS author tag if the NLP missed the employer name
                if job_data["employer_name"] == "Unknown Employer" and hasattr(entry, 'author'):
                    job_data["employer_name"] = entry.author
                    
                jobs_db.append(job_data)
        except Exception as e:
            print(f"Failed to fetch {feed_url}: {e}")
            continue
            
    # Save the database
    os.makedirs('data', exist_ok=True)
    with open('data/jobs.json', 'w') as f:
        json.dump(jobs_db, f, indent=2)
        
    print(f"Successfully processed and saved {len(jobs_db)} token-free global jobs.")

if __name__ == "__main__":
    run_scraper()

if __name__ == "__main__":
    run_scraper()
