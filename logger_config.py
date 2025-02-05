# import os
# import logging
# from datetime import datetime


# # Logging configuration
# log_format = "[%(asctime)s] %(lineno)d - %(filename)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
# now = datetime.now()

# # Create date-based folder (MM_DD_YYYY)
# LOG_FILE_FOLDER = now.strftime("%m_%d_%Y")
# # Create time-based file (HH-MM-SS.log)
# LOG_FILE = now.strftime("%H-%M-%S") + ".log"

# # Create logs directory structure
# logs_path = os.path.join(
#     os.path.dirname(os.path.abspath(__file__)), "logs", LOG_FILE_FOLDER
# )
# os.makedirs(logs_path, exist_ok=True)

# LOG_FILE_PATH = os.path.join(logs_path, LOG_FILE)

# # Setup logging configuration
# try:
#     logging.basicConfig(
#         level=logging.INFO,
#         format=log_format,
#         handlers=[
#             logging.FileHandler(LOG_FILE_PATH, mode="a", encoding="utf-8"),
#             logging.StreamHandler(),
#         ],
#         force=True,
#     )
#     logger = logging.getLogger(__name__)
#     logger.info("Logging initialized successfully")
#     logger.info(f"Log file created at: {LOG_FILE_PATH}")
# except Exception as e:
#     print(f"Error setting up logging: {str(e)}")
#     raise

# # Bellow code add log rotation to prevent the logs directory from growing too large over time.
# # Remove above code and uncomment below code after having a stable version means when no more testing is required.
# # Log rotation and cleanup configuration
# # from datetime import datetime, timedelta
# # import shutil
# # from logging.handlers import RotatingFileHandler
# # MAX_LOG_DAYS = 30  # Keep logs for 30 days
# # MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB per file
# # MAX_LOG_FILES = 5  # Number of backup files per log

# # def cleanup_old_logs():
# #     """Remove log folders older than MAX_LOG_DAYS"""
# #     logs_base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
# #     cutoff_date = datetime.now() - timedelta(days=MAX_LOG_DAYS)

# #     try:
# #         for folder in os.listdir(logs_base_path):
# #             folder_path = os.path.join(logs_base_path, folder)
# #             if not os.path.isdir(folder_path):
# #                 continue

# #             try:
# #                 # Convert folder name (MM_DD_YYYY) to datetime
# #                 folder_date = datetime.strptime(folder, "%m_%d_%Y")
# #                 if folder_date < cutoff_date:
# #                     shutil.rmtree(folder_path)
# #                     print(f"Removed old log folder: {folder}")
# #             except ValueError:
# #                 # Skip folders that don't match our date format
# #                 continue
# #     except Exception as e:
# #         print(f"Error during log cleanup: {str(e)}")

# # # Run cleanup before setting up new logs
# # cleanup_old_logs()

# # # Setup logging configuration with rotation
# # try:
# #     logging.basicConfig(
# #         level=logging.INFO,
# #         format=log_format,
# #         handlers=[
# #             RotatingFileHandler(
# #                 LOG_FILE_PATH,
# #                 maxBytes=MAX_LOG_SIZE,
# #                 backupCount=MAX_LOG_FILES,
# #                 encoding="utf-8"
# #             ),
# #             logging.StreamHandler(),
# #         ],
# #         force=True,
# #     )
# #     logger = logging.getLogger(__name__)
# #     logger.info("Logging initialized successfully")
# #     logger.info(f"Log file created at: {LOG_FILE_PATH}")
# # except Exception as e:
# #     print(f"Error setting up logging: {str(e)}")
# #     raise


import os
import logging
import shutil
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler


class CustomLogger:
    _instance = None
    _logger = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CustomLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, project_name="prospects"):
        if CustomLogger._logger is not None:
            return

        self.project_name = project_name
        self.log_format = "[%(asctime)s] %(lineno)d - %(filename)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
        self.now = datetime.now()

        # Constants
        self.MAX_LOG_DAYS = 30
        self.MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
        self.MAX_LOG_FILES = 5

        # Setup log paths
        self.LOG_FILE_FOLDER = self.now.strftime("%m_%d_%Y")
        self.LOG_FILE = self.now.strftime("%H-%M-%S") + ".log"

        # Get the root directory (where your main script is)
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.logs_path = os.path.join(self.root_dir, "logs", self.LOG_FILE_FOLDER)
        os.makedirs(self.logs_path, exist_ok=True)

        self.LOG_FILE_PATH = os.path.join(self.logs_path, self.LOG_FILE)

        # Initialize logger
        self._setup_logger()

    def cleanup_old_logs(self):
        """Remove log folders older than MAX_LOG_DAYS"""
        logs_base_path = os.path.join(self.root_dir, "logs")
        cutoff_date = datetime.now() - timedelta(days=self.MAX_LOG_DAYS)

        try:
            for folder in os.listdir(logs_base_path):
                folder_path = os.path.join(logs_base_path, folder)
                if not os.path.isdir(folder_path):
                    continue

                try:
                    folder_date = datetime.strptime(folder, "%m_%d_%Y")
                    if folder_date < cutoff_date:
                        shutil.rmtree(folder_path)
                        print(f"Removed old log folder: {folder}")
                except ValueError:
                    continue
        except Exception as e:
            print(f"Error during log cleanup: {str(e)}")

    def _setup_logger(self):
        """Configure and return a logger instance"""
        if CustomLogger._logger is not None:
            return

        try:
            # Run cleanup before setting up new logs
            self.cleanup_old_logs()

            # Setup logging configuration
            logging.basicConfig(
                level=logging.INFO,
                format=self.log_format,
                handlers=[
                    RotatingFileHandler(
                        self.LOG_FILE_PATH,
                        maxBytes=self.MAX_LOG_SIZE,
                        backupCount=self.MAX_LOG_FILES,
                        encoding="utf-8",
                    ),
                    logging.StreamHandler(),
                ],
                force=True,
            )

            CustomLogger._logger = logging.getLogger(self.project_name)
            CustomLogger._logger.info("Logging initialized successfully")
            CustomLogger._logger.info(f"Log file created at: {self.LOG_FILE_PATH}")

        except Exception as e:
            print(f"Error setting up logging: {str(e)}")
            raise

    @classmethod
    def get_logger(cls, project_name="prospects"):
        """Get or create a logger instance"""
        if cls._logger is None:
            cls(project_name)
        return cls._logger


# Helper function to get logger instance
def get_logger(project_name="prospects"):
    return CustomLogger.get_logger(project_name)
