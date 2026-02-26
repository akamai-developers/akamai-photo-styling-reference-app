# Social Media Content Transformer Agent - Project Specification

## Project Overview

Build a multi-agent system that transforms long-form content (blog posts, video transcripts) into optimized social media posts for X (Twitter) and LinkedIn. The system uses multiple AI agents orchestrated by CrewAI, with inference powered by NVIDIA Nemotron-3-Nano-30B running on vLLM.

**This is a demonstration project showcasing:**
- Infrastructure deployment (Terraform + Linode GPU)
- Model serving (vLLM with OpenAI-compatible API)
- Security (API key authentication for model access)
- Multi-agent orchestration (CrewAI)
- Web application development (FastAPI)

## Architecture

### Two-Machine Setup (Both Provisioned via Terraform)

**Machine 1: GPU Inference Server (Linode)**
- Provisioned by Terraform
- Runs vLLM serving NVIDIA Nemotron-3-Nano-30B
- Exposes OpenAI-compatible API on port 8000
- Deployed via Terraform with cloud-init

**Machine 2: Application Server (Linode)**
- Provisioned by Terraform
- FastAPI web application
- CrewAI orchestration logic
- File upload handling
- Makes HTTP requests to Machine 1
- Deployed via Terraform with cloud-init

### User Flow

1. User uploads source content (txt/pdf file containing blog post or transcript)
2. Optionally uploads example posts (txt/pdf with successful past posts for X and LinkedIn)
3. Selects target platforms (X, LinkedIn, or both)
4. System processes through multi-agent pipeline
5. Returns generated posts for each platform
6. User can copy or download results

## Tech Stack

### Infrastructure
- **Cloud Provider**: Linode (GPU instance for vLLM + standard instance for app)
- **IaC**: Terraform (provisions both GPU and application servers)
- **Provisioning**: Cloud-init (automated setup on both servers)
- **Model Serving**: vLLM
- **Model**: NVIDIA-Nemotron-3-Nano-30B-A3B-BF16

### Application
- **Backend**: FastAPI
- **Agent Framework**: CrewAI
- **File Processing**: pypdf (for PDFs), standard file I/O (for txt)
- **Frontend**: HTML/JavaScript (simple, no React needed)
- **Python Version**: 3.10+

### Key Dependencies
```
fastapi
uvicorn
crewai
crewai-tools
openai  # for vLLM client
pypdf
python-multipart  # for file uploads
pydantic
```

## Directory Structure

```
social-media-transformer/
├── infrastructure/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── cloud-init-vllm.yaml
│   └── cloud-init-app.yaml
├── app/
│   ├── main.py              # FastAPI application
│   ├── agents.py            # CrewAI agent definitions
│   ├── tasks.py             # CrewAI task definitions
│   ├── crew.py              # Crew orchestration
│   ├── file_processor.py    # File upload/parsing logic
│   └── models.py            # Pydantic models
├── static/
│   ├── index.html
│   └── styles.css
├── requirements.txt
└── README.md
```

## Infrastructure Setup (Terraform)

**Note:** The Terraform configuration below provisions BOTH the GPU inference server and the CPU application server in a single deployment. Both machines are created with one `terraform apply` command.

### File: infrastructure/main.tf

```hcl
terraform {
  required_providers {
    linode = {
      source  = "linode/linode"
      version = "~> 2.0"
    }
  }
}

provider "linode" {
  token = var.linode_token
}

# GPU instance for vLLM inference
resource "linode_instance" "vllm_server" {
  label           = "vllm-nemotron-server"
  region          = var.region
  type            = "g1-gpu-rtx6000-1"  # adjust based on model size needs
  image           = "linode/ubuntu22.04"
  
  metadata {
    user_data = templatefile("${path.module}/cloud-init-vllm.yaml", {
      vllm_api_key = var.vllm_api_key
    })
  }
  
  tags = ["vllm", "ai-inference"]
}

# Application server (no GPU)
resource "linode_instance" "app_server" {
  label           = "social-media-transformer-app"
  region          = var.region
  type            = "g6-standard-2"  # 2 CPU, 4GB RAM - adjust as needed
  image           = "linode/ubuntu22.04"
  
  metadata {
    user_data = templatefile("${path.module}/cloud-init-app.yaml", {
      vllm_api_key = var.vllm_api_key
    })
  }
  
  tags = ["app-server", "fastapi"]
}
```

