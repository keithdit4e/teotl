---
name: filesystem
version: 2.0.0
description: "Read, write, search, and navigate files and directories"
auth: none
triggers:
  - file
  - directory
  - folder
  - read
  - write
  - create
  - edit
  - find
  - search files
  - filesystem
---

# Filesystem Operations

Comprehensive file and directory management operations.

## Core Operations

### Read File Contents
```bash
cat /path/to/file
```

**Best practices:**
- Always verify file exists before reading: `[ -f /path/to/file ] && cat /path/to/file`
- For large files, use `head -n 100` to preview first 100 lines
- Use `wc -l` to check file size first
- Binary files: use `file /path` to detect type before reading

### Read Specific Lines
```bash
# Read lines 10-20
sed -n '10,20p' /path/to/file

# Read last 50 lines
tail -n 50 /path/to/file

# Read first 100 lines
head -n 100 /path/to/file
```

### Write/Create File
```bash
cat > /path/to/file << 'EOF'
Content goes here
Multiple lines supported
EOF
```

**Security:**
- Never overwrite files without checking first
- Use `[ ! -f /path ] || mv /path /path.backup` to backup before overwriting
- Set proper permissions after creating: `chmod 600 /path/to/file` for sensitive files

### Append to File
```bash
cat >> /path/to/file << 'EOF'
New content to append
EOF
```

### Search File Contents
```bash
# Case-insensitive search with line numbers
grep -in "pattern" /path/to/file

# Recursive search in directory
grep -rn "pattern" /path/to/dir/

# Search with context (2 lines before/after)
grep -C 2 "pattern" /path/to/file

# Search for whole words only
grep -w "pattern" /path/to/file
```

### Find Files by Name
```bash
# Find files matching pattern
find /path/to/search -name "*.txt" -type f

# Find recently modified files (last 24 hours)
find /path/to/search -mtime -1 -type f

# Find large files (>10MB)
find /path/to/search -size +10M -type f

# Find and execute command on results
find /path/to/search -name "*.log" -type f -exec ls -lh {} \;
```

## Directory Operations

### List Directory
```bash
# Detailed listing with hidden files
ls -lah /path/to/dir/

# Sort by modification time (newest first)
ls -lt /path/to/dir/

# Show only directories
ls -d /path/to/dir/*/

# Tree view (if available)
tree -L 2 /path/to/dir/
```

### Create Directory
```bash
# Create single directory
mkdir /path/to/dir

# Create nested directories
mkdir -p /path/to/nested/dir/structure
```

### Navigation
```bash
# Show current directory
pwd

# Change directory
cd /path/to/dir

# Go to home directory
cd ~

# Go to previous directory
cd -
```

## File Management

### Copy Files
```bash
# Copy file
cp /source/file /dest/file

# Copy directory recursively
cp -r /source/dir /dest/dir

# Copy with confirmation before overwrite
cp -i /source/file /dest/file

# Preserve permissions and timestamps
cp -p /source/file /dest/file
```

### Move/Rename Files
```bash
# Move file
mv /source/file /dest/file

# Rename file (same as move)
mv oldname.txt newname.txt

# Move with confirmation
mv -i /source/file /dest/file
```

### Delete Files
```bash
# Delete single file (CAUTION)
rm /path/to/file

# Delete with confirmation
rm -i /path/to/file

# Delete directory and contents (EXTREME CAUTION)
rm -r /path/to/dir

# Safe deletion to trash (macOS)
trash /path/to/file  # Requires trash-cli or similar
```

**CRITICAL:**
- Never use `rm -rf` without careful verification
- Always check path before deletion: `ls -ld /path/to/delete`
- Consider backup before deletion
- For important files, move to a .trash directory instead of rm

## File Information

### File Metadata
```bash
# Show file type and encoding
file /path/to/file

# Show file stats (size, permissions, timestamps)
stat /path/to/file

# Show file size in human-readable format
du -h /path/to/file

# Show directory size
du -sh /path/to/dir/

# Count lines, words, characters
wc /path/to/file
```

### Permissions
```bash
# View permissions
ls -l /path/to/file

# Change permissions (owner read/write only)
chmod 600 /path/to/file

# Make file executable
chmod +x /path/to/script.sh

# Change ownership
chown user:group /path/to/file
```

## Advanced Operations

### Text Processing
```bash
# Remove duplicate lines
sort /path/to/file | uniq

# Count occurrences
sort /path/to/file | uniq -c

# Extract specific columns
awk '{print $1, $3}' /path/to/file

# Replace text in file (create backup first)
sed -i.bak 's/old/new/g' /path/to/file
```

