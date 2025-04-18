import os
import time
import shutil
import logging
import socket
import threading
import sys
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, PatternMatchingEventHandler
from datetime import datetime, timedelta
from colorama import init, Fore, Style

# Initialize colorama
init()

# Custom formatter with colors
class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.ERROR: Fore.RED + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.INFO: Fore.GREEN + "%(asctime)s - %(levelname)s - %(message)s" + Style.RESET_ALL,
        logging.DEBUG: "%(asctime)s - %(levelname)s - %(message)s"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler without colors
file_handler = logging.FileHandler("sync_log.txt")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(file_handler)

# Console handler with colors
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Remote directory synchronization tool')
    parser.add_argument('--resource', required=True, help='Source directory path')
    parser.add_argument('--destination', required=True, help='Destination directory path')
    parser.add_argument('--initial-sync', action='store_true', help='Perform initial sync without asking')
    parser.add_argument('--no-watch', action='store_true', help='Exit after initial sync without watching for changes')
    return parser.parse_args()

# Get command line arguments
args = parse_arguments()
REMOTE_DIR = args.resource
LOCAL_DIR = args.destination

# Timeout and retry settings
TIMEOUT = 30  # Operation timeout (seconds)
MAX_RETRIES = 3  # Maximum retry attempts
RETRY_DELAY = 5  # Retry wait time (seconds)

# Runtime statistics
start_time = None  # Program start time
display_interval = 60  # Runtime display interval (seconds)
active_timers = {}  # Store all active timers

# Timer class for real-time operation duration display
class Timer:
    def __init__(self, operation_name, update_same_line=True):
        self.operation_name = operation_name
        self.start_time = time.time()
        self.last_update = self.start_time
        self.update_interval = 0.1  # Update display interval (seconds)
        self.active = True
        self.thread = None
        self.update_same_line = update_same_line
        self.task_id = f"{operation_name}_{int(time.time() * 1000)}"  # Create unique task ID
        
    def start(self):
        global active_timers
        active_timers[self.task_id] = self
        self.thread = threading.Thread(target=self._display_time)
        self.thread.daemon = True
        self.thread.start()
        return self
        
    def _display_time(self):
        while self.active:
            current_time = time.time()
            if current_time - self.last_update >= self.update_interval:
                elapsed = current_time - self.start_time
                if self.update_same_line:
                    # Use \r to update output on the same line instead of newline
                    total_elapsed = time.time() - start_time
                    sys.stdout.write(f"\r{self.operation_name}........{elapsed:.1f}s [Total: {total_elapsed:.1f}s]")
                    sys.stdout.flush()
                self.last_update = current_time
            time.sleep(0.05)  # Faster update frequency
    
    def stop(self):
        global active_timers
        self.active = False
        if self.thread:
            self.thread.join(1)  # Wait for thread to end, up to 1 second
        elapsed = time.time() - self.start_time
        # Print final result once and end with newline
        if self.update_same_line:
            total_elapsed = time.time() - start_time
            sys.stdout.write(f"\r{self.operation_name}........{elapsed:.1f}s [Total: {total_elapsed:.1f}s]\n")
            sys.stdout.flush()
        if self.task_id in active_timers:
            del active_timers[self.task_id]
        return elapsed

# Context manager to simplify timer usage
class TimerContext:
    def __init__(self, operation_name, update_same_line=True):
        self.timer = Timer(operation_name, update_same_line)
        
    def __enter__(self):
        self.timer.start()
        return self.timer
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.timer.stop()

# Remove the standalone total time display thread, as total time is now displayed directly after each operation
# def update_total_time_display():
#     global start_time
#     
#     while True:
#         total_elapsed = time.time() - start_time
#         # Display total time at the bottom
#         sys.stdout.write(f"\r\nTotal time: {total_elapsed:.1f}s")
#         sys.stdout.flush()
#         
#         # Move cursor back to original position
#         sys.stdout.write("\033[A")  # Move up one line
#         sys.stdout.flush()
#         
#         time.sleep(0.2)  # Update frequency

# Ensure directory exists, create if not
def ensure_dir_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        logging.info(f"Directory created: {dir_path}")

# Add network share mapping function
def map_network_drive():
    try:
        # Try to map network drive
        drive_letter = 'Z:'
        network_path = REMOTE_DIR
        cmd = f'net use {drive_letter} {network_path} /persistent:no'
        os.system(cmd)
        return drive_letter
    except Exception as e:
        logging.error(f"Failed to map network drive: {str(e)}")
        return None

