# Auto Ontology Generator

## 1. Project Overview
The **Auto Ontology Generator** is a Python-based application that automatically generates an ontology from structured database data.
It analyzes database tables, identifies entities and their attributes, detects relationships between tables, and uses NVIDIA AI models to generate semantic descriptions and validate relationships.
The project aims to reduce the manual effort involved in creating ontologies for different datasets.

## 2. Key Features
- Connects to a PostgreSQL database.
- Reads database schemas and sample records.
- Profiles columns and identifies primary key candidates.
- Detects possible relationships between tables.
- Uses NVIDIA AI models to generate semantic descriptions.
- Integrates with NVIDIA Auto Ontology.
- Validates the generated ontology.
- Exports ontology in JSON and YAML formats.
- Provides a Streamlit-based user interface.

## 3. How It Works
The project follows these steps:
1. **Database Connection:** Connects to PostgreSQL and retrieves database information.
2. **Schema Extraction:** Reads tables, columns, data types, and sample records.
3. **Data Profiling:** Analyzes columns, null values, unique values, and sample data.
4. **Primary Key Detection:** Identifies columns that can act as primary keys.
5. **Relationship Detection:** Finds possible relationships between tables using column names, data types, uniqueness, and value matching.
6. **AI-Based Semantic Generation:** Uses NVIDIA-hosted LLMs to generate entity descriptions and attribute meanings.
7. **Ontology Integration:** Retrieves semantic graph information from the NVIDIA Auto Ontology service.
8. **Validation:** Checks the generated ontology for errors and invalid references.
9. **Export:** Saves the final ontology as JSON and YAML files.

## 4. Project Structure

Auto-Ontology-Padmapriyaa/
│
├── ai/                  # NVIDIA AI integration and validation
├── analysis/            # Data profiling and relationship detection
├── database/            # Database connection and schema extraction
├── ontology/            # Ontology generation and validation
├── data/                # Dataset files
├── output/              # Generated ontology files               
├── main.py              # Main execution file
├── ui.py                # Streamlit user interface
├── requirements.txt     # Project dependencies
├── .env.example         # Environment configuration template
└── README.md

## 5. Prerequisites
Make sure you have the following installed:
- Python 3.10 or later
- PostgreSQL
- NVIDIA API key
- NVIDIA Auto Ontology service
- Git (optional)

## 6. Installation and Setup
### Step 1: Clone the Repository
bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Auto-Ontology-Padmapriyaa

### Step 2: Create a Virtual Environment
bash
python -m venv venv

Activate it on Windows:
bash
venv\Scripts\activate

### Step 3: Install Dependencies
bash
pip install -r requirements.txt

### Step 4: Configure Environment Variables
Create a '.env' file in the project root and add:
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
NVIDIA_API_KEY=your_nvidia_api_key
NVIDIA_AUTO_ONTOLOGY_URL=http://localhost:3001

Replace the placeholder values with your actual PostgreSQL and NVIDIA credentials.

### Step 5: Prepare the Database
- Start PostgreSQL.
- Create a database.
- Load your dataset tables into the database.
- Update the database credentials in `.env`.

### Step 6: Start NVIDIA Auto Ontology
Start the NVIDIA Auto Ontology service separately using its Docker Compose setup.
Make sure the service is running and accessible at the URL configured in '.env'.

## 7. Running the Project
### Run Using the Command Line
From the project root, execute:
bash
python main.py

Follow the prompts or configuration provided by the application.

### Option 2: Run Using the Streamlit Interface
Execute:
bash
streamlit run ui.py

Open the local URL displayed in the terminal, usually:
http://localhost:8501

Select the database and click the ontology generation button to start the process.

## 8. Output
After successful execution, generated files are saved in the 'output/' directory.

olist_ontology.json- Generated ontology in JSON format 
olist_ontology.yaml- Generated ontology in YAML format
validation_report.json- Ontology validation results

The output filenames may vary depending on the selected database.

## 9. Technologies Used
- **Python** – Core implementation
- **PostgreSQL** – Structured data storage
- **SQLAlchemy** – Database connectivity
- **Pandas** – Data profiling and analysis
- **NVIDIA API** – AI-powered semantic generation
- **NVIDIA Auto Ontology** – Semantic graph integration
- **Streamlit** – User interface
- **JSON and YAML** – Ontology export formats

## 10. Future Improvements
- Support for additional database systems.
- Improved detection of complex and composite relationships.
- Support for larger datasets.
- Enhanced ontology visualization.
- More advanced ontology validation.