### File: infrastructure/variables.tf

```hcl
variable "linode_token" {
  description = "Linode API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Linode region for deployment"
  type        = string
  default     = "us-east"  # GPU instances available in this region
}

variable "vllm_api_key" {
  description = "API key for authenticating requests to vLLM server"
  type        = string
  sensitive   = true
}
```

### File: infrastructure/outputs.tf

```hcl
output "vllm_ip" {
  value       = linode_instance.vllm_server.ip_address
  description = "IP address of the vLLM inference server"
}

output "app_ip" {
  value       = linode_instance.app_server.ip_address
  description = "IP address of the application server"
}

output "deployment_instructions" {
  value = <<-EOT
  
  ===== DEPLOYMENT READY =====
  
  vLLM Server: ${linode_instance.vllm_server.ip_address}
  App Server:  ${linode_instance.app_server.ip_address}
  
  Next steps:
  
  1. Wait 15-20 minutes for vLLM to download model and start
     Check: curl -H "Authorization: Bearer ${var.vllm_api_key}" http://${linode_instance.vllm_server.ip_address}:8000/v1/models
  
  2. SSH to app server:
     ssh root@${linode_instance.app_server.ip_address}
  
  3. Clone your repo:
     cd /opt
     git clone <your-repo-url> social-media-transformer
     cd social-media-transformer
  
  4. Install dependencies:
     pip3 install -r requirements.txt
  
  5. Set environment variables:
     source /root/.env.transformer  # Loads VLLM_API_KEY
     export VLLM_BASE_URL=http://${linode_instance.vllm_server.ip_address}:8000
  
  6. Run the application:
     uvicorn app.main:app --host 0.0.0.0 --port 8080
  
  7. Access at: http://${linode_instance.app_server.ip_address}:8080
  
  ===========================
  EOT
}
```

### File: infrastructure/cloud-init-vllm.yaml

```yaml
#cloud-config
package_update: true
package_upgrade: true

packages:
  - python3-pip
  - python3-venv
  - git
  - nvidia-cuda-toolkit

runcmd:
  # Install vLLM
  - pip3 install vllm
  - pip3 install huggingface-hub
  
  # Download model (this will take time on first boot)
  - huggingface-cli download nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
  
  # Create systemd service for vLLM with API key authentication
  - |
    cat > /etc/systemd/system/vllm.service <<'EOF'
    [Unit]
    Description=vLLM Inference Server
    After=network.target
    
    [Service]
    Type=simple
    User=root
    ExecStart=/usr/local/bin/vllm serve nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 --host 0.0.0.0 --port 8000 --api-key ${vllm_api_key}
    Restart=always
    RestartSec=10
    
    [Install]
    WantedBy=multi-user.target
    EOF
  
  # Enable and start vLLM service
  - systemctl daemon-reload
  - systemctl enable vllm
  - systemctl start vllm

write_files:
  - path: /root/check_vllm.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      curl -H "Authorization: Bearer ${vllm_api_key}" http://localhost:8000/v1/models
```

### File: infrastructure/cloud-init-app.yaml

```yaml
#cloud-config
package_update: true
package_upgrade: true

packages:
  - python3-pip
  - python3-venv
  - git
  - curl
  - build-essential
  - python3-dev

runcmd:
  # Upgrade pip
  - pip3 install --upgrade pip
  
  # Create application directory
  - mkdir -p /opt/social-media-transformer
  - chown root:root /opt/social-media-transformer

write_files:
  - path: /root/.env.transformer
    permissions: '0600'
    content: |
      VLLM_API_KEY=${vllm_api_key}
  
  - path: /root/deploy.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      # Helper script for deployment
      echo "===== Deployment Helper ====="
      echo "1. Clone your repo: git clone <repo-url> /opt/social-media-transformer"
      echo "2. cd /opt/social-media-transformer"
      echo "3. Install deps: pip3 install -r requirements.txt"
      echo "4. Load API key: source /root/.env.transformer"
      echo "5. Set vLLM URL: export VLLM_BASE_URL=http://<vllm-ip>:8000"
      echo "6. Run app: uvicorn app.main:app --host 0.0.0.0 --port 8080"
      echo ""
      echo "To run app as a service, create /etc/systemd/system/transformer.service"
  
  - path: /etc/systemd/system/transformer.service.example
    permissions: '0644'
    content: |
      [Unit]
      Description=Social Media Transformer API
      After=network.target
      
      [Service]
      Type=simple
      User=root
      WorkingDirectory=/opt/social-media-transformer
      Environment="VLLM_BASE_URL=http://<REPLACE_WITH_VLLM_IP>:8000"
      Environment="VLLM_API_KEY=${vllm_api_key}"
      ExecStart=/usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
      Restart=always
      RestartSec=10
      
      [Install]
      WantedBy=multi-user.target
```

