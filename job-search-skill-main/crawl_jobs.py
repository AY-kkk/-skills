import os
import time
import re
import argparse
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright

# ================= 配置区 =================
# 默认配置
BROWSER_PATH = None
USER_DATA_DIR = os.path.join(os.getcwd(), "user_data")
OUTPUT_FILE = "job_info.xlsx"
KEYWORDS = []
AUTO_MODE = True
MAX_PAGES = 20

# ================= 辅助函数 =================

def parse_salary(salary_text):
    """
    解析薪资文本，返回最低薪资数值（用于排序）。
    """
    if not salary_text or "面议" in salary_text:
        return 999999
    
    try:
        match = re.search(r'(\d+)', salary_text)
        if match:
            num = int(match.group(1))
            if 'k' in salary_text.lower():
                return num * 1000
            if '万' in salary_text or 'w' in salary_text.lower():
                return num * 10000
            return num
    except:
        pass
    return 999999

def extract_sentence(text, keyword):
    """
    提取包含关键词的完整句子。
    """
    if not text:
        return ""
    sentences = re.split(r'[。！？\n]', text)
    found_sentences = []
    for s in sentences:
        if keyword in s:
            found_sentences.append(s.strip())
    return " | ".join(found_sentences)

# ================= 策略基类 =================

class SiteStrategy:
    def __init__(self, page):
        self.page = page
        self.site_name = "Unknown"

    def navigate_home(self):
        """导航到首页/搜索页"""
        raise NotImplementedError

    def search(self, keywords):
        """执行搜索"""
        raise NotImplementedError

    def get_job_links(self, seen_links):
        """获取当前页的职位链接"""
        raise NotImplementedError

    def extract_job_detail(self, page, url):
        """在详情页提取信息"""
        raise NotImplementedError

    def next_page(self):
        """翻页操作"""
        raise NotImplementedError

# ================= 猎聘策略 =================

class LiepinStrategy(SiteStrategy):
    def __init__(self, page):
        super().__init__(page)
        self.site_name = "猎聘"

    def navigate_home(self):
        print("正在打开猎聘搜索页...")
        self.page.goto("https://www.liepin.com/zhaopin/")

    def search(self, keywords):
        # 猎聘通常需要手动输入或URL参数，这里假设用户手动或脚本辅助
        print(f"请在搜索框输入关键词：{' '.join(keywords)}")
        # 尝试自动输入（如果选择器匹配）
        try:
            input_box = self.page.locator("input[data-selector='search-input']")
            if input_box.count() > 0:
                input_box.fill(" ".join(keywords))
                self.page.locator(".search-btn").click()
                self.page.wait_for_load_state("networkidle")
        except:
            pass
        print("请确保职位列表已加载...")

    def get_job_links(self, seen_links):
        page_links = []
        # 兼容多种选择器
        job_card_selectors = [".job-list-item", ".job-card-pc-container", "[data-selector='job-card']", ".job-detail-box"]
        
        all_cards = []
        for sel in job_card_selectors:
            cards = self.page.locator(sel)
            if cards.count() > 0:
                for i in range(cards.count()):
                    all_cards.append(cards.nth(i))
                break

        print(f"找到 {len(all_cards)} 个职位卡片")
        for card in all_cards:
            try:
                link = card.locator("a[href*='/job/']").first
                if link.count() == 0:
                    link = card.locator("a").first
                if link.count() == 0: continue
                
                url = link.get_attribute("href")
                if not url: continue
                
                if url.startswith("//"): url = f"https:{url}"
                elif url.startswith("/"): url = f"https://www.liepin.com{url}"
                
                if "/job/" in url and url not in seen_links and url not in page_links:
                    page_links.append(url)
            except:
                pass
        return page_links

    def extract_job_detail(self, page, url):
        # 提取逻辑
        jd_content = ""
        selectors = [".job-intro-content", "section.job-intro", ".content-content", "[data-selector='job-intro-content']", ".job-item-container", ".job-description"]
        for sel in selectors:
            if page.locator(sel).count() > 0:
                jd_content = page.locator(sel).first.text_content()
                break
        
        # 薪资
        salary = "面议"
        header_area = page.locator(".job-apply-container, .job-title-box, .name-box").first
        if header_area.count() > 0:
            match = re.search(r'(\d+-\d+[kK万]|面议)', header_area.text_content())
            if match: salary = match.group(1)
        
        # 公司
        company = "未知公司"
        company_selectors = [".company-info-container .company-name", ".title-info h3 a", ".job-company-name", ".company-card .name"]
        for sel in company_selectors:
            el = page.locator(sel).first
            if el.count() > 0 and el.text_content().strip():
                company = el.text_content().strip()
                break

        # 地点
        area = "未知地点"
        area_el = page.locator(".job-dq, .job-area, .job-properties span").first
        if area_el.count() > 0:
            area = area_el.text_content()

        return {
            "公司名称": company,
            "职位介绍": jd_content,
            "薪资": salary,
            "工作地点": area,
            "职位链接": url
        }

    def next_page(self):
        try:
            next_btn = self.page.locator(".ant-pagination-next:not([aria-disabled='true'])")
            if next_btn.count() > 0:
                next_btn.click()
                return True
        except:
            pass
        return False

