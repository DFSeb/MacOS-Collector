#!/bin/zsh

# Script to select and copy files/folders to a sparsebundle with metadata preservation
# For forensic use on macOS

# Set up logging
log_file="/tmp/forensic_copy_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$log_file") 2>&1

# Function to log messages with timestamps
log() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1"
}

log "Starting forensic copy process"
log "Script executed by user: $(whoami)"
log "Host: $(hostname)"
log "macOS Version: $(sw_vers -productVersion)"

# Function to create sparsebundle
create_sparsebundle() {
    local location=$1
    local name=$2
    local size=$3
    
    log "Creating sparsebundle at $location/$name with size $size MB"
    
    # Create the sparsebundle
    hdiutil create -size "${size}m" -fs "HFS+" -volname "ForensicCopy" -type SPARSEBUNDLE "$location/$name"
    
    if [ $? -ne 0 ]; then
        log "ERROR: Failed to create sparsebundle"
        return 1
    fi
    
    log "Successfully created sparsebundle: $location/$name"
    return 0
}

# Function to mount sparsebundle
mount_sparsebundle() {
    local path=$1
    
    log "Mounting sparsebundle: $path"
    
    # Mount the sparsebundle
    local mount_output=$(hdiutil attach "$path" -owners on)
    
    if [ $? -ne 0 ]; then
        log "ERROR: Failed to mount sparsebundle"
        return 1
    fi
    
    # Extract mount point from output
    local mount_point=$(echo "$mount_output" | grep "/Volumes/" | awk '{print $NF}')
    
    log "Successfully mounted sparsebundle at: $mount_point"
    echo "$mount_point"
    return 0
}

# Function to copy files/folders with metadata
copy_with_metadata() {
    local source=$1
    local dest_dir=$2
    
    log "Copying: $source to $dest_dir"
    
    # Use ditto to preserve all metadata and resource forks
    ditto -v --keepParent "$source" "$dest_dir"
    
    local ditto_status=$?
    if [ $ditto_status -ne 0 ]; then
        log "ERROR: Failed to copy $source (ditto exited with status $ditto_status)"
        return 1
    fi
    
    log "Successfully copied $source with all metadata"
    
    # Create SHA-256 hash for the copied item
    if [ -f "$source" ]; then
        local original_hash=$(shasum -a 256 "$source" | awk '{print $1}')
        local dest_file="$dest_dir/$(basename "$source")"
        local copy_hash=$(shasum -a 256 "$dest_file" | awk '{print $1}')
        
        log "Original SHA-256: $original_hash"
        log "Copy SHA-256: $copy_hash"
        
        if [ "$original_hash" != "$copy_hash" ]; then
            log "WARNING: Hash mismatch for $source"
        else
            log "Hash verification successful for $source"
        fi
    else
        log "Directory copied - skipping hash verification for directory"
    fi
    
    return 0
}

# Function to gather extended attributes and permissions
gather_metadata() {
    local source=$1
    local metadata_dir=$2
    local base_name=$(basename "$source")
    
    log "Gathering metadata for: $source"
    
    # Create metadata file
    local metadata_file="$metadata_dir/${base_name}_metadata.txt"
    
    # File/folder info
    echo "===== File/Folder Information =====" > "$metadata_file"
    echo "Item: $source" >> "$metadata_file"
    echo "Captured by: $(whoami)" >> "$metadata_file"
    echo "Capture date: $(date)" >> "$metadata_file"
    echo "macOS Version: $(sw_vers -productVersion)" >> "$metadata_file"
    echo "" >> "$metadata_file"
    
    # Permissions and ownership
    echo "===== Permissions and Ownership =====" >> "$metadata_file"
    ls -la "$source" >> "$metadata_file"
    echo "" >> "$metadata_file"
    
    # Extended attributes
    echo "===== Extended Attributes =====" >> "$metadata_file"
    xattr -l "$source" >> "$metadata_file"
    echo "" >> "$metadata_file"
    
    # If it's a file, get hash
    if [ -f "$source" ]; then
        echo "===== File Hashes =====" >> "$metadata_file"
        echo "MD5: $(md5 -q "$source")" >> "$metadata_file"
        echo "SHA-1: $(shasum -a 1 "$source" | awk '{print $1}')" >> "$metadata_file"
        echo "SHA-256: $(shasum -a 256 "$source" | awk '{print $1}')" >> "$metadata_file"
        echo "" >> "$metadata_file"
    fi
    
    # ACLs
    echo "===== Access Control Lists =====" >> "$metadata_file"
    ls -le "$source" >> "$metadata_file"
    
    log "Metadata captured to $metadata_file"
}

# Main script execution starts here

