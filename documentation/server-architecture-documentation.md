# Super Singularity MCP Server Architecture Documentation

## Overview

This document provides comprehensive technical documentation for the Super Singularity MCP (Model Context Protocol) server implementation. The server acts as a bridge between Claude Desktop and the Super Singularity Learning Management System API, with enhanced capabilities for media generation and processing.

## Architecture Components

### 1. Core MCP Framework

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("super-singularity-api-server")
```

- **Framework**: Uses FastMCP for MCP protocol implementation
- **Transport**: Stdio transport for Claude Desktop communication
- **Tool Pattern**: Each API operation exposed as `@mcp.tool()` decorated functions

### 2. API Integration Layer

#### Authentication & Request Handling
```python
async def make_api_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]
```

**Features:**
- Bearer token authentication (`API_TOKEN`)
- Support for GET, POST, PUT methods
- 30-second timeout for all requests
- Comprehensive error handling with structured responses
- Returns `{"error": "message"}` on failures

**Configuration:**
```python
API_BASE_URL = os.getenv("API_BASE_URL")
API_TOKEN = os.getenv("API_TOKEN")
COMPANY_ID = os.getenv("COMPANY_ID")
```

### 3. Media Processing Pipeline

#### Audio Generation Workflow

**Step 1: Text-to-Speech Generation**
```python
async def generate_audio_with_elevenlabs(text: str) -> bytes
```
- **Service**: ElevenLabs API
- **Model**: `eleven_turbo_v2_5` or `eleven_v3`
- **Voice Settings**:
  - Stability: 0.71
  - Similarity Boost: 0.5
  - Style: 0.0
  - Speaker Boost: Enabled
- **Output**: Raw audio bytes (MP3 format)

**Step 2: Azure Storage Upload**
```python
async def upload_to_azure(file_data: bytes, filename: str, file_type: str, file_extension: str) -> str
```
- **Folder Structure**: `{file_type}/{filename}_{uuid[:8]}.{extension}`
- **Unique Naming**: UUID-based collision prevention
- **Public Access**: Returns publicly accessible URL

**Complete Audio Pipeline**
```python
async def generate_and_upload_audio(text: str, title: str) -> str
```
1. Generate audio using ElevenLabs
2. Process filename (spaces → underscores, lowercase)
3. Upload to Azure Storage in "audio" folder
4. Return public URL

#### Image Generation Workflow

**Step 1: Image Generation with Azure OpenAI**
```python
async def generate_image_with_azure_openai(prompt: str, size: str, output_format: str) -> bytes
```
- **Service**: Azure OpenAI gpt-image-1 deployment
- **API Version**: 2025-04-01-preview
- **Configuration**:
  - Quality: "medium"
  - Output Compression: 100
  - Timeout: 60 seconds
- **Size Validation**: Regex pattern `^\d+x\d+$`
- **Format Support**: PNG, JPG

**Step 2: WebP Conversion & Optimization**
```python
def convert_image_to_webp(image_bytes: bytes, quality: int = 85) -> bytes
```
- **Purpose**: Optimize for low latency devices and poor network conditions
- **Quality**: 85% (balanced quality/size ratio)
- **Color Mode Handling**: Converts RGBA/P modes to RGB for WebP compatibility
- **Optimization**: Enabled for maximum compression

**Step 3: Storage Upload**
```python
async def generate_and_upload_image(prompt: str, title: str, size: str, output_format: str) -> str
```
1. Generate image using Azure OpenAI
2. Convert to optimized WebP format
3. Upload to Azure Storage in "images" folder
4. Return public URL

### 4. Super Singularity API Integration

#### Course Management Tools

**Course Creation**
```python
@mcp.tool()
async def create_course(title: str, duration: Optional[int] = 0, ...)
```
- **UUID Generation**: Automatic unique ID assignment
- **Company Association**: Automatic `companyId` assignment
- **AI Tracking**: Always sets `createdByAgent: true` for MCP-created courses
- **Course Plan**: Optional `finalizedCoursePlan` field (max 13000 chars) for storing prompts and structure
- **Optional Fields**: Description, folder organization, theming
- **Publishing Control**: Draft/published state management

**Course Retrieval**
```python
@mcp.tool()
async def get_course(course_id: str)
@mcp.tool()
async def get_card(card_id: str)  # Get single card with contents
@mcp.tool() 
async def get_course_cards(course_id: str)
```

#### Card Creation Tools

**Content Cards with Image Tracking**
```python
@mcp.tool()
async def create_content_card(course_id: str, header1_text: str, ...)
```
- **Text Processing**: HTML tag stripping for clean text storage
- **Image Integration**: Optional image URL support
- **Image Generation Tracking**:
  - `imagePrompt`: Stores original generation prompt
  - `imageGenerated`: Boolean flag for AI-generated images
  - `imageGeneratedAt`: ISO timestamp when generated
  - `imageGeneratedBy`: Auto-set to "CLAUDE_MCP_SERVER"
- **Alignment Options**: "center center", "top", "bottom", "bg"

**Quiz Cards**
```python
@mcp.tool()
async def create_quiz_card(course_id: str, question: str, options: List[str], ...)
```
- **Validation**: 2-4 options required
- **Answer Verification**: Correct answer must match an option
- **Default Mandatory**: Quiz cards default to mandatory

**Audio Cards with Complete Tracking**
```python
@mcp.tool()
async def create_audio_card(course_id: str, audio_url: str, title: str, ...)
```
- **Audio Script Preservation**: Original text preserved in `audioScript`
- **Audio Generation Tracking**: 
  - `audioGenerated`: Boolean flag
  - `audioGeneratedAt`: ISO timestamp in IST timezone
  - `audioGeneratedBy`: Auto-set to "CLAUDE_MCP_SERVER"
- **Background Image Tracking**:
  - `imagePrompt`: Stores background image generation prompt
  - `imageGenerated`: Boolean flag for AI-generated background
  - `imageGeneratedAt`: ISO timestamp when generated
  - `imageGeneratedBy`: Auto-set to "CLAUDE_MCP_SERVER"

**Additional Card Types**:
- **Poll Cards**: Opinion collection with 2-4 options
- **Form Cards**: Open-ended input collection  
- **Video Cards**: Video content embedding
- **Link Cards**: External resource linking

#### Card Management

**Update Functionality with AI Metadata Preservation**
```python
@mcp.tool()
async def update_card(card_id: str, contents: Optional[Dict] = None, ...)
```
- **GET-Merge-PUT Workflow**: Automatically fetches current card and merges updates
- **AI Metadata Preservation**: Preserves `imagePrompt`, `audioScript`, and all tracking fields
- **Shallow Merge Strategy**: Top-level keys in contents are merged
- **Validation Control**: Only includes `cardType` when explicitly changing (avoids validation)
- **State Management**: Active/inactive, mandatory/optional controls

### 5. MCP Tool Workflow Patterns

#### Two-Step Media Workflows

Due to MCP timeout limitations, media creation requires separation:

**Audio Workflow:**
1. `generate_audio_from_text(text, title)` → Returns audio URL + instructions
2. `create_audio_card(course_id, audio_url, title, audio_script, audio_generated, audio_generated_at)`

**Content Card Image Workflow:**
1. `generate_image_from_text(prompt, title, aspect_ratio)` → Returns image URL + instructions
2. `create_content_card(course_id, header1_text, image_url, image_prompt, image_generated, image_generated_at)`

**Audio Card Background Image Workflow:**
1. `generate_background_image_for_audio(prompt, title)` → Returns portrait image URL + instructions
2. `create_audio_card(course_id, audio_url, title, background_image_url, image_prompt, image_generated, image_generated_at)`

#### Image Generation Tools

**General Image Generation** (`generate_image_from_text`):
- **Use for**: Content card images
- **Aspect Ratios**: "square" (1024x1024), "portrait" (1024x1536), "landscape" (1536x1024)
- **Auto-tracking**: Sets `imageGeneratedBy` to "CLAUDE_MCP_SERVER"

**Audio Background Generation** (`generate_background_image_for_audio`):
- **Use for**: Audio card background images only
- **Fixed Format**: Always portrait (1024x1536) - optimized for audio cards
- **Auto-tracking**: Sets `imageGeneratedBy` to "CLAUDE_MCP_SERVER"

### 6. Error Handling & Resilience

#### Exception Patterns
```python
try:
    # Operation
