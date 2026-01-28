#!/usr/bin/env python3
"""
Test script to verify Sentinel and Janitor API endpoints are working.
Tests both the raw endpoints and the fixes for empty results.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_endpoint(session, url, name):
    """Test a single endpoint and report results."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        async with session.get(url) as response:
            print(f"Status Code: {response.status}")
            
            if response.status == 200:
                data = await response.json()
                print(f"✅ SUCCESS - Data received")
                
                # Pretty print the response structure
                print(f"Response keys: {list(data.keys())}")
                
                # Check for common issues
                if "predictions" in data:
                    preds = data.get("predictions", [])
                    print(f"Predictions: {len(preds)} items")
                    if preds:
                        print(f"Sample prediction: {preds[0].get('type', 'unknown')}")
                    else:
                        print("⚠️  No predictions found")
                
                if "anomalies" in data:
                    anomalies = data.get("anomalies", [])
                    print(f"Anomalies: {len(anomalies)} items")
                
                if "recommendations" in data:
                    recs = data.get("recommendations", [])
                    print(f"Recommendations: {len(recs)} items")
                    if recs:
                        print(f"Sample: {recs[0]}")
                
                if "agents" in data:
                    agents = data.get("agents", [])
                    print(f"Agents: {len(agents)} items")
                    for agent in agents:
                        print(f"  - {agent.get('name', 'unknown')}: {agent.get('specialization', 'no specialization')}")
                
                if "downloads" in data:
                    downloads = data.get("downloads", {})
                    print(f"Downloads: {downloads.get('files', 0)} files, {downloads.get('size_mb', 0)} MB")
                
                if "errors" in data and data["errors"]:
                    errors = data.get("errors", [])
                    print(f"⚠️  Errors found: {len(errors)}")
                    for error in errors[:3]:  # Show first 3 errors
                        print(f"    - {error}")
                
                # Show mock data warnings
                if data.get("mock_data"):
                    print("🧪 MOCK DATA: Using simulated data for testing")
                
                if data.get("data_status"):
                    status = data.get("data_status", {})
                    print(f"Data Status: {status}")
                
                return True
            else:
                text = await response.text()
                print(f"❌ FAILED - Status {response.status}")
                print(f"Response: {text[:500]}")
                return False
                
    except aiohttp.ClientError as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON DECODE ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

async def main():
    """Run all endpoint tests."""
    print("🧪 Testing Sentinel and Janitor API Endpoints")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Base URL: {BASE_URL}")
    
    # Define test endpoints
    endpoints = [
        ("/api/sentinel/predictions", "Sentinel Predictions"),
        ("/api/sentinel/status", "Sentinel Status"),
        ("/api/agents", "Agent Registry"),
        ("/api/agents/janitor/quick-scan", "Janitor Quick Scan"),
        ("/api/agents/sentinel/health-report", "Sentinel Health Report"),
        ("/health", "Health Check"),
    ]
    
    async with aiohttp.ClientSession() as session:
        results = []
        
        for url, name in endpoints:
            success = await test_endpoint(session, f"{BASE_URL}{url}", name)
            results.append((name, success))
            
            # Small delay between requests
            await asyncio.sleep(0.5)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\nResults: {passed}/{total} endpoints working")
    
    if passed == total:
        print("🎉 ALL ENDPOINTS WORKING!")
    elif passed > 0:
        print("⚠️  Some endpoints working, some need attention")
    else:
        print("🚨 NO ENDPOINTS WORKING - Check if server is running")
    
    print(f"\n📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    print("🚀 Starting API endpoint tests...")
    print("⚠️  Make sure the microservice is running on http://localhost:8000")
    print("⚠️  Run: python -m app.main")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
