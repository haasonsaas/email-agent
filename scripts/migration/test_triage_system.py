#!/usr/bin/env python3
"""Test script for the AI-powered email triage system."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
from email_agent.agents.triage_agent import TriageAgent, TriageDecision
from email_agent.agents.crew import EmailAgentCrew


def create_triage_test_emails():
    """Create diverse test emails for triage testing."""
    now = datetime.now()
    base_date = now - timedelta(hours=2)
    
    return [
        # High priority - work urgent
        Email(
            id="urgent-work-1",
            message_id="<urgent-work-1@company.com>",
            subject="URGENT: Server down - immediate action required",
            sender=EmailAddress(email="ops@company.com", name="Operations Team"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Our main production server is down. We need immediate action to restore service. Please respond ASAP.",
            date=base_date,
            received_date=base_date,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.URGENT,
            is_read=False
        ),
        
        # High priority - boss email
        Email(
            id="boss-meeting-1",
            message_id="<boss-meeting-1@company.com>",
            subject="Can we meet tomorrow about the Q4 budget?",
            sender=EmailAddress(email="ceo@company.com", name="CEO"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Hi, I'd like to discuss the Q4 budget allocation with you. Are you available tomorrow afternoon?",
            date=base_date + timedelta(minutes=10),
            received_date=base_date + timedelta(minutes=10),
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Medium priority - team communication
        Email(
            id="team-update-1",
            message_id="<team-update-1@company.com>",
            subject="Weekly team standup notes",
            sender=EmailAddress(email="team-lead@company.com", name="Team Lead"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Here are this week's standup notes. Please review and add any comments.",
            date=base_date + timedelta(minutes=30),
            received_date=base_date + timedelta(minutes=30),
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Low priority - newsletter
        Email(
            id="newsletter-1",
            message_id="<newsletter-1@techcrunch.com>",
            subject="TechCrunch Daily: Latest tech news",
            sender=EmailAddress(email="newsletter@techcrunch.com", name="TechCrunch"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Here are today's top tech stories and startup news.",
            date=base_date + timedelta(hours=1),
            received_date=base_date + timedelta(hours=1),
            category=EmailCategory.UPDATES,
            priority=EmailPriority.NORMAL,
            is_read=False
        ),
        
        # Auto-archive - promotional
        Email(
            id="promo-1",
            message_id="<promo-1@store.com>",
            subject="50% off sale - limited time!",
            sender=EmailAddress(email="sales@onlinestore.com", name="Online Store"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Don't miss our biggest sale of the year! 50% off everything with code SALE50.",
            date=base_date + timedelta(hours=2),
            received_date=base_date + timedelta(hours=2),
            category=EmailCategory.PROMOTIONS,
            priority=EmailPriority.LOW,
            is_read=False
        ),
        
        # Auto-archive - social notification
        Email(
            id="social-1",
            message_id="<social-1@facebook.com>",
            subject="John liked your photo",
            sender=EmailAddress(email="notification@facebook.com", name="Facebook"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="John and 5 others liked your recent photo. See who else reacted.",
            date=base_date + timedelta(hours=3),
            received_date=base_date + timedelta(hours=3),
            category=EmailCategory.SOCIAL,
            priority=EmailPriority.LOW,
            is_read=False
        ),
        
        # Spam detection
        Email(
            id="spam-1",
            message_id="<spam-1@suspicious.com>",
            subject="You've won $1 million! Claim now!!!",
            sender=EmailAddress(email="winner@suspicious-site.com", name="Prize Center"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="CONGRATULATIONS! You have won our grand prize of $1 million! Click here to claim your prize immediately!",
            date=base_date + timedelta(hours=4),
            received_date=base_date + timedelta(hours=4),
            category=EmailCategory.PRIMARY,  # Categorizer should catch this as spam
            priority=EmailPriority.LOW,
            is_read=False
        ),
        
        # Old email - should have lower attention score
        Email(
            id="old-email-1",
            message_id="<old-email-1@company.com>",
            subject="Follow up on last week's discussion",
            sender=EmailAddress(email="colleague@company.com", name="Colleague"),
            recipients=[EmailAddress(email="me@company.com")],
            body_text="Just following up on our discussion from last week about the project timeline.",
            date=base_date - timedelta(days=5),
            received_date=base_date - timedelta(days=5),
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            is_read=False
        )
    ]


async def test_attention_scoring():
    """Test the attention scoring algorithm."""
    print("🎯 Testing Attention Scoring Algorithm")
    print("=" * 50)
    
    triage_agent = TriageAgent()
    test_emails = create_triage_test_emails()
    
    print(f"📧 Analyzing {len(test_emails)} test emails...\n")
    
    for email in test_emails:
        print(f"📨 Email: {email.subject}")
        print(f"   From: {email.sender.email}")
        print(f"   Category: {email.category.value}")
        
        attention_score = await triage_agent.calculate_attention_score(email)
        
        print(f"   🎯 Attention Score: {attention_score.score:.3f}")
        print(f"   📊 Factors: {', '.join([f'{k}={v:.2f}' for k, v in attention_score.factors.items()])}")
        print(f"   💭 Explanation: {attention_score.explanation}")
        print()
    
    await triage_agent.shutdown()


async def test_triage_decisions():
    """Test the complete triage decision making."""
    print("🧠 Testing Triage Decision Making")
    print("=" * 50)
    
    triage_agent = TriageAgent()
    test_emails = create_triage_test_emails()
    
    # Expected triage decisions for validation
    expected_decisions = {
        "urgent-work-1": TriageDecision.PRIORITY_INBOX,  # Urgent work email
        "boss-meeting-1": TriageDecision.PRIORITY_INBOX,  # From CEO
        "team-update-1": TriageDecision.REGULAR_INBOX,    # Regular team communication
        "newsletter-1": TriageDecision.AUTO_ARCHIVE,      # Newsletter/updates
        "promo-1": TriageDecision.AUTO_ARCHIVE,           # Promotional email
        "social-1": TriageDecision.AUTO_ARCHIVE,          # Social notification
        "spam-1": TriageDecision.SPAM_FOLDER,             # Suspicious email
        "old-email-1": TriageDecision.REGULAR_INBOX,      # Old but potentially relevant
    }
    
    correct_decisions = 0
    total_decisions = 0
    
    print(f"📧 Making triage decisions for {len(test_emails)} emails...\n")
    
    for email in test_emails:
        decision, attention_score = await triage_agent.make_triage_decision(email)
        expected = expected_decisions.get(email.id)
        
        is_correct = decision == expected if expected else True
        if is_correct:
            correct_decisions += 1
        total_decisions += 1
        
        status_icon = "✅" if is_correct else "❌"
        
        print(f"{status_icon} {email.subject}")
        print(f"   Decision: {decision.value}")
        print(f"   Score: {attention_score.score:.3f}")
        if expected:
            print(f"   Expected: {expected.value}")
        print()
    
    accuracy = (correct_decisions / total_decisions) * 100 if total_decisions > 0 else 0
    print(f"📊 Triage Accuracy: {accuracy:.1f}% ({correct_decisions}/{total_decisions})")
    
    await triage_agent.shutdown()
    return accuracy


async def test_batch_processing():
    """Test batch email processing and smart inbox creation."""
    print("📦 Testing Batch Processing & Smart Inbox")
    print("=" * 50)
    
    triage_agent = TriageAgent()
    test_emails = create_triage_test_emails()
    
    print(f"📧 Processing batch of {len(test_emails)} emails...\n")
    
    # Process emails in batch
    results = await triage_agent.process_email_batch(test_emails)
    
    # Display results
    for decision_type, emails in results.items():
        if emails:
            print(f"📁 {decision_type.replace('_', ' ').title()}: {len(emails)} emails")
            for email in emails:
                triage_data = email.connector_data.get("triage", {})
                score = triage_data.get("attention_score", {}).get("score", 0.0)
                print(f"   • {email.subject[:50]}... (score: {score:.2f})")
            print()
    
    # Show statistics
    stats = await triage_agent.get_triage_stats()
    print("📊 Triage Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    await triage_agent.shutdown()


async def test_crew_integration():
    """Test triage integration with EmailAgentCrew."""
    print("🤖 Testing CrewAI Integration")
    print("=" * 50)
    
    crew = EmailAgentCrew()
    await crew.initialize_crew({"verbose": False})
    
    test_emails = create_triage_test_emails()
    
    print(f"📧 Creating smart inbox for {len(test_emails)} emails...\n")
    
    # Test smart inbox creation
    smart_inbox = await crew.execute_task("smart_inbox", emails=test_emails)
    
    print("🧠 Smart Inbox Results:")
    stats = smart_inbox["stats"]
    print(f"   📊 Total: {stats['total_emails']} emails")
    print(f"   🔥 Priority: {stats['priority_count']} emails")
    print(f"   📧 Regular: {stats['regular_count']} emails")
    print(f"   📁 Archived: {stats['archived_count']} emails")
    print(f"   🗑️  Spam: {stats['spam_count']} emails")
    print()
    
    # Show priority emails
    if smart_inbox["priority_inbox"]:
        print("🔥 Priority Inbox:")
        for email in smart_inbox["priority_inbox"]:
            print(f"   • {email.subject}")
        print()
    
    # Show auto-archived emails
    if smart_inbox["auto_archived"]:
        print("📁 Auto-Archived:")
        for email in smart_inbox["auto_archived"]:
            print(f"   • {email.subject}")
        print()
    
    await crew.shutdown()


async def test_user_feedback_learning():
    """Test user feedback learning mechanism."""
    print("🎓 Testing User Feedback Learning")
    print("=" * 50)
    
    triage_agent = TriageAgent()
    
    # Simulate user feedback
    feedback_scenarios = [
        {"email_id": "test-1", "correct_decision": TriageDecision.PRIORITY_INBOX, "user_action": "moved_to_priority"},
        {"email_id": "test-2", "correct_decision": TriageDecision.AUTO_ARCHIVE, "user_action": "archived_manually"},
        {"email_id": "test-3", "correct_decision": TriageDecision.REGULAR_INBOX, "user_action": "correction_confirmed"}
    ]
    
    print("📝 Simulating user feedback scenarios...\n")
    
    for scenario in feedback_scenarios:
        await triage_agent.learn_from_user_feedback(
            scenario["email_id"],
            scenario["correct_decision"],
            scenario["user_action"]
        )
        print(f"✅ Feedback recorded: {scenario['email_id']} -> {scenario['correct_decision'].value}")
    
    # Check updated stats
    stats = await triage_agent.get_triage_stats()
    print(f"\n📊 Feedback count: {stats['feedback_count']}")
    
    await triage_agent.shutdown()


async def test_edge_cases():
    """Test edge cases and error handling."""
    print("🔧 Testing Edge Cases")
    print("=" * 50)
    
    triage_agent = TriageAgent()
    
    # Test empty email
    now = datetime.now()
    empty_email = Email(
        id="empty-1",
        message_id="<empty-1@test.com>",
        subject="",
        sender=EmailAddress(email="test@test.com"),
        recipients=[EmailAddress(email="me@test.com")],
        body_text="",
        date=now,
        received_date=now,
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.NORMAL,
        is_read=False
    )
    
    print("📧 Testing empty email...")
    attention_score = await triage_agent.calculate_attention_score(empty_email)
    print(f"   Score: {attention_score.score:.3f}")
    print(f"   Explanation: {attention_score.explanation}")
    
    # Test very old email
    old_email = Email(
        id="old-1",
        message_id="<old-1@test.com>",
        subject="Very old email",
        sender=EmailAddress(email="test@test.com"),
        recipients=[EmailAddress(email="me@test.com")],
        body_text="This email is very old",
        date=now - timedelta(days=30),
        received_date=now - timedelta(days=30),
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.NORMAL,
        is_read=False
    )
    
    print("\n📧 Testing very old email...")
    attention_score = await triage_agent.calculate_attention_score(old_email)
    print(f"   Score: {attention_score.score:.3f}")
    print(f"   Explanation: {attention_score.explanation}")
    
    await triage_agent.shutdown()


async def main():
    """Run comprehensive triage system tests."""
    print("🧪 Email Triage System Test Suite")
    print("=" * 50)
    print("Testing the AI-powered email screening and triage functionality\n")
    
    try:
        # Test individual components
        await test_attention_scoring()
        print("\n" + "="*50 + "\n")
        
        accuracy = await test_triage_decisions()
        print("\n" + "="*50 + "\n")
        
        await test_batch_processing()
        print("\n" + "="*50 + "\n")
        
        await test_crew_integration()
        print("\n" + "="*50 + "\n")
        
        await test_user_feedback_learning()
        print("\n" + "="*50 + "\n")
        
        await test_edge_cases()
        
        print("\n" + "="*50)
        print("🎉 Triage System Test Suite Complete!")
        print(f"📊 Overall triage accuracy: {accuracy:.1f}%")
        
        if accuracy >= 80:
            print("✅ Triage system is performing well!")
        else:
            print("⚠️  Triage system may need tuning")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
