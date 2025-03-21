#!/usr/bin/env python3
"""
Forensic Sparsebundle Creator

This script allows users to select files and folders, creates a sparsebundle,
mounts it, and copies the selected items while preserving metadata.
Designed for MacOS with forensic best practices in mind.
"""

import os
import sys
import subprocess
import shutil
import datetime
import logging
import hashlib
import plistlib
import time
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# Configure logging
log_dir = os.path.expanduser("~/forensic_logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"forensic_sparsebundle_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log_system_info():
    """Log system information for forensic documentation."""
    logger.info("=== System Information ===")
    try:
        logger.info(f"User: {subprocess.check_output('whoami', text=True).strip()}")
        logger.info(f"Hostname: {subprocess.check_output('hostname', text=True).strip()}")
        logger.info(f"macOS Version: {subprocess.check_output(['sw_vers', '-productVersion'], text=True).strip()}")
        logger.info(f"Build Version: {subprocess.check_output(['sw_vers', '-buildVersion'], text=True).strip()}")
        logger.info(f"Architecture: {subprocess.check_output(['uname', '-m'], text=True).strip()}")
        logger.info(f"Kernel Version: {subprocess.check_output(['uname', '-r'], text=True).strip()}")
        logger.info(f"Current Time: {datetime.datetime.now().isoformat()}")
        logger.info(f"Tool Version: Forensic Sparsebundle Creator 1.0.0")
    except subprocess.SubprocessError as e:
        logger.error(f"Error getting system information: {e}")

def calculate_hash(file_path, algorithm='sha256'):
    """Calculate hash for a file using the specified algorithm."""
    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None

def execute_command(cmd, description):
    """Execute a shell command and log the output."""
    logger.info(f"Executing: {description}")
    logger.debug(f"Command: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"{description} failed with code {process.returncode}")
            logger.error(f"Error output: {stderr.strip()}")
            return False, stderr
        
        logger.debug(f"Output: {stdout.strip()}")
        return True, stdout
    except Exception as e:
        logger.error(f"Exception while {description}: {e}")
        return False, str(e)

def create_sparsebundle(destination_path, name, size_mb=10240):
    """Create a sparsebundle with the given name and size."""
    logger.info(f"Creating sparsebundle: {name} with size: {size_mb}MB")
    
    sparsebundle_path = os.path.join(destination_path, f"{name}.sparsebundle")
    
    if os.path.exists(sparsebundle_path):
        logger.warning(f"Sparsebundle already exists at {sparsebundle_path}")
        return False, sparsebundle_path
    
    cmd = [
        'hdiutil', 'create',
        '-size', f'{size_mb}m',
        '-fs', 'HFS+',
        '-volname', name,
        '-type', 'SPARSEBUNDLE',
        '-encryption', 'AES-256',
        sparsebundle_path
    ]
    
    success, output = execute_command(cmd, "Creating sparsebundle")
    return success, sparsebundle_path

def mount_sparsebundle(sparsebundle_path):
    """Mount the sparsebundle and return the mount point."""
    logger.info(f"Mounting sparsebundle: {sparsebundle_path}")
    
    cmd = ['hdiutil', 'attach', sparsebundle_path, '-mountpoint', '/Volumes/ForensicData']
    success, output = execute_command(cmd, "Mounting sparsebundle")
    
    if success:
        # Find the mount point from output
        mount_point = '/Volumes/ForensicData'
        logger.info(f"Sparsebundle mounted at: {mount_point}")
        return True, mount_point
    else:
        return False, None

def unmount_sparsebundle(mount_point):
    """Unmount the sparsebundle."""
    logger.info(f"Unmounting sparsebundle from: {mount_point}")
    
    cmd = ['hdiutil', 'detach', mount_point, '-force']
    success, output = execute_command(cmd, "Unmounting sparsebundle")
    return success

def copy_with_metadata(source, destination, hash_log):
    """Copy files/folders preserving metadata and log file hashes."""
    logger.info(f"Copying: {source} -> {destination}")
    
    try:
        if os.path.isfile(source):
            # For files, use ditto to preserve all metadata
            cmd = ['ditto', '-v', source, destination]
            success, output = execute_command(cmd, f"Copying file {source}")
            
            if success:
                # Calculate and log hash
                source_hash = calculate_hash(source)
                dest_hash = calculate_hash(os.path.join(destination, os.path.basename(source)) 
                                         if os.path.isdir(destination) else destination)
                
                hash_entry = {
                    'source_path': source,
                    'destination_path': destination,
                    'sha256_source': source_hash,
                    'sha256_destination': dest_hash,
                    'timestamp': datetime.datetime.now().isoformat()
                }
                hash_log.append(hash_entry)
                
                if source_hash != dest_hash:
                    logger.error(f"Hash mismatch for {source}!")
                    logger.error(f"Source: {source_hash}")
                    logger.error(f"Destination: {dest_hash}")
                    return False
            else:
                return False
                
        elif os.path.isdir(source):
            # For directories, create destination directory first
            dest_dir = os.path.join(destination, os.path.basename(source))
            os.makedirs(dest_dir, exist_ok=True)
            
            # Use ditto to copy the entire directory with metadata
            cmd = ['ditto', '-v', source, dest_dir]
            success, output = execute_command(cmd, f"Copying directory {source}")
            
            if not success:
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error copying {source}: {e}")
        return False

def select_files_and_folders():
    """Open a file dialog for selecting multiple files and folders."""
    logger.info("Prompting user to select files and folders")
    
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Instructions for the user
    logger.info("Please select files and folders to include in the sparsebundle")
    
    # Open file dialog
    paths = filedialog.askopenfilenames(
        title="Select files to include in sparsebundle",
        multiple=True
    )
    files = list(paths)
    
    # Open folder dialog
    paths = []
    while True:
        path = filedialog.askdirectory(
            title="Select a folder to include (Cancel when done selecting folders)"
        )
        if not path:
            break
        paths.append(path)
    
    folders = paths
    
    root.destroy()
    
    all_paths = files + folders
    if not all_paths:
        logger.warning("No files or folders were selected")
    else:
        logger.info(f"Selected {len(files)} files and {len(folders)} folders")
        for path in all_paths:
            logger.info(f"Selected: {path}")
    
    return all_paths

def estimate_size_needed(paths):
    """Estimate the size needed for the sparsebundle."""
    logger.info("Estimating size needed for selected files and folders")
    
    total_size = 0
    for path in paths:
        try:
            if os.path.isfile(path):
                total_size += os.path.getsize(path)
            elif os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if os.path.exists(fp):
                            total_size += os.path.getsize(fp)
        except Exception as e:
            logger.error(f"Error calculating size for {path}: {e}")
    
    # Convert to MB and add 10% buffer
    size_mb = int((total_size / (1024 * 1024)) * 1.1)
    
    # Ensure minimum size of 100MB
    size_mb = max(size_mb, 100)
    
    logger.info(f"Estimated size needed: {size_mb}MB")
    return size_mb

def create_verification_report(hash_log, output_path, sparsebundle_path):
    """Create a verification report with all file hashes and operations."""
    logger.info("Creating verification report")
    
    report_path = os.path.join(output_path, "verification_report.plist")
    
    report_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'sparsebundle_path': sparsebundle_path,
        'tool_version': "Forensic Sparsebundle Creator 1.0.0",
        'system_info': {
            'user': subprocess.check_output('whoami', text=True).strip(),
            'hostname': subprocess.check_output('hostname', text=True).strip(),
            'macos_version': subprocess.check_output(['sw_vers', '-productVersion'], text=True).strip(),
        },
        'file_hashes': hash_log
    }
    
    try:
        with open(report_path, 'wb') as f:
            plistlib.dump(report_data, f)
        
        logger.info(f"Verification report created at: {report_path}")
        
        # Also create a text version
        txt_report_path = os.path.join(output_path, "verification_report.txt")
        with open(txt_report_path, 'w') as f:
            f.write(f"FORENSIC SPARSEBUNDLE VERIFICATION REPORT\n")
            f.write(f"=====================================\n\n")
            f.write(f"Created: {report_data['timestamp']}\n")
            f.write(f"Sparsebundle: {report_data['sparsebundle_path']}\n")
            f.write(f"Tool Version: {report_data['tool_version']}\n\n")
            
            f.write(f"SYSTEM INFORMATION\n")
            f.write(f"-----------------\n")
            for k, v in report_data['system_info'].items():
                f.write(f"{k}: {v}\n")
            
            f.write(f"\nFILE HASHES\n")
            f.write(f"-----------\n")
            for entry in hash_log:
                f.write(f"Source: {entry['source_path']}\n")
                f.write(f"Destination: {entry['destination_path']}\n")
                f.write(f"Source SHA256: {entry['sha256_source']}\n")
                f.write(f"Destination SHA256: {entry['sha256_destination']}\n")
                f.write(f"Match: {entry['sha256_source'] == entry['sha256_destination']}\n")
                f.write(f"Timestamp: {entry['timestamp']}\n\n")
        
        logger.info(f"Text verification report created at: {txt_report_path}")
        
    except Exception as e:
        logger.error(f"Error creating verification report: {e}")

def main():
    """Main function for the forensic sparsebundle creator."""
    try:
        logger.info("=== Forensic Sparsebundle Creator Started ===")
        log_system_info()
        
        # Check if running on macOS
        if sys.platform != 'darwin':
            logger.error("This script is designed to run only on macOS")
            return 1
        
        # Select files and folders
        selected_paths = select_files_and_folders()
        if not selected_paths:
            logger.error("No files or folders were selected. Exiting.")
            return 1
        
        # Get size estimate
        size_needed = estimate_size_needed(selected_paths)
        
        # Get destination for sparsebundle
        root = tk.Tk()
        root.withdraw()
        destination_path = filedialog.askdirectory(
            title="Select where to save the sparsebundle"
        )
        root.destroy()
        
        if not destination_path:
            logger.error("No destination selected. Exiting.")
            return 1
        
        # Generate a unique name for the sparsebundle
        sparsebundle_name = f"ForensicData_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create sparsebundle
        success, sparsebundle_path = create_sparsebundle(destination_path, sparsebundle_name, size_needed)
        if not success:
            logger.error("Failed to create sparsebundle. Exiting.")
            return 1
        
        # Mount sparsebundle
        success, mount_point = mount_sparsebundle(sparsebundle_path)
        if not success:
            logger.error("Failed to mount sparsebundle. Exiting.")
            return 1
        
        # Create a log directory inside the sparsebundle
        log_dir_in_sparsebundle = os.path.join(mount_point, "forensic_logs")
        os.makedirs(log_dir_in_sparsebundle, exist_ok=True)
        
        # Copy log file to the sparsebundle
        shutil.copy2(log_file, log_dir_in_sparsebundle)
        
        # Create a directory for copied files
        files_dir = os.path.join(mount_point, "copied_files")
        os.makedirs(files_dir, exist_ok=True)
        
        # Copy files and folders while preserving metadata
        hash_log = []
        success = True
        for path in selected_paths:
            if not copy_with_metadata(path, files_dir, hash_log):
                logger.error(f"Failed to copy {path}")
                success = False
        
        # Create verification report
        create_verification_report(hash_log, log_dir_in_sparsebundle, sparsebundle_path)
        
        # Unmount sparsebundle
        if not unmount_sparsebundle(mount_point):
            logger.error("Failed to unmount sparsebundle properly")
            return 1
        
        if success:
            logger.info("=== Forensic Sparsebundle Creator Completed Successfully ===")
            logger.info(f"Sparsebundle created at: {sparsebundle_path}")
            logger.info(f"Log file: {log_file}")
            return 0
        else:
            logger.error("=== Forensic Sparsebundle Creator Completed with Errors ===")
            return 1
            
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())