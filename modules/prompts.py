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

TEXT_GENERATION_USER_PROMPT_v1 = """
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

After the Bengali story, add a blank line then write exactly 2 English sentences with line gap, using the word naturally. Put them under this header (on its own line): 📝 English examples:
"""


TEXT_GENERATION_USER_PROMPT = """
Today's word: {word}

**Requirements:**
- Start with Bengali meaning of the word.
- Then write 3-5 sentences showing the word's usage through a vivid, relatable Bengali scenario
- The scenario should be the MOST NATURAL fit for the word's meaning:
  • For personal habits/feelings → a person's daily life moment
  • For social/political concepts → a community, institution, or system in action
  • For abstract ideas → a metaphor made concrete (a scene in nature, a workplace, a classroom)
  • For legal/formal words → a courtroom, office, or ceremony scene
  • Always pick whichever lens (person, group, place, event) makes the word come ALIVE most vividly
- Use the target word **multiple times** (2-3 times minimum) in different contexts
- If possible, use different forms of the word (noun, verb, adjective, adverb) to show varied usage
- Write entirely in Bengali EXCEPT the target word
- Format: English word with Bengali meaning in brackets → enervate (দুর্বল করা)
- Use line breaks between sentences or when the scene/thought shifts
- Write in natural, conversational Bengali - like a friend telling a story casually

**Style:**
- Natural Bengali spoken tone (যেমন বন্ধুকে গল্প বলছো)
- Create vivid, relatable everyday moments — person, crowd, institution, or object, whatever fits
- Show the word's meaning through action and scene, not just definition
- Keep it flowing and alive, not formal or robotic

After the Bengali story, add a blank line then write exactly 2 English sentences with line gap, using the word naturally. Put them under this header (on its own line): 📝 English examples:
"""



# ─── Call #2: Image generation prompt ─────────────────────────────────────────
# Input variable: {post_text}
IMAGE_PROMPT_SYSTEM_PROMPT = """
You are an expert at creating concise, vivid image prompts for SDXL Lightning that capture action and emotion.
"""

IMAGE_PROMPT_USER_PROMPT_v1 = """
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



IMAGE_PROMPT_USER_PROMPT = """
The English word is: {word}
The Bengali story about it: {post_text}

Your job: Design the SINGLE most powerful visual scene that makes the word's meaning instantly understood.

**Step 1 — Decide the best visual concept for this specific word:**
- A lone person acting it out? (e.g. abjure → man dramatically pushing away a cigarette pack)
- A group or crowd? (e.g. revolt → protesters flooding a street)
- An institution or system? (e.g. abolish → workers dismantling a law board or tearing down a sign)
- A symbolic/abstract scene? (e.g. ephemeral → soap bubbles floating over a city, one popping mid-air)
- A workplace, courtroom, classroom, nature scene? Pick whatever makes the word viscerally clear.

**Step 2 — Build the prompt with these rules:**
- The scene must SHOW the meaning visually — a viewer who doesn't know the word should sense it
- If a person is the focus: young South Asian appearance, expressive face, dynamic pose — NOT static
- If the focus is a system/place/event: make it detailed, cinematic, and emotionally charged
- Strong lighting: bright natural daylight or dramatic cinematic light — NO dark/black backgrounds
- Style: warm vibrant colors, soft shadows, photorealistic cinematic photography
- Composition: medium or wide shot depending on scene scale
- Background: contextually meaningful, slightly blurred to keep focus on the subject

**Step 3 — Output:**
Write only the final image prompt in a single paragraph. No explanations, no bullet points, no word labels.
"""