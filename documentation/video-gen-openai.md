# Image generation tool
- Now lets create a new tool for image generation using Azure OpenAI service.
- Take inspitration from how the audio generation flow is structured.
- After OpenAI generates and sends back a response, we have to convert it to webp with proper compression optimized for low latency devices in bad network areas but not compromising much on quality.
- Then upload it to azure just like audio file is done and return the client the image url, script and important note saying preserve the script text while creating content or audio card in contents
- The client will then use this URL to create content/audio card with correct parameters there so no need to worry for that part
- Explanations of API call parameters & responses are described in further sections

## OpenAI image generation cURL
```
curl --location 'https://ankur-mc1yo3gw-westus3.cognitiveservices.azure.com/openai/deployments/gpt-image-1/images/generations?api-version=2025-04-01-preview' \
--header 'Content-Type: application/json' \
--header 'api-key: 4bu3hXPE4TI2XtVAB5pzlGBBRD6eCpx60N77xDIyqsZCLwNONK6NJQQJ99BFACMsfrFXJ3w3AAAAACOGobHn' \
--data '{
    "prompt": "Create an illustrative image showwing the showdown of the GOATS messi vs ronaldo",
    "size": "1024x1024",
    "quality": "medium",
    "output_compression": 100,
    "output_format": "png",
    "n": 1
}'
```

**Parameters for API call**
1. prompt - a detailed prompt for the model to generate the image. The better the prompt, more detailed the image
2. size - for normal content cards with top/bottom alignment, use 1:1 aspect ratio and keep size 1024x1024. if the image is being generated to be used as background, then maintain 9:16 ratio (360x640)
3. quality - keep this to medium
4. output_compression - keep this to 100
5. output_format - can be png or jpg
6. n - keep this 1. this is no of image variations requested

**Parameters for toll call exposed to client**
In the tool call, the client can provide
1. prompt (mandatory)
2. override size (optional) but check if its in the format {int}x{int},
3. output format (optional but restricted to png or jpg)

## OpenAI image generation sample response
```
{
    "created": 1750255695,
    "background": "opaque",
    "data": [
        {
            "b64_json": "<<png/jpg base64 string>>"
        }
    ],
    "output_format": "png",
    "quality": "medium",
    "size": "1024x1024",
    "usage": {
        "input_tokens": 24,
        "input_tokens_details": {
            "image_tokens": 0,
            "text_tokens": 24
        },
        "output_tokens": 1056,
        "total_tokens": 1080
    }
}
```
