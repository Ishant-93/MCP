from typing import Any, Dict, List, Optional
import httpx
import uuid
import json
import base64
import re
from PIL import Image
import io
from datetime import datetime
import pytz
from mcp.server.fastmcp import FastMCP
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from azure.storage.blob import BlobServiceClient

# Configuration from environment variables
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("super-singularity-api-server")

API_BASE_URL = os.getenv("API_BASE_URL", "https://your-api-domain.com")
API_TOKEN = os.getenv("API_TOKEN", "your-bearer-token-here")
COMPANY_ID = os.getenv("COMPANY_ID", "your-company-id-here")

# ElevenLabs configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "your-elevenlabs-api-key")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Default: Rachel

# Azure Storage configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "your-azure-connection-string")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "audio-files")

# Azure OpenAI configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "your-azure-openai-api-key")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.cognitiveservices.azure.com")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-image-1")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

async def make_api_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make authenticated API request to Super Singularity API."""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    url = f"{API_BASE_URL}{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, timeout=30.0)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=data, timeout=30.0)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

def generate_uuid() -> str:
    """Generate a new UUID for courses and cards."""
    return str(uuid.uuid4())

async def generate_audio_with_elevenlabs(text: str) -> bytes:
    """Generate audio from text using ElevenLabs API.

    Args:
        text: The text to convert to speech

    Returns:
        Audio data as bytes
    """
    try:
        # Initialize ElevenLabs client
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        # Generate audio using the correct API method
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id="eleven_v3",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.5,
                style=0.0,
                use_speaker_boost=True
            )
        )

        # Convert generator to bytes
        audio_bytes = b"".join(audio)
        return audio_bytes

    except Exception as e:
        raise Exception(f"ElevenLabs audio generation failed: {str(e)}")

async def upload_to_azure(file_data: bytes, filename: str, file_type: str = "audio", file_extension: str = "mp3") -> str:
    """Upload file data to Azure Storage and return the public URL.

    Args:
        file_data: File data as bytes
        filename: Name for the uploaded file (without extension)
        file_type: Type of file (audio, video, image, etc.) for folder organization
        file_extension: File extension (mp3, mp4, jpg, png, etc.)

    Returns:
        Public URL of the uploaded file
    """
    try:
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

        # Generate unique filename with folder structure
        blob_name = f"{file_type}/{filename}_{generate_uuid()[:8]}.{file_extension}"

        # Upload the file
        blob_client = blob_service_client.get_blob_client(
            container=AZURE_CONTAINER_NAME,
            blob=blob_name
        )

        blob_client.upload_blob(file_data, overwrite=True)

        # Return the public URL
        return blob_client.url

    except Exception as e:
        raise Exception(f"Azure Storage upload failed: {str(e)}")

async def generate_and_upload_audio(text: str, title: str) -> str:
    """Generate audio from text and upload to Azure Storage.

    Args:
        text: The text to convert to speech
        title: Title for the audio file

    Returns:
        Public URL of the uploaded audio file
    """
    # Generate audio
    audio_data = await generate_audio_with_elevenlabs(text)

    # Upload to Azure
    filename = title.replace(" ", "_").lower()
    audio_url = await upload_to_azure(audio_data, filename, "audio", "mp3")

    return audio_url

async def generate_image_with_azure_openai(prompt: str, size: str = "1024x1024", output_format: str = "png") -> bytes:
    """Generate image from prompt using Azure OpenAI API.

    Args:
        prompt: The prompt to generate image from
        size: Image size in format "WIDTHxHEIGHT" (e.g., "1024x1024")
        output_format: Output format ("png" or "jpg")

    Returns:
        Image data as bytes
    """
    try:
        # Validate size format
        if not re.match(r'^\d+x\d+$', size):
            raise ValueError(f"Invalid size format: {size}. Must be in format 'WIDTHxHEIGHT'")

        # Validate output format
        if output_format not in ["png", "jpg"]:
            raise ValueError(f"Invalid output format: {output_format}. Must be 'png' or 'jpg'")

        url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/images/generations"

        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY
        }

        data = {
            "prompt": prompt,
            "size": size,
            "quality": "medium",
            "output_compression": 100,
            "output_format": output_format,
            "n": 1
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=data,
                params={"api-version": AZURE_OPENAI_API_VERSION},
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()

            # Extract base64 image data
            if "data" in result and len(result["data"]) > 0:
                b64_json = result["data"][0]["b64_json"]
                image_bytes = base64.b64decode(b64_json)
                return image_bytes
            else:
                raise Exception("No image data returned from Azure OpenAI")

    except Exception as e:
        raise Exception(f"Azure OpenAI image generation failed: {str(e)}")

def convert_image_to_webp(image_bytes: bytes, quality: int = 85) -> bytes:
    """Convert image bytes to WebP format with compression.

    Args:
        image_bytes: Original image bytes
        quality: WebP quality (0-100, default 85 for good quality/size balance)

    Returns:
        WebP image bytes
    """
    try:
        # Open the image
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary (WebP doesn't support all modes)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Save as WebP with compression
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="WebP", quality=quality, optimize=True)

        return output_buffer.getvalue()

    except Exception as e:
        raise Exception(f"Image conversion to WebP failed: {str(e)}")

async def generate_and_upload_image(prompt: str, title: str, size: str = "1024x1024", output_format: str = "png") -> str:
    """Generate image from prompt and upload to Azure Storage.

    Args:
        prompt: The prompt to generate image from
        title: Title for the image file
        size: Image size in format "WIDTHxHEIGHT"
        output_format: Original format from OpenAI ("png" or "jpg")

    Returns:
        Public URL of the uploaded image file
    """
    # Generate image
    image_data = await generate_image_with_azure_openai(prompt, size, output_format)

    # Convert to WebP for better compression and web optimization
    webp_data = convert_image_to_webp(image_data, quality=85)

    # Upload to Azure
    filename = title.replace(" ", "_").lower()
    image_url = await upload_to_azure(webp_data, filename, "images", "webp")

    return image_url

@mcp.tool()
async def get_course(course_id: str) -> str:
    """Get details of a specific course.

    Args:
        course_id: The ID of the course to retrieve
    """
    result = await make_api_request("GET", f"/api/course?id={course_id}")
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_course(
    title: str,
    duration: Optional[int] = 0,
    description: Optional[str] = None,
    folder_id: Optional[str] = None,
    finalized_course_plan: Optional[str] = None,
    is_published: bool = False,
    is_autoplay: bool = False,
    is_scorable: bool = False,
    gradient_from_color: Optional[str] = None,
    gradient_to_color: Optional[str] = None,
    theme_id: Optional[str] = None
) -> str:
    """Create a new course in Super Singularity.
    
    NOTE: All courses created via MCP server are automatically marked as AI-generated.

    Args:
        title: Course title (max 255 characters)
        duration: Course duration in minutes (default: 0)
        description: Course description (max 1000 characters)
        folder_id: ID of the folder to organize the course
        finalized_course_plan: Course plan in Markdown format (max 13000 chars) - stores original prompt and structure
        is_published: Whether the course is visible to learners (default: false)
        is_autoplay: Auto-advance cards (default: false)
        is_scorable: Track quiz scores (default: false)
        gradient_from_color: Hex color for gradient start (e.g., "#FF0000")
        gradient_to_color: Hex color for gradient end
        theme_id: Custom theme ID
    """
    course_data = {
        "id": generate_uuid(),
        "title": title,
        "companyId": COMPANY_ID,
        "duration": duration,
        "isPublished": is_published,
        "isAutoplay": is_autoplay,
        "isScorable": is_scorable,
        "createdByAgent": True  # Always true for MCP server created courses
    }

    # Add optional fields if provided
    if description:
        course_data["description"] = description
    if folder_id:
        course_data["folderId"] = folder_id
    if finalized_course_plan:
        course_data["finalizedCoursePlan"] = finalized_course_plan
    if gradient_from_color:
        course_data["gradientFromColor"] = gradient_from_color
    if gradient_to_color:
        course_data["gradientToColor"] = gradient_to_color
    if theme_id:
        course_data["themeId"] = theme_id

    result = await make_api_request("POST", "/api/createCourse", course_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_audio_card(
    course_id: str,
    audio_url: str,
    title: str,
    background_image_url: Optional[str] = None,
    audio_script: Optional[str] = None,
    audio_generated: Optional[bool] = None,
    audio_generated_at: Optional[str] = None,
    image_prompt: Optional[str] = None,
    image_generated: Optional[bool] = None,
    image_generated_at: Optional[str] = None,
    sort_order: Optional[int] = None,
    is_mandatory: bool = False
) -> str:
    """Create an audio card with existing audio URL.

    Args:
        course_id: The course to add this card to
        audio_url: URL of the audio file (MP3, WAV, OGG)
        title: Title text for the audio card
        background_image_url: Optional background image URL
        audio_script: Optional script text that was used to generate the audio
        audio_generated: Optional flag to indicate if audio was generated (true) or uploaded
        audio_generated_at: Optional timestamp when audio was generated (ISO string, IST)
        image_prompt: Optional original image generation prompt for background image
        image_generated: Optional flag to indicate if background image was generated
        image_generated_at: Optional timestamp when background image was generated
        sort_order: Position in course (auto-incremented if not provided)
        is_mandatory: Whether learner must listen to proceed
    """
    contents = {
        "_header1": {
            "text": title,
            "visibility": True,
            "size": "medium"
        },
        "header1": title,
        "audio": audio_url
    }

    if background_image_url:
        contents["image"] = background_image_url

    if audio_script:
        contents["audioScript"] = audio_script

    if audio_generated is not None:
        contents["audioGenerated"] = audio_generated

    if audio_generated_at:
        contents["audioGeneratedAt"] = audio_generated_at
    
    # Always set audioGeneratedBy to CLAUDE_MCP_SERVER when audio is generated
    if audio_generated:
        contents["audioGeneratedBy"] = "CLAUDE_MCP_SERVER"
    
    # Add image generation tracking fields for background image if provided
    if image_prompt:
        contents["imagePrompt"] = image_prompt
    if image_generated is not None:
        contents["imageGenerated"] = image_generated
    if image_generated_at:
        contents["imageGeneratedAt"] = image_generated_at
    # Always set imageGeneratedBy to CLAUDE_MCP_SERVER when background image is generated
    if image_generated:
        contents["imageGeneratedBy"] = "CLAUDE_MCP_SERVER"

    card_data = {
        "courseId": course_id,
        "cardType": "audio",
        "contents": contents,
        "isMandatory": is_mandatory
    }

    if sort_order:
        card_data["sortOrder"] = sort_order

    result = await make_api_request("POST", "/api/createCard", card_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def generate_background_image_for_audio(
    prompt: str,
    title: str
) -> str:
    """Generate a background image specifically for audio cards using Azure OpenAI.
    
    USE THIS TOOL FOR: Audio card background images ONLY.
    FOR CONTENT CARD IMAGES: Use generate_image_from_text instead (flexible aspect ratios).
    
    NOTE: Audio card background images are ALWAYS generated in portrait format (1024x1536) for optimal display.

    Args:
        prompt: Detailed prompt for background image generation
        title: Title for the image file
    """
    try:
        # Generate timestamp in IST
        ist = pytz.timezone('Asia/Kolkata')
        generated_at = datetime.now(ist).isoformat()
        
        # ALWAYS use portrait size for audio card backgrounds
        size = "1024x1536"

        # Generate and upload image
        image_url = await generate_and_upload_image(prompt, title, size, "png")

        return f"""Background image generated and uploaded successfully!

