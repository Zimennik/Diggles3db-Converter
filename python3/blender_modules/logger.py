import datetime

# Create a log file for debugging
log_file_path = 'blender_log.txt'
log_file = open(log_file_path, 'w')

def log(message, level="INFO"):
    """Log a message with timestamp and level."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message)
    log_file.write(log_message + "\n")
    log_file.flush()  # Ensure the message is written immediately

def error(message):
    """Log an error message."""
    log(message, "ERROR")

def close_log():
    """Close the log file."""
    log_file.close()

# Initial logs
log("DEBUG: Blender script is starting!")