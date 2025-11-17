# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Run the MCP server
uv run python server.py

# Test the server (optional)
uv run python -c "import server; print('Server loaded successfully')"
```

### Environment Configuration
Create a `.env` file with required API keys:
```bash
# Super Singularity API
API_BASE_URL=https://your-api-domain.com
API_TOKEN=your-bearer-token-here
COMPANY_ID=your-company-id-here

# ElevenLabs TTS
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_CONTAINER_NAME=media

# Azure OpenAI (for image generation)
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-image-1
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```

### Claude Desktop Integration
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

## Architecture

### MCP Server Implementation
- **FastMCP Framework**: Uses `mcp.server.fastmcp` for MCP protocol implementation
- **Tool-based Architecture**: Each API operation is exposed as an MCP tool decorated with `@mcp.tool()`
- **Async Operations**: All tools are async functions for non-blocking I/O
- **Transport**: Uses `stdio` transport for communication with Claude Desktop

### Key Components

1. **API Integration** (`make_api_request`):
   - Handles authenticated requests to Super Singularity API
   - Supports GET, POST, PUT methods with Bearer token authentication
   - Includes error handling and timeout management (30s timeout)
   - Returns error dict on failure: `{"error": "error message"}`

2. **Audio Generation Pipeline**:
   - **ElevenLabs TTS** (`generate_audio_with_elevenlabs`):
     - Converts text to speech using ElevenLabs API
     - Uses `eleven_turbo_v2_5` OR `eleven_v3` model with configurable voice settings
     - Returns audio data as bytes
   - **Azure Storage** (`upload_to_azure`):
     - Uploads generated audio to Azure Blob Storage
     - Supports folder organization by file type
     - Returns public URL of uploaded file
   - **Two-step workflow**: Due to MCP limitations, audio card creation requires:
     1. `generate_audio_from_text()` - Generate and upload audio
     2. `create_audio_card()` - Create card with audio URL and script

3. **Image Generation Pipeline**:
   - **Azure OpenAI gpt-image-1** (`generate_image_with_azure_openai`):
     - Generates images from text prompts using Azure OpenAI
     - Supports two aspect ratios: "square" (1024x1024) and "portrait" (900x1600)
     - Quality set to "medium" for optimal balance
     - Returns image data as bytes
   - **WebP Conversion** (`convert_image_to_webp`):
     - Converts generated images to WebP format with 85% quality
     - Optimized for low latency devices with poor network conditions
     - Maintains good visual quality while reducing file size
   - **Azure Storage Integration**:
     - Uploads optimized images to Azure Blob Storage in "images" folder
     - Returns public URL for use in content cards
   - **Two-step workflow**: Similar to audio, image card creation requires:
     1. `generate_image_from_text()` - Generate, convert, and upload image
     2. `create_content_card()` - Create card with image URL and preserve original prompt

4. **Course & Card Management**:
   - Complete support for all card types: content, quiz, poll, form, video, audio, link
   - UUID generation for unique IDs using `uuid.uuid4()`
   - Script preservation in audio cards for maintaining original text
   - First card automatically created with course

### Available MCP Tools

#### Course Management
- `get_course(course_id)` - Get course details
- `create_course(title, duration?, description?, folder_id?, is_published?, is_autoplay?, is_scorable?, gradient_from_color?, gradient_to_color?, theme_id?)` - Create new course
- `get_course_cards(course_id)` - Get all cards in a course

#### Card Creation
- `create_content_card(course_id, header1_text, header2_text?, image_url?, align?, sort_order?, is_mandatory?)` - Text/image content
- `create_quiz_card(course_id, question, options, correct_answer, comment?, sort_order?, is_mandatory?)` - Multiple choice quiz
- `create_video_card(course_id, video_url, sort_order?, is_mandatory?)` - Video content
- `create_audio_card(course_id, audio_url, title, background_image_url?, script?, sort_order?, is_mandatory?)` - Audio content
- `create_link_card(course_id, title, link_url, link_caption?, sort_order?)` - External links

#### Card Management
- `update_card(card_id, contents?, is_mandatory?, sort_order?, is_active?, card_type?)` - Update existing card

#### Audio Generation
- `generate_audio_from_text(text, title)` - Generate audio using ElevenLabs and upload to Azure

#### Image Generation
- `generate_image_from_text(prompt, title, aspect_ratio?, output_format?)` - Generate image using Azure OpenAI, convert to WebP, and upload to Azure

#### Utility
- `echo_message(message)` - Test tool for debugging
- `get_server_info()` - Get server information

### MCP Limitations Discovered
- **Cannot combine multiple async operations** in a single MCP tool (ElevenLabs + Azure + API calls)
- **Solution**: Separate tools for each operation with clear workflow instructions
- **Root cause**: Complex async operation chains exceed MCP timeout thresholds
- **Community validation**: Issues documented in [#424](https://github.com/anthropics/claude-code/issues/424) and [#417](https://github.com/modelcontextprotocol/python-sdk/issues/417)

### Best Practices Learned
1. Keep MCP tools simple and atomic - single responsibility per tool
2. Avoid combining multiple external service calls in one tool
3. Use helper functions for complex operations, but call them from separate tools
4. Provide clear instructions in tool responses to guide multi-step workflows
5. Test incrementally when adding new integrations

### External API Documentation
Complete Super Singularity API documentation available in `documentation/external-api-documentation.md` covering:
- Authentication methods (JWT/Bearer tokens)
- Course creation requirements and fields
- All card types with detailed content structures
- API endpoints and request/response formats
- Best practices for external integrations