import json
import re
import spacy
from datetime import datetime

# Load spaCy's lightweight, free NLP model for entity recognition
nlp = spacy.load("en_core_web_sm")

# Define a hardcoded list of relevant bioinformatics skills
BIOINFO_SKILLS = [
    "python", " r ", " r,", "r/bioconductor", "seurat", "scanpy", 
    "nextflow", "snakemake", "crispr", "alphafold", "machine learning",
    "transcriptomics", "single-cell", "genomics", "bash", "linux"
]

def extract_job_data(text):
    text_lower = text.lower()
    
    # 1. Filter: Ensure this is actually a job post
    hiring_keywords = ["hiring", "looking for", "open position", "join our", "we are expanding"]
    if not any(hk in text_lower for hk in hiring_keywords):
        return None # Skip this post, it's not a job ad

    # 2. Regex for Application Method (Email or URL)
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    url_match = re.search(r'https?://[^\s]+', text)
    
    application_method = None
    if email_match:
        application_method = email_match.group(0)
    elif url_match:
        application_method = url_match.group(0)
    elif "dm " in text_lower or "message " in text_lower:
        application_method = "Direct Message"
        
    # 3. Skill Extraction via Keyword Matching
    skills = []
    for skill in BIOINFO_SKILLS:
        if skill.strip(", ") in text_lower:
            skills.append(skill.strip(", ").title())
            
    # 4. Entity Extraction using spaCy (Organizations and Locations)
    doc = nlp(text)
    employer_name = None
    location = None
    
    # spaCy tags Organizations as 'ORG' and Locations as 'GPE' or 'LOC'
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    locs = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
    
    if orgs:
        employer_name = orgs[0] # Assume the first organization is the employer
        
    # Fallback regex for academic labs (e.g., "Chen Lab") since NER sometimes misses them
    if not employer_name:
         lab_match = re.search(r'([A-Z][a-z]+ Lab)', text)
         if lab_match:
             employer_name = lab_match.group(1)

    if locs:
        location = locs[0]
        
    # 5. Infer Job Type based on keywords
    job_type = "Unknown"
    if any(word in text_lower for word in ["phd", "postdoc", "university", "faculty", "lab"]):
        job_type = "Academia"
    elif any(word in text_lower for word in ["company", "startup", "industry", "inc", "ltd"]):
        job_type = "Industry"
        
    # 6. Extract Job Title using basic heuristic
    title = None
    common_titles = ["Postdoc", "Bioinformatician", "Data Scientist", "Computational Biology" ,"Computational Biologist", "PhD Student", "Software Engineer"]
    for t in common_titles:
        if t.lower() in text_lower:
            title = t
            break

    return {
        "employer_name": employer_name,
        "job_title": title,
        "job_type": job_type,
        "location": location,
        "application_method": application_method,
        "skills": list(set(skills)),
        "extracted_at": datetime.now().isoformat()
    }

def run_scraper():
    # In a real scenario, you would fetch these from Twitter/Mastodon APIs
    sample_posts = [
        "So excited to announce the Chen Lab is expanding! We're looking for a driven Postdoc to lead our new spatial transcriptomics project. Must have strong R/Bioconductor experience and know Seurat. Based in Boston. DM me or send your CV to chen@university.edu!",
        "I just published my first paper in Nature! #bioinformatics #transcriptomics"
    ]
    
    jobs_db = []
    
    for post in sample_posts:
        job_data = extract_job_data(post)
        if job_data:
            jobs_db.append(job_data)
            
    # Save the structured data to your static database file
    with open('data/jobs.json', 'w') as f:
        json.dump(jobs_db, f, indent=2)
        
    print(f"Successfully processed and saved {len(jobs_db)} jobs.")

if __name__ == "__main__":
    run_scraper()
