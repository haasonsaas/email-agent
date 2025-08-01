#!/usr/bin/env python3
"""Test script to verify AI categorization functionality."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
from email_agent.agents.categorizer import CategorizerAgent


def create_diverse_test_emails():
    """Create diverse test emails for categorization."""
    now = datetime.now()
    return [
        # Work/Business emails
        Email(
            id="work-1",
            message_id="<work-1@company.com>",
            subject="Quarterly budget review meeting - Action required",
            sender=EmailAddress(email="finance@company.com", name="Finance Team"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="We need to review the Q4 budget allocations. Please prepare your department's spending report and join the meeting on Friday at 2 PM.",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Social media notification
        Email(
            id="social-1",
            message_id="<social-1@facebook.com>",
            subject="John Doe liked your post",
            sender=EmailAddress(email="notification@facebook.com", name="Facebook"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="John Doe and 3 others liked your recent post about weekend hiking. View more reactions on Facebook.",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Promotional email
        Email(
            id="promo-1",
            message_id="<promo-1@store.com>",
            subject="🎉 Flash Sale: 70% OFF Everything - Limited Time!",
            sender=EmailAddress(email="deals@megastore.com", name="MegaStore"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Don't miss out! Our biggest sale of the year is happening now. Use code FLASH70 to get 70% off all items. Sale ends at midnight!",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Newsletter/Updates
        Email(
            id="update-1",
            message_id="<update-1@techcrunch.com>",
            subject="TechCrunch Daily: AI startup raises $100M, Apple's new features",
            sender=EmailAddress(email="newsletter@techcrunch.com", name="TechCrunch"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Today's top tech stories: Revolutionary AI startup secures massive funding, Apple announces groundbreaking features, and market analysis from our experts.",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Forum/Community
        Email(
            id="forum-1",
            message_id="<forum-1@stackoverflow.com>",
            subject="[Python] New answer to your question about async/await",
            sender=EmailAddress(email="noreply@stackoverflow.com", name="Stack Overflow"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Someone has posted a new answer to your question 'How to properly handle exceptions in async/await Python code'. Check it out and see if it helps solve your problem.",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Personal email
        Email(
            id="personal-1",
            message_id="<personal-1@gmail.com>",
            subject="Mom's birthday party this Saturday",
            sender=EmailAddress(email="sister@gmail.com", name="Sarah"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Hey! Don't forget about Mom's surprise birthday party this Saturday at 3 PM. Can you bring the cake? Let me know if you need the address again.",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Spam-like email
        Email(
            id="spam-1",
            message_id="<spam-1@suspicious.com>",
            subject="URGENT: Claim your $10,000 prize NOW!!!",
            sender=EmailAddress(email="winner@suspicious-lottery.com", name="Prize Committee"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="CONGRATULATIONS! You have won $10,000 in our international lottery! Click here immediately to claim your prize. Send us your bank details for instant transfer.",
            date=now,
            received_date=now,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        )
    ]


async def test_ai_categorization():
    """Test AI-powered email categorization."""
    print("🤖 Testing AI Email Categorization")
    print("=" * 50)
    
    # Initialize categorizer agent
    categorizer = CategorizerAgent()
    
    # Check if AI is available
    status = await categorizer.get_status()
    print(f"🔧 AI Enabled: {status['ai_enabled']}")
    print(f"🔧 AI Model: {status.get('ai_model', 'N/A')}")
    print(f"🔧 Rules Loaded: {status['rules_loaded']}")
    print()
    
    if not status['ai_enabled']:
        print("❌ AI categorization is not available. Please check OpenAI configuration.")
        return
    
    # Create test emails
    test_emails = create_diverse_test_emails()
    
    print(f"📧 Testing categorization of {len(test_emails)} emails...")
    print()
    
    # Expected categories for validation
    expected_categories = {
        "work-1": EmailCategory.PRIMARY,  # Business email
        "social-1": EmailCategory.SOCIAL,  # Facebook notification
        "promo-1": EmailCategory.PROMOTIONS,  # Sale email
        "update-1": EmailCategory.UPDATES,  # Newsletter
        "forum-1": EmailCategory.FORUMS,  # Stack Overflow
        "personal-1": EmailCategory.PRIMARY,  # Personal email
        "spam-1": EmailCategory.SPAM,  # Suspicious email
    }
    
    # Test individual email categorization
    results = []
    for email in test_emails:
        print(f"📨 Categorizing: {email.subject}")
        print(f"   From: {email.sender.email}")
        
        # Apply AI categorization
        original_category = email.category
        categorized_email = await categorizer._apply_ml_categorization(email)
        
        print(f"   Original: {original_category.value}")
        print(f"   AI Result: {categorized_email.category.value}")
        
        # Check if it matches expected
        expected = expected_categories.get(email.id)
        if expected:
            is_correct = categorized_email.category == expected
            print(f"   Expected: {expected.value}")
            print(f"   Accuracy: {'✅ Correct' if is_correct else '❌ Incorrect'}")
            results.append(is_correct)
        else:
            results.append(True)  # No expectation, count as correct
        
        print()
    
    # Calculate accuracy
    accuracy = (sum(results) / len(results)) * 100 if results else 0
    print(f"📊 Overall Accuracy: {accuracy:.1f}% ({sum(results)}/{len(results)})")
    
    # Test batch categorization
    print("\n🔄 Testing batch categorization...")
    
    # Reset categories to PRIMARY for batch test
    for email in test_emails:
        email.category = EmailCategory.PRIMARY
    
    categorized_emails = await categorizer.categorize_emails(test_emails)
    
    print(f"✅ Batch categorization completed for {len(categorized_emails)} emails")
    
    # Show category distribution
    category_counts = {}
    for email in categorized_emails:
        category = email.category.value
        category_counts[category] = category_counts.get(category, 0) + 1
    
    print("\n📊 Category Distribution:")
    for category, count in category_counts.items():
        print(f"   {category}: {count} emails")
    
    # Show agent stats
    print(f"\n📈 Agent Statistics:")
    stats = categorizer.stats
    print(f"   Emails Processed: {stats['emails_processed']}")
    print(f"   AI Categorizations: {stats['ai_categorizations']}")
    print(f"   Rules Applied: {stats['rules_applied']}")


async def test_categorization_confidence():
    """Test categorization confidence and edge cases."""
    print("\n🎯 Testing Categorization Edge Cases")
    print("=" * 50)
    
    categorizer = CategorizerAgent()
    
    # Test ambiguous email
    now = datetime.now()
    ambiguous_email = Email(
        id="ambiguous-1",
        message_id="<ambiguous-1@test.com>",
        subject="Update",
        sender=EmailAddress(email="info@company.com"),
        recipients=[EmailAddress(email="me@company.com")],
        body_text="Hello",
        date=now,
        received_date=now,
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.NORMAL,
        is_read=False
    )
    
    print("📧 Testing ambiguous email:")
    print(f"   Subject: {ambiguous_email.subject}")
    print(f"   Body: {ambiguous_email.body_text}")
    
    categorized = await categorizer._apply_ml_categorization(ambiguous_email)
    print(f"   AI Category: {categorized.category.value}")
    
    # Test empty email
    empty_email = Email(
        id="empty-1",
        message_id="<empty-1@test.com>",
        subject="",
        sender=EmailAddress(email="test@test.com"),
        recipients=[EmailAddress(email="me@company.com")],
        body_text="",
        date=now,
        received_date=now,
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.NORMAL,
        is_read=False
    )
    
    print("\n📧 Testing empty email:")
    print(f"   Subject: '{empty_email.subject}'")
    print(f"   Body: '{empty_email.body_text}'")
    
    categorized_empty = await categorizer._apply_ml_categorization(empty_email)
    print(f"   AI Category: {categorized_empty.category.value}")


async def main():
    """Run AI categorization tests."""
    try:
        await test_ai_categorization()
        await test_categorization_confidence()
        print("\n🎉 AI Categorization tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
