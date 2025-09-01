#!/usr/bin/env python3
"""
Simple test script to test faculty registration functionality
"""

import requests
import json

def test_faculty_registration():
    """Test faculty registration endpoint"""
    
    # Test data for faculty registration
    faculty_data = {
        'firstname': 'John',
        'lastname': 'Doe',
        'username': 'FAC-001',
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'faculty',
        'dept_id': '1',  # CCS - College of Computer Studies
        'position': 'Professor'
    }
    
    print("🧪 Testing Faculty Registration...")
    print(f"📋 Test data: {json.dumps(faculty_data, indent=2)}")
    
    try:
        # Test the registration endpoint
        response = requests.post(
            'http://localhost:5000/register/faculty',
            data=faculty_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        print(f"📡 Response Status: {response.status_code}")
        print(f"📡 Response Headers: {dict(response.headers)}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                result = response.json()
                print(f"📋 Response JSON: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError:
                print(f"📋 Response Text (not JSON): {response.text}")
        else:
            print(f"📋 Response Text: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server might not be running")
        print("💡 Make sure to start the Flask server first with: python app.py")
    except Exception as e:
        print(f"💥 Error during test: {e}")

if __name__ == "__main__":
    test_faculty_registration()
