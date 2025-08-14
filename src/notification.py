"""
通知模块 - 发送分析结果通知
"""
import os
import json
import requests
import smtplib
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from email.mime.base import MIMEBase as MimeBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .utils.logger import log_info, log_warning, log_error, log_debug
from .config import NOTIFICATION_CONFIG

class NotificationManager:
    """通知管理器"""

    def __init__(self):
        self.config = NOTIFICATION_CONFIG

    def send_completion_notification(self, status: str, analysis_summary: Dict = None):
        """发送任务完成通知"""
        try:
            # 准备通知内容
            title = self._generate_title(status)
            content = self._generate_content(status, analysis_summary)

            # 发送各种类型的通知
            if self.config['telegram']['enabled']:
                self._send_telegram_notification(title, content)

            if self.config['email']['enabled']:
                self._send_email_notification(title, content, analysis_summary)

            if self.config['webhook']['enabled']:
                self._send_webhook_notification(title, content, analysis_summary)

            log_info("任务完成通知发送成功")

        except Exception as e:
            log_error(f"发送通知失败: {e}")

    def _generate_title(self, status: str) -> str:
        """生成通知标题"""
        status_map = {
            'success': '✅ 基金分析任务完成',
            'failure': '❌ 基金分析任务失败',
            'partial': '⚠️ 基金分析部分完成'
        }

        return status_map.get(status, '📊 基金分析任务状态更新')

    def _generate_content(self, status: str, analysis_summary: Dict = None) -> str:
        """生成通知内容"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        content = f"""
📊 **基金分析系统通知**

⏰ **时间**: {current_time}
📈 **状态**: {self._get_status_emoji(status)} {status.upper()}

"""

        if analysis_summary:
            content += f"""
📋 **分析摘要**:
• 总基金数: {analysis_summary.get('total_funds', 0)}
• 成功分析: {analysis_summary.get('successful_analyses', 0)}
• 失败分析: {analysis_summary.get('failed_analyses', 0)}
• 生成报告: {analysis_summary.get('reports_generated', 0)}

🎯 **重点关注**:
"""

            # 添加重点基金信息
            featured_funds = analysis_summary.get('featured_funds', [])
            if featured_funds:
                for fund in featured_funds[:5]:  # 只显示前5个
                    signal = fund.get('signal_type', '持有')
                    confidence = fund.get('confidence', 0)
                    fund_name = fund.get('fund_name', '')
                    content += f"• {fund_name}: {signal} (置信度: {confidence:.1%})\n"

            content += f"""

📊 **市场概况**:
• 平均技术得分: {analysis_summary.get('avg_technical_score', 50):.1f}/100
• 平均基本面得分: {analysis_summary.get('avg_fundamental_score', 50):.1f}/100
• 买入信号数量: {analysis_summary.get('buy_signals', 0)}
• 卖出信号数量: {analysis_summary.get('sell_signals', 0)}

