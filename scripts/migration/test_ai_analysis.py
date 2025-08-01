#!/usr/bin/env python3
"""Test script to verify AI analysis functionality."""

import asyncio
import sys
import os
from datetime import datetime, date
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_agent.config import settings
from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
from email_agent.agents.summarizer import SummarizerAgent
from email_agent.agents.crew import EmailAgentCrew


def create_test_emails():
    """Create sample test emails for analysis."""
    now = datetime.now()
    return [
        Email(
            id="test-1",
            message_id="<test-1@company.com>",
            subject="Urgent: Project deadline moved to Friday",
            sender=EmailAddress(email="boss@company.com", name="Manager"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Hi team, Due to client requirements, we need to move the project deadline to this Friday. Please prioritize this and let me know if you need any resources.",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.URGENT,
            is_read=False
        ),
        Email(
            id="test-2",
            message_id="<test-2@techblog.com>",
            subject="Weekly Newsletter - Tech Updates",
            sender=EmailAddress(email="newsletter@techblog.com", name="Tech Blog"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Here are this week's top tech stories: AI advances, cloud computing trends, and developer tools updates.",
            date=now,
            received_date=now,
            category=EmailCategory.UPDATES,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        Email(
            id="test-3",
            message_id="<test-3@company.com>",
            subject="Meeting reminder: Team standup at 10 AM",
            sender=EmailAddress(email="calendar@company.com", name="Calendar"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Don't forget about the team standup meeting at 10 AM today. We'll discuss project progress and any blockers.",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        Email(
            id="test-4",
            message_id="<test-4@saasapp.com>",
            subject="Special offer: 50% off premium features",
            sender=EmailAddress(email="sales@saasapp.com", name="SaaS App"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Limited time offer! Get 50% off our premium features for new subscribers. Use code SAVE50 at checkout.",
            date=now,
            received_date=now,
            category=EmailCategory.PROMOTIONS,
            priority=EmailPriority.LOW,
            is_read=True
        )
    ]


async def test_openai_connection():
    """Test OpenAI API connection."""
    print("🔍 Testing OpenAI API connection...")
    
    if not settings.openai_api_key:
        print("❌ OpenAI API key not found in configuration")
        return False
    
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Simple test call
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, Email Agent!' if you can hear me."}
            ],
            max_tokens=50
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ OpenAI API connected successfully!")
        print(f"   Model: {settings.openai_model}")
        print(f"   Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API connection failed: {str(e)}")
        return False


async def test_email_summarization():
    """Test individual email summarization."""
    print("\n📧 Testing email summarization...")
    
    summarizer = SummarizerAgent()
    test_emails = create_test_emails()
    
    for i, email in enumerate(test_emails[:2], 1):  # Test first 2 emails
        print(f"\n--- Email {i}: {email.subject} ---")
        
        try:
            summary_data = await summarizer.summarize_email(email)
            
            print(f"✅ Summary: {summary_data.get('summary', 'N/A')}")
            print(f"📋 Action Items: {summary_data.get('action_items', [])}")
            print(f"⚡ Priority: {summary_data.get('priority', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Summarization failed: {str(e)}")


async def test_daily_brief_generation():
    """Test daily brief generation."""
    print("\n📰 Testing daily brief generation...")
    
    summarizer = SummarizerAgent()
    test_emails = create_test_emails()
    
    try:
        brief = await summarizer.generate_brief(test_emails, date.today())
        
        print(f"✅ Brief generated successfully!")
        print(f"📊 Total emails: {brief.total_emails}")
        print(f"📬 Unread emails: {brief.unread_emails}")
        print(f"📰 Headline: {brief.headline}")
        print(f"📝 Summary: {brief.summary}")
        print(f"📋 Action items: {len(brief.action_items)}")
        for item in brief.action_items:
            print(f"   - {item}")
        print(f"⏰ Deadlines: {len(brief.deadlines)}")
        for deadline in brief.deadlines:
            print(f"   - {deadline}")
        
    except Exception as e:
        print(f"❌ Brief generation failed: {str(e)}")


async def test_ai_email_filtering():
    """Test AI-powered email filtering."""
    print("\n🔍 Testing AI email filtering...")
    
    summarizer = SummarizerAgent()
    test_emails = create_test_emails()
    
    queries = [
        "urgent emails about projects",
        "newsletters and updates",
        "meeting reminders"
    ]
    
    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        
        try:
            filtered_emails = await summarizer.filter_emails_by_query(test_emails, query)
            
            print(f"✅ Found {len(filtered_emails)} matching emails:")
            for email in filtered_emails:
                print(f"   - {email.subject} (from {email.sender.email})")
                
        except Exception as e:
            print(f"❌ Filtering failed: {str(e)}")


async def test_crew_integration():
    """Test CrewAI integration."""
    print("\n🤖 Testing CrewAI integration...")
    
    try:
        crew = EmailAgentCrew()
        await crew.initialize_crew({"verbose": False})
        
        print("✅ EmailAgentCrew initialized successfully")
        
        # Test email summarization task
        test_email = create_test_emails()[0]
        
        result = await crew.execute_task("summarize_email", email=test_email)
        print(f"✅ Email summarization task completed")
        print(f"   Summary: {result.get('summary', 'N/A')}")
        
        # Test brief generation task
        test_emails = create_test_emails()
        brief = await crew.execute_task("generate_brief", emails=test_emails, date=date.today())
        print(f"✅ Brief generation task completed")
        print(f"   Brief headline: {brief.headline}")
        
        await crew.shutdown()
        print("✅ CrewAI integration test completed")
        
    except Exception as e:
        print(f"❌ CrewAI integration failed: {str(e)}")


async def test_configuration():
    """Test configuration settings."""
    print("⚙️ Testing configuration...")
    
    print(f"✅ OpenAI API Key: {'✓ Set' if settings.openai_api_key else '❌ Missing'}")
    print(f"✅ OpenAI Model: {settings.openai_model}")
    print(f"✅ Database URL: {settings.database_url}")
    print(f"✅ Data Directory: {settings.data_dir}")
    print(f"✅ Briefs Directory: {settings.briefs_dir}")
    
    # Check if Google credentials exist
    gmail_secrets = Path("client_secret_933646724600-ga9867god7driiqpsbkqd84a0v95ae3d.apps.googleusercontent.com.json")
    print(f"✅ Gmail Config: {'✓ Found' if gmail_secrets.exists() else '❌ Missing'}")


async def main():
    """Run all AI analysis tests."""
    print("🧪 Email Agent AI Analysis Test Suite")
    print("=" * 50)
    
    # Test configuration
    await test_configuration()
    
    # Test OpenAI connection
    openai_works = await test_openai_connection()
    
    if openai_works:
        # Test AI features
        await test_email_summarization()
        await test_daily_brief_generation()
        await test_ai_email_filtering()
        await test_crew_integration()
    else:
        print("\n⚠️  Skipping AI tests due to OpenAI connection issues")
        print("   Please check your OpenAI API key configuration")
    
    print("\n🎉 Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())
