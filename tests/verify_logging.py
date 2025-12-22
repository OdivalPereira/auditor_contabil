from src.common.logging_config import setup_logging, get_logger, set_request_id
import json
import os

def test_logging():
    log_file = "logs/test_verification.log"
    if os.path.exists(log_file):
        os.remove(log_file)
        
    setup_logging(log_file=log_file)
    logger = get_logger("test_logger")
    
    set_request_id("TEST-REQ-123")
    
    logger.info("Test message", key="value", nested={"a": 1})
    
    with open(log_file, "r", encoding='utf-8') as f:
        lines = f.readlines()
        
    found = False
    for line in lines:
        data = json.loads(line)
        if data["message"] == "Test message":
            print("Log entry found:")
            print(json.dumps(data, indent=2))
            
            assert data["request_id"] == "TEST-REQ-123"
            assert data["key"] == "value"
            assert data["nested"]["a"] == 1
            found = True
            break
            
    assert found, "Test message not found in logs"
    print("\nVerification successful! JSON format and metadata are correct.")

if __name__ == "__main__":
    test_logging()
