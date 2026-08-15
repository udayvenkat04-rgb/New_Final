import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file safely
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    def __init__(self):
        # Database Configurations
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
        self.DATABASE_NAME: str = os.getenv("DATABASE_NAME", "missing_person_db")

        # SMTP Configurations
        self.SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        
        try:
            self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
        except ValueError:
            self.SMTP_PORT = 587
            
        self.SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
        self.SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")

        # Notification & Email Alert Settings
        self.EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() in ("true", "1", "t", "yes")
        try:
            self.MAX_NOTIFICATION_ATTEMPTS: int = int(os.getenv("MAX_NOTIFICATION_ATTEMPTS", "3"))
        except ValueError:
            self.MAX_NOTIFICATION_ATTEMPTS = 3

        # Aliases / Compatibility variables for older implementation references
        self.SMTP_USER: str = self.SMTP_USERNAME
        self.ALERT_RECEIVER_EMAIL: str = self.SMTP_FROM_EMAIL

        # System & Security Settings
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key-32-chars-long-or-more")
        
        try:
            self.FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", 0.60))
        except ValueError:
            self.FACE_MATCH_THRESHOLD = 0.60

        try:
            self.KNN_N_NEIGHBORS: int = int(os.getenv("KNN_N_NEIGHBORS", 5))
        except ValueError:
            self.KNN_N_NEIGHBORS = 5

        # Default Map Coordinate Configurations
        try:
            self.DEFAULT_LATITUDE: float = float(os.getenv("DEFAULT_LATITUDE", 28.6139))
        except ValueError:
            self.DEFAULT_LATITUDE = 28.6139

        try:
            self.DEFAULT_LONGITUDE: float = float(os.getenv("DEFAULT_LONGITUDE", 77.2090))
        except ValueError:
            self.DEFAULT_LONGITUDE = 77.2090

        try:
            self.DEFAULT_ZOOM: int = int(os.getenv("DEFAULT_ZOOM", 12))
        except ValueError:
            self.DEFAULT_ZOOM = 12

        # Media Storage Directories
        self.DATA_DIR: str = str(BASE_DIR / "data")
        self.UPLOADS_DIR: str = str(BASE_DIR / "data" / "uploads")
        self.FACES_DIR: str = str(BASE_DIR / "data" / "faces")
        self.VIDEOS_DIR: str = str(BASE_DIR / "data" / "videos")
        self.MODELS_DIR: str = str(BASE_DIR / "data" / "models")

        # MediaPipe Face Landmarker configuration
        # Download from: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
        self.MEDIAPIPE_MODEL_PATH: str = os.getenv(
            "MEDIAPIPE_MODEL_PATH",
            str(BASE_DIR / "data" / "models" / "face_landmarker.task")
        )
        try:
            self.MEDIAPIPE_NUM_FACES: int = int(os.getenv("MEDIAPIPE_NUM_FACES", "5"))
        except ValueError:
            self.MEDIAPIPE_NUM_FACES = 5
        try:
            self.MEDIAPIPE_MIN_DETECTION_CONF: float = float(os.getenv(
                "MEDIAPIPE_MIN_DETECTION_CONF", "0.5"
            ))
        except ValueError:
            self.MEDIAPIPE_MIN_DETECTION_CONF = 0.5
        try:
            self.MEDIAPIPE_MIN_PRESENCE_CONF: float = float(os.getenv(
                "MEDIAPIPE_MIN_PRESENCE_CONF", "0.5"
            ))
        except ValueError:
            self.MEDIAPIPE_MIN_PRESENCE_CONF = 0.5
        try:
            self.MEDIAPIPE_MIN_TRACKING_CONF: float = float(os.getenv(
                "MEDIAPIPE_MIN_TRACKING_CONF", "0.5"
            ))
        except ValueError:
            self.MEDIAPIPE_MIN_TRACKING_CONF = 0.5

        # Video Processing Configuration
        try:
            self.MAX_VIDEO_SIZE_MB: int = int(os.getenv("MAX_VIDEO_SIZE_MB", "100"))
        except ValueError:
            self.MAX_VIDEO_SIZE_MB = 100

        try:
            self.VIDEO_SAMPLE_INTERVAL_SECONDS: float = float(os.getenv("VIDEO_SAMPLE_INTERVAL_SECONDS", "1.0"))
        except ValueError:
            self.VIDEO_SAMPLE_INTERVAL_SECONDS = 1.0

        try:
            self.MAX_VIDEO_FRAMES_TO_PROCESS: int = int(os.getenv("MAX_VIDEO_FRAMES_TO_PROCESS", "500"))
        except ValueError:
            self.MAX_VIDEO_FRAMES_TO_PROCESS = 500

        try:
            self.VIDEO_SIGHTING_GAP_SECONDS: float = float(os.getenv("VIDEO_SIGHTING_GAP_SECONDS", "5.0"))
        except ValueError:
            self.VIDEO_SIGHTING_GAP_SECONDS = 5.0

        self.ALLOWED_VIDEO_EXTENSIONS: set[str] = {".mp4", ".avi", ".mov", ".mkv"}

        # Validate required configurations
        self.validate()

    def validate(self):
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be specified in the environment/configuration.")
        if not self.DATABASE_NAME:
            raise ValueError("DATABASE_NAME must be specified in the environment/configuration.")

    def __repr__(self):
        # Safe repr that never prints secrets (e.g. SMTP_PASSWORD)
        return (
            f"Settings(DATABASE_URL='{self.DATABASE_URL}', DATABASE_NAME='{self.DATABASE_NAME}', "
            f"SMTP_HOST='{self.SMTP_HOST}', SMTP_PORT={self.SMTP_PORT}, "
            f"SMTP_USERNAME='{self.SMTP_USERNAME}', SMTP_FROM_EMAIL='{self.SMTP_FROM_EMAIL}', "
            f"SMTP_PASSWORD='[MASKED]')"
        )

