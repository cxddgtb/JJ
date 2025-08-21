import os
from datetime import datetime
import pytz
from github import Github
import google.generativeai as genai

# --- 配置 ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
REPO_ACCESS_TOKEN = os.environ.get('REPO_ACCESS_TOKEN')
REPO_NAME = os.environ.get('GITHUB_REPOSITORY')

genai.configure(api_key=GEMINI_API_KEY)

def generate_and_polish_article(analysis_content):
    """
    使用Gemini生成初稿，并进行二次润色。
    """
    try:
        model = genai.GenerativeModel('gemini-pro')

        # 1. 生成文章初稿
        prompt_generate = f"""
        根据以下市场分析报告，撰写一篇面向基金投资社区的专业文章。
        文章需要包括：
        1. 一个吸引人的标题。
        2. 市场概览：简述当前市场情况和主要新闻。
        3. 核心观点：清晰地阐述报告中的买卖建议。
        4. 论据支撑：结合报告中的新闻和数据，详细解释做出该建议的原因。
        5. 风险提示：提醒投资者注意潜在风险。

        **分析报告原文:**
        ---
        {analysis_content}
        ---
        """
        print("正在生成文章初稿...")
        draft_response = model.generate_content(prompt_generate)
        draft_article = draft_response.text

        # 2. 润色文章
        prompt_polish = f"""
        请将以下文章进行润色，使其语言更流畅、更具吸引力，更适合在投资者社区发表。
        注意：保持核心观点和论据不变，主要优化语言表达和排版结构。

        **文章草稿:**
        ---
        {draft_article}
        ---
        """
        print("正在润色文章...")
        polished_response = model.generate_content(prompt_polish)
        return polished_response.text

    except Exception as e:
        print(f"调用Gemini API生成文章时出错: {e}")
        return "文章生成失败。"

def commit_to_repo(article_content, repo_name, token):
    """
    将生成的文章提交到GitHub仓库。
    """
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # 使用北京时间命名文件
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today_str = datetime.now(beijing_tz).strftime('%Y-%m-%d')
        file_path = f'articles/{today_str}-基金操作分析.md'
        
        commit_message = f"自动生成文章：{today_str} 基金分析报告"

        # 检查文件是否存在，如果存在则更新，否则创建
        try:
            contents = repo.get_contents(file_path, ref="main")
            repo.update_file(contents.path, commit_message, article_content, contents.sha, branch="main")
            print(f"成功更新文件: {file_path}")
        except Exception:
            repo.create_file(file_path, commit_message, article_content, branch="main")
            print(f"成功创建文件: {file_path}")

    except Exception as e:
        print(f"提交到GitHub仓库时出错: {e}")

if __name__ == "__main__":
    try:
        with open("analysis_result.txt", "r", encoding="utf-8") as f:
            analysis = f.read()
    except FileNotFoundError:
        print("错误：未找到分析结果文件 'analysis_result.txt'。")
        exit(1)

    final_article = generate_and_polish_article(analysis)
    
    print("\n--- 最终生成的文章 ---\n")
    print(final_article)
    print("\n----------------------\n")

    if not REPO_ACCESS_TOKEN or not REPO_NAME:
        print("未配置REPO_ACCESS_TOKEN或GITHUB_REPOSITORY，跳过自动提交。")
    else:
        commit_to_repo(final_article, REPO_NAME, REPO_ACCESS_TOKEN)
