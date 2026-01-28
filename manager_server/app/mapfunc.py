import requests
from .config import get_settings

settings = get_settings()

def baidu_reverse_geocode(latitude, longitude):
    """
    调用百度地图逆地理位置解析 API，根据经纬度返回具体地点信息
    :param latitude: 纬度（如 39.908823）
    :param longitude: 经度（如 116.397470）
    :param ak: 百度地图开放平台获取的 API 密钥（AK）
    :return: 解析成功返回地点信息字典，失败返回 None
    """
    # 百度逆地理解析 API 接口地址（JSON 格式返回，更易解析）
    # api_url = "http://api.map.baidu.com/geocoder/v2/"
    api_url = "https://api.map.baidu.com/reverse_geocoding/v3/"
    ak = settings.baidu_ak
    if not ak:
        return None
    # 构造请求参数
    params = {
        "location": f"{latitude},{longitude}",  # 格式：纬度,经度
        "output": "json",                       # 返回数据格式：json 或 xml
        "ak": ak,                               # 你的百度地图 AK
        "pois": "0"                             # 是否返回周边POI，0=不返回，1=返回（按需调整）
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        # 检查请求是否成功（状态码 200 表示成功）
        response.raise_for_status()
        result = response.json()
        if result.get("status") == 0:
            address_result = result.get("result", {})

            return {
                "address": address_result.get("formatted_address", "未获取到完整地址"),
                "simple_address": address_result.get("addressComponent", {}).get("street", "未获取到街道")
                + address_result.get("addressComponent", {}).get("street_number", "未获取到门牌号"),
            }
        else:
            print(f"百度 API 解析失败，错误信息：{result.get('message', '未知错误')}")
            return None
    
    except requests.exceptions.Timeout:
        print("请求超时，网络连接可能不稳定")
        return None
    except requests.exceptions.RequestException as e:
        print(f"请求异常：{str(e)}")
        return None
    except Exception as e:
        print(f"未知异常：{str(e)}")
        return None

# ret = baidu_reverse_geocode(29.368823, 105.937470)
# print(ret)