### File Comparison
```bash
# Compare two files
diff /path/to/file1 /path/to/file2

# Show side-by-side comparison
diff -y /path/to/file1 /path/to/file2

# Recursive directory comparison
diff -r /path/to/dir1 /path/to/dir2
```

### Archive Operations
```bash
# Create tar archive
tar -czf archive.tar.gz /path/to/dir/

# Extract tar archive
tar -xzf archive.tar.gz

# List archive contents
tar -tzf archive.tar.gz

# Create zip archive
zip -r archive.zip /path/to/dir/

# Extract zip archive
unzip archive.zip
```

## Common Workflows

### Safely Edit a Configuration File
```bash
# 1. Backup original
cp /etc/config.conf /etc/config.conf.backup

# 2. Verify backup created
ls -l /etc/config.conf.backup

# 3. Edit file
cat > /etc/config.conf << 'EOF'
new configuration
EOF

# 4. Test new configuration
validate-config /etc/config.conf

# 5. If fails, restore backup
# mv /etc/config.conf.backup /etc/config.conf
```

### Search for Files Containing Text
```bash
# Find all Python files containing "TODO"
find /project -name "*.py" -type f -exec grep -l "TODO" {} \;

# Same with line numbers
find /project -name "*.py" -type f -exec grep -n "TODO" {} \;
```

### Clean Up Old Log Files
```bash
# Find log files older than 30 days
find /var/log -name "*.log" -mtime +30 -type f

# Review before deleting
find /var/log -name "*.log" -mtime +30 -type f -exec ls -lh {} \;

# Delete (after review!)
find /var/log -name "*.log" -mtime +30 -type f -exec rm {} \;
```

## Security Considerations

### Protected Directories
Never read from or write to without explicit user approval:
- `/etc/` - System configuration
- `/var/` - System data
- `/usr/` - System binaries
- `~/.ssh/` - SSH keys
- `~/.gnupg/` - GPG keys
- `~/.aws/` - Cloud credentials
- `.git/` internals - Git internal objects

### Safe Practices
1. **Always verify paths** before destructive operations
2. **Create backups** before modifying important files
3. **Check file permissions** for sensitive data
4. **Use absolute paths** when possible to avoid confusion
5. **Validate file types** before reading to avoid binary content
6. **Set restrictive permissions** for sensitive files (600 or 400)
7. **Never trust user-provided paths** without sanitization

### Dangerous Patterns to Avoid
```bash
# NEVER do these without extreme caution:
rm -rf /*           # Deletes entire filesystem
rm -rf ~/*          # Deletes entire home directory
chmod -R 777 /      # Makes everything world-writable
```

## Error Handling

### Check Command Success
```bash
# Check if file exists before reading
if [ -f /path/to/file ]; then
    cat /path/to/file
else
    echo "Error: File not found"
fi

# Check if command succeeded
if grep -q "pattern" /path/to/file; then
    echo "Pattern found"
else
    echo "Pattern not found"
fi
```

### Verify Before Destructive Operations
```bash
# Verify path exists and is expected type
if [ -d /path/to/delete ]; then
    echo "Directory exists: $(ls -ld /path/to/delete)"
    read -p "Confirm deletion? (yes/no) " confirm
    if [ "$confirm" = "yes" ]; then
        rm -r /path/to/delete
    fi
fi
```

## Performance Tips

1. **For large directories**, use `find` with `-maxdepth` to limit recursion
2. **For large files**, use `head`/`tail` instead of reading entire file
3. **For searching**, use `grep -F` for fixed strings (faster than regex)
4. **Use pipes efficiently**: `cat file | grep pattern` → `grep pattern file`
5. **Check file size first**: `stat -f%z file` before reading

## Quick Reference

| Operation | Command | Safety Level |
|-----------|---------|--------------|
| Read file | `cat /path` | Safe |
| Write file | `cat > /path << 'EOF'` | Medium - backup first |
| Append to file | `cat >> /path << 'EOF'` | Safe |
| Delete file | `rm /path` | **Dangerous - verify first** |
| Delete directory | `rm -r /path` | **CRITICAL - verify first** |
| Search files | `grep -rn "pattern" /path` | Safe |
| Find files | `find /path -name "pattern"` | Safe |
| List directory | `ls -lah /path` | Safe |

---

**Remember**: When in doubt, ask the user for confirmation before any operation that modifies or deletes data.
