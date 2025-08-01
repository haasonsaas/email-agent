# Advanced AI Features

This document describes the advanced AI-powered features implemented in the Email Agent system for intelligent email processing and generation.

## AI Draft Suggestions Agent

The Draft Suggestions Agent analyzes your writing style from sent emails and generates personalized draft responses.

### Features

- **Writing Style Analysis**: Analyzes patterns from your sent emails including:
  - Average email length and formality level
  - Common greetings and closings
  - Sentence complexity and tone keywords
  - Punctuation style and preferred sending times
  
- **Draft Generation**: Creates multiple draft suggestions for responding to emails:
  - Quick, concise responses
  - Detailed, thorough responses
  - Formal, professional responses
  - Casual, friendly responses (when appropriate)
  - Urgent, action-oriented responses

- **Style Matching**: Each draft includes confidence scores for:
  - Overall confidence in the suggestion (0.0-1.0)
  - Style match with your writing patterns (0.0-1.0)
  - Suggested tone and estimated length

### Usage

```bash
# Analyze your writing style from sent emails
email-agent drafts analyze-style

# Generate draft suggestions for responding to an email
email-agent drafts generate --email-id <email-id> --num-suggestions 3

# View current writing style summary
email-agent drafts style-summary

# Use a specific draft suggestion
email-agent drafts use-draft --email-id <email-id> --draft-index 0
```

### API Usage

```python
from email_agent.agents.crew import EmailAgentCrew

crew = EmailAgentCrew()
await crew.initialize_crew({})

# Analyze writing style
results = await crew.execute_task(
    "analyze_writing_style",
    sent_emails=sent_emails,
    force_refresh=False
)

# Generate draft suggestions
results = await crew.execute_task(
    "generate_drafts",
    original_email=email,
    context="reply",
    num_suggestions=3
)
```

## Enhanced Narrative Summarizer

The Enhanced Summarizer creates narrative-style daily briefs that read like engaging stories rather than boring reports.

### Features

- **Narrative Structure**: Transforms email data into compelling stories with:
  - Beginning, middle, and end structure
  - Character development (key people in emails)
  - Plot progression and conflict resolution
  - Engaging language while maintaining accuracy

- **Optimized Reading Time**: Targets sub-60 second reading time:
  - Approximately 150-200 words maximum
  - Estimated reading time calculation
  - Narrative score indicating story-like quality

- **Story Elements**:
  - **Key Characters**: Important people and their roles
  - **Main Themes**: Central topics and patterns
  - **Story Arcs**: Ongoing email conversations and threads
  - **Temporal Flow**: How events unfolded throughout the day
  - **Emotional Tone**: Overall mood and sentiment

### Usage

```bash
# Generate a narrative-style daily brief
email-agent brief narrative --date 2023-10-15

# Generate and save narrative brief
email-agent brief narrative --save --format markdown

# Compare with regular brief
email-agent brief generate --date 2023-10-15
```

### API Usage

```python
from email_agent.agents.crew import EmailAgentCrew

crew = EmailAgentCrew()
await crew.initialize_crew({})

# Generate narrative brief
results = await crew.execute_task(
    "generate_narrative_brief",
    emails=emails,
    target_date=date.today(),
    context={"user_preferences": {"reading_time": 60}}
)

# Access narrative elements
brief_data = results["brief"]
print(f"Reading time: {brief_data['estimated_reading_time']} seconds")
print(f"Narrative score: {brief_data['narrative_score']}")
print(f"Key characters: {brief_data['key_characters']}")
```

## Integration with Existing Features

Both advanced features integrate seamlessly with the existing Email Agent system:

### Triage System Integration
- Draft suggestions are informed by email priority and attention scores
- Narrative briefs incorporate triage results for story structure

### Configuration
```python
# Enhanced configuration for AI features
config = {
    'openai_api_key': 'your-api-key',
    'draft_agent': {
        'min_emails_for_analysis': 10,
        'style_cache_expiry_days': 7
    },
    'enhanced_summarizer': {
        'target_reading_time': 60,  # seconds
        'max_words': 200,
        'narrative_temperature': 0.6
    }
}
```

## Performance and Accuracy

### Draft Suggestions
- Writing style analysis processes 10+ sent emails for accuracy
- Style patterns cached for 7 days to improve performance
- Multiple draft types ensure variety and appropriateness
- Confidence scoring helps users choose the best option

### Narrative Briefs
- Rule-based fallback ensures functionality without AI
- Optimized prompting for consistent narrative structure
- Theme extraction using both AI and keyword analysis
- Reading time estimation based on word count and complexity

## Privacy and Security

- Writing style analysis is performed locally when possible
- AI prompts are designed to minimize sensitive data exposure
- User email content is processed with privacy considerations
- Style patterns are stored locally, not shared externally

## Future Enhancements

- **Communication Habit Learning**: Adapt responses based on user interaction patterns
- **Multi-language Support**: Extend style analysis to different languages
- **Custom Templates**: User-defined draft templates and narrative styles
- **Integration Feedback**: Learn from user corrections and preferences