# Check if remote directory is accessible
def is_remote_accessible():
    try:
        # First try direct access
        if os.path.exists(REMOTE_DIR):
            return True
            
        # If direct access fails, try mapping network drive
        drive_letter = map_network_drive()
        if drive_letter:
            mapped_path = f"{drive_letter}\\"
            if os.path.exists(mapped_path):
                return True
                
        # Check if server is reachable (extract IP address)
        server_ip = REMOTE_DIR.split('\\\\')[1].split('\\')[0]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((server_ip, 445))  # SMB service port
        sock.close()
        
        return False
    except Exception as e:
        logging.warning(f"Remote directory not accessible: {str(e)}")
        return False

# File operation with retry
def retry_operation(operation, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logging.warning(f"Operation failed (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise

# Safe file copy (with timeout)
def safe_copy_file(src, dst):
    def copy_with_timeout():
        try:
            # Ensure target directory exists and has correct permissions
            dst_dir = os.path.dirname(dst)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir, mode=0o777, exist_ok=True)
            
            # If target file exists, ensure it is writable
            if os.path.exists(dst):
                os.chmod(dst, 0o777)
                
            # Copy file
            shutil.copy2(src, dst)
            
            # Set target file permissions
            os.chmod(dst, 0o666)
        except PermissionError as e:
            logging.warning(f"Permission error while copying {src} to {dst}: {str(e)}")
            # Attempt to handle with elevated privileges
            if os.name == 'nt':  # Windows system
                try:
                    import ctypes
                    if not ctypes.windll.shell32.IsUserAnAdmin():
                        logging.warning("Attempting to run with elevated privileges...")
                    # Even if not admin, attempt to force set permissions
                    os.chmod(dst_dir, 0o777)
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0o666)
                except Exception as e:
                    logging.error(f"Failed to copy with elevated privileges: {str(e)}")
                    raise
            else:
                raise
    
    # Run copy operation in separate thread
    thread = threading.Thread(target=copy_with_timeout)
    thread.daemon = True
    thread.start()
    thread.join(TIMEOUT)
    
    if thread.is_alive():
        # Timeout, cannot directly stop thread, but log the issue
        logging.error(f"Copy file timeout: {src} -> {dst}")
        raise TimeoutError(f"Copy file operation timeout")
    
    return True

# Calculate and format runtime
def format_runtime(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(seconds)}s"

# Check if path should be ignored
def should_ignore_path(path):
    # Convert to relative path
    if path.startswith(REMOTE_DIR):
        rel_path = os.path.relpath(path, REMOTE_DIR)
    elif path.startswith(LOCAL_DIR):
        rel_path = os.path.relpath(path, LOCAL_DIR)
    else:
        rel_path = path

    # Split path components
    path_parts = rel_path.split(os.sep)
    
    # Ignore build directory (at any level)
    if 'build' in path_parts:
        return True
        
    return False

