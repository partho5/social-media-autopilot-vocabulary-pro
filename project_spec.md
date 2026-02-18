This is just one module of the software system. Later more modules will be added. Structure must be modular and scalable. Each module can be run standalone.

# Workflow Description: Automated Facebook Word-of-the-Day Posting System

## Overview
Create a webhook-based system that automatically posts educational English vocabulary content to Facebook when triggered by a cron job. The system processes words sequentially from a predefined list, generates Bengali content and images, and publishes to Facebook.

## Core Requirements

### 1. Word Management System
- Maintain an array of English words (e.g. thousands IELTS/GRE vocabulary). I will provide the array.
- Track last processed word using persistent storage (text file or JSON)
- Each execution picks the next word sequentially. When all words are processed start processing with the first word. make a function like selectNextWord(){//now simply next, but later i can set complex logic. return a word string regardless of implementation}
- System maintains state between executions.

### 2. Content Generation Pipeline

**Step 1: Text Content Generation**
- API call to OpenAI GPT-4o mini with `strict: true`
- Input: Current English word
- Output: Educational Bengali text explaining the word, I will provide the prompt template with variable inside it.

**Step 2: Image Prompt Generation**
- Second API call to GPT-4o mini
- Input: Generated post text, along with a prompt
- Output: Image generation prompt for Google AI Studio

**Step 3: Image Generation**
- Use Google AI Studio (Gemini) API
- Input: Prompt + reference image for character consistency
- Output: Generated image with consistent character design

### 3. Image Processing
- Create vertical rectangular canvas (taller than square)
- Place generated square image at bottom
- Add text overlay at top: "আজকের ওয়ার্ড: [English word]"
- Use Python PIL/Pillow for image manipulation

### 4. Facebook Publishing
- Combine generated Bengali text, processed image, and hashtags
- Post to Facebook Page via Graph API
- Post includes: text content + image + hashtag list

### 5. Facebook Token Management
**CRITICAL: Automatic Token Refresh**
- Facebook Page Access Tokens expire after 60 days
- Implement automatic token refresh mechanism to prevent manual intervention
- System should detect token expiration and refresh automatically
- Store refresh token securely
- Use Facebook's long-lived token exchange API endpoint
- Log token refresh events
- Implement token validation checks before posting
- Fallback notification mechanism if auto-refresh fails (email/log alert)
- Developer should not need to manually update tokens after initial setup. 
- but initially developer will provide whatever long or short lived token or API key i secret that is needed. Ask me what needed.

## Technical Specifications

### Language & Architecture
- **Python** for easier image manipulation
- **Modular design** with separate modules for:
  - Word tracking/state management
  - OpenAI API client
  - Google AI Studio API client
  - Image processing
  - Facebook API client with token refresh
  - Configuration management
- **Error handling** for API failures and network issues
- **Logging** for execution tracking

### API Integration Points
- **OpenAI GPT-4o mini**: Two calls per execution (text generation, image prompt generation)
- **Google AI Studio**: Image generation with reference image
- **Facebook Graph API**: Page posting with automatic token refresh

### State Management
- Store last processed word index
- Atomic operations to prevent race conditions
- Persist between application restarts

### Configuration Required
- OpenAI API credentials and prompt templates
- Google AI Studio credentials and reference image
- Facebook Page credentials with auto-refresh configuration
- English word array (IELTS/GRE top 3000 words)
- Hashtag list
- Image styling parameters

## Execution Flow
1. Webhook triggered by cron job
2. Retrieve next English word from list
3. Generate Bengali text content (GPT-4o mini call #1)
4. Generate image prompt (GPT-4o mini call #2)
5. Generate image with reference (Google AI Studio)
6. Process image: add "আজকের ওয়ার্ড: [word]" label
7. Validate/refresh Facebook token if needed
8. Post to Facebook (text + image + hashtags)
9. Update state with processed word
10. Return success/failure response
11. Before every work flow check validity of previous step, is data empty , valid etc.


##Deployment 
This will run in vPS server as background process. For deployment or restart single comment should work. The application must be restart safe.

---

**Ask me questions before starting.**