# Ask user to select files/folders
log "Prompting user to select files/folders"
echo "Please select files and/or folders to copy (multiple selections allowed):"
selected_items=$(osascript -e 'choose file with multiple selections allowed' 2>/dev/null || echo "cancelled")

# Check if selection was cancelled
if [[ "$selected_items" == "cancelled" ]]; then
    log "User cancelled file selection. Exiting."
    exit 1
fi

# Convert the AppleScript result to array
items=()
for item in $(echo "$selected_items" | tr ':' '\n'); do
    # Convert from AppleScript path to POSIX path
    posix_path=$(echo "$item" | sed 's/:/\//g')
    if [[ "$posix_path" != /* ]]; then
        posix_path="/$posix_path"
    fi
    items+=("$posix_path")
    log "Selected: $posix_path"
done

# Calculate approximate size needed (with 20% buffer)
total_size=0
for item in "${items[@]}"; do
    if [[ -e "$item" ]]; then
        item_size=$(du -sm "$item" | awk '{print $1}')
        total_size=$((total_size + item_size))
        log "Size of $item: $item_size MB"
    fi
done

# Add 20% buffer
total_size=$((total_size + (total_size / 5)))
log "Total size needed (with 20% buffer): $total_size MB"

# Ask user for sparsebundle location
log "Prompting user to select location for sparsebundle"
echo "Please select location to save the sparsebundle:"
sparsebundle_location=$(osascript -e 'choose folder' 2>/dev/null | sed 's/:/\//g')

# Check if selection was cancelled
if [[ -z "$sparsebundle_location" ]]; then
    log "User cancelled location selection. Exiting."
    exit 1
fi

if [[ "$sparsebundle_location" != /* ]]; then
    sparsebundle_location="/$sparsebundle_location"
fi

log "Selected sparsebundle location: $sparsebundle_location"

# Create sparsebundle name with timestamp
sparsebundle_name="ForensicCopy_$(date +%Y%m%d_%H%M%S).sparsebundle"

# Create the sparsebundle
create_sparsebundle "$sparsebundle_location" "$sparsebundle_name" "$total_size"
if [ $? -ne 0 ]; then
    log "Failed to create sparsebundle. Exiting."
    exit 1
fi

# Mount the sparsebundle
sparsebundle_path="$sparsebundle_location/$sparsebundle_name"
mount_point=$(mount_sparsebundle "$sparsebundle_path")
if [ -z "$mount_point" ]; then
    log "Failed to mount sparsebundle. Exiting."
    exit 1
fi

# Create metadata directory
metadata_dir="$mount_point/Metadata"
mkdir -p "$metadata_dir"
log "Created metadata directory: $metadata_dir"

# Copy each selected item
success_count=0
failure_count=0

for item in "${items[@]}"; do
    if [[ -e "$item" ]]; then
        # Gather metadata first
        gather_metadata "$item" "$metadata_dir"
        
        # Then copy the item
        copy_with_metadata "$item" "$mount_point"
        
        if [ $? -eq 0 ]; then
            ((success_count++))
        else
            ((failure_count++))
        fi
    else
        log "ERROR: Item does not exist: $item"
        ((failure_count++))
    fi
done

# Create a summary report
summary_file="$mount_point/ForensicCopy_Summary.txt"
echo "===== Forensic Copy Summary =====" > "$summary_file"
echo "Date: $(date)" >> "$summary_file"
echo "Operator: $(whoami)" >> "$summary_file"
echo "Host: $(hostname)" >> "$summary_file"
echo "macOS Version: $(sw_vers -productVersion)" >> "$summary_file"
echo "" >> "$summary_file"
echo "Items successfully copied: $success_count" >> "$summary_file"
echo "Items failed to copy: $failure_count" >> "$summary_file"
echo "" >> "$summary_file"
echo "Selected items:" >> "$summary_file"
for item in "${items[@]}"; do
    echo "- $item" >> "$summary_file"
done
echo "" >> "$summary_file"
echo "Log file: $log_file" >> "$summary_file"

# Copy the log file to the sparsebundle
cp "$log_file" "$mount_point/forensic_copy.log"
log "Log file copied to sparsebundle"

# Unmount the sparsebundle
log "Unmounting sparsebundle"
hdiutil detach "$mount_point"
if [ $? -ne 0 ]; then
    log "WARNING: Failed to unmount sparsebundle cleanly. You may need to unmount manually."
fi

log "Forensic copy process completed"
echo ""
echo "Forensic copy process completed."
echo "Successfully copied: $success_count items"
echo "Failed to copy: $failure_count items"
echo "Sparsebundle created at: $sparsebundle_path"
echo "Log file: $log_file"