# Centralized Settings Instance
settings = Settings()

# Export settings as global attributes for legacy module import compatibility
DATABASE_URL = settings.DATABASE_URL
DATABASE_NAME = settings.DATABASE_NAME
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USERNAME = settings.SMTP_USERNAME
SMTP_PASSWORD = settings.SMTP_PASSWORD
SMTP_FROM_EMAIL = settings.SMTP_FROM_EMAIL
EMAIL_ENABLED = settings.EMAIL_ENABLED
MAX_NOTIFICATION_ATTEMPTS = settings.MAX_NOTIFICATION_ATTEMPTS

# Backward-compatible variables
SMTP_USER = settings.SMTP_USER
ALERT_RECEIVER_EMAIL = settings.ALERT_RECEIVER_EMAIL
SECRET_KEY = settings.SECRET_KEY
APP_ENV = settings.APP_ENV
FACE_MATCH_THRESHOLD = settings.FACE_MATCH_THRESHOLD
KNN_N_NEIGHBORS = settings.KNN_N_NEIGHBORS
DEFAULT_LATITUDE = settings.DEFAULT_LATITUDE
DEFAULT_LONGITUDE = settings.DEFAULT_LONGITUDE
DEFAULT_ZOOM = settings.DEFAULT_ZOOM
DATA_DIR = settings.DATA_DIR
UPLOADS_DIR = settings.UPLOADS_DIR
FACES_DIR = settings.FACES_DIR
VIDEOS_DIR = settings.VIDEOS_DIR
MODELS_DIR = settings.MODELS_DIR
MEDIAPIPE_MODEL_PATH = settings.MEDIAPIPE_MODEL_PATH
MEDIAPIPE_NUM_FACES = settings.MEDIAPIPE_NUM_FACES
MEDIAPIPE_MIN_DETECTION_CONF = settings.MEDIAPIPE_MIN_DETECTION_CONF
MEDIAPIPE_MIN_PRESENCE_CONF = settings.MEDIAPIPE_MIN_PRESENCE_CONF
MEDIAPIPE_MIN_TRACKING_CONF = settings.MEDIAPIPE_MIN_TRACKING_CONF
MAX_VIDEO_SIZE_MB = settings.MAX_VIDEO_SIZE_MB
VIDEO_SAMPLE_INTERVAL_SECONDS = settings.VIDEO_SAMPLE_INTERVAL_SECONDS
MAX_VIDEO_FRAMES_TO_PROCESS = settings.MAX_VIDEO_FRAMES_TO_PROCESS
VIDEO_SIGHTING_GAP_SECONDS = settings.VIDEO_SIGHTING_GAP_SECONDS
ALLOWED_VIDEO_EXTENSIONS = settings.ALLOWED_VIDEO_EXTENSIONS


# Initialize directories if they do not exist
for directory in [DATA_DIR, UPLOADS_DIR, FACES_DIR, VIDEOS_DIR, MODELS_DIR]:
    os.makedirs(directory, exist_ok=True)