Image URL: {image_url}
Image Format: Portrait (1024x1536) - optimized for audio cards

IMPORTANT: When creating the audio card with this background image, include these parameters:
- background_image_url: "{image_url}"
- image_prompt: "{prompt}"
- image_generated: true
- image_generated_at: "{generated_at}"

Use create_audio_card with all audio parameters PLUS these image tracking parameters for the background.

Note: The system automatically sets imageGeneratedBy to 'CLAUDE_MCP_SERVER' when image_generated is true."""
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def echo_message(message: str) -> str:
    """Echo back a message for testing.

    Args:
        message: The message to echo back
    """
    return f"Echo: {message}"

@mcp.tool()
async def generate_audio_from_text(text: str, title: str) -> str:
    """Generate audio from text using ElevenLabs TTS and upload to Azure Storage.

    Args:
        text: Text to convert to speech
        title: Title for the audio file
    """
    try:
        # Generate timestamp in IST
        ist = pytz.timezone('Asia/Kolkata')
        generated_at = datetime.now(ist).isoformat()
        
        audio_url = await generate_and_upload_audio(text, title)
        return f"""Audio generated and uploaded successfully!

Audio URL: {audio_url}

IMPORTANT: When creating the audio card, include these parameters to properly track generated audio:
- script: "{text}"
- audio_generated: true
- audio_generated_at: "{generated_at}"

