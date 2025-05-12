import asyncio
import aiohttp
import time
from datetime import datetime
import json
from typing import List, Dict
import random

class LoadTester:
    def __init__(self, base_url: str = "http://localhost:5050"):
        self.base_url = base_url
        self.results: List[Dict] = []
        
    async def make_request(self, session: aiohttp.ClientSession, endpoint: str, method: str = "GET", data: dict = None) -> Dict:
        start_time = time.time()
        try:
            if method == "GET":
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    status = response.status
                    text = await response.text()
            else:
                async with session.post(f"{self.base_url}{endpoint}", json=data) as response:
                    status = response.status
                    text = await response.text()
                    
            duration = time.time() - start_time
            return {
                "endpoint": endpoint,
                "method": method,
                "status": status,
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            duration = time.time() - start_time
            return {
                "endpoint": endpoint,
                "method": method,
                "status": "error",
                "error": str(e),
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            }

    async def run_test(self, num_requests: int = 100, concurrent_requests: int = 10):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for _ in range(num_requests):
                # Randomly choose an endpoint
                endpoint = random.choice([
                    "/api/browse",
                    "/api/queue",
                    "/health",
                    "/api/transcribe"
                ])
                
                # For transcribe endpoint, use POST with test data
                if endpoint == "/api/transcribe":
                    data = {"path": "test.mp4"}
                    task = self.make_request(session, endpoint, "POST", data)
                else:
                    task = self.make_request(session, endpoint)
                
                tasks.append(task)
                
                # Process in batches of concurrent_requests
                if len(tasks) >= concurrent_requests:
                    results = await asyncio.gather(*tasks)
                    self.results.extend(results)
                    tasks = []
            
            # Process any remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks)
                self.results.extend(results)

    def analyze_results(self):
        if not self.results:
            print("No results to analyze")
            return
        
        # Calculate statistics
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r["status"] == 200)
        failed_requests = total_requests - successful_requests
        rate_limited = sum(1 for r in self.results if r["status"] == 429)
        
        # Calculate response times
        durations = [r["duration"] for r in self.results]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        # Print results
        print("\nLoad Test Results:")
        print(f"Total Requests: {total_requests}")
        print(f"Successful Requests: {successful_requests}")
        print(f"Failed Requests: {failed_requests}")
        print(f"Rate Limited Requests: {rate_limited}")
        print(f"\nResponse Times:")
        print(f"Average: {avg_duration:.3f}s")
        print(f"Maximum: {max_duration:.3f}s")
        print(f"Minimum: {min_duration:.3f}s")
        
        # Save detailed results to file
        with open("load_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

async def main():
    tester = LoadTester()
    print("Starting load test...")
    await tester.run_test(num_requests=200, concurrent_requests=20)
    tester.analyze_results()

if __name__ == "__main__":
    asyncio.run(main()) 