#!/usr/bin/env python3
"""
Lambda Cloud Instance Finder
Finds the lowest-priced available instance in us-east-1 region under $2.00/hour
"""

import requests
import json
import os
import dotenv
from typing import Dict, List, Optional, Tuple

class LambdaCloudClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://cloud.lambda.ai/api/v1"
        self.headers = {
            'accept': 'application/json'
        }
    
    def get_instance_types(self) -> Dict:
        """Fetch all available instance types from Lambda Cloud API"""
        url = f"{self.base_url}/instance-types"
        
        try:
            response = requests.get(
                url, 
                headers=self.headers, 
                auth=(self.api_key, '')
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from API: {e}")
            return {}
    
    def find_cheapest_instance(
        self, 
        target_region: str = "us-east-1", 
        max_price_cents: int = 200
    ) -> Optional[Tuple[str, Dict]]:
        """
        Find the cheapest available instance in the target region under max price
        
        Args:
            target_region: Region to search for instances (default: us-east-1)
            max_price_cents: Maximum price in cents per hour (default: 200)
            
        Returns:
            Tuple of (instance_name, instance_data) or None if no match found
        """
        data = self.get_instance_types()
        
        if not data or 'data' not in data:
            print("No data received from API")
            return None
        
        available_instances = []
        
        # Filter instances by region availability and price
        for instance_name, instance_info in data['data'].items():
            instance_type = instance_info.get('instance_type', {})
            regions = instance_info.get('regions_with_capacity_available', [])
            price = instance_type.get('price_cents_per_hour', float('inf'))
            
            # Check if instance is available in target region and under price limit
            region_available = any(
                region.get('name') == target_region 
                for region in regions
            )
            
            if region_available and price <= max_price_cents:
                available_instances.append((instance_name, instance_info, price))
        
        if not available_instances:
            print(f"No instances found in {target_region} under {max_price_cents} cents/hour")
            return None
        
        # Sort by price and return the cheapest
        available_instances.sort(key=lambda x: x[2])
        cheapest_name, cheapest_info, cheapest_price = available_instances[0]
        
        
        return cheapest_name, cheapest_info
    
    def display_instance_info(self, instance_name: str, instance_info: Dict):
        """Display formatted instance information"""
        instance_type = instance_info['instance_type']
        specs = instance_type['specs']
        regions = instance_info['regions_with_capacity_available']
        
        print(f"\n{'='*50}")
        print(f"FOUND: {instance_name}")
        print(f"{'='*50}")
        print(f"Description: {instance_type['description']}")
        print(f"Price: ${instance_type['price_cents_per_hour']/100:.2f}/hour")
        print(f"GPU: {instance_type['gpu_description']}")
        print(f"vCPUs: {specs['vcpus']}")
        print(f"Memory: {specs['memory_gib']} GiB")
        print(f"Storage: {specs['storage_gib']} GiB")
        print(f"GPUs: {specs['gpus']}")
        
        print(f"\nAvailable Regions:")
        for region in regions:
            print(f"  - {region['name']}: {region['description']}")

def main():
    # Get API key from environment variable
    api_key = os.getenv('LAMBDA_API_KEY')
    
    if not api_key:
        print("Error: Please set the LAMBDA_API_KEY environment variable")
        print("Example: export LAMBDA_API_KEY='your_secret_key_here'")
        return
    
    # Initialize client
    client = LambdaCloudClient(api_key)
    
    # Configuration
    TARGET_REGION = "us-east-1"
    MAX_PRICE_CENTS = 200  # $2.00/hour
    
    print(f"Searching for cheapest instance in {TARGET_REGION} under ${MAX_PRICE_CENTS/100:.2f}/hour...")
    
    # Find the cheapest instance
    result = client.find_cheapest_instance(TARGET_REGION, MAX_PRICE_CENTS)
    
    if result:
        instance_name, instance_info = result
        client.display_instance_info(instance_name, instance_info)
        os.system("notify-send 'Instance Found'")
        
        # Optional: Return instance data for programmatic use
        return {
            'name': instance_name,
            'data': instance_info
        }
    else:
        print(f"No suitable instances found in {TARGET_REGION} under ${MAX_PRICE_CENTS/100:.2f}/hour")
        
        # Show what's available in the region (any price)
        print(f"\nChecking all available instances in {TARGET_REGION}...")
        all_in_region = client.find_cheapest_instance(TARGET_REGION, float('inf'))
        if all_in_region:
            name, info = all_in_region
            print(f"Cheapest available in {TARGET_REGION}: {name} at ${info['instance_type']['price_cents_per_hour']/100:.2f}/hour")

if __name__ == "__main__":
    dotenv.load_dotenv()
    main()