Use create_audio_card with script, audio_generated, and audio_generated_at parameters to maintain proper tracking.

If you're also generating a background image for this audio card, remember to include the image tracking parameters as well.

Note: For audio card background images, consider using generate_background_image_for_audio which automatically generates portrait-format images optimized for audio cards."""
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def generate_image_from_text(
    prompt: str,
    title: str,
    aspect_ratio: Optional[str] = None,
    output_format: Optional[str] = None
) -> str:
    """Generate image from text prompt using Azure OpenAI and upload to Azure Storage.
    
    USE THIS TOOL FOR: Content card images (any aspect ratio).
    FOR AUDIO CARD BACKGROUNDS: Use generate_background_image_for_audio instead (optimized portrait format).

    Args:
        prompt: Detailed prompt for image generation (mandatory)
        title: Title for the image file (mandatory)
        aspect_ratio: Image aspect ratio ("square", "portrait", or "landscape", optional, defaults to "square")
        output_format: Original format from OpenAI ("png" or "jpg", optional, defaults to "png")
    """
    try:
        # Generate timestamp in IST
        ist = pytz.timezone('Asia/Kolkata')
        generated_at = datetime.now(ist).isoformat()
        
        # Set defaults
        if aspect_ratio is None:
            aspect_ratio = "square"
        if output_format is None:
            output_format = "png"

        # Map aspect ratio to size
        if aspect_ratio.lower() == "square":
            size = "1024x1024"
        elif aspect_ratio.lower() == "portrait":
            size = "1024x1536"
        elif aspect_ratio.lower() == "landscape":
            size = "1536x1024"
        else:
            # Default to square if invalid aspect ratio provided
            size = "1024x1024"

        # Validate output format
        if output_format not in ["png", "jpg"]:
            return f"Error: Invalid output format '{output_format}'. Must be 'png' or 'jpg'"

        # Generate and upload image
        image_url = await generate_and_upload_image(prompt, title, size, output_format)

        return f"""Image generated and uploaded successfully!

