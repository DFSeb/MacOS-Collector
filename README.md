# macOS Forensic Acquisition Script

A zsh script for creating forensically sound copies of files and folders on macOS systems. This script creates a sparsebundle image that preserves all file metadata, permissions, and extended attributes while maintaining detailed logs for chain of custody and verification.

## Features

- **User-friendly File Selection**: Select multiple files and folders through macOS's native file picker interface
- **Metadata Preservation**: Maintains all original file attributes, creation dates, permissions, and resource forks
- **Forensic Integrity**: Generates and verifies SHA-256 hashes for all copied files
- **Comprehensive Logging**: Creates detailed logs with timestamps for chain of custody documentation
- **Detailed Metadata Collection**:
  - File hashes (MD5, SHA-1, SHA-256)
  - Extended attributes
  - Access Control Lists (ACLs)
  - Permission settings
  - Ownership information
- **Sparsebundle Storage**: Automatically sizes and creates a sparsebundle disk image for efficient storage
- **Summary Reporting**: Generates an overview report of the copy operation

## Requirements

- macOS (10.13 or later recommended)
- zsh shell (default on modern macOS)
- Administrative access may be required for certain files

## Installation

1. Download the script file
2. Make it executable:
   ```
   chmod +x MacOS_collector.sh
   ```

## Usage

1. Run the script:
   ```
   ./forensic_copy.sh
   ```

2. Follow the prompts to:
   - Select files and folders to copy
   - Choose a location to save the sparsebundle

3. The script will:
   - Calculate required space (with 20% buffer)
   - Create and mount a sparsebundle
   - Copy all selected items with metadata
   - Generate hashes and verification data
   - Create comprehensive logs
   - Unmount the sparsebundle when complete

## Output

The script generates:

1. A sparsebundle disk image containing:
   - All copied files and folders
   - A `Metadata` directory with detailed information for each copied item
   - A `ForensicCopy_Summary.txt` file with operation details
   - A copy of the process log

2. A timestamped log file in `/tmp/` with complete operation details

## Forensic Best Practices

This script follows forensic best practices by:
- Preserving all file metadata using `ditto`
- Creating a read-only copy option
- Generating and verifying cryptographic hashes
- Maintaining detailed logs for chain of custody
- Creating separate metadata records for each copied item

## Limitations

- The script does not create a complete disk image, only copies selected files/folders
- Not suitable for copying actively changing files (use proper forensic hardware for live systems)
- Requires sufficient disk space for the sparsebundle

## Troubleshooting

- **Permissions Errors**: Run with elevated privileges if copying system files
- **Failed to Mount**: Check disk space and permissions at the destination
- **Hash Verification Failures**: May indicate the file changed during copy or media errors

## License

This script is provided as-is without warranty. Use at your own risk.

## Author

Sebastian Caballero with the use of AI
Created for forensic investigation and archival purposes.