## CrewAI Agent System

### Agent Roles

**1. Content Harvester**
- **Role**: Extract key insights from source material
- **Goal**: Identify the most important points, quotes, and themes
- **Output**: Structured JSON with key insights and supporting quotes

**2. X Platform Specialist**
- **Role**: Transform content for X (Twitter)
- **Goal**: Create engaging posts that fit X best practices
- **Constraints**: 280 characters, conversational tone, thread-friendly
- **Output**: 1-3 optimized X posts

**3. LinkedIn Platform Specialist**
- **Role**: Transform content for LinkedIn
- **Goal**: Create professional posts that drive engagement on LinkedIn
- **Constraints**: 3000 character limit, professional tone, paragraph format
- **Output**: 1-2 optimized LinkedIn posts

**4. Quality Validator**
- **Role**: Verify output quality and constraints
- **Goal**: Ensure character limits, verify no hallucinations, check formatting
- **Output**: Validation report + final approved posts

### File: app/agents.py

```python
from crewai import Agent
from openai import OpenAI
import os

def get_llm_config(vllm_base_url: str, api_key: str):
    """Configure OpenAI client to point at vLLM server with API key"""
    return OpenAI(
        base_url=f"{vllm_base_url}/v1",
        api_key=api_key
    )

def create_agents(vllm_base_url: str, api_key: str):
    llm = get_llm_config(vllm_base_url, api_key)
    
    harvester = Agent(
        role="Content Harvester",
        goal="Extract the most important insights, themes, and quotable moments from source content",
        backstory="""You are an expert content analyst who excels at identifying 
        the core message and key takeaways from long-form content. You have a keen 
        eye for what will resonate on social media.""",
        llm=llm,
        verbose=True
    )
    
    x_specialist = Agent(
        role="X Platform Specialist",
        goal="Transform content into engaging X (Twitter) posts that drive engagement",
        backstory="""You are a social media expert specializing in X. You understand 
        the platform's conversational tone, the importance of hooks, and how to craft 
        posts that stop the scroll. You respect the 280 character limit and know when 
        to use threads.""",
        llm=llm,
        verbose=True
    )
    
    linkedin_specialist = Agent(
        role="LinkedIn Platform Specialist",
        goal="Transform content into professional LinkedIn posts that establish thought leadership",
        backstory="""You are a LinkedIn content strategist who knows how to write posts 
        that get engagement in professional contexts. You understand the balance between 
        valuable insights and personal storytelling that works on LinkedIn.""",
        llm=llm,
        verbose=True
    )
    
    validator = Agent(
        role="Quality Validator",
        goal="Ensure all posts meet platform requirements and maintain factual accuracy",
        backstory="""You are a meticulous quality assurance specialist. You verify that 
        posts stay within character limits, that no information has been fabricated, and 
        that the tone matches the examples provided.""",
        llm=llm,
        verbose=True
    )
    
    return {
        "harvester": harvester,
        "x_specialist": x_specialist,
        "linkedin_specialist": linkedin_specialist,
        "validator": validator
    }
```

### File: app/tasks.py

