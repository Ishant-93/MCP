# Super Singularity MCP Server

A Model Context Protocol (MCP) server for integrating Claude Desktop with Super Singularity's course creation API, ElevenLabs text-to-speech, and Azure Blob Storage.

## Features

- **Complete Course Management**: Create, update, and manage courses
- **All Card Types**: Support for content, quiz, poll, form, video, audio, and link cards  
- **Text-to-Speech**: Generate audio from text using ElevenLabs TTS
- **Cloud Storage**: Upload and host audio files on Azure Blob Storage
- **Script Preservation**: Store original script text in audio card contents
- **Production Ready**: Environment configuration, error handling, and timeout management

## Quick Start

1. **Clone and Install**:
   ```bash
   git clone <repository-url>
   cd mcp-servers
   uv sync
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Add to Claude Desktop**:
   Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "super-singularity": {
         "command": "uv",
         "args": ["run", "python", "/path/to/mcp-servers/server.py"]
       }
     }
   }
   ```

4. **Restart Claude Desktop** and start creating courses!

## Environment Configuration

Required environment variables in `.env`:

```bash
# Super Singularity API
API_BASE_URL=https://your-api-domain.com
API_TOKEN=your-bearer-token-here  
COMPANY_ID=your-company-id-here

# ElevenLabs TTS
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Azure Blob Storage  
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_CONTAINER_NAME=audio-files
```

## Available Tools

### Course Management
- `get_course(course_id)` - Get course details
- `create_course(title, ...)` - Create new course
- `get_course_cards(course_id)` - Get all cards in course

### Card Creation
- `create_content_card()` - Text content with optional image
- `create_quiz_card()` - Multiple choice questions
- `create_poll_card()` - Opinion polls for collecting learner feedback
- `create_form_card()` - Form inputs for collecting learner responses
- `create_video_card()` - Video content
- `create_audio_card()` - Audio content with optional script preservation
- `create_link_card()` - External resource links

### Audio Generation
- `generate_audio_from_text(text, title)` - Generate audio using ElevenLabs TTS
- Creates audio files and uploads to Azure Storage
- Returns URL and script preservation instructions

## Audio Card Workflow

Due to MCP limitations, audio card creation from script requires two steps:

1. **Generate Audio**:
   ```
   generate_audio_from_text("Your script text here", "Audio Title")
   ```

2. **Create Card with Script Preservation**:
   ```
   create_audio_card(course_id, audio_url, title, script="Your script text here")
   ```

The script parameter preserves the original text in the card contents for future reference.

## MCP Limitations Discovered

### The Problem
MCP tools that combine multiple async operations (ElevenLabs + Azure + API requests) cause "Internal Server Error" in Claude Desktop, regardless of function names or implementation approach.

### Failed Attempts
All of these caused Internal Server Errors:
- `create_audio_card_from_script()`
- `generate_audio_url_from_script()`  
- `create_audio_card_using_script()`
- `test_helper_function_plus_api()`

### Working Solution
 **Separate tools for each operation**:
- `generate_audio_from_text()` - Only handles ElevenLabs + Azure
- `create_audio_card()` - Only handles API requests
- Two-step workflow with clear instructions for script preservation

### Root Cause Analysis
The limitation appears to be related to:
- Complex async operation chains in single MCP tools
- Timeout thresholds for multi-step operations  
- Memory/resource constraints in Claude Desktop MCP client
- Event loop handling of combined external service calls

## Community Validation

Our findings align with known MCP issues documented in the community:
- [GitHub Issue #424](https://github.com/anthropics/claude-code/issues/424): "MCP Timeout needs to be configurable"
- [GitHub Issue #417](https://github.com/modelcontextprotocol/python-sdk/issues/417): "MCP Server Internal Server Error Report"
- Multiple forum discussions about timeout errors and Internal Server Errors

## Best Practices Learned

1. **Keep MCP tools simple and atomic** - Single responsibility per tool
2. **Avoid combining multiple external service calls** in one tool
3. **Use helper functions** for complex operations, but call them from separate tools
4. **Provide clear instructions** in tool responses to guide multi-step workflows
5. **Test incrementally** when adding new integrations

## API Documentation

Complete API documentation available in: [`documentation/external-api-documentation.md`](documentation/external-api-documentation.md)

## Dependencies

- `mcp` - Model Context Protocol Python SDK
- `httpx` - Async HTTP client for API requests
- `elevenlabs` - ElevenLabs TTS integration  
- `azure-storage-blob` - Azure Blob Storage client
- `python-dotenv` - Environment variable management

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]
