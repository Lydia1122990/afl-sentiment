from atproto import Client
import socket
import os
from datetime import datetime
import time

def test_connection(host, port, timeout=5):

    try:
        socket.create_connection((host, port), timeout=timeout)
        print(f"✅ Connection to {host}:{port} successful")
        return True
    except Exception as e:
        print(f"❌ Connection to {host}:{port} failed: {e}")
        return False

def main():
    print("Starting debug function...")
    
   
    print("Testing network connections...")
    
    es_host = "elasticsearch-master.elastic.svc.cluster.local"
    es_port = 9200
    test_connection(es_host, es_port)
    
    
    current_time = datetime.now().isoformat()
    return {
        "status": "debug complete",
        "time": current_time,
        "message": "Connection test completed"
    }