```python
from crewai import Task

def create_tasks(agents: dict, source_content: str, examples: dict, platforms: list):
    """
    Create tasks for the agent pipeline
    
    Args:
        agents: Dictionary of agent instances
        source_content: The blog post or transcript text
        examples: Dictionary with 'x' and 'linkedin' keys containing example posts
        platforms: List of platforms to generate for ['x', 'linkedin']
    """
    
    harvest_task = Task(
        description=f"""Analyze this content and extract the key insights:
        
        {source_content}
        
        Extract:
        1. The main thesis or argument
        2. 3-5 key supporting points
        3. Notable quotes (if any)
        4. The target audience and tone
        
        Return your findings in a structured format.""",
        agent=agents["harvester"],
        expected_output="Structured analysis with main points, quotes, and audience insights"
    )
    
    tasks = [harvest_task]
    
    # Create platform-specific tasks based on selection
    if "x" in platforms:
        x_examples_text = "\n\n".join(examples.get("x", [])) if examples.get("x") else "No examples provided"
        
        x_task = Task(
            description=f"""Using the harvested insights, create 1-3 engaging posts for X (Twitter).
            
            CONSTRAINTS:
            - Maximum 280 characters per post
            - Conversational, punchy tone
            - Include a hook in the first line
            - Use line breaks for readability
            
            EXAMPLES OF GOOD X POSTS:
            {x_examples_text}
            
            Study the style and tone of these examples. Match that voice while incorporating the key insights.""",
            agent=agents["x_specialist"],
            expected_output="1-3 X posts, each under 280 characters",
            context=[harvest_task]
        )
        tasks.append(x_task)
    
    if "linkedin" in platforms:
        linkedin_examples_text = "\n\n---\n\n".join(examples.get("linkedin", [])) if examples.get("linkedin") else "No examples provided"
        
        linkedin_task = Task(
            description=f"""Using the harvested insights, create 1-2 engaging posts for LinkedIn.
            
            CONSTRAINTS:
            - Maximum 3000 characters
            - Professional but authentic tone
            - Use paragraphs and spacing for readability
            - Start with a strong hook
            - End with a question or call-to-action
            
            EXAMPLES OF GOOD LINKEDIN POSTS:
            {linkedin_examples_text}
            
            Study the style and structure of these examples. Match that voice while incorporating the key insights.""",
            agent=agents["linkedin_specialist"],
            expected_output="1-2 LinkedIn posts with professional formatting",
            context=[harvest_task]
        )
        tasks.append(linkedin_task)
    
    # Validation task
    validate_task = Task(
        description=f"""Review all generated posts and verify:
        
        1. Character limits are respected (X: 280, LinkedIn: 3000)
        2. All facts match the source content (no hallucinations)
        3. Tone matches the provided examples
        4. Posts are ready to publish
        
        Return ONLY the final, validated posts with platform labels.""",
        agent=agents["validator"],
        expected_output="Final validated posts organized by platform",
        context=tasks  # Has access to all previous tasks
    )
    tasks.append(validate_task)
    
    return tasks
```

### File: app/crew.py

```python
from crewai import Crew
from app.agents import create_agents
from app.tasks import create_tasks

def run_transformation(
    source_content: str,
    examples: dict,
    platforms: list,
    vllm_base_url: str,
    vllm_api_key: str
) -> str:
    """
    Execute the multi-agent content transformation pipeline
    
    Returns:
        String containing the final validated posts
    """
    
    agents = create_agents(vllm_base_url, vllm_api_key)
    tasks = create_tasks(agents, source_content, examples, platforms)
    
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process="sequential",  # Tasks run in order
        verbose=True
    )
    
    result = crew.kickoff()
    
    return result
```

## File Processing

### File: app/file_processor.py

```python
import pypdf
from typing import List

def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from a txt file"""
    return file_content.decode('utf-8')

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from a PDF file"""
    import io
    pdf_file = io.BytesIO(file_content)
    pdf_reader = pypdf.PdfReader(pdf_file)
    
    text = []
    for page in pdf_reader.pages:
        text.append(page.extract_text())
    
    return "\n\n".join(text)

def parse_examples(file_content: bytes, file_extension: str) -> List[str]:
    """
    Parse example posts from a file
    Assumes examples are separated by blank lines or "---"
    """
    if file_extension == ".pdf":
        text = extract_text_from_pdf(file_content)
    else:
        text = extract_text_from_txt(file_content)
    
    # Split by common separators
    examples = []
    for separator in ["\n---\n", "\n\n\n"]:
        if separator in text:
            examples = [e.strip() for e in text.split(separator) if e.strip()]
            break
    
    # If no separators found, treat whole file as one example
    if not examples:
        examples = [text.strip()]
    
    return examples
```

## FastAPI Application

### File: app/models.py

```python
from pydantic import BaseModel
from typing import List, Optional

class TransformRequest(BaseModel):
    platforms: List[str]  # ["x", "linkedin"]

class TransformResponse(BaseModel):
    result: str
    status: str
```

### File: app/main.py

