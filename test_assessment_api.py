#!/usr/bin/env python3
"""
Test script for the assessment API endpoint.
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_assessment_api():
    """Test the assessment API endpoints."""
    base_url = "http://localhost:8000"
    
    print("🏥 Testing NG12 Cancer Risk Assessment API")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test health endpoint first
            print("1. Testing health endpoint...")
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✓ Health check: {health_data['status']}")
            else:
                print(f"   ✗ Health check failed: {response.status_code}")
                return False
            
            # Test assessment stats
            print("\n2. Testing assessment stats endpoint...")
            try:
                response = await client.get(f"{base_url}/assess/stats")
                if response.status_code == 200:
                    stats_data = response.json()
                    print(f"   ✓ Assessment stats retrieved")
                    print(f"   - Engine healthy: {stats_data.get('health_status', {}).get('engine_healthy', 'Unknown')}")
                else:
                    print(f"   ⚠ Stats endpoint returned: {response.status_code}")
            except Exception as e:
                print(f"   ⚠ Stats endpoint error: {e}")
            
            # Test individual patient assessments
            test_patients = ["PT-101", "PT-102", "PT-103"]
            
            print(f"\n3. Testing individual patient assessments...")
            for patient_id in test_patients:
                print(f"\n   Testing patient: {patient_id}")
                try:
                    response = await client.post(
                        f"{base_url}/assess",
                        json={"patient_id": patient_id}
                    )
                    
                    if response.status_code == 200:
                        assessment = response.json()
                        print(f"   ✓ Assessment: {assessment['assessment']}")
                        print(f"   ✓ Reasoning: {assessment['reasoning'][:100]}...")
                        print(f"   ✓ Citations: {len(assessment['citations'])} found")
                        if assessment.get('confidence_score'):
                            print(f"   ✓ Confidence: {assessment['confidence_score']:.2f}")
                    else:
                        print(f"   ✗ Assessment failed: {response.status_code}")
                        print(f"   Error: {response.text}")
                        
                except Exception as e:
                    print(f"   ✗ Request failed: {e}")
            
            # Test batch assessment
            print(f"\n4. Testing batch assessment...")
            try:
                response = await client.post(
                    f"{base_url}/assess/batch",
                    json=test_patients
                )
                
                if response.status_code == 200:
                    batch_results = response.json()
                    print(f"   ✓ Batch assessment completed: {len(batch_results)} results")
                    
                    # Summary of results
                    assessments = [r['assessment'] for r in batch_results]
                    urgent_referrals = assessments.count('Urgent Referral')
                    urgent_investigations = assessments.count('Urgent Investigation')
                    no_actions = assessments.count('No Action')
                    
                    print(f"   - Urgent Referrals: {urgent_referrals}")
                    print(f"   - Urgent Investigations: {urgent_investigations}")
                    print(f"   - No Actions: {no_actions}")
                    
                else:
                    print(f"   ✗ Batch assessment failed: {response.status_code}")
                    print(f"   Error: {response.text}")
                    
            except Exception as e:
                print(f"   ✗ Batch request failed: {e}")
            
            # Test invalid patient ID
            print(f"\n5. Testing error handling...")
            try:
                response = await client.post(
                    f"{base_url}/assess",
                    json={"patient_id": "INVALID-ID"}
                )
                
                if response.status_code == 404:
                    print(f"   ✓ Correctly handled invalid patient ID (404)")
                else:
                    print(f"   ⚠ Unexpected status for invalid ID: {response.status_code}")
                    
            except Exception as e:
                print(f"   ✗ Error handling test failed: {e}")
            
            print("\n" + "=" * 50)
            print("✅ Assessment API testing completed!")
            return True
            
        except httpx.ConnectError:
            print("✗ Cannot connect to server. Make sure it's running on localhost:8000")
            print("Start with: docker-compose up --build -d")
            return False
        except Exception as e:
            print(f"✗ Test failed: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_assessment_api())
    exit(0 if success else 1)