# ================= Boss直聘策略 =================

class BossStrategy(SiteStrategy):
    def __init__(self, page):
        super().__init__(page)
        self.site_name = "Boss直聘"

    def navigate_home(self):
        print("正在打开Boss直聘...")
        self.page.goto("https://www.zhipin.com/")

    def search(self, keywords):
        print(f"请在搜索框输入关键词：{' '.join(keywords)}")
        try:
            # Boss直聘搜索框通常是 .ipt-search
            input_box = self.page.locator(".ipt-search").first
            search_btn = self.page.locator("button.btn-search").first
            
            if input_box.count() > 0:
                input_box.fill(" ".join(keywords))
                search_btn.click()
                self.page.wait_for_load_state("networkidle")
            else:
                # 可能是新版或者已经在搜索页
                print("未找到搜索框，请手动搜索...")
        except:
            pass
        print("请确保职位列表已加载...")

    def get_job_links(self, seen_links):
        page_links = []
        # Boss列表页卡片
        cards = self.page.locator(".job-card-wrapper")
        print(f"找到 {cards.count()} 个职位卡片")
        
        for i in range(cards.count()):
            try:
                card = cards.nth(i)
                # 链接通常在 .job-card-body > a 或者 .job-card-left
                link = card.locator("a.job-card-left").first
                if link.count() == 0:
                    link = card.locator("a[href*='/job_detail/']").first
                
                if link.count() > 0:
                    url = link.get_attribute("href")
                    if url:
                        if url.startswith("/"): url = f"https://www.zhipin.com{url}"
                        if url not in seen_links and url not in page_links:
                            page_links.append(url)
            except:
                pass
        return page_links

    def extract_job_detail(self, page, url):
        # Boss详情页提取
        jd_content = ""
        # 详情内容
        jd_el = page.locator(".job-sec-text").first
        if jd_el.count() > 0:
            jd_content = jd_el.text_content()

        # 薪资
        salary = "面议"
        salary_el = page.locator(".salary").first
        if salary_el.count() > 0:
            salary = salary_el.text_content()

        # 公司
        company = "未知公司"
        company_el = page.locator(".company-info a[ka='job-detail-company_custompage']").first
        if company_el.count() == 0:
            company_el = page.locator(".business-info h4").first # 侧边栏
        if company_el.count() > 0:
            company = company_el.text_content().strip()

        # 地点
        area = "未知地点"
        area_el = page.locator(".text-desc.text-city").first
        if area_el.count() == 0:
            area_el = page.locator(".location-address").first
        if area_el.count() > 0:
            area = area_el.text_content()

        return {
            "公司名称": company,
            "职位介绍": jd_content,
            "薪资": salary,
            "工作地点": area,
            "职位链接": url
        }

    def next_page(self):
        try:
            # Boss翻页按钮 .ui-icon-arrow-right
            next_btn = self.page.locator(".options-pages a.next").first
            if next_btn.count() > 0 and "disabled" not in next_btn.get_attribute("class", ""):
                next_btn.click()
                return True
        except:
            pass
        return False

# ================= 智联招聘策略 =================

