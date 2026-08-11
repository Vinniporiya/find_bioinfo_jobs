import json
import re
import spacy
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import os

# Load the local NLP model
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
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    application_method = default_link
    if email_match:
        application_method = email_match.group(0)
        
    skills = []
    for skill in BIOINFO_SKILLS:
        if skill.strip(", ") in text_lower:
            skills.append(skill.strip(", ").title())
            
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
    rss_feeds = [
        "https://www.nature.com/naturecareers/jobs/rss?keywords=bioinformatics",
        "https://jobs.sciencecareers.org/jobs/bioinformatics/?format=rss",
        "https://euraxess.ec.europa.eu/jobs/search/feed/rss?keywords=bioinformatics",
        "https://www.findapostdoc.com/rss/jobs.aspx?Keywords=bioinformatics",
        "https://www.findaphd.com/rss/phds.aspx?Keywords=bioinformatics",
        "https://jobrxiv.org/job-category/bioinformatics/feed/",
        "https://www.bioinformatics.org/jobs/?format=rss",
        "https://thenode.biologists.com/jobs/feed/",
        "https://www.reddit.com/r/bioinformatics/.rss"
    ]
    
    jobs_db = []
    
    # STRICT HIRING PHRASES: We removed the word "job" from this list entirely 
    # to prevent matching "bash job" or "VCF job".
    hiring_phrases = [
        "hiring", "open position", "vacancy", "looking for a postdoc", 
        "seeking a", "we are expanding", "join our lab", "postdoc position"
    ]
    
    for feed_url in rss_feeds:
        print(f"Fetching token-free jobs from {feed_url}...")
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                clean_text = clean_html(entry.get('description', '') + " " + entry.get('summary', ''))
                full_text = entry.title + " " + clean_text
                
                # Apply the strict filter to noisy feeds (Reddit & The Node)
                is_noisy_feed = "reddit.com" in feed_url or "thenode" in feed_url
                if is_noisy_feed and not any(phrase in full_text.lower() for phrase in hiring_phrases):
                    continue # Skip this post, it's just a discussion
    
                job_data = extract_job_data(
                    text=full_text, 
                    default_link=entry.link, 
                    default_title=entry.title
                )
                
                if job_data["employer_name"] == "Unknown Employer" and hasattr(entry, 'author'):
                    job_data["employer_name"] = entry.author
                    
                jobs_db.append(job_data)
        except Exception as e:
            print(f"Failed to fetch {feed_url}: {e}")
            continue
            
    os.makedirs('data', exist_ok=True)
    with open('data/jobs.json', 'w') as f:
        json.dump(jobs_db, f, indent=2)
        
    print(f"Successfully processed and saved {len(jobs_db)} token-free global jobs.")

if __name__ == "__main__":
    run_scraper()
