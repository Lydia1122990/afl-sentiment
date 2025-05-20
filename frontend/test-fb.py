import requests
import re
import json
from datetime import datetime

def main():
    afl_teams_fb = {
        "westernbulldogs": "https://www.facebook.com/westernbulldogs",  # 只抓一个做测试
        # 后面可以继续加其他球队
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
    }

    retrieval_time = datetime.now().isoformat().replace(":", "-")

    for team, url in afl_teams_fb.items():
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            page = response.text

            # 先找JSON块，里面可能有粉丝数
            json_data_matches = re.findall(r'{"__bbox":.+?}}}}', page)
            followers = "N/A"

            for block in json_data_matches:
                if 'page_fan_count' in block:
                    try:
                        json_obj = json.loads(block)
                        # 深挖可能存在的粉丝数字段
                        for k, v in json_obj.items():
                            if isinstance(v, dict):
                                for inner_key, inner_value in v.items():
                                    if isinstance(inner_value, dict) and 'page_fan_count' in inner_value:
                                        followers = inner_value.get('page_fan_count', 'N/A')
                                        break
                    except json.JSONDecodeError:
                        continue

            # 兜底：如果找不到page_fan_count，再粗暴搜 followers 字符串
            if followers == "N/A":
                match = re.search(r'([\d.,KkMm]+)\s+followers', page, re.IGNORECASE)
                followers = match.group(1) if match else "N/A"

            print(f"{team}: {followers} followers (retrieved at {retrieval_time})")

        except Exception as e:
            print(f"Failed to fetch or parse {team}: {e}")

if __name__ == "__main__":
    main()
