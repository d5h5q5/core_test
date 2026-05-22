import requests
import json
import os
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse
import argparse
from typing import List, Dict, Optional
import urllib3

from sdk import CoreSDK

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SunonNewsCollector:
    def __init__(self, base_url: str = "https://mmm.isunon.com/news/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = False
        proxyDomain = "10.2.3.112:4396"

        # 通过环境变量获取代理认证信息
        try:
            proxyAuth = os.environ.get("PROXY_AUTH")
            CoreSDK.Log.info(f"当前获取的代理认证信息: {proxyAuth}")
        except Exception as e:
            # 捕获其他未知异常
            CoreSDK.Log.error(f"当前获取代理认证信息失败: {e}")
            proxyAuth = None

        # 拼接代理信息
        proxyUrl = f"socks5://{proxyAuth}@{proxyDomain}"
        CoreSDK.Log.info(f"当前获取的代理地址是: {proxyUrl}")

        # 添加代理配置
        self.session.proxies = {
            'http': proxyUrl,
            'https': proxyUrl
        }

        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def download_image(self, img_url: str, save_dir: str = "news_images") -> Optional[str]:
        """
        下载图片到本地
        """
        try:
            # 创建图片保存目录
            os.makedirs(save_dir, exist_ok=True)

            # 获取图片文件名
            parsed_url = urlparse(img_url)
            filename = os.path.basename(parsed_url.path)
            if not filename or '.' not in filename:
                filename = f"news_{int(time.time())}.jpg"

            filepath = os.path.join(save_dir, filename)

            # 下载图片
            response = self.session.get(img_url, timeout=10, verify=False)
            response.raise_for_status()

            # 保存图片
            with open(filepath, 'wb') as f:
                f.write(response.content)

            print(f"图片已保存: {filepath}")
            return filepath

        except Exception as e:
            print(f"下载图片失败 {img_url}: {e}")
            return None

    def parse_news_list(self, html_content: str, max_items: int = 10, download_images: bool = False) -> List[Dict]:
        """
        解析新闻列表页
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        news_items = []

        # 根据提供的HTML结构，新闻项目在 ul.swiper-e1.ul-news > li 中
        news_elements = soup.select('ul.swiper-e1.ul-news li')

        print(f"找到 {len(news_elements)} 个新闻项目")

        for i, element in enumerate(news_elements[:max_items]):
            try:
                news_data = {}

                # 提取标题 - 在 .tit 类中
                title_elem = element.select_one('.tit')
                if title_elem:
                    news_data['title'] = title_elem.get_text(strip=True)

                # 提取链接 - 在 a.con 标签中
                link_elem = element.select_one('a.con')
                if link_elem and link_elem.get('href'):
                    news_data['link'] = urljoin(self.base_url, link_elem['href'])

                # 提取描述 - 在 .desc 类中
                desc_elem = element.select_one('.desc')
                if desc_elem:
                    news_data['description'] = desc_elem.get_text(strip=True)

                # 提取发布时间 - 在 .date 类中
                date_elem = element.select_one('.date')
                if date_elem:
                    news_data['publish_time'] = date_elem.get_text(strip=True)

                # 提取分类 - 在 .span 类中
                category_elem = element.select_one('.span')
                if category_elem:
                    news_data['category'] = category_elem.get_text(strip=True)

                # 提取图片 - 在 .pic img 中
                img_elem = element.select_one('.pic img')
                if img_elem and img_elem.get('src'):
                    img_url = urljoin(self.base_url, img_elem['src'])
                    news_data['image_url'] = img_url

                    # 提取图片alt文本
                    if img_elem.get('alt'):
                        news_data['image_alt'] = img_elem['alt']

                    # 如果需要下载图片
                    if download_images:
                        local_path = self.download_image(img_url)
                        news_data['local_image_path'] = local_path

                if news_data.get('title'):  # 确保有标题
                    news_data['index'] = i + 1
                    news_items.append(news_data)
                    print(f"成功提取第 {i + 1} 条新闻: {news_data['title']}")

            except Exception as e:
                print(f"解析第 {i + 1} 个新闻项目时出错: {e}")
                continue

        return news_items

    def get_total_pages(self, html_content: str) -> int:
        """
        获取总页数
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        page_elements = soup.select('.pages .page-numbers a, .pages .page-numbers span')

        max_page = 1
        for element in page_elements:
            if element.name == 'a' and element.get('href'):
                # 从链接中提取页码
                href = element['href']
                if 'pg=' in href:
                    try:
                        page_num = int(href.split('pg=')[1])
                        max_page = max(max_page, page_num)
                    except:
                        pass
            elif element.get_text().isdigit():
                try:
                    page_num = int(element.get_text())
                    max_page = max(max_page, page_num)
                except:
                    pass

        print(f"检测到总页数: {max_page}")
        return max_page

    def collect_page(self, url, max_items: int = 10, download_images: bool = False) -> List[Dict]:
        """
        采集指定页面的新闻
        """
        try:
            # 构建URL
            url = f"{url}"



            # 发送请求
            response = self.session.get(url, timeout=15, verify=False)
            response.raise_for_status()
            response.encoding = 'utf-8'

            print(f"页面请求成功，状态码: {response.status_code}")

            # 解析页面
            news_list = self.parse_news_list(response.text, max_items, download_images)


            return news_list

        except requests.RequestException as e:
            print(f"请求失败: {e}")
            return []
        except Exception as e:
            print(f"处理时发生错误: {e}")
            return []

    def collect_all_pages(self, max_items_per_page: int = 10, download_images: bool = False, max_pages: int = None) -> \
    List[Dict]:
        """
        采集所有页面的新闻
        """
        all_news = []

        # 先获取第一页来检测总页数
        first_page_news = self.collect_page(1, max_items_per_page, download_images)
        if not first_page_news:
            return []

        all_news.extend(first_page_news)

        # 获取总页数
        try:
            response = self.session.get(f"{self.base_url}?pg=1", timeout=15, verify=False)
            response.encoding = 'utf-8'
            total_pages = self.get_total_pages(response.text)

            if max_pages and max_pages < total_pages:
                total_pages = max_pages

            print(f"开始采集共 {total_pages} 页数据...")

            # 采集后续页面
            for page in range(2, total_pages + 1):
                news_list = self.collect_page(page, max_items_per_page, download_images)
                all_news.extend(news_list)

                # 添加延迟，避免请求过于频繁
                if page < total_pages:
                    time.sleep(1)

        except Exception as e:
            print(f"获取总页数失败: {e}")

        return all_news

    def save_to_json(self, data: List[Dict], filename: str = "sunon_news.json"):
        """
        保存数据到JSON文件
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到: {filename}")
        except Exception as e:
            print(f"保存文件失败: {e}")

    def save_to_txt(self, data: List[Dict], filename: str = "sunon_news.txt"):
        """
        保存数据到文本文件
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(f"序号: {item.get('index', 'N/A')}\n")
                    f.write(f"标题: {item.get('title', '无标题')}\n")
                    f.write(f"链接: {item.get('link', '无链接')}\n")
                    f.write(f"描述: {item.get('description', '无描述')}\n")
                    f.write(f"发布时间: {item.get('publish_time', '未知')}\n")
                    f.write(f"分类: {item.get('category', '未知')}\n")
                    f.write(f"图片URL: {item.get('image_url', '无图片')}\n")
                    if item.get('image_alt'):
                        f.write(f"图片描述: {item.get('image_alt')}\n")
                    if item.get('local_image_path'):
                        f.write(f"本地图片路径: {item.get('local_image_path')}\n")
                    f.write("=" * 60 + "\n\n")
            print(f"文本数据已保存到: {filename}")
        except Exception as e:
            print(f"保存文本文件失败: {e}")

    def save_to_csv(self, data: List[Dict], filename: str = "sunon_news.csv"):
        """
        保存数据到CSV文件
        """
        try:
            import csv
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                if data:
                    fieldnames = ['index', 'title', 'link', 'description', 'publish_time', 'category', 'image_url',
                                  'image_alt', 'local_image_path']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for item in data:
                        row = {field: item.get(field, '') for field in fieldnames}
                        writer.writerow(row)
            print(f"CSV数据已保存到: {filename}")
        except Exception as e:
            print(f"保存CSV文件失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='圣奥新闻采集脚本')
    parser.add_argument('--pages', type=int, default=1, help='要采集的页数')
    parser.add_argument('--max-items', type=int, default=10, help='每页采集的最大条目数')
    parser.add_argument('--download-images', action='store_true', help='是否下载图片')
    parser.add_argument('--all-pages', action='store_true', help='采集所有页面')
    parser.add_argument('--output-json', type=str, default='sunon_news.json', help='JSON输出文件名')
    parser.add_argument('--output-txt', type=str, default='sunon_news.txt', help='文本输出文件名')
    parser.add_argument('--output-csv', type=str, default='sunon_news.csv', help='CSV输出文件名')

    args = parser.parse_args()

    # 创建采集器实例
    collector = SunonNewsCollector()

    all_news = []

    if args.all_pages:
        # 采集所有页面
        all_news = collector.collect_all_pages(
            max_items_per_page=args.max_items,
            download_images=args.download_images
        )
    else:
        # 采集指定页数
        for page in range(1, args.pages + 1):
            news_list = collector.collect_page(
                page=page,
                max_items=args.max_items,
                download_images=args.download_images
            )
            all_news.extend(news_list)

            # 添加延迟，避免请求过于频繁
            if page < args.pages:
                time.sleep(1)

    # 保存结果
    if all_news:
        collector.save_to_json(all_news, args.output_json)
        collector.save_to_txt(all_news, args.output_txt)
        collector.save_to_csv(all_news, args.output_csv)

        print(f"\n采集完成！共采集 {len(all_news)} 条新闻")

        # 显示统计信息
        categories = {}
        for item in all_news:
            category = item.get('category', '未知')
            categories[category] = categories.get(category, 0) + 1

        print("\n分类统计:")
        for category, count in categories.items():
            print(f"  {category}: {count} 条")

        with_images = sum(1 for item in all_news if item.get('image_url'))
        print(f"\n包含图片的新闻: {with_images} 条")
        print(f"数据文件: {args.output_json}, {args.output_txt}, {args.output_csv}")
        if args.download_images:
            print(f"图片保存在: news_images/ 目录")

        # 显示前3条结果预览
        print("\n前3条新闻预览:")
        for i, news in enumerate(all_news[:3]):
            print(f"\n--- 新闻 {i + 1} ---")
            print(f"标题: {news.get('title')}")
            print(f"时间: {news.get('publish_time')}")
            print(f"分类: {news.get('category')}")
            print(f"描述: {news.get('description', '无描述')[:50]}...")
    else:
        print("没有采集到任何数据，请检查网络连接或网站结构")


if __name__ == "__main__":


    input_json_dict = CoreSDK.Parameter.get_input_json_dict()
    # 直接运行示例
    collector = SunonNewsCollector()

    # 设置表头（如果使用SDK）
    headers = [
        {
            "label": "标题v4_1",
            "key": "title",
            "format": "text",
        },
        {
            "label": "时间",
            "key": "publish_time",
            "format": "text",
        },
        {
            "label": "分类",
            "key": "category",
            "format": "text",
        },
    ]
    res = CoreSDK.Result.set_table_header(headers)
    CoreSDK.Log.info(f"push_data resp: {res.code}, {res.message}")

    CoreSDK.Log.info(f"开始采集圣奥新闻...")

    for attempt in range(1):
        # 采集第1页，前5条数据，不下载图片
        news_data = collector.collect_page(input_json_dict["url"], input_json_dict["maximum"], input_json_dict["download_images"])

        CoreSDK.Log.info(f"news data: {news_data}")
        # 保存结果
        if news_data:
            CoreSDK.Log.info(f"采集完成...")

            # 打印结果
            for i, news in enumerate(news_data):
                print(f"\n--- 新闻 {i + 1} ---")
                print(f"标题: {news.get('title')}")
                print(f"时间: {news.get('publish_time')}")
                print(f"分类: {news.get('category')}")
                print(f"链接: {news.get('link')}")
                print(f"描述: {news.get('description')}")
                print(f"图片: {news.get('image_url', '无')}")

                obj = {
                    "title": news.get('title'),
                    "publish_time": news.get('publish_time'),
                    "category": news.get('category'),
                }

                CoreSDK.Log.info(f"push_data resp: {obj}")
                time.sleep(2)
                res = CoreSDK.Result.push_data(obj)
                CoreSDK.Log.info(f"push_data resp: {res.code}, {res.message}")
        else:
            print("采集失败，请检查网络连接")

        time.sleep(5)