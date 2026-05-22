from DrissionPage import ChromiumPage, ChromiumOptions
from bs4 import BeautifulSoup
import json
import time
import sys
import os
from urllib.parse import urljoin


from sdk import CafeSDK

class CafeHookScraper:
    def __init__(self):
        print("🚀 初始化 DrissionPage...")
        self.base_url = "https://www.cafehook.com"

        try:
            # 配置浏览器选项
            co = ChromiumOptions()
            # 可以设置无头模式，如果需要可视化可以注释掉
            # co.headless()

            # 其他配置
            co.set_argument('--no-sandbox')
            co.set_argument("--headless")
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--disable-gpu')
            co.set_argument('--window-size=1920,1080')
            co.set_user_agent(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

            # 创建页面对象 - 正确的初始化方式
            self.page = ChromiumPage(addr_or_opts=co)
            print("✅ DrissionPage 初始化成功")

        except Exception as e:
            print(f"❌ DrissionPage 初始化失败: {e}")
            print("尝试使用默认配置...")
            try:
                # 尝试使用默认配置
                self.page = ChromiumPage()
                print("✅ DrissionPage 使用默认配置初始化成功")
            except Exception as e2:
                print(f"❌ DrissionPage 默认配置也失败: {e2}")
                print("请确保已安装 DrissionPage: pip install DrissionPage")
                sys.exit(1)

    def __del__(self):
        """析构函数，关闭浏览器"""
        if hasattr(self, 'page'):
            print("正在关闭浏览器...")
            try:
                self.page.quit()
            except:
                pass

    def scroll_page_to_bottom(self, scroll_pause_time=1, max_scrolls=20):
        """渐进式滚动页面以触发懒加载"""
        print("🔄 开始渐进式滚动页面以触发懒加载...")

        # 获取页面高度和视口高度
        page_height = self.page.run_js("return document.body.scrollHeight")
        viewport_height = self.page.run_js("return window.innerHeight")

        print(f"📏 页面总高度: {page_height}px, 视口高度: {viewport_height}px")

        # 计算需要滚动的次数
        scroll_steps = max(1, page_height // viewport_height)
        scroll_steps = min(scroll_steps, max_scrolls)  # 不超过最大滚动次数

        print(f"📈 计划进行 {scroll_steps} 次渐进滚动")

        for step in range(scroll_steps):
            # 计算当前滚动位置
            scroll_position = int((step + 1) * viewport_height * 0.8)  # 每次滚动视口的80%，确保有重叠

            # 确保不超过页面高度
            scroll_position = min(scroll_position, page_height - viewport_height)

            # 滚动到指定位置
            self.page.run_js(f"window.scrollTo(0, {scroll_position});")

            print(f"📜 滚动进度: {step + 1}/{scroll_steps}次，位置: {scroll_position}px")

            # 等待内容加载
            time.sleep(scroll_pause_time)

            # 检查页面高度是否变化（可能由于懒加载内容增加了页面高度）
            new_page_height = self.page.run_js("return document.body.scrollHeight")
            if new_page_height > page_height:
                print(f"📐 页面高度增加: {page_height}px -> {new_page_height}px")
                page_height = new_page_height
                # 重新计算剩余滚动步骤
                remaining_steps = max(1, (page_height - scroll_position) // viewport_height)
                scroll_steps = min(step + 1 + remaining_steps, max_scrolls)

        # 最后滚动到底部确保所有内容都加载
        self.page.scroll.to_bottom()
        time.sleep(scroll_pause_time)

        print("✅ 渐进式滚动完成")

        # 检查最终页面高度
        final_page_height = self.page.run_js("return document.body.scrollHeight")
        print(f"📏 最终页面高度: {final_page_height}px")

    def scroll_element_into_view(self, element):
        """将特定元素滚动到视图中"""
        try:
            self.page.scroll.to_element(element)
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"滚动元素到视图失败: {e}")
            return False

    def scrape_article_list(self, url=None):
        """
        从cafehook网站采集文章列表

        Args:
            url: 要采集的URL，默认为首页
        """
        if url is None:
            url = self.base_url

        try:
            print(f"🌐 开始访问: {url}")
            self.page.get(url)

            # 等待页面加载完成
            print("⏳ 等待页面加载...")
            self.page.wait.load_start()
            time.sleep(3)

            # 打印当前页面标题和URL以确认访问成功
            print(f"📄 页面标题: {self.page.title}")
            print(f"🔗 当前URL: {self.page.url}")

            # 滚动页面以触发懒加载
            self.scroll_page_to_bottom()

            # 获取页面源码并用 BeautifulSoup 解析
            print("🔄 解析页面内容...")
            html = self.page.html
            soup = BeautifulSoup(html, 'html.parser')

            # 保存页面源码以便调试
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print("💾 页面源码已保存: page_source.html")

            # 找到列表容器
            list_container = soup.find('ul', class_='list-group')
            if not list_container:
                print("⚠️ 未找到ul.list-group，尝试其他选择器...")
                # 尝试其他可能的选择器
                list_container = (soup.find('div', class_='article-list') or
                                  soup.find('div', class_='posts-container') or
                                  soup.find('main'))
                if not list_container:
                    print("❌ 无法找到文章列表容器")
                    # 打印所有可能的容器用于调试
                    all_containers = soup.find_all(['ul', 'div', 'main'])
                    print(f"📊 页面中共有 {len(all_containers)} 个容器元素")
                    return []

            # 找到所有的li元素（文章项）
            article_items = list_container.find_all('li')
            print(f"📝 找到 {len(article_items)} 个li元素")

            # 如果没有找到li，尝试直接查找文章卡片
            if len(article_items) == 0:
                print("⚠️ 未找到li元素，尝试直接查找文章卡片...")
                article_items = list_container.find_all('div', class_=lambda x: x and 'card' in x if x else False)
                print(f"🃏 通过卡片找到 {len(article_items)} 篇文章")

            # 如果仍然没有找到，尝试更通用的选择器
            if len(article_items) == 0:
                print("⚠️ 仍然没有找到文章项，尝试通用选择器...")
                # 查找所有可能的文章容器
                possible_selectors = [
                    'li',
                    'div[class*="card"]',
                    'div[class*="item"]',
                    'article',
                    'div.list-group-item'
                ]
                for selector in possible_selectors:
                    article_items = list_container.select(selector)
                    if article_items:
                        print(f"🎯 使用选择器 '{selector}' 找到 {len(article_items)} 个文章项")
                        break

            results = []

            for index, item in enumerate(article_items):
                try:
                    print(f"\n🔧 处理第 {index + 1} 个文章项...")
                    article_data = self.extract_article_data(item, index)
                    if article_data and article_data['title']:  # 确保有标题
                        results.append(article_data)
                        print(f"✅ 成功提取第 {index + 1} 篇文章: {article_data['title'][:30]}...")
                    else:
                        print(f"❌ 第 {index + 1} 篇文章数据不完整，跳过")
                        # 保存该项的HTML以便调试
                        with open(f'item_{index}.html', 'w', encoding='utf-8') as f:
                            f.write(item.prettify())

                except Exception as e:
                    print(f"❌ 提取第 {index + 1} 篇文章时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue

            return results

        except Exception as e:
            print(f"❌ 采集失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_article_data(self, item, index):
        """从单个文章项中提取数据"""
        data = {
            'index': index + 1,
            'title': '',
            'author': '',
            'author_avatar': '',
            'article_url': '',
            'image_url': '',
            'tags': [],
            'stats': {
                'likes': 0,
                'comments': 0,
                'views': 0,
                'publish_date': ''
            }
        }

        # 尝试多种提取方式
        self._extract_from_item(item, data, index)

        return data

    def _extract_from_item(self, item, data, index):
        """从项目元素中提取数据"""
        # 提取标题和文章链接
        title_elem = (item.find('h2', class_='title') or
                      item.find('h3', class_='title') or
                      item.find('h2') or
                      item.find('h3') or
                      item.find('a', class_=lambda x: x and 'title' in x if x else False))

        if title_elem:
            title_link = title_elem.find('a') if title_elem.name != 'a' else title_elem
            if title_link:
                data['title'] = title_link.get_text().strip()
                if title_link.get('href'):
                    data['article_url'] = urljoin(self.base_url, title_link['href'])
                    # 从title属性获取完整标题（如果有）
                    if title_link.get('title'):
                        data['title'] = title_link.get('title').strip()

        # 如果还没有标题，尝试其他方式
        if not data['title']:
            # 查找任何包含标题文本的元素
            possible_title = item.find(
                class_=lambda x: x and any(word in x for word in ['title', 'head', 'name']) if x else False)
            if possible_title and possible_title.get_text().strip():
                data['title'] = possible_title.get_text().strip()

        # 提取作者信息
        author_links = item.find_all('a', href=lambda x: x and '/user-profile/' in x if x else False)
        for author_link in author_links:
            author_name_elem = author_link.find('span')
            if author_name_elem:
                data['author'] = author_name_elem.get_text().strip()
                break

            # 如果没有span，直接获取链接文本
            if not data['author'] and author_link.get_text().strip():
                data['author'] = author_link.get_text().strip()

        # 提取作者头像
        avatar_div = item.find('div', class_='base-avatar')
        if avatar_div:
            img = avatar_div.find('img')
            if img and img.get('src'):
                data['author_avatar'] = urljoin(self.base_url, img['src'])
            else:
                # 处理文字头像的情况
                name_avatar = avatar_div.find('div', class_='name-avatar')
                if name_avatar:
                    data['author_avatar'] = f"文字头像: {name_avatar.get_text().strip()}"

        # 提取标签
        tags_section = item.find('div', class_='tags')
        if tags_section:
            tag_links = tags_section.find_all('a', href=lambda x: x and '/tag/' in x if x else False)
            for tag_link in tag_links:
                tag_text = tag_link.get_text().strip()
                # 移除开头的#号
                if tag_text.startswith('#'):
                    tag_text = tag_text[1:].strip()
                if tag_text and tag_text not in data['tags']:
                    data['tags'].append(tag_text)

        # 专门从缩略图区域提取图片 - 修复版本
        img_url = self._extract_image_from_item(item, index)
        if img_url:
            data['image_url'] = img_url
            print(f"✅ 第 {index + 1} 篇文章图片: {img_url[:50]}...")
        else:
            print(f"❌ 第 {index + 1} 篇文章未找到图片URL")

        # 提取统计数据
        self._extract_stats(item, data)

    def _extract_image_from_item(self, item, index):
        """从文章项中提取图片URL"""
        # 方法1: 查找缩略图区域
        thumb_section = item.find('div', class_='list-group__thumb')
        if thumb_section:
            print(f"🔍 第 {index + 1} 项: 找到缩略图区域，尝试提取图片...")
            img_url = self._extract_image_url(thumb_section)
            if img_url:
                return img_url

        # 方法2: 直接在整个项目内查找图片
        all_imgs = item.find_all('img')
        if all_imgs:
            print(f"🔍 第 {index + 1} 项: 找到 {len(all_imgs)} 个图片，尝试提取...")
            for img in all_imgs:
                # 优先检查src属性
                if img.get('src'):
                    img_url = urljoin(self.base_url, img['src'])
                    # 检查是否是有效的图片URL
                    if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        return img_url

                # 检查data-src等延迟加载属性
                for attr in ['data-src', 'data-original', 'data-lazy-src', 'data-url']:
                    if img.get(attr):
                        img_url = urljoin(self.base_url, img[attr])
                        if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                            return img_url

        # 方法3: 使用DrissionPage直接查找当前项的图片
        print(f"🔍 第 {index + 1} 项: 尝试使用DrissionPage查找图片...")
        img_url = self._extract_image_with_drissionpage(index)
        if img_url:
            return img_url

        return None

    def _extract_image_url(self, thumb_section):
        """从缩略图区域提取图片URL"""
        # 方法1: 查找img标签
        img = thumb_section.find('img')
        if img:
            print(f"📷 找到img标签，属性: {list(img.attrs.keys())}")
            # 优先检查src属性
            if img.get('src'):
                img_url = urljoin(self.base_url, img['src'])
                if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    return img_url

            # 方法2: 查找data-src等延迟加载属性
            for attr in ['data-src', 'data-original', 'data-lazy-src', 'data-url']:
                if img.get(attr):
                    print(f"📷 从{attr}属性找到图片")
                    img_url = urljoin(self.base_url, img[attr])
                    if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        return img_url

        # 方法3: 查找背景图片
        style = thumb_section.get('style', '')
        if 'background-image' in style:
            import re
            bg_match = re.search(r'background-image\s*:\s*url\(["\']?(.*?)["\']?\)', style)
            if bg_match:
                print("📷 从background-image找到图片")
                img_url = urljoin(self.base_url, bg_match.group(1))
                if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    return img_url

        # 方法4: 查找子元素中的图片
        all_imgs = thumb_section.find_all('img')
        for img in all_imgs:
            for attr in ['src', 'data-src', 'data-original']:
                if img.get(attr):
                    print(f"📷 从子元素{attr}属性找到图片")
                    img_url = urljoin(self.base_url, img[attr])
                    if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        return img_url

        return None

    def _extract_image_with_drissionpage(self, index):
        """使用DrissionPage直接查找特定索引的图片元素"""
        try:
            # 找到所有文章项
            print(f"🔍 DrissionPage查找第 {index + 1} 个文章项的图片...")
            # 使用CSS选择器查找元素
            items = self.page.eles('tag:li')
            if not items:
                # 尝试其他选择器
                items = self.page.eles('.list-group-item') or self.page.eles('.card')

            if index < len(items):
                item_element = items[index]

                # 将该元素滚动到视图中，确保图片加载
                self.scroll_element_into_view(item_element)

                # 在该项中查找图片
                imgs = item_element.eles('tag:img')
                print(f"📷 在第 {index + 1} 项中找到 {len(imgs)} 个图片")

                for i, img in enumerate(imgs):
                    # 检查src属性
                    img_src = img.attr('src')
                    if img_src and any(ext in img_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        print(f"✅ 从第 {index + 1} 项的第 {i + 1} 个图片找到src: {img_src[:50]}...")
                        return urljoin(self.base_url, img_src)

                    # 检查data-src等属性
                    for attr in ['data-src', 'data-original', 'data-lazy-src']:
                        data_src = img.attr(attr)
                        if data_src and any(
                                ext in data_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                            print(f"✅ 从第 {index + 1} 项的第 {i + 1} 个图片的{attr}属性找到: {data_src[:50]}...")
                            return urljoin(self.base_url, data_src)
            else:
                print(f"❌ 索引{index}超出范围，共{len(items)}个元素")

        except Exception as e:
            print(f"❌ DrissionPage提取第 {index + 1} 项图片失败: {e}")

        return None

    def _extract_stats(self, item, data):
        """提取统计数据"""
        # 查找所有可能的统计容器
        meta_containers = [
            item.find('div', class_='card-meta'),
            item.find('div', class_='meta'),
            item.find('div', class_='stats'),
        ]

        for meta_container in meta_containers:
            if not meta_container:
                continue

            meta_items = meta_container.find_all('div', class_='meta-item')
            for meta_item in meta_items:
                self._parse_meta_item(meta_item, data)

    def _parse_meta_item(self, meta_item, data):
        """解析单个统计项"""
        spans = meta_item.find_all('span')
        if len(spans) >= 2:
            value = spans[-1].get_text().strip()  # 最后一个span通常是数值
            icon_span = spans[0]
            icon_class = icon_span.get('class', [])

            if any('dianzan' in cls for cls in icon_class) or '赞' in icon_span.get_text():  # 点赞
                data['stats']['likes'] = self._parse_number(value)
            elif any('pinglun' in cls for cls in icon_class) or '评论' in icon_span.get_text():  # 评论
                data['stats']['comments'] = self._parse_number(value)
            elif any('yuedu' in cls for cls in icon_class) or '阅读' in icon_span.get_text():  # 阅读
                data['stats']['views'] = self._parse_number(value)
            elif any('shijian' in cls for cls in icon_class) or '时间' in icon_span.get_text():  # 时间
                data['stats']['publish_date'] = value

    def _parse_number(self, text):
        """解析数字文本"""
        try:
            # 移除逗号等非数字字符
            cleaned = ''.join(filter(str.isdigit, text))
            return int(cleaned) if cleaned else 0
        except:
            return 0

    def print_results(self, results):
        """打印采集结果到控制台"""
        print(f"\n{'=' * 80}")
        print(f"采集结果汇总 - 共 {len(results)} 篇文章")
        print(f"{'=' * 80}")

        for article in results:
            time.sleep(2)  # 减少延迟
            stats = article['stats']
            obj = {
                'title': article['title'],
                'image_url': article['image_url'],
                'tag': article['tags'],
                'author': article.get('author', '未知'),
                'author_avatar': article['author_avatar'],
                'article_url': article['article_url'],
                'views': stats['views'],
                'created_at': stats['publish_date']
            }

            res = CafeSDK.Result.push_data(obj)
            print("push_data resp:", res.code, res.message)

            print(f"\n📖 第 {article['index']} 篇文章")
            print(f"  标题: {article['title']}")
            print(f"  作者: {article.get('author', '未知')}")

            if article.get('author_avatar'):
                if '文字头像' in article['author_avatar']:
                    print(f"  头像: {article['author_avatar']}")
                else:
                    print(f"  头像: {article['author_avatar'][:50]}...")

            if article.get('article_url'):
                print(f"  链接: {article['article_url']}")

            if article.get('image_url'):
                print(f"  图片: {article['image_url'][:50]}...")
            else:
                print(f"  图片: 未找到")

            if article['tags']:
                print(f"  标签: {', '.join(article['tags'])}")

            stats_text = []
            if stats['likes'] > 0:
                stats_text.append(f"👍 {stats['likes']}")
            if stats['comments'] > 0:
                stats_text.append(f"💬 {stats['comments']}")
            if stats['views'] > 0:
                stats_text.append(f"👀 {stats['views']}")
            if stats['publish_date']:
                stats_text.append(f"📅 {stats['publish_date']}")

            if stats_text:
                print(f"  统计: {' | '.join(stats_text)}")

            print(f"  {'─' * 50}")

    def save_results(self, results, filename='cafehook_articles.json'):
        """保存采集结果到JSON文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 数据已保存到 {filename}")
        except Exception as e:
            print(f"\n❌ 保存文件失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 CafeHook 文章采集器 - DrissionPage 版本 (支持懒加载)")
    print("=" * 60)

    scraper = None
    try:
        scraper = CafeHookScraper()
        input_json_dict = CafeSDK.Parameter.get_input_json_dict()
        # 从网站采集数据
        results = scraper.scrape_article_list(input_json_dict['url'])

        # 设置表头（如果使用SDK）
        headers = [
            {
                "label": "标题",
                "key": "title",
                "format": "text",
            }, {
                "label": "缩略图",
                "key": "image_url",
                "format": "image",
            }, {
                "label": "标签",
                "key": "tag",
                "format": "array",
            }, {
                "label": "作者",
                "key": "author",
                "format": "text",
            }, {
                "label": "头像",
                "key": "author_avatar",
                "format": "image",
            }, {
                "label": "链接",
                "key": "article_url",
                "format": "link",
            }, {
                "label": "浏览数",
                "key": "views",
                "format": "number",
            }, {
                "label": "发布时间",
                "key": "created_at",
                "format": "text",
            },
        ]
        res = CafeSDK.Result.set_table_header(headers)
        print("push_data resp:", res.code, res.message)

        if results:
            # 打印结果到控制台
            scraper.print_results(results)

            # 保存结果到文件
            scraper.save_results(results)

            print(f"\n🎉 采集完成！共采集到 {len(results)} 篇文章")

            # 统计图片采集情况
            images_found = sum(1 for article in results if article.get('image_url'))
            print(f"📊 图片采集统计: {images_found}/{len(results)} 篇文章成功采集到图片")
        else:
            print("\n❌ 未采集到任何数据")
            print("💡 建议检查：")
            print("   1. 网络连接是否正常")
            print("   2. 网站结构是否变化")
            print("   3. 查看生成的 page_source.html 和截图文件")

    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 确保浏览器被关闭
        if scraper and hasattr(scraper, 'page'):
            print("\n🔄 清理资源...")
            scraper.page.quit()
            print("✅ 浏览器已关闭")


if __name__ == "__main__":
    main()
