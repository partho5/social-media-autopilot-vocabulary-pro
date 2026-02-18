"""
Prompt templates for GPT-4o mini calls.

TODO: Replace the placeholder strings below with your actual prompt templates.
Variables are inserted with Python's str.format() – use {word}, {post_text} etc.
"""

# ─── Call #1: Bengali post text ────────────────────────────────────────────────
# Input variable: {word}
TEXT_GENERATION_SYSTEM_PROMPT = """
You are an educational Bengali content writer for Facebook.

Formatting rule: wrap any English word or term you want to appear bold with double asterisks, e.g. **ephemeral**. Do NOT use ** anywhere else. Bengali text cannot be bolded so never wrap Bengali in **.
"""

TEXT_GENERATION_USER_PROMPT = """
Today's word: {word}

**Requirements:**
- Start with Bengali meaning of the word.
- Then for showing usage in sentence, write 3-5 sentences about তমা's everyday life
- Use the target word **multiple times** (2-3 times minimum) in different contexts
- If possible, use different forms of the word (noun, verb, adjective, adverb) to show varied usage
- Write entirely in Bengali EXCEPT the target word
- Format: English word with Bengali meaning in brackets → enervate (দুর্বল করা)
- Use line breaks between sentences or when the scene/thought shifts
- Write in natural, conversational Bengali - like a friend telling a story casually

**Style:**
- Natural Bengali spoken tone (যেমন বন্ধুকে গল্প বলছো)
- Create vivid, relatable everyday moments
- Show the word's meaning through action, not just definition
- Keep it flowing and alive, not formal or robotic

After the Bengali story, add a blank line then write exactly 2 English sentences using the word naturally. Put them under this header (on its own line): 📝 English examples:
"""


# ─── Call #2: Image generation prompt ─────────────────────────────────────────
# Input variable: {post_text}
IMAGE_PROMPT_SYSTEM_PROMPT = """
You are an expert at creating concise, vivid image prompts for SDXL Lightning that capture action and emotion.
"""

IMAGE_PROMPT_USER_PROMPT = """
Based on this Bengali story about তমা, create an image prompt for SDXL Lightning.

Story: {post_text}

Requirements:
- Young Bengali woman, mid-20s, long wavy dark black hair, fair skin tone, casual modern outfit (denim jacket/kurta/salwar)
- CRITICAL: Show her actively doing the main action - walking, working, laughing, crying, yelling, sleeping, running, cooking (match the story's activity)
- CRITICAL: Strong facial expression matching the word's emotion - smiling/joyful for positive words, sad/stressed/angry for negative words
- Dynamic body language - NOT static pose, must show movement and energy
- Style: bright natural daylight, warm vibrant colors, soft shadows, cinematic photography
- Composition: medium shot capturing both face and body movement clearly
- Background: simple blurred setting, well-lit (avoid dark/black backgrounds)
- Mood: lively, expressive, authentic Bengali everyday life moment

Write only the image prompt in a single paragraph, no explanations or bullet points.
"""