class ZhaopinStrategy(SiteStrategy):
    def __init__(self, page):
        super().__init__(page)
        self.site_name = "智联招聘"

    def navigate_home(self):
        print("正在打开智联招聘...")
        self.page.goto("https://sou.zhaopin.com/")

    def search(self, keywords):
        print(f"请在搜索框输入关键词：{' '.join(keywords)}")
        try:
            # 智联搜索框
            input_box = self.page.locator(".search-box__input").first
            search_btn = self.page.locator(".search-box__button").first
            
            if input_box.count() > 0:
                input_box.fill(" ".join(keywords))
                search_btn.click()
                self.page.wait_for_load_state("networkidle")
        except:
            pass

    def get_job_links(self, seen_links):
        page_links = []
        # 智联列表
        cards = self.page.locator(".joblist-box__item")
        print(f"找到 {cards.count()} 个职位卡片")
        
        for i in range(cards.count()):
            try:
                card = cards.nth(i)
                link = card.locator(".jobinfo__name a").first
                if link.count() > 0:
                    url = link.get_attribute("href")
                    if url and url not in seen_links and url not in page_links:
                        page_links.append(url)
            except:
                pass
        return page_links

    def extract_job_detail(self, page, url):
        # 智联详情
        jd_content = ""
        # 描述
        jd_el = page.locator(".describtion__detail-content").first
        if jd_el.count() > 0:
            jd_content = jd_el.text_content()

        # 薪资
        salary = "面议"
        salary_el = page.locator(".summary-plane__salary").first
        if salary_el.count() > 0:
            salary = salary_el.text_content()

        # 公司
        company = "未知公司"
        company_el = page.locator(".company-name").first
        if company_el.count() > 0:
            company = company_el.text_content().strip()

        # 地点
        area = "未知地点"
        area_el = page.locator(".summary-plane__info-box .summary-plane__info-text").first
        if area_el.count() > 0:
            area = area_el.text_content()

        return {
            "公司名称": company,
            "职位介绍": jd_content,
            "薪资": salary,
            "工作地点": area,
            "职位链接": url
        }

    def next_page(self):
        try:
            # 智联翻页
            next_btn = self.page.locator(".soupager__btn:has-text('下一页')").first
            if next_btn.count() > 0:
                next_btn.click()
                return True
        except:
            pass
        return False

# ================= 主程序 =================