# Perform initial sync
def initial_sync(skip_if_exists=False):
    if skip_if_exists and os.path.exists(LOCAL_DIR) and os.listdir(LOCAL_DIR):
        logging.info("Local directory exists and is not empty, skipping initial sync")
        return
    
    logging.info("Starting initial synchronization...")
    ensure_dir_exists(LOCAL_DIR)
    
    # Check remote connection
    with TimerContext("Checking remote connection") as timer:
        if not is_remote_accessible():
            logging.error("Remote directory not accessible, cannot perform initial sync")
            return
    
    # Count files to display progress
    total_files = 0
    processed_files = 0
    sync_start_time = time.time()
    current_file = ""
    
    try:
        # First count total files (this task does not need real-time display)
        logging.info("Calculating total files...")
        
        for root, dirs, files in os.walk(REMOTE_DIR):
            # Filter out directories to be ignored
            dirs[:] = [d for d in dirs if not should_ignore_path(os.path.join(root, d))]
            
            # Only count files that should not be ignored
            for file in files:
                if not should_ignore_path(os.path.join(root, file)):
                    total_files += 1
                    if total_files % 100 == 0:
                        total_elapsed = time.time() - start_time
                        sys.stdout.write(f"\r{' ' * 100}\r")  # Clear line
                        sys.stdout.write(f"Calculating files: Found {total_files} files... [Total: {total_elapsed:.1f}s]")
                        sys.stdout.flush()
        
        # After counting, print total and newline
        total_elapsed = time.time() - start_time
        sys.stdout.write(f"\r{' ' * 100}\r")  # Clear line
        sys.stdout.write(f"Calculating files: Found {total_files} files [Total: {total_elapsed:.1f}s]\n")
        sys.stdout.flush()
        
        logging.info(f"Found {total_files} files to sync")
        
        # Start file sync
        with TimerContext(f"Syncing {total_files} files") as sync_timer:
            for root, dirs, files in os.walk(REMOTE_DIR):
                # Filter out directories to be ignored
                dirs[:] = [d for d in dirs if not should_ignore_path(os.path.join(root, d))]
                
                # Get relative path
                rel_path = os.path.relpath(root, REMOTE_DIR)
                # Calculate corresponding local path
                local_path = os.path.join(LOCAL_DIR, rel_path) if rel_path != '.' else LOCAL_DIR
                
                # Ensure local directory exists
                ensure_dir_exists(local_path)
                
                # Copy files
                for file in files:
                    remote_file = os.path.join(root, file)
                    
                    # Skip files to be ignored
                    if should_ignore_path(remote_file):
                        continue
                        
                    local_file = os.path.join(local_path, file)
                    current_file = file
                    
                    # If local file does not exist or remote file is newer, copy
                    try:
                        if not os.path.exists(local_file) or os.path.getmtime(remote_file) > os.path.getmtime(local_file):
                            with TimerContext(f"Copying file: {os.path.basename(remote_file)}") as file_timer:
                                retry_operation(safe_copy_file, remote_file, local_file)
                            
                            processed_files += 1
                            # Update progress more frequently
                            elapsed_time = time.time() - sync_start_time
                            estimated_total_time = (elapsed_time / processed_files * total_files) if processed_files > 0 else 0
                            remaining_time = estimated_total_time - elapsed_time if processed_files > 0 else 0
                            total_elapsed = time.time() - start_time
                            
                            # Enhanced progress display with line clearing
                            progress_line = (
                                f"Progress: {processed_files}/{total_files} ({int(processed_files/total_files*100)}%) | "
                                f"Current: {current_file} | "
                                f"Remaining: {format_runtime(remaining_time)} | "
                                f"Speed: {processed_files/elapsed_time:.1f} files/s | "
                                f"Total: {total_elapsed:.1f}s"
                            )
                            sys.stdout.write(f"\r{' ' * 200}\r")  # Clear line with extra space
                            sys.stdout.write(progress_line)
                            sys.stdout.flush()
                        else:
                            processed_files += 1
                            # Update progress even for skipped files
                            elapsed_time = time.time() - sync_start_time
                            estimated_total_time = (elapsed_time / processed_files * total_files) if processed_files > 0 else 0
                            remaining_time = estimated_total_time - elapsed_time if processed_files > 0 else 0
                            total_elapsed = time.time() - start_time
                            
                            progress_line = (
                                f"Progress: {processed_files}/{total_files} ({int(processed_files/total_files*100)}%) | "
                                f"Current: {current_file} (skipped) | "
                                f"Remaining: {format_runtime(remaining_time)} | "
                                f"Speed: {processed_files/elapsed_time:.1f} files/s | "
                                f"Total: {total_elapsed:.1f}s"
                            )
                            sys.stdout.write(f"\r{' ' * 200}\r")  # Clear line with extra space
                            sys.stdout.write(progress_line)
                            sys.stdout.flush()
                    except Exception as e:
                        logging.error(f"Failed to sync file: {remote_file} -> {local_file}, Error: {str(e)}")
            
            # Sync complete, print final progress
            total_elapsed = time.time() - start_time
            final_progress = (
                f"Progress: {processed_files}/{total_files} (100%) | "
                f"Completed! | "
                f"Total time: {format_runtime(total_elapsed)} | "
                f"Average speed: {processed_files/total_elapsed:.1f} files/s\n"
            )
            sys.stdout.write(f"\r{' ' * 200}\r")  # Clear line with extra space
            sys.stdout.write(final_progress)
            sys.stdout.flush()
            
        total_time = time.time() - sync_start_time
        logging.info(f"Initial sync completed! Total time: {format_runtime(total_time)}")
    except Exception as e:
        logging.error(f"Initial sync failed: {str(e)}")

