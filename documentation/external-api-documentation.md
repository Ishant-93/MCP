# External API Guide for Creating Courses & Cards

This guide provides comprehensive instructions for external platforms and tools to create courses and cards directly in the Super Singularity database.

## Table of Contents
1. [Authentication](#authentication)
2. [Company Requirements](#company-requirements)
3. [Course Creation](#course-creation)
4. [Card Types & Requirements](#card-types--requirements)
5. [API Endpoints](#api-endpoints)
6. [Best Practices](#best-practices)

## Authentication

All API requests require authentication via one of these methods:
- **JWT Token**: For browser-based sessions (cookie-based)
- **Bearer Token**: For external API access (Authorization header)

```
Authorization: Bearer YOUR_API_TOKEN
```

## Company Requirements

All courses must belong to a company. Before creating courses:
1. Ensure the company exists in the database
2. Use the company's `id` (not slug) for course creation
3. Respect multi-tenant isolation - users can only create courses in their company

## Course Creation

### Required Fields
- `id`: Unique identifier (**MUST** use UUID)
- `title`: Course title (max 255 characters)
- `companyId`: The company ID this course belongs to

### Optional Fields
- `duration`: Course duration in minutes (default: 0)
- `folderId`: ID of the folder to organize the course (default: empty / NULL)
- `description`: Course description (max 1000 characters)
- `isPublished`: Whether the course is visible to learners (default: false)
- `isAutoplay`: Auto-advance cards (default: false)
- `isScorable`: Track quiz scores (default: false)
- `gradientFromColor`: Hex color for gradient start (e.g., "#FF0000")
- `gradientToColor`: Hex color for gradient end
- `themeId`: Custom theme ID (default: NULL)

### Automatic Fields
- `courseMagicLink`: Auto-generated unique link for sharing
- `createdAt`, `updatedAt`: Auto-managed timestamps
- First card is automatically created with course title

## Card Types & Requirements

### Common Fields for All Cards
- `id`: Unique identifier (**MUST** use UUID)
- `courseId`: The course this card belongs to
- `cardType`: Type of card (see below for valid types)
- `sortOrder`: Position in the course (1-based, auto-incremented if not provided)
- `align`: Text/content alignment (default: "center center")
- `isActive`: Whether card is active (default: true)

### 1. First Card (`cardType: "first card"`)
**Purpose**: Course introduction/title card (auto-created with course)

**Contents Structure**:
```json
{
  "_header1": {
    "text": "Course Title",
    "visibility": true,
    "size": "large"  // "small", "medium", or "large"
  },
  "_header2": {
    "text": "Course Subtitle",
    "visibility": true,
    "size": "medium"
  },
  "header1": "Course Title",  // Plain text copy
  "header2": "Course Subtitle",  // Plain text copy
  "image": "https://example.com/logo.png",  // Optional logo
}
```

### 2. Content Card (`cardType: "content"`)
**Purpose**: Static content with optional image

**Contents Structure**:
```json
{
  "_header1": {
    "text": "Main heading with <b>HTML formatting</b>",
    "visibility": true,
    "size": "large"
  },
  "_header2": {
    "text": "Supporting text or description",
    "visibility": true,
    "size": "medium"
  },
  "header1": "Main heading with HTML formatting",  // Plain text copy
  "header2": "Supporting text or description",  // Plain text copy
  "image": "https://example.com/image.png",  // Optional
  "align": "top"  // "top", "bottom", or "bg" (background)
}
```

### 3. Quiz Card (`cardType: "quiz"`)
**Purpose**: Multiple choice questions with scoring

**Contents Structure**:
```json
{
  "_header1": {
    "text": "What is 2 + 2?",
    "visibility": true,
    "size": "large"
  },
  "header1": "What is 2 + 2?",  // Plain text copy
  "options": ["3", "4", "5", "6"],  // 2-4 options required
  "correct": ["4"],  // Single correct answer (must match an option exactly)
  "comment": "Great job! 2 + 2 equals 4."  // Optional explanation
}
```

**Additional Fields**:
- `isMandatory`: Boolean - learner must answer to proceed (true by default)

### 4. Poll Card (`cardType: "poll"`)
**Purpose**: Opinion gathering without right/wrong answers

**Contents Structure**:
```json
{
  "_header1": {
    "text": "What's your favorite color?",
    "visibility": true,
    "size": "large"
  },
  "header1": "What's your favorite color?",  // Plain text copy
  "options": ["Red", "Blue", "Green", "Yellow"],  // 2-4 options required
  "hideResults": false  // Whether to hide results from learners
}
```

**Additional Fields**:
- `isMandatory`: Boolean - learner must respond to proceed

### 5. Form Card (`cardType: "form"`)
**Purpose**: Collect subjective answer/feedback/opinion from learners; contains only 1 text field in form.

**Contents Structure**:
```json
{
  "_header1": { // for form question
    "text": "Feedback Form",
    "visibility": true,
    "size": "large"
  },
  "header1": "Feedback Form"  // Plain text copy
}
```

### 6. Video Card (`cardType: "video"`)
**Purpose**: Video content delivery

**Contents Structure**:
```json
{
  "video": "https://example.com/video.mp4"  // Required video URL
}
```

**Additional Fields**:
- `isMandatory`: Boolean - learner must watch to proceed (default false)

### 7. Audio Card (`cardType: "audio"`)
**Purpose**: Audio content with optional background

**Contents Structure**:
```json
{
  "_header1": {
    "text": "Listen to this podcast",
    "visibility": true,
    "size": "large"
  },
  "header1": "Listen to this podcast",  // Plain text copy
  "audio": "https://example.com/audio.mp3",  // Required audio URL
  "image": "https://example.com/background.jpg",  // Optional background
}
```

**Additional Fields**:
- `isMandatory`: Boolean - learner must listen to proceed (default false)

### 8. Link Card (`cardType: "link"`)
**Purpose**: External resource links

**Contents Structure**:
```json
{
  "_header1": {
    "text": "Additional Resources",
    "visibility": true,
    "size": "large"
  },
  "header1": "Additional Resources",  // Plain text copy
  "link": "https://example.com/resource",  // Required URL
  "linkcaption": "Visit Resource",  // Button text (default: "Visit Link")
}
```

## API Endpoints

### Get Course Data
```
GET /api/course?id={courseId}
Authorization: Bearer YOUR_TOKEN

Response:
{
  "id": "course-id",
  "title": "Course Title",
  "description": "Course description",
  "companyId": "company-id",
  "duration": 30,
  "folderId": "folder-id",
  "isPublished": true,
  "isAutoplay": false,
  "isScorable": true,
  "gradientFromColor": "#FF0000",
  "gradientToColor": "#0000FF",
  "themeId": "theme-id",
  "courseMagicLink": "unique-magic-link",
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z",
  "courseMagicLink": "coffee",
  "cardsBackgroundImage": null,
  "cardsTransitionEffect": null,
  "isEditable": true,
  "background": null,
  "finalizedCoursePlan": null,
  "createdByAgent": false,
  "isActive": true,
  "qrCodeLink": null,
  "lastSharedAt": "2025-05-23T06:52:53.000Z",
  "folderId": null
}
```

### Create Course
```
POST /api/createCourse
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "id": "unique-course-id",
  "title": "My Course Title",
  "companyId": "company-id",
  "duration": 30,
  "folderId": "optional-folder-id"
}
```

### Update Course
```
POST /api/courses/{courseId}/edit
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "title": "Updated Course Title",
  "duration": 45,
  "folderId": "folder-id"
}
```

### Get Cards for Course
```
GET /api/courses/{courseId}/cards
Authorization: Bearer YOUR_TOKEN

Response:
[
  {
    "id": "card-id",
    "courseId": "course-id",
    "cardType": "first card",
    "sortOrder": 1,
    "align": "center center",
    "isActive": true,
    "isMandatory": false,
    "contents": {
      "_header1": {
        "text": "Course Title",
        "visibility": true,
        "size": "large"
      },
      "header1": "Course Title",
      "image": "https://example.com/image.jpg"
    },
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
]
```

### Create Card
```
POST /api/createCard
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "courseId": "course-id",
  "cardType": "quiz",
  "contents": { /* See card type structures above */ },
  "sortOrder": 2,
  "isMandatory": true
}
```

### Update Card
```
PUT /api/card/{cardId}
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "contents": { /* Updated contents */ },
  "isMandatory": false
}
```

## Best Practices

### 1. ID Generation
- Use UUIDs for all IDs to avoid conflicts
- Never reuse IDs across different entities
- Use a hardcoded companyid from env file to create courses & cards with that companyid

### 2. Content Formatting
- Support HTML in header texts for rich formatting (inside _header1.text & _header2.text too)
- Always provide both `_header` (with formatting) and plain text versions
- Escape special characters properly

### 3. Media Files
- Upload media files to cloud storage first
- Use HTTPS URLs for all media
- Supported formats:
  - Images: JPG, PNG, GIF, WebP
  - Videos: MP4, WebM
  - Audio: MP3, WAV, OGG

### 4. Validation Rules
- Quiz/Poll: 2-4 options required
- Quiz: Exactly one correct answer
- Form: At least one field required
- All URLs must be valid and accessible

### 5. Course Structure
- First card is auto-created - don't create another
- Maintain sequential sortOrder without gaps
- Set isPublished=true only when course is complete

### 6. Error Handling
- Check for 400/404/500 status codes
- Validate company and course existence before creating cards
- Handle network timeouts for media uploads

### 7. Batch Operations
- Create course first, then cards in sortOrder
- Use transactions when possible for consistency
- Limit batch sizes to avoid timeouts

## Example: Complete Course Creation

```javascript
// 1. Create course
const course = await fetch('/api/createCourse', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    id: generateUUID(),
    title: 'Introduction to Safety',
    companyId: 'company-123',
    duration: 15
  })
});

const { courseId } = await course.json();

// 2. Add content card
await fetch('/api/createCard', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    courseId,
    cardType: 'content',
    sortOrder: 2,
    contents: {
      _header1: {
        text: 'Welcome to <b>Safety Training</b>',
        visibility: true,
        size: 'large'
      },
      _header2: {
        text: 'This course covers essential safety procedures',
        visibility: true,
        size: 'medium'
      },
      header1: 'Welcome to Safety Training',
      header2: 'This course covers essential safety procedures',
      image: 'https://example.com/safety-image.jpg',
      align: 'top'
    }
  })
});

// 3. Add quiz card
await fetch('/api/createCard', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    courseId,
    cardType: 'quiz',
    sortOrder: 3,
    isMandatory: true,
    contents: {
      _header1: {
        text: 'What should you do in case of fire?',
        visibility: true,
        size: 'large'
      },
      header1: 'What should you do in case of fire?',
      options: [
        'Run to the nearest exit',
        'Use the elevator',
        'Hide under desk',
        'Call manager first'
      ],
      correct: ['Run to the nearest exit'],
      comment: 'Always evacuate immediately using stairs, not elevators.'
    }
  })
});
```

## Support

For additional support or to report issues:
- Check API response messages for specific errors
- Ensure all required fields are provided
- Validate JSON structure matches specifications
- Contact support with request/response logs for debugging