import os
import json
import google.generativeai as genai

# 从环境变量中获取API密钥
API_KEY = os.environ.get('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("未找到GEMINI_API_KEY！请在GitHub Secrets中设置。")

genai.configure(api_key=API_KEY)

def analyze_market_data(data):
    """
    调用Gemini AI分析市场数据并生成买卖点建议。
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # 精心设计的Prompt，引导AI进行专业分析
        prompt = f"""
        作为一名专业的基金经理，请基于以下全网搜集的最新新闻资讯和市场指标，为我提供一份关于当前基金市场的买卖点分析报告。

        ### **市场新闻摘要:**
        {json.dumps(data.get('news', []), ensure_ascii=False, indent=2)}

        ### **关键指标数据:**
        {json.dumps(data.get('indicators', []), ensure_ascii=False, indent=2)}

        ### **你的任务:**
        1.  **市场情绪分析**: 综合所有新闻，判断当前市场的整体情绪是“乐观”、“悲观”还是“中性”。
        2.  **关键事件解读**: 识别出可能对市场产生重大影响的关键新闻或政策，并简要解读其潜在影响。
        3.  **买卖点判断**: 结合市场情绪和关键事件，给出明确的买卖点建议。请说明是“积极买入”、“谨慎建仓”、“持仓观望”、“减仓卖出”还是“清仓离场”。
        4.  **核心逻辑阐述**: 详细说明你做出该判断的核心原因，并引用具体的新闻或数据作为论据。
        5.  **格式化输出**: 请以简洁、专业的格式返回你的分析结果。
        """

        print("正在向Gemini发送请求进行分析...")
        response = model.generate_content(prompt)
        print("已收到Gemini的分析结果。")
        return response.text

    except Exception as e:
        print(f"调用Gemini API时出错: {e}")
        return "AI分析失败，请检查API密钥或网络连接。"

if __name__ == "__main__":
    # 读取爬虫收集的数据
    try:
        with open("collected_data.json", "r", encoding="utf-8") as f:
            market_data = json.load(f)
    except FileNotFoundError:
        print("错误：未找到数据文件 'collected_data.json'。")
        exit(1)

    # 获取AI分析结果
    analysis_result = analyze_market_data(market_data)

    # 保存分析结果
    with open("analysis_result.txt", "w", encoding="utf-8") as f:
        f.write(analysis_result)
    
    print("AI分析报告已生成并保存到 analysis_result.txt。")