# File system event handler
class SyncHandler(FileSystemEventHandler):
    def _should_handle_event(self, event):
        if should_ignore_path(event.src_path):
            return False
        if hasattr(event, 'dest_path') and event.dest_path and should_ignore_path(event.dest_path):
            return False
        return True
    
    def on_created(self, event):
        if self._should_handle_event(event):
            self._sync_event(event, "Created")
    
    def on_modified(self, event):
        if self._should_handle_event(event):
            self._sync_event(event, "Modified")
    
    def on_moved(self, event):
        if not self._should_handle_event(event):
            return
            
        # Check if source and destination paths exist
        if not event.src_path or not event.dest_path:
            logging.warning("Invalid move event: source or destination path is empty")
            return
            
        try:
            rel_src_path = os.path.relpath(event.src_path, REMOTE_DIR)
            rel_dest_path = os.path.relpath(event.dest_path, REMOTE_DIR)
            
            local_src_path = os.path.join(LOCAL_DIR, rel_src_path)
            local_dest_path = os.path.join(LOCAL_DIR, rel_dest_path)
            
            # Ensure target directory exists
            ensure_dir_exists(os.path.dirname(local_dest_path))
            
            # If local source file exists, move it; otherwise copy remote destination file
            if os.path.exists(local_src_path):
                try:
                    with TimerContext(f"Moving file: {os.path.basename(local_src_path)} -> {os.path.basename(local_dest_path)}"):
                        retry_operation(shutil.move, local_src_path, local_dest_path)
                        logging.info(f"File moved: {local_src_path} -> {local_dest_path}")
                except Exception as e:
                    logging.error(f"Failed to move file: {str(e)}")
            else:
                try:
                    with TimerContext(f"Copying file: {os.path.basename(event.dest_path)}"):
                        retry_operation(safe_copy_file, event.dest_path, local_dest_path)
                        logging.info(f"File copied: {event.dest_path} -> {local_dest_path}")
                except Exception as e:
                    logging.error(f"Failed to copy file: {str(e)}")
        except Exception as e:
            logging.error(f"Move event handling failed: {str(e)}")
    
    def on_deleted(self, event):
        if self._should_handle_event(event):
            rel_path = os.path.relpath(event.src_path, REMOTE_DIR)
            local_path = os.path.join(LOCAL_DIR, rel_path)
            
            if os.path.exists(local_path):
                try:
                    with TimerContext(f"Deleting: {os.path.basename(local_path)}"):
                        if os.path.isdir(local_path):
                            retry_operation(shutil.rmtree, local_path)
                        else:
                            retry_operation(os.remove, local_path)
                        logging.info(f"Deleted: {local_path}")
                except Exception as e:
                    logging.error(f"Failed to delete: {str(e)}")
    
    def _sync_event(self, event, action):
        # Ignore directory events
        if event.is_directory:
            return
            
        # Get relative path
        rel_path = os.path.relpath(event.src_path, REMOTE_DIR)
        local_path = os.path.join(LOCAL_DIR, rel_path)
        
        # Ensure target directory exists
        ensure_dir_exists(os.path.dirname(local_path))
        
        try:
            # Time the copy operation
            with TimerContext(f"{action} file: {os.path.basename(event.src_path)}"):
                # Copy file, preserving metadata
                retry_operation(safe_copy_file, event.src_path, local_path)
                logging.info(f"File {action.lower()}: {event.src_path} -> {local_path}")
        except Exception as e:
            logging.error(f"Sync failed: {str(e)}")

def main():
    global start_time
    start_time = time.time()
    logging.info(f"Program started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check remote directory accessibility first
    if not is_remote_accessible():
        logging.error("Cannot access remote directory. Please check your network connection and permissions.")
        return
    
    # Perform initial sync based on command line argument
    skip_initial_sync = not args.initial_sync
    if not skip_initial_sync:
        initial_sync(skip_if_exists=False)
    else:
        skip_initial_sync = input("Skip initial sync? (y/n): ").lower() == 'y'
        initial_sync(skip_if_exists=skip_initial_sync)
    
    # If --no-watch is specified, exit after initial sync
    if args.no_watch:
        logging.info("Initial sync completed, exiting without monitoring")
        return
    
    # Set up file monitoring
    event_handler = SyncHandler()
    observer = Observer()
    
    try:
        # Use timer to measure observer start time
        with TimerContext("Starting file monitoring"):
            observer.schedule(event_handler, REMOTE_DIR, recursive=True)
            observer.start()
        
        logging.info(f"Started monitoring remote directory: {REMOTE_DIR}")
        
        try:
            while True:
                # Check if remote directory is accessible
                if not is_remote_accessible():
                    logging.warning("Remote directory not accessible, waiting for reconnection...")
                    # Use timer to display wait time for reconnection
                    with TimerContext("Waiting for reconnection") as timer:
                        deadline = time.time() + 60
                        while time.time() < deadline:
                            time.sleep(1)
                            if is_remote_accessible():
                                logging.info("Remote directory connection restored")
                                break
                    continue
                
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            total_runtime = time.time() - start_time
            logging.info(f"Monitoring stopped, total runtime: {format_runtime(total_runtime)}")
        
        observer.join()
    except Exception as e:
        logging.error(f"Monitoring error: {str(e)}")

if __name__ == "__main__":
    main()
