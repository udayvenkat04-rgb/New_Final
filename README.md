# Missing Person Identification System

A comprehensive, multi-role Streamlit web application designed to help law enforcement and the public report, track, and identify missing persons using face detection, embedding matching, and spatial mapping.

This application is powered by **MongoDB** for database operations, **PyMongo** for Python connectivity, and **Streamlit** for the frontend dashboard interface.

---

## Features

- **Multi-Role Authentication**: Secure login flow for Admins, Officers, and a Public Portal for anonymous tips.
- **Missing Persons Directory**: Searchable registry of cases with age, gender, location, status filters, and historical timelines.
- **AI-Powered Face Matching**: Drag-and-drop face matching against the registered database with matching confidence scores.
- **Interactive Tracking Board (Map)**: Live Folium map visualization of all reported sightings, last-seen positions, and cases.
- **Report Sightings & Tips**: Public/Officer sighting submission with geo-coordinates and details.
- **CCTV Stream Simulation**: Simulated scan mode to search frames in surveillance video feeds.

---

## Installation & Setup

### 1. MongoDB Database Setup
Ensure that you have MongoDB installed and running on your system.
- **Windows**: Install [MongoDB Community Edition](https://www.mongodb.com/try/download/community) and ensure the MongoDB service is running. You can start it in Windows Command Prompt/PowerShell running as **Administrator**:
  ```cmd
  net start MongoDB
  ```
  Alternatively, you can run the MongoDB daemon directly:
  ```cmd
  mongod
  ```
- Default connection port: `mongodb://localhost:27017`

### 2. Clone the Repository
```bash
git clone <repository_url>
cd missing_person_identification
```

### 3. Install Dependencies
Install the required python packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Configure the environment file. Create a file named `.env` at the root of the project:
```ini
DATABASE_URL=mongodb://localhost:27017
DATABASE_NAME=missing_person_db

# (Optional Configurations)
FACE_MATCH_THRESHOLD=0.60
DEFAULT_LATITUDE=28.6139
DEFAULT_LONGITUDE=77.2090
DEFAULT_ZOOM=12
```

### 5. Seed the MongoDB Database
Populate your MongoDB database with the default system collections and data using the MongoDB seed utility:
```bash
python -m database.seed_mongo
```
This utility sets up collections for `users`, `missing_persons`, `face_vectors`, `sightings`, `match_results`, and `case_history` and automatically creates optimized query indexes.

### 6. Run the Application
Start the Streamlit application:
```bash
streamlit run app.py
```

---

## Project Structure

```
missing_person_identification/
│
├── app.py                     # Main Streamlit entrance & layout router
├── requirements.txt           # Python dependency file
├── README.md                  # Project documentation
├── .env                       # Local environment variables
│
├── config/                    # Settings & env loaders (python-dotenv)
├── database/                  # MongoDB client connection, collections & seed logic
├── auth/                      # Authentication mock helpers & role-based helpers
├── services/                  # Business logic (face detection, maps, cctv simulation)
├── pages/                     # Streamlit views (pages)
├── utils/                     # Validators, security helpers
├── data/                      # Local storage for uploads & face photos
└── tests/                     # Automated testing suite (pytest)
```

---

## Database Health Checks & Diagnostics
If MongoDB is offline or unavailable when running Streamlit, the dashboard pages will automatically show a clear error banner and prompt you to start your local MongoDB daemon.
You can run automated test suites to verify database connectivity and access:
```bash
pytest
```