except Exception as e:
    raise Exception(f"Service operation failed: {str(e)}")
```

#### API Error Responses
```python
return {"error": "HTTP 400: Bad Request details"}
return {"error": "Request failed: Connection timeout"}
```

#### Validation Layers
- Input validation at tool level
- Format validation for external APIs
- Content structure validation for card creation

### 7. Environment Configuration

#### Required Environment Variables
```env
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

# Azure OpenAI
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-image-1
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```

### 8. Key Technical Decisions

#### WebP Optimization Strategy
- **Rationale**: Optimized for users with poor network conditions
- **Quality Setting**: 85% balances visual quality with file size
- **Format Conversion**: Always convert generated images to WebP regardless of source format

#### UUID Generation
- Uses `uuid.uuid4()` for guaranteed uniqueness
- Applied to courses, cards, and file naming
- Truncated (8 chars) for file naming to prevent long paths

#### Timezone Handling
- Audio generation timestamps use IST timezone
- Consistent with target user base expectations
- ISO format for API compatibility

#### MCP Timeout Management
- Separated complex operations into atomic tools
- Maximum individual operation timeout: 60 seconds (image generation)
- HTTP request timeout: 30 seconds
- Clear workflow instructions provided in tool responses
- GET-then-PUT pattern for safe card updates that preserve AI metadata

## Performance Considerations

### Async Operations
- All API calls and media operations are async
- Non-blocking I/O for improved responsiveness
- Proper exception propagation for debugging

### Memory Management
- Streaming audio generation (generator to bytes conversion)
- In-memory image processing with PIL
- Immediate cleanup of temporary objects

### Network Optimization
- Connection pooling via httpx.AsyncClient context managers
- Appropriate timeout settings for different operation types
- Retry logic handled by underlying HTTP libraries

## Security Features

### Authentication
- Bearer token authentication for Super Singularity API
- API key authentication for ElevenLabs and Azure services
- Environment variable based credential management

### Data Handling
- No credential logging or exposure
- Secure file upload with overwrite protection
- Public URL generation for controlled access

This architecture provides a robust, scalable foundation for learning content creation with integrated media generation capabilities.