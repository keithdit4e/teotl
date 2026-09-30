---
name: web
version: 2.0.0
description: "Fetch web pages, download files, make HTTP requests"
auth: none
triggers:
  - url
  - website
  - download
  - fetch
  - http
  - https
  - api
  - curl
  - web request
  - REST
---

# Web Operations

Comprehensive web request and HTTP operations using curl.

## Core Operations

### Fetch Web Page (Text)
```bash
# Fetch and display page
curl -sL https://example.com

# Limit output (first 200 lines)
curl -sL https://example.com | head -200

# Follow redirects and show only response body
curl -sL https://example.com
```

**Flags:**
- `-s` = silent (no progress bar)
- `-L` = follow redirects
- `-f` = fail silently on HTTP errors
- `-S` = show errors even with `-s`

### Check URL Status
```bash
# Show HTTP headers only
curl -sI https://example.com | head -5

# Check status code
curl -so /dev/null -w "%{http_code}" https://example.com

# Verbose connection info
curl -v https://example.com 2>&1 | head -20
```

### Download Files
```bash
# Download file (original name)
curl -sLO https://example.com/file.zip

# Download with custom name
curl -sL https://example.com/file.zip -o myfile.zip

# Download with progress bar
curl -L https://example.com/largefile.zip -o file.zip

# Resume partial download
curl -C - -L https://example.com/file.zip -o file.zip
```

## API Requests

### GET Requests
```bash
# Simple GET
curl -s https://api.example.com/endpoint

# GET with headers
curl -s -H "Accept: application/json" https://api.example.com/endpoint

# GET with query parameters
curl -s "https://api.example.com/search?q=query&limit=10"

# GET with authentication
curl -s -H "Authorization: Bearer TOKEN" https://api.example.com/endpoint
```

### POST Requests
```bash
# POST JSON data
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}' \
  https://api.example.com/endpoint

# POST form data
curl -s -X POST \
  -d "field1=value1" \
  -d "field2=value2" \
  https://api.example.com/form

# POST file upload
curl -s -X POST \
  -F "file=@/path/to/file" \
  https://api.example.com/upload
```

### PUT Requests
```bash
# PUT JSON data
curl -s -X PUT \
  -H "Content-Type: application/json" \
  -d '{"updated": "value"}' \
  https://api.example.com/resource/123
```

### DELETE Requests
```bash
# DELETE resource
curl -s -X DELETE https://api.example.com/resource/123

# DELETE with authentication
curl -s -X DELETE \
  -H "Authorization: Bearer TOKEN" \
  https://api.example.com/resource/123
```

### PATCH Requests
```bash
# PATCH partial update
curl -s -X PATCH \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}' \
  https://api.example.com/resource/123
```

## Authentication

### Bearer Token
```bash
curl -s \
  -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.example.com/endpoint
```

### Basic Auth
```bash
# With username:password in URL
curl -s -u username:password https://api.example.com/endpoint

# Or as header
curl -s -H "Authorization: Basic BASE64_CREDENTIALS" \
  https://api.example.com/endpoint
```

### API Key (Header)
```bash
curl -s -H "X-API-Key: YOUR_API_KEY" \
  https://api.example.com/endpoint
```

### API Key (Query Parameter)
```bash
curl -s "https://api.example.com/endpoint?api_key=YOUR_API_KEY"
```

## Advanced Features

### Custom Headers
```bash
# Multiple custom headers
curl -s \
  -H "Accept: application/json" \
  -H "User-Agent: MyApp/1.0" \
  -H "X-Custom-Header: value" \
  https://api.example.com/endpoint
```

### Cookies
```bash
# Send cookie
curl -s -b "session=abc123" https://example.com

# Save cookies to file
curl -s -c cookies.txt https://example.com

# Load cookies from file
curl -s -b cookies.txt https://example.com

# Both save and load
curl -s -b cookies.txt -c cookies.txt https://example.com
```

### Timeouts and Retries
```bash
# Connection timeout (5 seconds)
curl -s --connect-timeout 5 https://example.com

# Max time for entire operation (30 seconds)
curl -s --max-time 30 https://example.com

# Retry on failure (3 times)
curl -s --retry 3 --retry-delay 2 https://example.com
```

### Response Inspection
```bash
# Save response headers to file
curl -sL -D headers.txt https://example.com

# Show response time
curl -so /dev/null -w "Time: %{time_total}s\n" https://example.com

# Show all timing details
curl -so /dev/null -w "\
DNS lookup: %{time_namelookup}s\n\
Connect: %{time_connect}s\n\
TLS handshake: %{time_appconnect}s\n\
Total: %{time_total}s\n" https://example.com
```

### JSON Processing
```bash
# Pretty-print JSON response (requires jq)
curl -s https://api.example.com/json | jq '.'

# Extract specific JSON field
curl -s https://api.example.com/json | jq '.data.items'

# Count array elements
curl -s https://api.example.com/json | jq '.items | length'
```

## Common Workflows

### Testing API Endpoint
```bash
# 1. Check if endpoint is reachable
curl -sI https://api.example.com/health | head -1

# 2. Make test request
curl -s https://api.example.com/endpoint | head -50

# 3. Check response structure
curl -s https://api.example.com/endpoint | jq '.'

# 4. Verify authentication
curl -s -H "Authorization: Bearer TOKEN" \
  https://api.example.com/protected | jq '.'
```

### Downloading Multiple Files
```bash
# Download URLs from file
while read url; do
  curl -sLO "$url"
done < urls.txt

# Download with pattern
curl -sLO "https://example.com/file[1-5].zip"
```