```python
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from typing import Optional, List

from app.file_processor import extract_text_from_txt, extract_text_from_pdf, parse_examples
from app.crew import run_transformation
from app.models import TransformResponse

app = FastAPI(title="Social Media Content Transformer")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Get vLLM configuration from environment variables
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
VLLM_API_KEY = os.getenv("VLLM_API_KEY")

if not VLLM_API_KEY:
    raise ValueError("VLLM_API_KEY environment variable must be set")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/transform", response_model=TransformResponse)
async def transform_content(
    source_file: UploadFile = File(...),
    platforms: str = Form(...),  # Comma-separated: "x,linkedin"
    x_examples_file: Optional[UploadFile] = File(None),
    linkedin_examples_file: Optional[UploadFile] = File(None)
):
    """
    Transform source content into platform-specific social media posts
    """
    
    try:
        # Parse platforms
        platform_list = [p.strip() for p in platforms.split(",")]
        if not all(p in ["x", "linkedin"] for p in platform_list):
            raise HTTPException(status_code=400, detail="Invalid platform selection")
        
        # Read source content
        source_content_bytes = await source_file.read()
        file_ext = os.path.splitext(source_file.filename)[1].lower()
        
        if file_ext == ".pdf":
            source_content = extract_text_from_pdf(source_content_bytes)
        elif file_ext == ".txt":
            source_content = extract_text_from_txt(source_content_bytes)
        else:
            raise HTTPException(status_code=400, detail="Source file must be .txt or .pdf")
        
        # Parse example files if provided
        examples = {}
        
        if x_examples_file:
            x_content = await x_examples_file.read()
            x_ext = os.path.splitext(x_examples_file.filename)[1].lower()
            examples["x"] = parse_examples(x_content, x_ext)
        
        if linkedin_examples_file:
            linkedin_content = await linkedin_examples_file.read()
            linkedin_ext = os.path.splitext(linkedin_examples_file.filename)[1].lower()
            examples["linkedin"] = parse_examples(linkedin_content, linkedin_ext)
        
        # Run the transformation
        result = run_transformation(
            source_content=source_content,
            examples=examples,
            platforms=platform_list,
            vllm_base_url=VLLM_BASE_URL,
            vllm_api_key=VLLM_API_KEY
        )
        
        return TransformResponse(result=str(result), status="success")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transformation failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "vllm_url": VLLM_BASE_URL}
```

## Frontend

### File: static/index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Media Content Transformer</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <h1>Social Media Content Transformer</h1>
        <p>Transform your long-form content into optimized social media posts</p>
        
        <form id="transformForm">
            <div class="form-group">
                <label for="sourceFile">Source Content (required)</label>
                <input type="file" id="sourceFile" name="sourceFile" accept=".txt,.pdf" required>
                <small>Upload your blog post or transcript (.txt or .pdf)</small>
            </div>
            
            <div class="form-group">
                <label>Target Platforms</label>
                <div class="checkbox-group">
                    <label>
                        <input type="checkbox" name="platform" value="x" checked>
                        X (Twitter)
                    </label>
                    <label>
                        <input type="checkbox" name="platform" value="linkedin" checked>
                        LinkedIn
                    </label>
                </div>
            </div>
            
            <div class="form-group">
                <label for="xExamples">X Examples (optional)</label>
                <input type="file" id="xExamples" name="xExamples" accept=".txt,.pdf">
                <small>Upload examples of successful X posts</small>
            </div>
            
            <div class="form-group">
                <label for="linkedinExamples">LinkedIn Examples (optional)</label>
                <input type="file" id="linkedinExamples" name="linkedinExamples" accept=".txt,.pdf">
                <small>Upload examples of successful LinkedIn posts</small>
            </div>
            
            <button type="submit" id="submitBtn">Transform Content</button>
        </form>
        
        <div id="loading" style="display: none;">
            <p>Processing... This may take a minute.</p>
        </div>
        
        <div id="results" style="display: none;">
            <h2>Generated Posts</h2>
            <pre id="resultContent"></pre>
            <button id="copyBtn">Copy to Clipboard</button>
        </div>
        
        <div id="error" style="display: none;">
            <h2>Error</h2>
            <p id="errorContent"></p>
        </div>
    </div>
    
    <script>
        const form = document.getElementById('transformForm');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const error = document.getElementById('error');
        const submitBtn = document.getElementById('submitBtn');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Reset UI
            loading.style.display = 'block';
            results.style.display = 'none';
            error.style.display = 'none';
            submitBtn.disabled = true;
            
            // Gather form data
            const formData = new FormData();
            formData.append('source_file', document.getElementById('sourceFile').files[0]);
            
            // Get selected platforms
            const platforms = Array.from(document.querySelectorAll('input[name="platform"]:checked'))
                .map(cb => cb.value);
            formData.append('platforms', platforms.join(','));
            
            // Add example files if present
            const xExamples = document.getElementById('xExamples').files[0];
            if (xExamples) formData.append('x_examples_file', xExamples);
            
            const linkedinExamples = document.getElementById('linkedinExamples').files[0];
            if (linkedinExamples) formData.append('linkedin_examples_file', linkedinExamples);
            
            try {
                const response = await fetch('/transform', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Transformation failed');
                }
                
                const data = await response.json();
                
                // Display results
                document.getElementById('resultContent').textContent = data.result;
                results.style.display = 'block';
                
            } catch (err) {
                document.getElementById('errorContent').textContent = err.message;
                error.style.display = 'block';
            } finally {
                loading.style.display = 'none';
                submitBtn.disabled = false;
            }
        });
        
        document.getElementById('copyBtn').addEventListener('click', () => {
            const content = document.getElementById('resultContent').textContent;
            navigator.clipboard.writeText(content);
            alert('Copied to clipboard!');
        });
    </script>
