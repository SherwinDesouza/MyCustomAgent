import sys
sys.path.append(r"C:\Users\PAX\My Conversational Bot")

print("Starting verification...")
try:
    import graph
    print("Successfully imported graph.py! Fix verified.")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
