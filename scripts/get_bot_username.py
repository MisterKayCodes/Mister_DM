import requests
import sys

def get_bot_info(token):
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("ok"):
            bot = data["result"]
            print(f"✅ Bot found!")
            print(f"   Username: @{bot['username']}")
            print(f"   First Name: {bot.get('first_name', 'N/A')}")
            print(f"   Bot ID: {bot['id']}")
            print(f"   Can Join Groups: {bot.get('can_join_groups', False)}")
            print(f"   Can Read Messages: {bot.get('can_read_all_group_messages', False)}")
            return bot["username"]
        else:
            print(f"❌ Error: {data.get('description', 'Invalid token')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        token = input("Enter your bot token: ").strip()
    else:
        token = sys.argv[1]
    
    if not token:
        print("❌ No token provided.")
    else:
        get_bot_info(token)