</body>
</html>
```

### File: static/styles.css

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f5;
    padding: 20px;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
    margin-bottom: 10px;
    color: #333;
}

h2 {
    margin-top: 30px;
    margin-bottom: 15px;
    color: #333;
}

p {
    color: #666;
    margin-bottom: 30px;
}

.form-group {
    margin-bottom: 25px;
}

label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #333;
}

input[type="file"] {
    display: block;
    width: 100%;
    padding: 10px;
    border: 2px solid #e0e0e0;
    border-radius: 4px;
    cursor: pointer;
}

small {
    display: block;
    margin-top: 5px;
    color: #999;
    font-size: 13px;
}

.checkbox-group {
    display: flex;
    gap: 20px;
}

.checkbox-group label {
    display: flex;
    align-items: center;
    font-weight: normal;
}

.checkbox-group input[type="checkbox"] {
    margin-right: 8px;
}

button {
    background: #007bff;
    color: white;
    border: none;
    padding: 12px 30px;
    border-radius: 4px;
    font-size: 16px;
    cursor: pointer;
    transition: background 0.2s;
}

button:hover {
    background: #0056b3;
}

button:disabled {
    background: #ccc;
    cursor: not-allowed;
}

#loading {
    margin-top: 30px;
    padding: 20px;
    background: #e7f3ff;
    border-radius: 4px;
    text-align: center;
}

#results {
    margin-top: 30px;
}

#resultContent {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 4px;
    white-space: pre-wrap;
    max-height: 500px;
    overflow-y: auto;
    margin-bottom: 15px;
}

#copyBtn {
    background: #28a745;
}

#copyBtn:hover {
    background: #218838;
}

#error {
    margin-top: 30px;
    padding: 20px;
    background: #f8d7da;
    border-radius: 4px;
    color: #721c24;
}
```

## Requirements File

### File: requirements.txt

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
crewai==0.1.0
crewai-tools==0.1.0
openai==1.3.0
pypdf==3.17.0
python-multipart==0.0.6
pydantic==2.5.0
```

## Deployment Instructions

### 1. Deploy Both Servers with Terraform

```bash
cd infrastructure

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Deploy both servers
terraform apply

# Save the output
terraform output
```

You'll get output showing both IP addresses and deployment instructions.

### 2. Wait for vLLM Server to be Ready

The vLLM server needs 15-20 minutes to download the model and start serving.

Monitor progress:
```bash
# SSH to vLLM server
ssh root@<vllm-ip>

# Check vLLM service status
systemctl status vllm

# Watch logs
journalctl -u vllm -f

# Test endpoint (once running) - note the Authorization header
curl -H "Authorization: Bearer <your-api-key>" http://localhost:8000/v1/models
```

### 3. Deploy Application Code

SSH to the application server:
```bash
ssh root@<app-ip>
```

Clone your repository:
```bash
cd /opt
git clone <your-repo-url> social-media-transformer
cd social-media-transformer
```

Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

Set environment variables:
```bash
# Load the API key that was written by cloud-init
source /root/.env.transformer