### Web Scraping (Text Extraction)
```bash
# Fetch page and extract links
curl -sL https://example.com | grep -oP 'href="\K[^"]*'

# Fetch page and extract specific text
curl -sL https://example.com | grep -A 5 "search term"

# Fetch page and convert HTML to text (requires html2text or lynx)
curl -sL https://example.com | lynx -stdin -dump
```

### API Pagination
```bash
# Fetch multiple pages
for page in {1..5}; do
  curl -s "https://api.example.com/items?page=$page"
done

# Fetch until empty response
page=1
while true; do
  response=$(curl -s "https://api.example.com/items?page=$page")
  if [ -z "$response" ] || [ "$response" = "[]" ]; then
    break
  fi
  echo "$response"
  ((page++))
done
```

## Security Considerations

### Network Access
- Network requests require confirmation under standard guardrail policy
- Always verify URLs before making requests
- Never expose sensitive credentials in URLs (use headers instead)
- Use HTTPS instead of HTTP whenever possible

### Protected Operations
Require explicit user approval:
- Requests to localhost/127.0.0.1 (potential SSRF)
- Requests to private IP ranges (10.0.0.0/8, 192.168.0.0/16, 172.16.0.0/12)
- POST/PUT/DELETE requests that modify data
- File uploads
- Authentication credential transmission

### Safe Practices
1. **Validate URLs** before making requests
2. **Use environment variables** for API keys (never hardcode)
3. **Check response codes** before processing data
4. **Limit response size** with `head` to avoid flooding context
5. **Sanitize user input** in URLs and request bodies
6. **Use timeouts** to prevent hanging requests
7. **Verify SSL certificates** (don't use `-k` in production)

### Dangerous Patterns to Avoid
```bash
# NEVER do these:
curl -k https://...              # Disables SSL verification
curl "$(user_input)"            # Unsanitized user input in URL
curl -H "Auth: $RAW_PASSWORD"   # Exposing passwords in headers
```

## Error Handling

### Check HTTP Status
```bash
# Store status code
status=$(curl -so /dev/null -w "%{http_code}" https://example.com)

if [ "$status" -eq 200 ]; then
  echo "Success"
elif [ "$status" -eq 404 ]; then
  echo "Not found"
else
  echo "Error: HTTP $status"
fi
```

### Handle Network Errors
```bash
# Check if request succeeded
if curl -sf https://example.com > /dev/null; then
  echo "Site is up"
else
  echo "Site is down or unreachable"
fi
```

### Verbose Error Debugging
```bash
# Show detailed error information
curl -v https://example.com 2>&1 | grep -E "^(>|<|\*)"
```

## Performance Tips

1. **Use `-s` flag** to suppress progress bar (faster in scripts)
2. **Limit output** with `head` to avoid processing large responses
3. **Use connection reuse** with `--keepalive-time` for multiple requests
4. **Compress responses** with `-H "Accept-Encoding: gzip"`
5. **Set reasonable timeouts** to prevent hanging
6. **Use parallel requests** with `xargs -P` for bulk operations

## Response Format Handling

### HTML
```bash
# Fetch and extract text
curl -sL https://example.com | html2text

# Or with lynx
curl -sL https://example.com | lynx -stdin -dump
```

### JSON
```bash
# Pretty-print
curl -s https://api.example.com | jq '.'

# Extract field
curl -s https://api.example.com | jq '.field'
```

### XML
```bash
# Pretty-print (requires xmllint)
curl -s https://example.com/rss | xmllint --format -

# Extract with xpath
curl -s https://example.com/xml | xmllint --xpath '//item/title/text()' -
```

### CSV
```bash
# Fetch CSV data
curl -sL https://example.com/data.csv

# Process with awk
curl -sL https://example.com/data.csv | awk -F, '{print $1, $3}'
```

## Rate Limiting

### Respect API Rate Limits
```bash
# Add delay between requests
for url in "${urls[@]}"; do
  curl -s "$url"
  sleep 1  # 1 second delay
done

# Check rate limit headers
curl -sI https://api.example.com | grep -i "x-ratelimit"
```

## Common API Patterns

### GraphQL
```bash
# GraphQL query
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ user(id: 123) { name email } }"
  }' \
  https://api.example.com/graphql
```

### REST CRUD Operations
```bash
# CREATE (POST)
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"name": "New Item"}' \
  https://api.example.com/items

# READ (GET)
curl -s https://api.example.com/items/123

# UPDATE (PUT)
curl -s -X PUT -H "Content-Type: application/json" \
  -d '{"name": "Updated Item"}' \
  https://api.example.com/items/123

# DELETE (DELETE)
curl -s -X DELETE https://api.example.com/items/123
```

### Webhook Testing
```bash
# Send test webhook payload
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "event": "test",
    "data": {"key": "value"}
  }' \
  https://webhook.example.com/endpoint
```

## Quick Reference

| Operation | Command | Safety Level |
|-----------|---------|--------------|
| GET request | `curl -s https://...` | Safe |
| POST request | `curl -X POST -d '{}' https://...` | Medium - confirm |
| Download file | `curl -sLO https://...` | Safe |
| Check status | `curl -sI https://...` | Safe |
| API with auth | `curl -H "Authorization: ..." https://...` | Medium - verify token |
| Local request | `curl http://localhost:...` | **Dangerous - SSRF risk** |

## Environment Variables for Credentials

Always use environment variables for sensitive data:

```bash
# Good: Use environment variable
curl -s -H "Authorization: Bearer $API_TOKEN" https://api.example.com

# Bad: Hardcoded token
curl -s -H "Authorization: Bearer abc123..." https://api.example.com
```

---

**Remember**: Always verify URLs and require confirmation for operations that modify data or access sensitive endpoints.
