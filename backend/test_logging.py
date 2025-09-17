#!/usr/bin/env python3
"""
Test script for the professional logging system
"""

import os
import asyncio
from logger import get_logger, log_execution_time, log_ai_generation, log_schema_processing, log_quota_check, log_user_context

# Test different environment configurations
def test_logger_environments():
    """Test logger in different environments"""
    print("🧪 Testing Logger Environments")
    print("=" * 50)
    
    # Test DEV environment
    os.environ['APP_ENV'] = 'dev'
    os.environ['APP_LOG_FORMAT'] = 'text'
    print("\n📝 DEV Environment (Detailed Text Format):")
    
    logger = get_logger("test_module")
    logger.info(
        "Test message in DEV environment", 
        module_name="test",
        func_name="test_dev",
        doc_id="doc123",
        exercise_id="ex456",
        schema_type="triangle"
    )
    
    # Test PROD environment with text format
    os.environ['APP_ENV'] = 'prod'
    os.environ['APP_LOG_FORMAT'] = 'text'
    print("\n📝 PROD Environment (Text Format):")
    
    logger = get_logger("test_module") 
    logger.info(
        "Test message in PROD text environment",
        module_name="test", 
        func_name="test_prod_text",
        doc_id="doc789",
        duration_ms=250
    )
    
    # Test PROD environment with JSON format
    os.environ['APP_ENV'] = 'prod'
    os.environ['APP_LOG_FORMAT'] = 'json'
    print("\n📝 PROD Environment (JSON Format):")
    
    logger = get_logger("test_module")
    logger.info(
        "Test message in PROD JSON environment",
        module_name="export",
        func_name="render_pdf", 
        doc_id="doc999",
        schema_type="cercle",
        duration_ms=340,
        status="success"
    )

def test_sensitive_data_filtering():
    """Test sensitive data filtering"""
    print("\n🔒 Testing Sensitive Data Filtering")
    print("=" * 50)
    
    logger = get_logger("security_test")
    
    # Test email redaction
    logger.info(
        "User login attempt from john.doe@example.com with token abc123xyz",
        module_name="auth",
        func_name="login"
    )
    
    # Test API key redaction  
    logger.info(
        "Processing payment with stripe key sk_test_abcd1234567890xyz",
        module_name="payment",
        func_name="process_stripe"
    )
    
    # Test session token redaction
    logger.info(
        "Session validation: session_token=sess_very_long_token_12345",
        module_name="auth", 
        func_name="validate"
    )

def test_convenience_functions():
    """Test convenience logging functions"""
    print("\n🎯 Testing Convenience Functions")
    print("=" * 40)
    
    # Test user context logging
    log_user_context("pro", "doc123", subscription_status="active")
    log_user_context("guest", doc_id="doc456")
    
    # Test quota logging
    log_quota_check("guest", current_count=2, limit=3, guest_id="guest789")
    log_quota_check("pro", current_count=15, limit=100, user_email="pro***@example.com")
    
    # Test schema processing logging
    log_schema_processing("triangle", True, doc_id="doc123", exercise_id="ex1")
    log_schema_processing("cylindre", False, doc_id="doc456", exercise_id="ex2", error="invalid_data")
    
    # Test AI generation logging
    log_ai_generation("first_pass", True, doc_id="doc789", nb_exercices=3)
    log_ai_generation("second_pass", False, doc_id="doc789", error="timeout")

@log_execution_time("test_decorator")
async def test_async_function():
    """Test async function with logging decorator"""
    logger = get_logger()
    logger.info("Inside async test function")
    await asyncio.sleep(0.1)  # Simulate some work
    return "async_result"

@log_execution_time("test_sync_decorator")
def test_sync_function():
    """Test sync function with logging decorator"""
    logger = get_logger()
    logger.info("Inside sync test function")
    import time
    time.sleep(0.05)  # Simulate some work
    return "sync_result"

def test_function_decorators():
    """Test function execution time decorators"""
    print("\n⏱️ Testing Function Decorators")
    print("=" * 40)
    
    # Test sync decorator
    result = test_sync_function()
    print(f"Sync function result: {result}")
    
    # Test async decorator
    async def run_async_test():
        result = await test_async_function()
        print(f"Async function result: {result}")
    
    asyncio.run(run_async_test())

def test_error_logging():
    """Test error logging with stack traces"""
    print("\n❌ Testing Error Logging")
    print("=" * 40)
    
    logger = get_logger("error_test")
    
    try:
        # Simulate an error
        result = 1 / 0
    except Exception as e:
        logger.error(
            "Division by zero error occurred",
            module_name="math",
            func_name="divide",
            doc_id="error_doc",
            operation="division",
            exc_info=True  # This will include the stack trace
        )

def test_different_log_levels():
    """Test different logging levels"""
    print("\n📊 Testing Different Log Levels")
    print("=" * 40)
    
    logger = get_logger("level_test")
    
    logger.debug("Debug message - detailed info", module_name="test", func_name="debug_test")
    logger.info("Info message - general info", module_name="test", func_name="info_test")  
    logger.warning("Warning message - potential issue", module_name="test", func_name="warning_test")
    logger.error("Error message - something failed", module_name="test", func_name="error_test")
    logger.critical("Critical message - system failure", module_name="test", func_name="critical_test")

def main():
    """Run all logging tests"""
    print("🚀 Professional Logging System Test Suite")
    print("=" * 60)
    
    # Run all tests
    test_logger_environments()
    test_sensitive_data_filtering()
    test_convenience_functions()
    test_function_decorators()
    test_error_logging()
    test_different_log_levels()
    
    print("\n✅ All logging tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()