# Set the vLLM URL
export VLLM_BASE_URL=http://<vllm-ip>:8000
```

Run the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Access the web interface at `http://<app-ip>:8080`

### 4. (Optional) Run as Systemd Service

For production, set up the app as a service:

```bash
# Copy and edit the example service file
cp /etc/systemd/system/transformer.service.example /etc/systemd/system/transformer.service

# Edit to replace <REPLACE_WITH_VLLM_IP> with actual IP
nano /etc/systemd/system/transformer.service
# The VLLM_API_KEY is already set correctly from the template

# Enable and start
systemctl daemon-reload
systemctl enable transformer
systemctl start transformer

# Check status
systemctl status transformer
```

## Testing the System

### 1. Verify vLLM is Running

```bash
# From vLLM server
curl -H "Authorization: Bearer <your-api-key>" http://localhost:8000/v1/models

# From another machine
curl -H "Authorization: Bearer <your-api-key>" http://<vllm-ip>:8000/v1/models
```

### 2. Test the Web Application

1. Create a test blog post (save as `test_blog.txt`)
2. Create example X posts (save as `x_examples.txt` with posts separated by `---`)
3. Create example LinkedIn posts (save as `linkedin_examples.txt`)
4. Upload files through the web interface at `http://<app-ip>:8080`
5. Select target platforms
6. Submit and wait for results

### 3. Test API Directly (Optional)

```bash
curl -X POST http://<app-ip>:8080/transform \
  -F "source_file=@test_blog.txt" \
  -F "platforms=x,linkedin" \
  -F "x_examples_file=@x_examples.txt" \
  -F "linkedin_examples_file=@linkedin_examples.txt"
```

## Configuration

### Terraform Variables

Create `infrastructure/terraform.tfvars`:
```hcl
linode_token = "your-linode-api-token-here"
region       = "us-east"  # GPU instances are available in this region
vllm_api_key = "your-secure-api-key-here"  # Generate a strong random key
```

Or set as environment variables:
```bash
export TF_VAR_linode_token="your-token"
export TF_VAR_vllm_api_key="your-secure-api-key"
```

**Generating a secure API key:**
```bash
# On Linux/Mac
openssl rand -hex 32

# Or use Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Application Environment Variables

Set on the application server before running uvicorn:

- `VLLM_BASE_URL`: Base URL for the vLLM server (e.g., `http://123.45.67.89:8000`)
- `VLLM_API_KEY`: API key for authenticating with vLLM (same as in Terraform variables)

The API key is automatically written to `/root/.env.transformer` by cloud-init.

Example:
```bash
source /root/.env.transformer  # Loads VLLM_API_KEY
export VLLM_BASE_URL=http://$(cd /path/to/terraform && terraform output -raw vllm_ip):8000
```

## Notes

### Infrastructure
- **Single Terraform deployment provisions BOTH servers:**
  - GPU server (g1-gpu-rtx6000-1) for vLLM inference
  - CPU server (g6-standard-2) for FastAPI application
- Both servers use cloud-init for initial setup
- vLLM server is fully automated - model downloads and serves automatically
- App server has dependencies pre-installed but requires manual code deployment
- Both instances are created in a single `terraform apply`

### Security
- vLLM requires API key authentication via `Authorization: Bearer <key>` header
- API key is defined in Terraform variables and injected via cloud-init
- The same API key is used by both vLLM server and the application
- Generate a secure random key (32+ characters) for production use
- API key is stored in `/root/.env.transformer` on app server (restricted to root)

### Deployment Process
- vLLM model download takes 15-20 minutes on first boot
- You must manually clone repo and install Python deps on app server
- Processing time depends on content length (expect 30-60 seconds per request)
- No database required - all processing happens in-memory
- Files are not persisted after processing

### Resource Requirements
- vLLM requires significant GPU memory - adjust instance type based on model size
- App server can be scaled down if needed (g6-standard-1 for 1 CPU/2GB RAM)
- Both servers should be in the same Linode region for lower latency
- GPU instances are only available in specific regions (us-east confirmed for RTX 6000, check Linode docs for others)

## Future Enhancements (Out of Scope)

- Add async processing with job queue
- Store processing history in database
- Support more platforms (Instagram, Facebook)
- Add image generation for visual posts
- Implement user authentication
- Add analytics tracking
