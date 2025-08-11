from fpdf import FPDF
import matplotlib.pyplot as plt
from datetime import datetime
from config import settings
from .utils import save_data, setup_logging

logger = setup_logging()

class TradingReportGenerator:
    def __init__(self, combined_signals):
        self.signals = combined_signals
        self.trading_date = datetime.now().strftime('%Y-%m-%d')
        
    def generate_pdf_report(self):
        """生成PDF格式的报告"""
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # 标题
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt=f"交易信号分析报告 - {self.trading_date}", ln=True, align='C')
            pdf.ln(10)
            
            # 市场趋势
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="市场整体趋势分析", ln=True)
            pdf.set_font("Arial", size=12)
            
            mt = self.signals['market_trend']
            pdf.multi_cell(0, 8, f"市场强度指数: {mt['market_strength']}\n市场情绪: {mt['market_sentiment']}")
            pdf.ln(5)
            
            # 添加图表
            if 'chart_path' in self.signals and self.signals['chart_path']:
                pdf.image(self.signals['chart_path'], x=10, y=pdf.get_y(), w=180)
                pdf.ln(90)
            
            # 股票推荐
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="股票交易推荐", ln=True)
            pdf.set_font("Arial", size=12)
            
            rec = self.signals['recommendations']
            pdf.cell(200, 10, txt="推荐买入股票:", ln=True)
            for stock in rec['top_buy_stocks']:
                pdf.multi_cell(0, 8, f"{stock['code']} - RSI: {stock['rsi']:.2f}, MACD: {stock['macd_hist']:.4f}")
            
            pdf.ln(5)
            pdf.cell(200, 10, txt="推荐卖出股票:", ln=True)
            for stock in rec['top_sell_stocks']:
                pdf.multi_cell(0, 8, f"{stock['code']} - RSI: {stock['rsi']:.2f}, MACD: {stock['macd_hist']:.4f}")
            
            # 基金推荐
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="基金交易推荐", ln=True)
            pdf.set_font("Arial", size=12)
            
            pdf.cell(200, 10, txt="推荐买入基金:", ln=True)
            for fund in rec['top_buy_funds']:
                pdf.multi_cell(0, 8, f"{fund['name']} ({fund['code']}) - 净值: {fund['net_value']:.4f}, 日涨幅: {fund['daily_return']:.2f}%")
            
            pdf.ln(5)
            pdf.cell(200, 10, txt="推荐卖出基金:", ln=True)
            for fund in rec['top_sell_funds']:
                pdf.multi_cell(0, 8, f"{fund['name']} ({fund['code']}) - 净值: {fund['net_value']:.4f}, 日涨幅: {fund['daily_return']:.2f}%")
            
            # 保存报告
            report_path = save_data(pdf.output(dest='S').encode('latin1'), "trading_report.pdf")
            return report_path
        except Exception as e:
            logger.exception("生成PDF报告失败")
            return None
            
    def send_email_report(self, report_path):
        """发送邮件报告"""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.application import MIMEApplication
            
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_USER
            msg['To'] = settings.EMAIL_RECEIVER
            msg['Subject'] = f"交易信号分析报告 - {self.trading_date}"
            
            # 邮件正文
            body = f"交易信号分析报告已生成，请查看附件。\n\n市场情绪: {self.signals['market_trend']['market_sentiment']}"
            msg.attach(MIMEText(body, 'plain'))
            
            # 添加附件
            with open(report_path, 'rb') as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header('Content-Disposition', 'attachment', filename=f"trading_report_{self.trading_date}.pdf")
                msg.attach(attach)
            
            # 发送邮件
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                server.starttls()
                server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
                server.send_message(msg)
                
            logger.info(f"报告邮件已发送至 {settings.EMAIL_RECEIVER}")
            return True
        except Exception as e:
            logger.exception("发送邮件报告失败")
            return False
            
    def run(self):
        """生成并发送报告"""
        logger.info("开始生成交易报告")
        
        if settings.REPORT_FORMAT == "pdf":
            report_path = self.generate_pdf_report()
        else:
            logger.error(f"不支持的报告格式: {settings.REPORT_FORMAT}")
            return False
            
        if not report_path:
            logger.error("报告生成失败")
            return False
            
        # 发送邮件
        if self.send_email_report(report_path):
            logger.info("报告发送成功")
            return True
        return False