Image URL: {image_url}

IMPORTANT: When creating content or audio cards with this image, include these parameters to properly track generated images:
- image_prompt: "{prompt}"
- image_generated: true
- image_generated_at: "{generated_at}"

For content cards: Use create_content_card with image_url, image_prompt, image_generated, and image_generated_at parameters.
For audio cards (background image): Use create_audio_card with background_image_url, image_prompt, image_generated, and image_generated_at parameters.

Note: The system automatically sets imageGeneratedBy to 'CLAUDE_MCP_SERVER' when image_generated is true."""
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_card(card_id: str) -> str:
    """Get details of a specific card.

    Args:
        card_id: The ID of the card to retrieve
    """
    result = await make_api_request("GET", f"/api/card/{card_id}")
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_course_cards(course_id: str) -> str:
    """Get all cards for a specific course.

    Args:
        course_id: The ID of the course to get cards for
    """
    result = await make_api_request("GET", f"/api/courses/{course_id}/cards")
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_content_card(
    course_id: str,
    header1_text: str,
    header2_text: Optional[str] = None,
    image_url: Optional[str] = None,
    image_prompt: Optional[str] = None,
    image_generated: Optional[bool] = None,
    image_generated_at: Optional[str] = None,
    align: str = "center center",
    sort_order: Optional[int] = None,
    is_mandatory: bool = False
) -> str:
    """Create a content card with text and optional image.

    Args:
        course_id: The course to add this card to
        header1_text: Main heading text (supports HTML formatting)
        header2_text: Secondary text or description
        image_url: Optional image URL
        image_prompt: Optional original image generation prompt
        image_generated: Optional flag to indicate if image was generated
        image_generated_at: Optional timestamp when image was generated (ISO string)
        align: Content alignment ("center center", "top", "bottom", or "bg")
        sort_order: Position in course (auto-incremented if not provided)
        is_mandatory: Whether card is mandatory to view
    """
    contents = {
        "_header1": {
            "text": header1_text,
            "visibility": True,
            "size": "medium"
        },
        "header1": header1_text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
    }

    if header2_text:
        contents["_header2"] = {
            "text": header2_text,
            "visibility": True,
            "size": "medium"
        }
        contents["header2"] = header2_text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")

    if image_url:
        contents["image"] = image_url
        contents["align"] = align
    
    # Add image generation tracking fields if provided
    if image_prompt:
        contents["imagePrompt"] = image_prompt
    if image_generated is not None:
        contents["imageGenerated"] = image_generated
    if image_generated_at:
        contents["imageGeneratedAt"] = image_generated_at
    # Always set imageGeneratedBy to CLAUDE_MCP_SERVER when image is generated
    if image_generated:
        contents["imageGeneratedBy"] = "CLAUDE_MCP_SERVER"

    card_data = {
        "courseId": course_id,
        "cardType": "content",
        "contents": contents,
        "align": align,
        "isMandatory": is_mandatory
    }

    if sort_order:
        card_data["sortOrder"] = sort_order

    result = await make_api_request("POST", "/api/createCard", card_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_quiz_card(
    course_id: str,
    question: str,
    options: List[str],
    correct_answer: str,
    comment: Optional[str] = None,
    sort_order: Optional[int] = None,
    is_mandatory: bool = True
) -> str:
    """Create a quiz card with multiple choice question.

    Args:
        course_id: The course to add this card to
        question: The quiz question
        options: List of 2-4 answer options
        correct_answer: The correct answer (must match one of the options exactly)
        comment: Optional explanation for the answer
        sort_order: Position in course (auto-incremented if not provided)
        is_mandatory: Whether learner must answer to proceed (default: true)
    """
    if len(options) < 2 or len(options) > 4:
        return json.dumps({"error": "Quiz must have 2-4 options"}, indent=2)

    if correct_answer not in options:
        return json.dumps({"error": f"Correct answer '{correct_answer}' must be one of the provided options"}, indent=2)

    contents = {
        "_header1": {
            "text": question,
            "visibility": True,
            "size": "medium"
        },
        "header1": question,
        "options": options,
        "correct": [correct_answer]
    }

    if comment:
        contents["comment"] = comment

    card_data = {
        "courseId": course_id,
        "cardType": "quiz",
        "contents": contents,
        "isMandatory": is_mandatory
    }

    if sort_order:
        card_data["sortOrder"] = sort_order

    result = await make_api_request("POST", "/api/createCard", card_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_poll_card(
    course_id: str,
    question: str,
    options: List[str],
    sort_order: Optional[int] = None,
    is_mandatory: bool = False
) -> str:
    """Create a poll card for collecting learner opinions.

    Args:
        course_id: The course to add this card to
        question: The poll question
        options: List of 2-4 poll options
        sort_order: Position in course (auto-incremented if not provided)
        is_mandatory: Whether learner must respond to proceed
    """
    if len(options) < 2 or len(options) > 4:
        return json.dumps({"error": "Poll must have 2-4 options"}, indent=2)

    contents = {
        "_header1": {
            "text": question,
            "visibility": True,
            "size": "medium"
        },
        "options": options
    }

    card_data = {
        "courseId": course_id,
        "cardType": "poll",
        "contents": contents,
        "isMandatory": is_mandatory
    }

    if sort_order:
        card_data["sortOrder"] = sort_order

    result = await make_api_request("POST", "/api/createCard", card_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_form_card(
    course_id: str,
    question: str,
    sort_order: Optional[int] = None,
    is_mandatory: bool = False
) -> str:
    """Create a form card for collecting learner input.

    Args:
        course_id: The course to add this card to
        question: The form question/prompt
        sort_order: Position in course (auto-incremented if not provided)
        is_mandatory: Whether learner must respond to proceed
    """
    contents = {
        "_header1": {
            "text": question,
            "visibility": True,
            "size": "medium"
        }
    }

    card_data = {
        "courseId": course_id,
        "cardType": "form",
        "contents": contents,
        "isMandatory": is_mandatory
    }

    if sort_order:
        card_data["sortOrder"] = sort_order

    result = await make_api_request("POST", "/api/createCard", card_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_video_card(
    course_id: str,
    video_url: str,
    sort_order: Optional[int] = None,
    is_mandatory: bool = False
) -> str:
    """Create a video card for video content.

    Args:
        course_id: The course to add this card to
        video_url: URL of the video file (MP4, WebM)
        sort_order: Position in course (auto-incremented if not provided)
        is_mandatory: Whether learner must watch to proceed
    """
    contents = {
        "video": video_url
    }

    card_data = {
        "courseId": course_id,
        "cardType": "video",
        "contents": contents,
        "isMandatory": is_mandatory
    }

    if sort_order:
        card_data["sortOrder"] = sort_order

    result = await make_api_request("POST", "/api/createCard", card_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_link_card(
    course_id: str,
    title: str,
    link_url: str,
    link_caption: str = "Visit Link",
    sort_order: Optional[int] = None
) -> str:
    """Create a link card for external resources.

    Args:
        course_id: The course to add this card to
        title: Title text for the link card
        link_url: URL of the external resource
        link_caption: Text for the link button (default: "Visit Link")
        sort_order: Position in course (auto-incremented if not provided)
    """
    contents = {
        "_header1": {
            "text": title,
            "visibility": True,
            "size": "medium"
        },
        "header1": title,
        "link": link_url,
        "linkcaption": link_caption
    }

    card_data = {
        "courseId": course_id,
        "cardType": "link",
        "contents": contents
    }

    if sort_order:
        card_data["sortOrder"] = sort_order

    result = await make_api_request("POST", "/api/createCard", card_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def update_card(
    card_id: str,
    contents: Optional[Dict] = None,
    is_mandatory: Optional[bool] = None,
    sort_order: Optional[int] = None,
    is_active: Optional[bool] = None,
    card_type: Optional[str] = None
) -> str:
    """Update an existing card with automatic preservation of AI-generated metadata.
    
    IMPORTANT: When updating contents, this tool automatically fetches the current card
    and merges your updates to preserve existing AI metadata (imagePrompt, audioScript, etc.).

    Args:
        card_id: The ID of the card to update
        contents: Partial contents updates to merge with existing (preserves AI metadata)
        is_mandatory: Whether the card is mandatory
        sort_order: Position in course
        is_active: Whether the card is active
        card_type: Change card type (WARNING: triggers validation, may remove fields)
    """
    update_data = {}

    # Handle contents update with GET-merge-PUT to preserve AI metadata
    if contents is not None:
        # Fetch current card to preserve existing fields
        current_result = await make_api_request("GET", f"/api/card/{card_id}")
        
        if "error" in current_result:
            return json.dumps({"error": f"Failed to fetch card for update: {current_result['error']}"}, indent=2)
        
        # Merge contents (shallow merge - preserves all top-level keys)
        current_contents = current_result.get("contents", {})
        merged_contents = {
            **current_contents,  # Preserve all existing fields
            **contents           # Apply updates
        }
        update_data["contents"] = merged_contents

    # Add other fields if provided
    if is_mandatory is not None:
        update_data["isMandatory"] = is_mandatory
    if sort_order is not None:
        update_data["sortOrder"] = sort_order
    if is_active is not None:
        update_data["isActive"] = is_active
    
    # Only include cardType if explicitly changing it
    # WARNING: This triggers validation which may clean/remove AI metadata fields
    if card_type is not None:
        update_data["cardType"] = card_type
        # Note: Changing card type may cause validation to remove some fields

    if not update_data:
        return json.dumps({"error": "No update data provided"}, indent=2)

    result = await make_api_request("PUT", f"/api/card/{card_id}", update_data)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_server_info() -> str:
    """Get basic information about this MCP server."""
    return "Super Singularity MCP Server v1.0 - Complete course and card creation with ElevenLabs TTS + Azure Storage"

if __name__ == "__main__":
    # Only launch the server when running locally or directly.
    mcp.run(transport="http", host="0.0.0.0", port=8080, streamable=True)

# Export the ASGI app, so async environments can import it and manage the event loop.
app = mcp.app