def main():
    global KEYWORDS, OUTPUT_FILE, BROWSER_PATH

    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="通用职位爬虫工具 (支持猎聘/Boss/智联)")
    parser.add_argument("--browser-path", help="浏览器可执行文件路径", default=BROWSER_PATH)
    parser.add_argument("--keywords", help="搜索关键词 (逗号分隔)", default="")
    parser.add_argument("--output", help="输出文件名", default=OUTPUT_FILE)
    parser.add_argument("--site", help="目标网站", choices=["liepin", "boss", "zhaopin"], default="liepin")
    parser.add_argument("--session", help="会话ID (用于区分不同用户数据)", default="default")
    parser.add_argument("--headless", help="是否使用无头模式 (不显示浏览器窗口)", action="store_true")

    args = parser.parse_args()
    
    # 2. 处理配置
    if args.browser_path: BROWSER_PATH = args.browser_path
    if args.keywords: KEYWORDS = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if args.output != OUTPUT_FILE: OUTPUT_FILE = args.output
    
    # 设置用户数据目录
    USER_DATA_DIR = os.path.join(os.getcwd(), "user_data", args.session)

        
    # 3. 交互式询问
    if not KEYWORDS:
        print("请输入要搜索的职位关键词 (多个关键词用空格分隔):")
        try:
            k_input = input(">>> ").strip()
            if k_input: KEYWORDS = k_input.split()
            else: print("未输入关键词，默认搜索全部。")
        except: pass
            
    print(f"=== 通用职位爬虫 ===")
    print(f"目标网站: {args.site}")
    print(f"关键词: {KEYWORDS}")
    print(f"输出文件: {OUTPUT_FILE}")
    
    if BROWSER_PATH and not os.path.exists(BROWSER_PATH):
        print(f"错误: 找不到浏览器: {BROWSER_PATH}")
        return

    # 准备数据容器
    all_data = []
    seen_links = set()

    with sync_playwright() as p:
        print("正在启动浏览器...")
        launch_args = {
            "user_data_dir": USER_DATA_DIR,
            "headless": args.headless,
            "args": ["--start-maximized", "--no-default-browser-check"],
            "ignore_default_args": ["--enable-automation"]
        }
        if BROWSER_PATH: launch_args["executable_path"] = BROWSER_PATH

        try:
            # 尝试启动持久化上下文
            if args.headless:
                 # 无头模式下通常更稳定
                 context = p.chromium.launch_persistent_context(**launch_args)
            else:
                 # 有头模式下，尝试先launch browser再new context，或者直接launch_persistent
                 # 为了避免某些系统上 persistent context 卡死，这里做一个兼容
                 context = p.chromium.launch_persistent_context(**launch_args)
                 
        except Exception as e:
            print(f"启动失败: {e}，尝试备用模式...")
            browser_launch_args = {"headless": args.headless, "args": ["--no-default-browser-check"]}
            if BROWSER_PATH: browser_launch_args["executable_path"] = BROWSER_PATH
            browser = p.chromium.launch(**browser_launch_args)
            context = browser.new_context()
        
        page = context.pages[0] if context.pages else context.new_page()
        
        # 选择策略
        strategy_map = {
            "liepin": LiepinStrategy,
            "boss": BossStrategy,
            "zhaopin": ZhaopinStrategy
        }
        strategy = strategy_map[args.site](page)
        
        # 执行流程
        strategy.navigate_home()
        
        # 自动执行搜索（如果有关键词）
        if KEYWORDS:
            strategy.search(KEYWORDS)
        
        print("\n" + "="*50)
        print("【等待用户操作】")
        print("1. 请确保已登录（如果不登录，部分网站无法查看更多职位）。")
        print("2. 如遇验证码，请手动在浏览器中完成验证。")
        print("3. 确认搜索关键词及筛选条件（城市/薪资等）是否正确。")
        print("4. 确保职位列表已加载完毕。")
        print("="*50 + "\n")
        
        # 强制等待用户确认
        input(">>> 请在浏览器中完成登录/验证/筛选后，按 Enter 键开始抓取...")
        
        # 再次激活当前页面，确保它是活动状态
        page.bring_to_front()
        
        page_index = 0
        while True:
            # 自动模式或手动模式控制
            if not AUTO_MODE:
                action = input(">>> 按 Enter 抓取当前页，输入 'n' 翻页，'q' 结束: ").strip().lower()
                if action == 'q': break
                if action == 'n':
                    if strategy.next_page():
                        print("已翻页，等待加载...")
                        page.wait_for_timeout(3000)
                    else:
                        print("翻页失败或已到末页")
                    continue
            else:
                if MAX_PAGES > 0 and page_index >= MAX_PAGES: break

            print(f"正在解析第 {page_index + 1} 页...")
            
            # 1. 获取链接
            links = strategy.get_job_links(seen_links)
            if not links:
                print("未找到职位链接，请检查页面是否加载或尝试手动滚动。")
                # 尝试保存源码
                # with open("debug_source.html", "w") as f: f.write(page.content())
                
                # 如果是第一页就没找到链接，可能是因为页面还没刷新，或者还在加载
                if page_index == 0:
                     print("可能是页面未刷新，尝试刷新页面...")
                     page.reload()
                     page.wait_for_load_state("networkidle")
                     # 再次尝试获取
                     links = strategy.get_job_links(seen_links)
                
                if not links:
                    if AUTO_MODE:
                        print("自动模式下未找到链接，尝试翻页...")
                        if not strategy.next_page(): break
                        page.wait_for_timeout(3000)
                        page_index += 1
                        continue
            
            # 2. 遍历链接
            for i, url in enumerate(links):
                print(f"[{i+1}/{len(links)}] 正在查看: {url[:60]}...")
                new_page = context.new_page()
                try:
                    new_page.goto(url, wait_until="domcontentloaded")
                    # 随机延时
                    time.sleep(2)
                    
                    # 提取详情
                    item = strategy.extract_job_detail(new_page, url)
                    item["抓取时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    item["_sort_salary"] = parse_salary(item["薪资"])
                    
                    # 提取关键词上下文
                    matched_sentences = []
                    for kw in KEYWORDS:
                        s = extract_sentence(item["职位介绍"], kw)
                        if s: matched_sentences.append(f"[{kw}]: {s}")
                    if matched_sentences:
                        item["关键词上下文"] = " | ".join(matched_sentences)
                    
                    all_data.append(item)
                    seen_links.add(url)
                    print(f"  [√] 已收录: {item['公司名称']}")
                    
                except Exception as e:
                    print(f"  [!] 失败: {e}")
                finally:
                    new_page.close()
                    time.sleep(1) # 防封控
            
            # 3. 翻页
            if AUTO_MODE:
                print("尝试自动翻页...")
                if strategy.next_page():
                    page.wait_for_timeout(3000)
                    page_index += 1
                else:
                    print("无法翻页，停止。")
                    break
            
            # 实时保存
            save_to_excel(all_data)

    print("\n所有任务完成。")

def save_to_excel(data):
    if not data: return
    df = pd.DataFrame(data)
    df = df.sort_values(by=["公司名称", "_sort_salary"], ascending=[True, True])
    output_df = df.drop(columns=["_sort_salary"])
    output_df = output_df.drop_duplicates(subset=["公司名称", "职位链接"])
    try:
        output_df.to_excel(OUTPUT_FILE, index=False, sheet_name="Jobs")
        print(f"已保存 {len(output_df)} 条数据到 {OUTPUT_FILE}")
    except Exception as e:
        print(f"保存 Excel 失败: {e}")

if __name__ == "__main__":
    main()