📁 **报告位置**: reports/
🔗 **GitHub仓库**: {os.getenv('GITHUB_REPOSITORY', 'Unknown')}
"""

        return content

    def _get_status_emoji(self, status: str) -> str:
        """获取状态表情符号"""
        emoji_map = {
            'success': '✅',
            'failure': '❌',
            'partial': '⚠️',
            'running': '🔄',
            'pending': '⏳'
        }
        return emoji_map.get(status, '📊')

    def _send_telegram_notification(self, title: str, content: str):
        """发送Telegram通知"""
        try:
            bot_token = self.config['telegram']['bot_token']
            chat_id = self.config['telegram']['chat_id']

            if not bot_token or not chat_id:
                log_warning("Telegram配置不完整，跳过通知")
                return

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            message = f"{title}\n\n{content}"

            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }

            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()

            log_info("Telegram通知发送成功")

        except Exception as e:
            log_error(f"Telegram通知发送失败: {e}")

    def _send_email_notification(self, title: str, content: str, analysis_summary: Dict = None):
        """发送邮件通知"""
        try:
            smtp_server = self.config['email']['smtp_server']
            smtp_port = self.config['email']['smtp_port']
            username = self.config['email']['username']
            password = self.config['email']['password']
            recipients = self.config['email']['recipients']

            if not all([smtp_server, username, password, recipients]):
                log_warning("邮件配置不完整，跳过通知")
                return

            # 创建邮件
            msg = MimeMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = title

            # HTML格式的邮件内容
            html_content = self._generate_html_email_content(title, content, analysis_summary)
            msg.attach(MimeText(html_content, 'html', 'utf-8'))

            # 附加报告文件
            self._attach_report_files(msg)

            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)

            log_info("邮件通知发送成功")

        except Exception as e:
            log_error(f"邮件通知发送失败: {e}")

    def _generate_html_email_content(self, title: str, content: str, analysis_summary: Dict = None) -> str:
        """生成HTML格式的邮件内容"""
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .summary-item {{ text-align: center; padding: 15px; background-color: #f8f9fa; border-radius: 8px; }}
        .summary-item .number {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .summary-item .label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .fund-list {{ margin: 20px 0; }}
        .fund-item {{ padding: 10px; margin: 5px 0; background-color: #f8f9fa; border-left: 4px solid #667eea; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #666; }}
        .status-success {{ color: #28a745; }}
        .status-failure {{ color: #dc3545; }}
        .status-partial {{ color: #ffc107; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>基金分析系统自动生成 • {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</p>
        </div>

        <div class="content">
            <pre style="white-space: pre-wrap; font-family: inherit;">{content}</pre>
        </div>
"""

        # 添加分析摘要图表
        if analysis_summary:
            html_template += f"""
        <div class="summary">
            <div class="summary-item">
                <div class="number">{analysis_summary.get('total_funds', 0)}</div>
                <div class="label">总基金数</div>
            </div>
            <div class="summary-item">
                <div class="number">{analysis_summary.get('successful_analyses', 0)}</div>
                <div class="label">成功分析</div>
            </div>
            <div class="summary-item">
                <div class="number">{analysis_summary.get('reports_generated', 0)}</div>
                <div class="label">生成报告</div>
            </div>
            <div class="summary-item">
                <div class="number">{analysis_summary.get('buy_signals', 0)}</div>
                <div class="label">买入信号</div>
            </div>
        </div>
"""

        html_template += """
        <div class="footer">
            <p>此邮件由基金分析系统自动发送，请勿回复</p>
            <p>如有问题，请查看GitHub仓库或系统日志</p>
        </div>
    </div>
</body>
</html>
"""

        return html_template

    def _attach_report_files(self, msg: MimeMultipart):
        """附加报告文件到邮件"""
        try:
            reports_dir = Path('reports')

            # 查找最新的报告文件
            report_files = []

            # 查找markdown报告
            markdown_files = list(reports_dir.glob('*.md'))
            if markdown_files:
                latest_md = max(markdown_files, key=lambda x: x.stat().st_mtime)
                report_files.append(latest_md)

            # 查找市场总结
            summary_files = list(reports_dir.glob('market_summary_*.json'))
            if summary_files:
                latest_summary = max(summary_files, key=lambda x: x.stat().st_mtime)
                report_files.append(latest_summary)

            # 限制附件数量和大小
            for file_path in report_files[:3]:  # 最多3个文件
                if file_path.stat().st_size < 5 * 1024 * 1024:  # 小于5MB
                    with open(file_path, 'rb') as f:
                        part = MimeBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {file_path.name}'
                        )
                        msg.attach(part)

        except Exception as e:
            log_warning(f"附加报告文件失败: {e}")

    def _send_webhook_notification(self, title: str, content: str, analysis_summary: Dict = None):
        """发送Webhook通知"""
        try:
            webhook_url = self.config['webhook']['url']
            headers = self.config['webhook']['headers'] or {}

            if not webhook_url:
                log_warning("Webhook URL未配置，跳过通知")
                return

            # 准备payload
            payload = {
                'title': title,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'summary': analysis_summary or {}
            }

            # 设置默认headers
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'

            response = requests.post(
                webhook_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            log_info("Webhook通知发送成功")

        except Exception as e:
            log_error(f"Webhook通知发送失败: {e}")

def send_notification(status: str, analysis_summary: Dict = None):
    """发送通知的便捷函数"""
    try:
        notification_manager = NotificationManager()
        notification_manager.send_completion_notification(status, analysis_summary)
    except Exception as e:
        log_error(f"通知发送失败: {e}")

if __name__ == "__main__":
    # 测试通知功能
    import sys

    if len(sys.argv) > 1:
        status = sys.argv[1]
    else:
        status = "success"

    # 模拟分析摘要
    test_summary = {
        'total_funds': 100,
        'successful_analyses': 95,
        'failed_analyses': 5,
        'reports_generated': 10,
        'buy_signals': 15,
        'sell_signals': 8,
        'avg_technical_score': 65.5,
        'avg_fundamental_score': 72.3,
        'featured_funds': [
            {
                'fund_name': '易方达蓝筹精选混合',
                'signal_type': '买入',
                'confidence': 0.85
            },
            {
                'fund_name': '华夏成长混合',
                'signal_type': '强烈买入',
                'confidence': 0.92
            }
        ]
    }

    send_notification(status, test_summary)
    print(f"测试通知已发送，状态: {status}")
